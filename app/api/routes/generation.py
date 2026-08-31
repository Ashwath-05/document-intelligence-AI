"""RAG answer-generation endpoint.

`async def`, unlike documents.py/search.py's `def` routes -- this route's
work includes a real network call to Groq (see LLMProvider.generate's
docstring for why that's async), not just blocking DB/file I/O that
FastAPI's threadpool already handles for a plain `def` route.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.embedding.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from app.providers.llm.base import LLMGenerationError
from app.providers.llm.groq_provider import GroqProvider
from app.repositories.chunk_repository import ChunkRepository
from app.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationSourceItem,
)
from app.services.generation_service import GenerationService
from app.services.search_service import SearchService

router = APIRouter(prefix="/generate", tags=["generation"])


def get_generation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GenerationService:
    """Assemble a GenerationService for this request.

    Same Depends(...) chain shape as get_document_service/get_search_service
    -- built here, not inside the service, so GenerationService itself never
    imports a concrete provider (see providers/llm/base.py).
    """
    chunk_repository = ChunkRepository(db)
    embedding_provider = SentenceTransformerProvider()
    search_service = SearchService(chunk_repository, embedding_provider)
    llm_provider = GroqProvider(settings)
    return GenerationService(search_service, llm_provider, settings)


@router.post("", response_model=GenerationResponse)
async def generate_answer(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationResponse:
    try:
        result = await service.answer(request.question, request.document_id, request.top_k)
    except LLMGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return GenerationResponse(
        question=request.question,
        answer=result["answer"],
        sources=[GenerationSourceItem(**s) for s in result["sources"]],
    )
