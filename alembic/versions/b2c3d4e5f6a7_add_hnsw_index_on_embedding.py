"""add hnsw index on chunks.embedding

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-22

HNSW over IVFFlat: no training step, no "how many lists" tuning, and better
recall/latency for most workloads at our scale. vector_cosine_ops matches
the <=> operator we use everywhere -- the index only gets used if the query
distance function matches the operator class it was built with.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
