"""Application configuration loaded from environment variables.

Reads configuration from a ``.env`` file and environment variables using Pydantic
for validation. All settings are namespaced under a single :class:`Settings` class
so they can be injected via FastAPI dependency injection.

Usage::

    from config.settings import get_settings
    settings = get_settings()
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Load the .env file once at module level
# ---------------------------------------------------------------------------
load_dotenv()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Central configuration store for the AI service layer.

    Every value can be overridden via an environment variable; sensible defaults
    are provided for local development.
    """

    # -- DeepSeek / LLM ------------------------------------------------------
    DEEPSEEK_API_KEY: str = Field(
        default="",
        description="API key for the DeepSeek-compatible endpoint.",
    )
    BASE_URL: str = Field(
        default="https://api.deepseek.com",
        description="Base URL of the OpenAI-compatible API.",
    )
    MODEL_NAME: str = Field(
        default="deepseek-chat",
        description="Model identifier passed to the LLM provider.",
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for LLM calls.",
    )
    LLM_MAX_TOKENS: int = Field(
        default=2048,
        ge=1,
        description="Maximum tokens in the LLM response.",
    )
    LLM_TIMEOUT: int = Field(
        default=60,
        ge=1,
        description="HTTP timeout (seconds) for LLM API calls.",
    )
    LLM_MAX_RETRIES: int = Field(
        default=2,
        ge=0,
        description="Number of retries on transient LLM failures.",
    )

    # -- Embedding -----------------------------------------------------------
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="HuggingFace SentenceTransformer model name.",
    )
    EMBEDDING_DEVICE: str = Field(
        default="cpu",
        description="Torch device: 'cpu' or 'cuda'.",
    )

    # -- RAG / Vector Store --------------------------------------------------
    TOP_K: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Default number of chunks to retrieve from FAISS.",
    )
    CHUNK_SIZE: int = Field(
        default=512,
        ge=64,
        description="Character count per text chunk.",
    )
    CHUNK_OVERLAP: int = Field(
        default=64,
        ge=0,
        description="Character overlap between adjacent chunks.",
    )
    FAISS_INDEX_PATH: str = Field(
        default="ai_service/data/faiss_index",
        description="Directory where the FAISS index is persisted.",
    )

    # -- Similarity threshold ------------------------------------------------
    SIMILARITY_THRESHOLD: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity for recommendation matches.",
    )

    # -- Logging -------------------------------------------------------------
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Loguru log level.",
    )
    LOG_FILE: str = Field(
        default="logs/ai_service.log",
        description="Rotating log file path.",
    )
    LOG_ROTATION: str = Field(
        default="10 MB",
        description="When to rotate the log file.",
    )
    LOG_RETENTION: str = Field(
        default="7 days",
        description="How long to retain rotated logs.",
    )

    # -- Server --------------------------------------------------------------
    HOST: str = Field(default="0.0.0.0", description="Uvicorn bind address.")
    PORT: int = Field(default=8000, ge=1, le=65535, description="Uvicorn port.")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# ---------------------------------------------------------------------------
# Cached singleton (dependency-injection friendly)
# ---------------------------------------------------------------------------

@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    The ``lru_cache`` decorator ensures the ``.env`` file is parsed only once
    per process lifetime. Call this function wherever you need configuration
    instead of instantiating ``Settings`` directly.

    Returns
    -------
    Settings
        The application-wide settings object.
    """
    return Settings()
