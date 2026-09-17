"""Central configuration loaded from environment variables / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    DATA_DIR: Path = Path("data")
    CHROMA_DIR: Path = Path("data/chroma")
    GRAPH_PATH: Path = Path("data/knowledge_graph.json")
    SQLITE_PATH: Path = Path("data/postmortem.db")

    # Model names
    PRIMARY_MODEL: str = "llama-3.1-8b-instant"
    FALLBACK_MODEL: str = "mixtral-8x7b-32768"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Rate limiting
    GROQ_RPM: int = 30
    GROQ_RETRY_ATTEMPTS: int = 3

    # Retrieval settings
    VECTOR_TOP_K: int = 5
    GRAPH_MAX_HOPS: int = 2
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # API keys (optional at import time — required only when calling Groq)
    GROQ_API_KEY: str = ""


settings = Settings()
