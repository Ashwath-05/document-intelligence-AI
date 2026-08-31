"""ORM model for the chunks table.

Same pattern as Document (Phase 2): a Python class mapped to a table,
Alembic reads it via Base.metadata to generate the migration.
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.document import Document

from app.core.database import Base


class Chunk(Base):
    """A single chunk of a document's extracted text."""

    __tablename__ = "chunks"
    __table_args__ = (
        # Makes it impossible to insert two chunks claiming the same
        # position within the same document -- database-enforced, same
        # philosophy as the status CheckConstraint on documents (Phase 2).
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ondelete="CASCADE": when a document is deleted, Postgres itself
    # deletes its chunks automatically -- enforced at the database level,
    # not left to application code to remember to do.
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # NOT NULL, not nullable-then-backfilled: embeddings are generated
    # eagerly, in one batch, right before chunk rows are ever inserted (see
    # document_service.py) -- there's no point in this pipeline where a
    # chunk row exists without its embedding already computed, so the
    # database can enforce that as a hard guarantee, not just a convention.
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)

    # lazy="joined": search results always need the parent document's
    # filename (see search_service.py), so SQLAlchemy JOINs it into the same
    # query automatically instead of issuing a separate query per chunk
    # (the classic N+1 problem -- 5 search results would otherwise mean
    # 1 query for chunks + 5 more for their documents).
    document: Mapped["Document"] = relationship("Document", lazy="joined")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} document_id={self.document_id} index={self.chunk_index}>"
