"""Embedding provider contract.

Same seam as LLMProvider (Phase 1): services depend on this interface, never
on a concrete implementation. Swapping this local model for an API-based
provider later means a new class here, not a rewrite of anything that calls it.
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, one vector per text, same order in/out.

        Batched deliberately -- embedding all of a document's chunks in one
        call is cheaper and faster than looping over them individually, true
        for both API-based providers and local models like this one.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Vector length this provider produces. Must match the DB column."""
        raise NotImplementedError
