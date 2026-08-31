"""The Document table -- your schema design from Phase 2's planning step,
translated into SQLAlchemy.

This IS the schema in your codebase; Alembic reads this file (via
Base.metadata) to know what table to create. Change a column here, generate
a new migration -- the model and the real database schema are meant to
never drift apart.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    """The complete, fixed set of states a document can be in.

    Inheriting from `str` as well as `Enum` means DocumentStatus.UPLOADED
    behaves as the plain string "uploaded" wherever a string is expected
    (JSON serialization, SQL parameters) while still giving IDE autocomplete
    and a typo-proof reference everywhere in Python code.

    This Python-level set and the CheckConstraint below enforce the same
    four values in two places on purpose: Python catches a typo the moment
    you write the code; the database constraint catches it even if some
    other tool or a raw SQL script tries to write bad data directly.
    """

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    """One uploaded document and its processing state.

    No user_id, no chunks relationship, no question history -- matches the
    Phase 0 MVP scope exactly. Multi-document support, chunks, and auth
    each add columns/tables in their own later phase, not now.
    """

    __tablename__ = "documents"
    __table_args__ = (
        # Derived from DocumentStatus, not retyped -- one enum, one
        # constraint, impossible for them to drift out of sync.
        CheckConstraint(
            "status IN ({})".format(
                ", ".join(f"'{s.value}'" for s in DocumentStatus)
            ),
            name="ck_documents_status_valid",
        ),
    )

    # UUID primary key, not an auto-incrementing integer: unguessable
    # (nobody can probe /documents/2 after seeing /documents/1), and
    # generated client-side without a round trip to learn what ID a new
    # row got.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Pointer to the actual PDF bytes in Supabase Storage -- this table
    # never stores the file itself, only where to find it.
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Nullable because these don't exist yet at upload time -- they're
    # filled in by later processing steps (Phase 4 extraction, Phase 9
    # summarization). A NOT NULL constraint here would make the very first
    # insert impossible.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DocumentStatus.UPLOADED.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # onupdate runs on every UPDATE, not just insert -- this is what makes
    # updated_at actually track "last modified" instead of duplicating
    # created_at forever.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r} status={self.status!r}>"
