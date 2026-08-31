"""Multi-turn conversation: reformulate follow-ups into standalone search
queries, generate a grounded answer with real conversation context, and
persist both turns.

Built on top of GenerationService (Phase 8) rather than duplicating its
retrieval/threshold/citation logic -- this only adds what's genuinely new
for multi-turn: query reformulation and persistence. See
GenerationService.answer's docstring for how search_query and history
plug into the Phase 8 machinery underneath.
"""

from uuid import UUID

from app.core.config import Settings
from app.models.conversation import Conversation
from app.models.message import MessageRole
from app.providers.llm.base import LLMProvider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.generation_service import GenerationService

REFORMULATION_SYSTEM_PROMPT = (
    "Rewrite the user's latest message as a standalone question that makes "
    "sense with no prior context, incorporating anything it implicitly "
    "relies on from the conversation history. Output ONLY the rewritten "
    "question -- no preamble, no quotes, no explanation. If the message is "
    "already standalone, return it unchanged."
)


class ConversationNotFoundError(Exception):
    pass


class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        generation_service: GenerationService,
        llm_provider: LLMProvider,
        settings: Settings,
    ):
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.generation_service = generation_service
        self.llm_provider = llm_provider
        self.settings = settings

    async def ask(
        self,
        question: str,
        conversation_id: UUID | None = None,
        document_id: UUID | None = None,
        top_k: int = 5,
    ) -> dict:
        conversation = self._get_or_create_conversation(conversation_id, document_id)

        history = self.message_repository.list_by_conversation(conversation.id)
        # Bound how far back we look -- unbounded history means every turn
        # makes the next prompt (and its cost) a little bigger forever, with
        # no ceiling. Windowing to the last N messages is the simple first
        # mitigation; summarising older turns instead of dropping them is
        # the natural next step once N stops being enough, not something
        # this phase needs yet.
        windowed = history[-self.settings.chat_history_window :]
        history_dicts = [{"role": m.role, "content": m.content} for m in windowed]

        # Reformulation costs a real LLM call, so skip it entirely on a
        # conversation's first turn -- there's no prior context to condense
        # against, and the question is already standalone by definition.
        search_query = question
        if history_dicts:
            search_query = await self._reformulate(question, history_dicts)

        # conversation.document_id, not the request's document_id -- a
        # conversation's scope is fixed at creation (see
        # _get_or_create_conversation); later turns can't silently
        # re-scope it to a different document.
        result = await self.generation_service.answer(
            question,
            document_id=conversation.document_id,
            top_k=top_k,
            search_query=search_query,
            history=history_dicts,
        )

        # Persisted only after a successful answer -- a failed generation
        # (LLMGenerationError, see below) leaves no dangling user question
        # with no reply sitting in the transcript to confuse the next
        # turn's reformulation.
        self.message_repository.create(conversation.id, MessageRole.USER, question)
        self.message_repository.create(
            conversation.id, MessageRole.ASSISTANT, result["answer"]
        )
        # Marks this conversation as the thing that just happened -- see
        # ConversationRepository.touch's docstring for why this call has to
        # be explicit.
        self.conversation_repository.touch(conversation.id)

        return {
            "conversation_id": conversation.id,
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
        }

    def _get_or_create_conversation(
        self, conversation_id: UUID | None, document_id: UUID | None
    ) -> Conversation:
        if conversation_id is None:
            return self.conversation_repository.create(document_id=document_id)

        conversation = self.conversation_repository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"No conversation found with id={conversation_id}"
            )
        return conversation

    async def _reformulate(self, question: str, history: list[dict[str, str]]) -> str:
        response = await self.llm_provider.generate(
            question,
            system_prompt=REFORMULATION_SYSTEM_PROMPT,
            history=history,
            temperature=0.0,  # deterministic rewriting, not creative
        )
        return response.text.strip()

    def get_conversation(self, conversation_id: UUID) -> tuple[Conversation, list]:
        """One conversation plus its full transcript, oldest message first.

        Not async, unlike ask() -- this is plain DB reads, no LLM call
        involved, so the route calling this stays a `def` (see
        conversations.py) and gets FastAPI's automatic threadpool offload
        instead of an event loop held open for nothing.
        """
        conversation = self.conversation_repository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"No conversation found with id={conversation_id}"
            )
        messages = self.message_repository.list_by_conversation(conversation_id)
        return conversation, messages

    def list_conversations(
        self,
        document_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """Most recently active conversations first -- see
        ConversationRepository.list_all/touch for what keeps that ordering
        actually meaningful.
        """
        return self.conversation_repository.list_all(document_id, limit, offset)
