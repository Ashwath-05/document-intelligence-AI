"""Contracts for the RAG answer-generation API."""

from uuid import UUID

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    question: str = Field(min_length=1, description="Natural-language question to answer.")
    document_id: UUID | None = Field(
        default=None,
        description="Restrict retrieval to one document. Omit to search across all.",
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of chunks to retrieve as context."
    )


class GenerationSourceItem(BaseModel):
    model_config = {"from_attributes": True}

    chunk_id: UUID
    document_id: UUID
    filename: str
    chunk_index: int
    text: str
    distance: float = Field(description="Cosine distance -- lower means more relevant.")


class GenerationResponse(BaseModel):
    question: str
    answer: str
    sources: list[GenerationSourceItem]
