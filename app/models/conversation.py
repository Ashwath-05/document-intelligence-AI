"""ORM model for the conversations table.

Same pattern as Document/Chunk: a Python class mapped to a table, Alembic
reads it via Base.metadata to generate the migration.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.document import Document

from app.core.database import Base


class Conversation(Base):
    """One multi-turn chat thread.

    document_id is nullable and set once, at creation -- from the first
    request's document_id if one was given. Every later turn in this
    conversation reuses it automatically (see ConversationService), so the
    caller doesn't have to keep resending it. No user_id yet: same "add it
    when auth actually lands" reasoning Document used for Phase 0.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ondelete="SET NULL", not CASCADE -- deleting a document shouldn't
    # silently delete someone's chat transcript about it; the conversation
    # just loses its document scope and search falls back to "all
    # documents" for any further turns.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    document: Mapped["Document | None"] = relationship("Document", lazy="joined")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} document_id={self.document_id}>"
