"""Semantic search: embed a query, retrieve the closest chunks.

This is the payoff of Phases 5-6 -- chunking and embedding existed purely
to make this possible. Everything up to here was preparation.
"""

from uuid import UUID

from app.providers.embedding.base import EmbeddingProvider
from app.repositories.chunk_repository import ChunkRepository


class SearchService:
    def __init__(self, chunk_repository: ChunkRepository, embedding_provider: EmbeddingProvider):
        self.chunk_repository = chunk_repository
        self.embedding_provider = embedding_provider

    def search(
        self, query: str, document_id: UUID | None = None, top_k: int = 5
    ) -> list[tuple]:
        """Embed the query the same way chunks were embedded, then find the
        closest ones. Same model, same vector space -- a query embedded with
        a different model wouldn't be comparable to these vectors at all.
        """
        query_embedding = self.embedding_provider.embed([query])[0]
        return self.chunk_repository.search_similar(
            query_embedding, top_k=top_k, document_id=document_id
        )