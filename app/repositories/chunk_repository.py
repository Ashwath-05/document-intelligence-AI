"""Data access for the chunks table."""

from uuid import UUID

from sqlalchemy.orm import Session

from typing import Optional

from app.models.chunk import Chunk


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, document_id: UUID, chunks: list[dict]) -> list[Chunk]:
        """Bulk-insert chunks for a document in one transaction.

        add_all + one commit, not one create() call per chunk -- a document
        might produce dozens of chunks, and committing once per chunk would
        mean dozens of round trips to Postgres for what's logically one
        operation: "store this document's chunks."
        """
        objects = [
            Chunk(
                document_id=document_id,
                text=c["text"],
                chunk_index=c["chunk_index"],
                token_count=c["token_count"],
                embedding=c["embedding"],
            )
            for c in chunks
        ]
        self.db.add_all(objects)
        self.db.commit()
        for obj in objects:
            self.db.refresh(obj)
        return objects

    def get_by_document_id(self, document_id: UUID) -> list[Chunk]:
        return (
            self.db.query(Chunk)
            .filter(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .all()
        )

    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: Optional[UUID] = None,
    ) -> list[tuple[Chunk, float]]:
        """Return the top_k chunks closest to query_embedding, with their
        distance, ordered nearest-first.

        Chunk.embedding.cosine_distance(...) is pgvector's SQLAlchemy
        comparator -- it compiles to the same <=> operator we used by hand
        in Supabase's SQL editor, so this is the exact query we already
        verified manually, now callable from the app. The HNSW index (see
        the migration) is what keeps this fast as the chunks table grows;
        without it, this becomes a full table scan on every search.
        """
        distance = Chunk.embedding.cosine_distance(query_embedding)
        query = self.db.query(Chunk, distance.label("distance"))
        if document_id is not None:
            query = query.filter(Chunk.document_id == document_id)
        query = query.order_by(distance).limit(top_k)
        return query.all()
