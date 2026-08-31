"""Contracts for the conversation history API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessageItem(BaseModel):
    model_config = {"from_attributes": True}

    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    document_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageItem]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    limit: int
    offset: int
