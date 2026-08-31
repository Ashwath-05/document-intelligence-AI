"""ORM model for the messages table.

Same pattern as Document/Chunk/Conversation: a Python class mapped to a
table, Alembic reads it via Base.metadata to generate the migration.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MessageRole(str, enum.Enum):
    """The complete, fixed set of speakers in a conversation.

    Same str+Enum double-duty as DocumentStatus (see document.py): behaves
    as a plain string wherever one's expected, while the CheckConstraint
    below enforces the same two values at the database level too.
    """

    USER = "user"
    ASSISTANT = "assistant"


class Message(Base):
    """One turn in a conversation -- either what the user asked, or what
    the assistant answered.

    Stores the ORIGINAL question the user typed, never the LLM-reformulated
    standalone version ConversationService generates for retrieval -- that
    reformulation is a search-quality tool, not something either party
    actually said, and persisting it would falsify the transcript.
    """

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ({})".format(", ".join(f"'{r.value}'" for r in MessageRole)),
            name="ck_messages_role_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ondelete="CASCADE": deleting a conversation deletes its messages,
    # same enforced-at-the-database-level reasoning as Chunk -> Document.
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Short fixed-set string, same String(20) choice as Document.status.
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} conversation_id={self.conversation_id} role={self.role!r}>"
