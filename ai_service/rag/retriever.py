"""RAG Retriever — the high-level entry-point for the RAG pipeline.

Orchestrates :class:`DocumentLoader`, :class:`TextSplitter`,
:class:`EmbeddingService`, and :class:`VectorStore` so that callers only
need a single method: ``retrieve(query)`` → ``(context, sources)``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ai_service.config.settings import get_settings
from ai_service.rag.embedding import EmbeddingService
from ai_service.rag.loader import DocumentLoader, TextSplitter
from ai_service.rag.vector_store import VectorStore
from ai_service.utils.logger import logger


class Retriever:
    """High-level RAG retriever.

    Usage::

        retriever = Retriever()
        retriever.ingest(products)              # load & embed products
        context, sources = retriever.retrieve("这个手机续航如何？")
    """

    # ------------------------------------------------------------------
    def __init__(
        self,
        *,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        """Initialise the retriever.

        Parameters
        ----------
        embedding_service : EmbeddingService, optional
            Pre-built embedding service. Created on-demand if not given.
        vector_store : VectorStore, optional
            Pre-built vector store. Created on-demand during ``ingest()``.
        """
        self._settings = get_settings()
        self._loader = DocumentLoader()
        self._splitter = TextSplitter()
        self._embedder = embedding_service or EmbeddingService()
        self._store = vector_store  # set during ingest()

        logger.info("Retriever initialised")

    # ------------------------------------------------------------------
    def ingest(
        self,
        products: List[Dict[str, Any]],
        *,
        save: bool = False,
        save_path: Optional[str] = None,
    ) -> int:
        """Full ingest pipeline: load → split → embed → index.

        Parameters
        ----------
        products : list[dict]
            Product data dicts.
        save : bool
            If ``True``, persist the index to disk after ingest.
        save_path : str, optional
            Custom save directory.

        Returns
        -------
        int
            Number of chunks indexed.
        """
        logger.info("Ingest pipeline started | {} products", len(products))

        # 1. Load & flatten
        docs = self._loader.load_from_dicts(products)

        # 2. Split
        chunks = self._splitter.split(docs)

        if not chunks:
            logger.warning("Ingest produced 0 chunks — check input data")
            return 0

        # 3. Embed
        embeddings = self._embedder.encode(chunks)

        # 4. Index
        if self._store is None:
            self._store = VectorStore(dimension=self._embedder.dimension)

        self._store.add(chunks, embeddings)

        # 5. Persist (optional)
        if save:
            self._store.save(save_path)

        logger.info("Ingest complete | chunks={} total_in_store={}", len(chunks), self._store.count)
        return len(chunks)

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Retrieve context for a user query.

        Parameters
        ----------
        query : str
            Natural-language question.
        top_k : int, optional
            Number of chunks to retrieve; defaults to ``TOP_K``.

        Returns
        -------
        tuple[str, list[dict]]
            - ``context`` — concatenated text of the top chunks.
            - ``sources`` — list of ``{"text": …, "score": …}`` dicts.

        Raises
        ------
        RuntimeError
            If the store has not been populated yet.
        """
        if self._store is None or self._store.is_empty:
            raise RuntimeError(
                "VectorStore is empty — call ingest() before retrieve()"
            )

        if top_k is None:
            top_k = self._settings.TOP_K

        # 1. Embed query
        query_vec = self._embedder.encode(query)

        # 2. Search
        results = self._store.search(query_vec, top_k=top_k)

        # 3. Build context string
        context_parts: List[str] = []
        sources: List[Dict[str, Any]] = []
        for i, (text, score, _) in enumerate(results, 1):
            context_parts.append(f"[相关产品片段 {i}] (相关度: {score:.4f})\n{text}")
            sources.append({"text": text, "score": round(score, 4)})

        context = "\n\n---\n\n".join(context_parts)

        logger.info("Retrieve done | query_len={} top_k={} returned={}", len(query), top_k, len(results))
        return context, sources

    # ------------------------------------------------------------------
    @property
    def is_ready(self) -> bool:
        """Check whether the store is populated and searchable."""
        return self._store is not None and not self._store.is_empty

    # ------------------------------------------------------------------
    @property
    def store(self) -> Optional[VectorStore]:
        """Expose the underlying :class:`VectorStore` for advanced usage."""
        return self._store
