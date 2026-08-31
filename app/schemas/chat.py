"""Contracts for the multi-turn conversation API."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.generation import GenerationSourceItem


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, description="The user's message.")
    conversation_id: UUID | None = Field(
        default=None,
        description=(
            "Continue an existing conversation. Omit to start a new one -- "
            "the response returns the new conversation_id to use on "
            "subsequent turns."
        ),
    )
    document_id: UUID | None = Field(
        default=None,
        description=(
            "Restrict retrieval to one document. Only used when STARTING a "
            "new conversation (conversation_id omitted) -- once a "
            "conversation exists its document scope is fixed, and this "
            "field is ignored on later turns."
        ),
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of chunks to retrieve as context."
    )


class ChatResponse(BaseModel):
    conversation_id: UUID
    question: str
    answer: str
    sources: list[GenerationSourceItem]
