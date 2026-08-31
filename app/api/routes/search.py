"""Semantic search endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.providers.embedding.sentence_transformer_provider import (
    SentenceTransformerProvider,
)
from app.repositories.chunk_repository import ChunkRepository
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    chunk_repository = ChunkRepository(db)
    embedding_provider = SentenceTransformerProvider()
    return SearchService(chunk_repository, embedding_provider)


@router.post("", response_model=SearchResponse)
def search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    results = service.search(request.query, request.document_id, request.top_k)
    return SearchResponse(
        query=request.query,
        results=[
            SearchResultItem(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=chunk.document.filename,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                distance=distance,
            )
            for chunk, distance in results
        ],
    )
