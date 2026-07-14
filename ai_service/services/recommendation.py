"""Product recommendation engine based on embedding similarity.

Encodes the query product and compares it against all indexed products
in the vector store.  Returns the most similar products above the
configured similarity threshold.
"""

from __future__ import annotations

from typing import List, Optional

from ai_service.config.settings import get_settings
from ai_service.models.request import RecommendRequest
from ai_service.models.response import RecommendResponse, RecommendedProduct
from ai_service.rag.embedding import EmbeddingService
from ai_service.rag.retriever import Retriever
from ai_service.utils.logger import logger


class RecommendationEngine:
    """Recommend similar products via embedding similarity.

    The engine requires a pre-populated :class:`Retriever` (with product
    data already ingested).  A "product description" string is built from
    the request, embedded, and compared against the vector store.

    Parameters
    ----------
    retriever : Retriever
        Pre-populated retriever with the product catalogue.
    embedding_service : EmbeddingService, optional
        Injected embedding service.
    """

    def __init__(
        self,
        retriever: Retriever,
        embedding_service: Optional[EmbeddingService] = None,
    ) -> None:
        self._retriever = retriever
        self._embedder = embedding_service or EmbeddingService()
        self._settings = get_settings()

    # ------------------------------------------------------------------
    def recommend(self, request: RecommendRequest) -> RecommendResponse:
        """Find products similar to the given product.

        Parameters
        ----------
        request : RecommendRequest
            Product info and the desired number of recommendations.

        Returns
        -------
        RecommendResponse
            Ranked list of recommended products.
        """
        logger.info(
            "RecommendationEngine | product='{}' top_n={}",
            request.product_name,
            request.top_n,
        )

        # 1. Build a descriptive query string
        query_text = self._build_query_text(request)

        # 2. Embed the query
        query_vec = self._embedder.encode(query_text)

        # 3. Search the vector store (fetch more than top_n so we can filter)
        results = self._retriever.store.search(
            query_vec,
            top_k=request.top_n * 2,
        )

        # 4. Filter by threshold & deduplicate
        seen: set[str] = set()
        recommendations: List[RecommendedProduct] = []

        for text, score, _ in results:
            if len(recommendations) >= request.top_n:
                break
            if score < self._settings.SIMILARITY_THRESHOLD:
                continue
            # Use first line as product name proxy
            name = text.split("\n")[0] if text else "未知产品"
            if name in seen:
                continue
            seen.add(name)
            recommendations.append(
                RecommendedProduct(
                    product_name=name,
                    similarity_score=round(float(score), 4),
                )
            )

        logger.info("RecommendationEngine done | {} recommendations", len(recommendations))
        return RecommendResponse(recommendations=recommendations)

    # ------------------------------------------------------------------
    @staticmethod
    def _build_query_text(request: RecommendRequest) -> str:
        """Build a dense query string from request fields.

        Parameters
        ----------
        request : RecommendRequest
            Input product data.

        Returns
        -------
        str
            Human-readable query embedding input.
        """
        parts = [
            f"产品名称：{request.product_name}",
            f"产品特点：{request.features}",
            f"产品类目：{request.category}",
        ]
        return "\n".join(parts)
