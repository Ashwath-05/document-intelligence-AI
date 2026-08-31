"""RAG answer generation: retrieve relevant chunks, then ask an LLM to
answer strictly from them.

Built on top of SearchService rather than duplicating its embed-then-search
logic -- retrieval is exactly what SearchService already does (Phase 7);
this only adds a prompt and an LLM call on top of what it returns. Same
"business logic knows nothing about HTTP" boundary as every other service:
this returns plain dicts, and the route layer maps them into
GenerationResponse.
"""

import re
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.models.chunk import Chunk
from app.providers.llm.base import LLMProvider
from app.services.search_service import SearchService

NO_CONTEXT_MESSAGE = "I don't have enough information in the document to answer this."

SYSTEM_PROMPT = (
    "You are a document Q&A assistant. Answer strictly using the numbered "
    "context passages below. Cite the passages you rely on inline using "
    "their number in square brackets, e.g. [1] or [2][3]. If the context "
    f'does not contain enough information, respond with exactly: "{NO_CONTEXT_MESSAGE}"'
)

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


class GenerationService:
    def __init__(
        self,
        search_service: SearchService,
        llm_provider: LLMProvider,
        settings: Settings,
    ):
        self.search_service = search_service
        self.llm_provider = llm_provider
        self.settings = settings

    async def answer(
        self,
        question: str,
        document_id: UUID | None = None,
        top_k: int = 5,
        *,
        search_query: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict:
        """Retrieve context, then generate a grounded, cited answer.

        This method is async because generate() makes a real network call
        to Groq and must not block the event loop while waiting on it (see
        LLMProvider.generate's docstring). SearchService.search() is
        SYNCHRONOUS, though -- it's a plain SQLAlchemy query, same pattern
        as documents.py/search.py's `def` routes. Calling it directly here
        would block the event loop for the duration of that DB round trip,
        the exact bug FastAPI's threadpool offload prevents for `def`
        routes but does NOT prevent inside `async def` code. run_in_threadpool
        is the same mechanism FastAPI uses internally for that offload,
        applied explicitly since we're now inside an async function.

        search_query and history exist for Phase 9's ConversationService,
        which is the ONLY caller that ever passes them -- Phase 8's
        stateless /generate route calls this with neither, and gets
        exactly its original single-shot behaviour back, unchanged.

        search_query: what to embed and retrieve with, if different from
            `question`. Multi-turn callers pass an LLM-reformulated
            standalone version here (e.g. "What about tier targets?" ->
            "What are the tier targets for priority assignment on new
            clients?") while still answering the ORIGINAL `question` --
            retrieval needs the standalone form, but the model should
            respond to what the user actually asked, not a paraphrase of it.
        history: prior conversation turns, passed straight through to
            llm_provider.generate() as real role-tagged messages (see
            LLMProvider.generate's docstring) rather than flattened into
            the prompt text -- conversational continuity comes from the
            message array, not from string surgery on the RAG prompt.
        """
        effective_search_query = search_query or question
        results = await run_in_threadpool(
            self.search_service.search, effective_search_query, document_id, top_k
        )

        # pgvector's cosine_distance (the <=> operator) is a DISTANCE, not a
        # similarity score -- 0 means identical, larger means less alike.
        # Lower is better, which is the opposite of a 0-1 "higher is better"
        # score. Real Phase 7 testing put strong matches around 0.67 and a
        # weak one around 0.78, so rag_max_distance_threshold sits between
        # them: anything worse isn't worth sending to the LLM at all, since
        # a bad match still gets a confident-sounding answer out of it.
        if not results or results[0][1] > self.settings.rag_max_distance_threshold:
            return {"answer": NO_CONTEXT_MESSAGE, "sources": []}

        prompt = self._build_prompt(question, results)
        response = await self.llm_provider.generate(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            history=history,
            temperature=0.2,
        )

        # Only surface sources the model actually cited, not every chunk
        # retrieved -- a chunk can be retrieved (close enough to be in
        # top_k) without being what the answer is actually grounded in.
        cited_indices = {int(n) for n in _CITATION_PATTERN.findall(response.text)}
        sources = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "filename": chunk.document.filename,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "distance": distance,
            }
            for i, (chunk, distance) in enumerate(results)
            if (i + 1) in cited_indices
        ]

        return {"answer": response.text, "sources": sources}

    @staticmethod
    def _build_prompt(question: str, results: list[tuple[Chunk, float]]) -> str:
        context_blocks = "\n\n".join(
            f"[{i + 1}] {chunk.text}" for i, (chunk, _distance) in enumerate(results)
        )
        return f"Context:\n{context_blocks}\n\nQuestion: {question}\n\nAnswer:"
