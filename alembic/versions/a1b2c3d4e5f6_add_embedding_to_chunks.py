"""add embedding column to chunks

Revision ID: a1b2c3d4e5f6
Revises: 6084c9307ac2
Create Date: 2026-08-10

Written by hand rather than via autogenerate -- adding pgvector's extension
and a NOT NULL vector column is simple enough to write directly, and it
avoids relying on autogenerate to correctly detect an extension-dependent
column type it may not fully understand.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6084c9307ac2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enables Postgres's vector type and similarity operators. Supabase
    # supports this extension natively -- this just turns it on for this
    # database, a one-time step.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "chunks",
        sa.Column("embedding", Vector(384), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("chunks", "embedding")
