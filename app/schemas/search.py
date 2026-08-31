"""Contracts for the semantic search API."""

from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Natural-language search query.")
    document_id: UUID | None = Field(
        default=None,
        description="Restrict search to one document. Omit to search across all.",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to return.")


class SearchResultItem(BaseModel):
    model_config = {"from_attributes": True}

    chunk_id: UUID
    document_id: UUID
    filename: str
    chunk_index: int
    text: str
    distance: float = Field(description="Cosine distance -- lower means more relevant.")


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
