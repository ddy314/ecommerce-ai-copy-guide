"""FastAPI application entrypoint for the AI Intelligent Service Layer.

Starts a Uvicorn server exposing the AI gateway.

Usage::

    python -m ai_service.app
    # or
    uvicorn ai_service.app:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_service.config.settings import get_settings
from ai_service.gateway.router import router
from ai_service.utils.logger import logger


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic.

    On startup:
        - Ensure the FAISS data directory exists.
        - Log configuration summary.

    On shutdown:
        - (Reserved for graceful resource cleanup.)
    """
    settings = get_settings()

    # -- ensure data directory exists ----------------------------------------
    Path(settings.FAISS_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "=" * 60 + "\n"
        "  AI Service Layer starting …\n"
        "  Model  : {} @ {}\n"
        "  Embed  : {}\n"
        "  Top-K  : {}\n"
        "  Server : {}:{}\n"
        "=".format(
            settings.MODEL_NAME,
            settings.BASE_URL,
            settings.EMBEDDING_MODEL,
            settings.TOP_K,
            settings.HOST,
            settings.PORT,
        ),
    )

    yield  # --- application runs here ---

    logger.info("AI Service Layer shutting down")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title="E-Commerce AI Copy Guide — AI Service Layer",
    description="Intelligent e-commerce assistant: title & description generation, "
    "RAG-powered Q&A, review sentiment analysis, product recommendations, "
    "and livestream script generation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Health-check at root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """Redirect to the API docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ai_service.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
