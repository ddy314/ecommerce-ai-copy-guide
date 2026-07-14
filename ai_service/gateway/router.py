"""FastAPI router — all AI service endpoints.

Wires Pydantic request/response models to the business services.  Endpoints
are self-documenting via FastAPI's auto-generated OpenAPI schema.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from ai_service.llm.dispatcher import LLMDispatcher
from ai_service.models.request import (
    ChatRequest,
    DescriptionRequest,
    LivestreamRequest,
    RecommendRequest,
    SentimentRequest,
    TitleRequest,
)
from ai_service.models.response import (
    ChatResponse,
    DescriptionResponse,
    ErrorResponse,
    LivestreamResponse,
    RecommendResponse,
    SentimentResponse,
    TitleResponse,
)
from ai_service.rag.embedding import EmbeddingService
from ai_service.rag.retriever import Retriever
from ai_service.services.copywriting import DescriptionGenerator, TitleGenerator
from ai_service.services.livestream import LivestreamScriptGenerator
from ai_service.services.qa import ShoppingAssistant
from ai_service.services.recommendation import RecommendationEngine
from ai_service.services.sentiment import SentimentAnalyser
from ai_service.utils.logger import logger
from ai_service.utils.prompt_loader import PromptLoader

# ---------------------------------------------------------------------------
# Module-level singletons (lazy-initialised)
# ---------------------------------------------------------------------------

_router = APIRouter(prefix="/api/v1", tags=["AI Services"])

_dispatcher: LLMDispatcher | None = None
_embedder: EmbeddingService | None = None
_retriever: Retriever | None = None
_prompt_loader: PromptLoader | None = None


def _get_dispatcher() -> LLMDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = LLMDispatcher()
    return _dispatcher


def _get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(embedding_service=_get_embedder())
    return _retriever


def _get_prompt_loader() -> PromptLoader:
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


# ======================================================================
# Endpoints
# ======================================================================

# -- Ingestion (utility) ------------------------------------------------

@_router.post(
    "/ingest",
    response_model=Dict[str, Any],
    summary="Ingest product data into the RAG knowledge base",
)
def ingest_products(
    products: List[Dict[str, Any]],
    retriever: Retriever = Depends(_get_retriever),
) -> Dict[str, Any]:
    """Load a list of product dicts into the vector store for RAG."""
    try:
        count = retriever.ingest(products, save=True)
        return {"status": "ok", "chunks_indexed": count}
    except Exception as exc:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- 1. Product Title ---------------------------------------------------

@_router.post(
    "/title",
    response_model=TitleResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate 5 optimised product titles",
)
def generate_titles(
    body: TitleRequest,
    dispatcher: LLMDispatcher = Depends(_get_dispatcher),
    loader: PromptLoader = Depends(_get_prompt_loader),
) -> TitleResponse:
    """Generate five SEO-friendly product titles."""
    try:
        svc = TitleGenerator(dispatcher=dispatcher, prompt_loader=loader)
        return svc.generate(body)
    except Exception as exc:
        logger.exception("Title generation failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- 2. Product Description ---------------------------------------------

@_router.post(
    "/description",
    response_model=DescriptionResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate a professional product description",
)
def generate_description(
    body: DescriptionRequest,
    dispatcher: LLMDispatcher = Depends(_get_dispatcher),
    loader: PromptLoader = Depends(_get_prompt_loader),
) -> DescriptionResponse:
    """Generate a Markdown-formatted product description."""
    try:
        svc = DescriptionGenerator(dispatcher=dispatcher, prompt_loader=loader)
        return svc.generate(body)
    except Exception as exc:
        logger.exception("Description generation failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- 3. Shopping Assistant (RAG) ----------------------------------------

@_router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    summary="RAG-powered intelligent shopping assistant",
)
def chat(
    body: ChatRequest,
    retriever: Retriever = Depends(_get_retriever),
    dispatcher: LLMDispatcher = Depends(_get_dispatcher),
    loader: PromptLoader = Depends(_get_prompt_loader),
) -> ChatResponse:
    """Answer a user question with RAG over the product knowledge base."""
    try:
        if not retriever.is_ready:
            raise HTTPException(
                status_code=400,
                detail="Knowledge base is empty. Call /ingest first.",
            )
        svc = ShoppingAssistant(
            retriever=retriever,
            dispatcher=dispatcher,
            prompt_loader=loader,
        )
        return svc.ask(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- 4. Sentiment Analysis ----------------------------------------------

@_router.post(
    "/sentiment",
    response_model=SentimentResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Analyse review sentiment",
)
def analyse_sentiment(
    body: SentimentRequest,
    dispatcher: LLMDispatcher = Depends(_get_dispatcher),
    loader: PromptLoader = Depends(_get_prompt_loader),
) -> SentimentResponse:
    """Analyse the sentiment of product reviews."""
    try:
        svc = SentimentAnalyser(dispatcher=dispatcher, prompt_loader=loader)
        return svc.analyse(body)
    except Exception as exc:
        logger.exception("Sentiment analysis failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- 5. Product Recommendation ------------------------------------------

@_router.post(
    "/recommend",
    response_model=RecommendResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Recommend similar products by embedding similarity",
)
def recommend_products(
    body: RecommendRequest,
    retriever: Retriever = Depends(_get_retriever),
) -> RecommendResponse:
    """Find similar products via embedding similarity."""
    try:
        if not retriever.is_ready:
            raise HTTPException(
                status_code=400,
                detail="Knowledge base is empty. Call /ingest first.",
            )
        engine = RecommendationEngine(retriever=retriever)
        return engine.recommend(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Recommendation failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- 6. Livestream Script -----------------------------------------------

@_router.post(
    "/livestream",
    response_model=LivestreamResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate a complete livestream sales script",
)
def generate_livestream(
    body: LivestreamRequest,
    dispatcher: LLMDispatcher = Depends(_get_dispatcher),
    loader: PromptLoader = Depends(_get_prompt_loader),
) -> LivestreamResponse:
    """Generate a 6-phase livestream script."""
    try:
        svc = LivestreamScriptGenerator(dispatcher=dispatcher, prompt_loader=loader)
        return svc.generate(body)
    except Exception as exc:
        logger.exception("Livestream script generation failed")
        raise HTTPException(status_code=500, detail=str(exc))


# -- Health -------------------------------------------------------------

@_router.get(
    "/health",
    summary="Health check",
)
def health() -> Dict[str, str]:
    """Return service status and provider name."""
    dispatcher = _get_dispatcher()
    retriever = _get_retriever()
    return {
        "status": "ok",
        "llm_provider": dispatcher.provider_name,
        "rag_ready": str(retriever.is_ready),
    }


# ======================================================================
# Public alias
# ======================================================================
router = _router
