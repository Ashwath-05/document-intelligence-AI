"""Multi-turn conversation endpoint.

`async def`, same reasoning as generation.py -- real network calls to Groq,
now potentially TWO per request: query reformulation (skipped on a
conversation's first turn, see ConversationService.ask), then generation.
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
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.generation import GenerationSourceItem
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
)
from app.services.generation_service import GenerationService
from app.services.search_service import SearchService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_conversation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConversationService:
    """Assemble a ConversationService for this request.

    Same shape as get_generation_service, extended: one GroqProvider
    instance serves both the reformulation call and the final generation
    call (see ConversationService.ask), and conversation/message
    repositories are added alongside the Phase 8 pieces.
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


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> ChatResponse:
    try:
        result = await service.ask(
            request.question,
            conversation_id=request.conversation_id,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LLMGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ChatResponse(
        conversation_id=result["conversation_id"],
        question=result["question"],
        answer=result["answer"],
        sources=[GenerationSourceItem(**s) for s in result["sources"]],
    )
