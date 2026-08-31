"""Local embedding generation via Sentence Transformers.

No API key, no per-call cost, runs on CPU. 384 dimensions -- smaller than
OpenAI's 1536-dim default on purpose, since fewer dimensions means less
storage and faster similarity search through the HNSW index (Phase 7).
See the model choice comment below for why this is a retrieval-tuned model,
not a general-purpose sentence-similarity one.
"""

from functools import lru_cache

from app.providers.embedding.base import EmbeddingProvider

# Swapped from all-MiniLM-L6-v2 (Phase 6) to multi-qa-MiniLM-L6-cos-v1.
# The original is a general-purpose sentence-similarity model -- good at
# judging whether two similarly-shaped sentences mean the same thing, not
# specifically trained for ASYMMETRIC search (a short question against long
# declarative passages). multi-qa-MiniLM-L6-cos-v1 is trained on real
# question/passage pairs (MS MARCO and others) specifically for this
# "does this passage answer this question" task -- same architecture family,
# same 384 dimensions, so the schema and HNSW index don't change at all.
# The embeddings themselves DO change, though: vectors from the two models
# live in different, incompatible spaces. Anything already embedded with the
# old model must be re-embedded, not just left in place.
_MODEL_NAME = "multi-qa-MiniLM-L6-cos-v1"
_DIMENSIONS = 384


@lru_cache
def _get_model():
    """Lazily load and cache the model.

    Same reasoning as get_engine() (database.py) and _get_encoding()
    (chunking.py): importing this module, and the app booting, shouldn't
    require downloading model weights over the network -- only actually
    calling embed() should. First real call downloads ~90MB from Hugging
    Face and caches it locally; every call after that is instant, offline.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


class SentenceTransformerProvider(EmbeddingProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = _get_model().encode(texts, convert_to_numpy=False)
        return [[float(x) for x in v] for v in vectors]

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS