"""Conversation history endpoints -- list past conversations, or fetch one
with its full message transcript.

Both plain `def`, unlike chat.py -- these are blocking DB reads only, no
LLM call involved, so FastAPI's automatic threadpool offload is exactly
what's wanted here (same reasoning as documents.py/search.py), not an
event loop held open for a network round trip that never happens on
either of these two routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.embedding.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from app.providers.llm.groq_provider import GroqProvider
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.conversation import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    MessageItem,
)
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
)
from app.services.generation_service import GenerationService
from app.services.search_service import SearchService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConversationService:
    """Identical assembly to chat.py's get_conversation_service -- both
    routers share ConversationService, since history is just a read-only
    view over the same conversations/messages tables /chat writes to.
    Duplicated here rather than imported from chat.py because every route
    file in this codebase builds its own DI function independently, even
    when the construction overlaps (generation.py and chat.py both build a
    SearchService + GenerationService the same way too) -- one clear,
    predictable pattern per file beats a shared dependencies module these
    two routes would be the only users of.

    Building a GroqProvider here even though neither route below ever
    calls it isn't the waste it might look like: the constructor just
    builds an async HTTP client object, it doesn't make a network call --
    that only happens inside generate(), which these two routes never
    reach.
    """
    chunk_repository = ChunkRepository(db)
    embedding_provider = SentenceTransformerProvider()
    search_service = SearchService(chunk_repository, embedding_provider)
    llm_provider = GroqProvider(settings)
    generation_service = GenerationService(search_service, llm_provider, settings)

    conversation_repository = ConversationRepository(db)
    message_repository = MessageRepository(db)
    return ConversationService(
        conversation_repository,
        message_repository,
        generation_service,
        llm_provider,
        settings,
    )


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    document_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    conversations = service.list_conversations(document_id, limit, offset)
    return ConversationListResponse(
        conversations=[ConversationSummary.model_validate(c) for c in conversations],
        limit=limit,
        offset=offset,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    try:
        conversation, messages = service.get_conversation(conversation_id)
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ConversationDetail(
        id=conversation.id,
        document_id=conversation.document_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageItem.model_validate(m) for m in messages],
    )
