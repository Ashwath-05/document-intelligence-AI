"""Application configuration.

All config comes from environment variables (Twelve-Factor). Nothing is
hardcoded, and no secret ever lands in source control.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "AI Document Intelligence Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- LLM provider ---
    # No default -- required, same reasoning as database_url below. Before
    # Phase 8, GroqProvider didn't exist and nothing read this key, so an
    # empty default let the app boot without it. Now that GenerationService
    # actually calls Groq, a missing key should fail fast at startup, not
    # surface as a confusing 401 on the first real /generate request.
    groq_api_key: str
    llm_model: str = "openai/gpt-oss-120b"
    llm_timeout_seconds: int = 60

    # --- Database (Phase 2) ---
    # No default -- required. The database is core to everything from this
    # phase onward, so the app should refuse to start without a real
    # connection string rather than boot into a broken state.
    database_url: str
    # Logs every SQL statement SQLAlchemy generates when True. Loud, but
    # useful while learning what the ORM produces under the hood.
    db_echo: bool = False

    # --- File upload (Phase 3) ---
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    allowed_extensions: tuple[str, ...] = (".pdf",)

    # --- Chunking (Phase 5) ---
    # Lowered from 500/75 after Phase 7 testing showed large chunks blur
    # retrieval: a single chunk covering several unrelated bullet points
    # produces an embedding that's a vague average of all of them, none
    # sharply matched. Smaller chunks keep each one's embedding on-topic.
    chunk_size_tokens: int = 180
    chunk_overlap_tokens: int = 30

    # --- RAG generation (Phase 8) ---
    # pgvector's cosine_distance is a DISTANCE (0 = identical, lower =
    # closer), not a 0-1 similarity score. Set from real Phase 7 testing:
    # a strong match measured ~0.67, a weak one ~0.78 -- this sits between
    # them. A top result worse (larger) than this doesn't get sent to the
    # LLM at all; see GenerationService.answer.
    rag_max_distance_threshold: float = 0.75

    # --- Multi-turn conversation (Phase 9) ---
    # Messages, not turns -- 6 means the last 3 user/assistant exchanges.
    # A hard cap on how far back both reformulation and generation look,
    # so prompt size (and cost) stops growing once a conversation passes
    # this length instead of growing forever. Summarising older turns
    # instead of just dropping them is the natural upgrade once 6 proves
    # too short in practice.
    chat_history_window: int = 6


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()