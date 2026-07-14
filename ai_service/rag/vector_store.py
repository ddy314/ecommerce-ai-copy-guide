"""FAISS vector-store wrapper for dense retrieval.

Manages index creation, persistence, and similarity search.  Each entry
in the store has a unique ID, a text payload, and an embedding vector.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from ai_service.config.settings import get_settings
from ai_service.utils.logger import logger


class VectorStore:
    """A FAISS-backed document store with text payloads.

    The index is an ``IndexIDMap`` wrapping a ``FlatIP`` (inner-product)
    index, which is appropriate when embeddings are L2-normalised (cosine
    similarity ≈ inner product).

    Parameters
    ----------
    dimension : int
        Embedding vector dimension.
    settings : Settings, optional
        Application settings (injected).

    Examples
    --------
    >>> store = VectorStore(dimension=384)
    >>> store.add(["doc1 text", "doc2 text"], embeddings)
    >>> results = store.search(query_vector, top_k=5)
    """

    def __init__(self, dimension: int) -> None:
        self._settings = get_settings()
        self._dimension = dimension

        # -- build the FAISS index -------------------------------------------
        # FlatIP → exhaustive inner-product search (fast enough for < 100k docs)
        quantizer = faiss.IndexFlatIP(dimension)
        self._index = faiss.IndexIDMap(quantizer)

        # -- metadata ------------------------------------------------
        self._id_counter: int = 0
        self._texts: Dict[int, str] = {}          # id → original text
        self._metadata: Dict[int, Dict[str, Any]] = {}  # id → extra metadata

        logger.info("VectorStore created | dim={} index_type=IndexIDMap(FlatIP)", dimension)

    # ------------------------------------------------------------------
    def add(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        *,
        metadata: Optional[List[Optional[Dict[str, Any]]]] = None,
    ) -> List[int]:
        """Add documents to the store.

        Parameters
        ----------
        texts : list[str]
            Document texts (one per embedding row).
        embeddings : np.ndarray
            Embedding matrix of shape ``(n_texts, dim)``, dtype ``float32``.
        metadata : list[dict], optional
            Optional metadata dicts, one per document.

        Returns
        -------
        list[int]
            Assigned IDs for the newly added documents.
        """
        n = len(texts)
        if embeddings.shape[0] != n:
            raise ValueError(
                f"Mismatch: {n} texts vs {embeddings.shape[0]} embedding rows"
            )
        if embeddings.shape[1] != self._dimension:
            raise ValueError(
                f"Embedding dim mismatch: expected {self._dimension}, "
                f"got {embeddings.shape[1]}"
            )

        embeddings = embeddings.astype(np.float32)
        ids = list(range(self._id_counter, self._id_counter + n))

        self._index.add_with_ids(embeddings, np.array(ids, dtype=np.int64))
        self._id_counter += n

        for i, tid in enumerate(ids):
            self._texts[tid] = texts[i]
            if metadata and metadata[i]:
                self._metadata[tid] = metadata[i]

        logger.info("Added {} docs to VectorStore | total={}", n, self._id_counter)
        return ids

    # ------------------------------------------------------------------
    def search(
        self,
        query_vector: np.ndarray,
        top_k: Optional[int] = None,
    ) -> List[Tuple[str, float, Optional[Dict[str, Any]]]]:
        """Search for the most similar documents.

        Parameters
        ----------
        query_vector : np.ndarray
            1-D embedding of shape ``(dim,)``.
        top_k : int, optional
            Number of results; defaults to ``TOP_K`` from settings.

        Returns
        -------
        list[tuple[str, float, dict | None]]
            Sorted list of ``(text, score, metadata)``, best-match first.
        """
        if top_k is None:
            top_k = self._settings.TOP_K

        query = query_vector.astype(np.float32).reshape(1, -1)

        if self._index.ntotal == 0:
            logger.warning("VectorStore search on empty index — returning []")
            return []

        effective_k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(query, effective_k)

        results: List[Tuple[str, float, Optional[Dict[str, Any]]]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:          # FAISS sentinel for "no result"
                continue
            text = self._texts.get(int(idx), "")
            meta = self._metadata.get(int(idx))
            results.append((text, float(dist), meta))

        logger.debug("Search returned {} results (asked top_k={})", len(results), top_k)
        return results

    # ------------------------------------------------------------------
    def save(self, path: Optional[str] = None) -> None:
        """Persist the index and metadata to disk.

        Parameters
        ----------
        path : str, optional
            Directory to save to; defaults to ``FAISS_INDEX_PATH`` from settings.
        """
        save_dir = Path(path or self._settings.FAISS_INDEX_PATH)
        save_dir.mkdir(parents=True, exist_ok=True)

        # -- FAISS index ------------------------------------------------------
        faiss.write_index(self._index, str(save_dir / "index.faiss"))

        # -- metadata ---------------------------------------------------------
        meta = {
            "id_counter": self._id_counter,
            "texts": self._texts,
            "metadata": self._metadata,
            "dimension": self._dimension,
        }
        with (save_dir / "metadata.pkl").open("wb") as fh:
            pickle.dump(meta, fh)

        logger.info("VectorStore saved to {} | total_docs={}", save_dir, self._id_counter)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Optional[str] = None) -> "VectorStore":
        """Load a previously saved index and metadata.

        Parameters
        ----------
        path : str, optional
            Directory to load from; defaults to ``FAISS_INDEX_PATH`` from settings.

        Returns
        -------
        VectorStore
            Restored store instance.
        """
        load_dir = Path(path or get_settings().FAISS_INDEX_PATH)

        index_path = load_dir / "index.faiss"
        meta_path = load_dir / "metadata.pkl"

        if not index_path.is_file() or not meta_path.is_file():
            raise FileNotFoundError(
                f"VectorStore files not found in {load_dir}"
            )

        meta = pickle.loads(meta_path.read_bytes())

        store = cls(dimension=meta["dimension"])
        store._index = faiss.read_index(str(index_path))
        store._id_counter = meta["id_counter"]
        store._texts = meta["texts"]
        store._metadata = meta.get("metadata", {})
        store._dimension = meta["dimension"]

        logger.info("VectorStore loaded from {} | total_docs={}", load_dir, store._id_counter)
        return store

    # ------------------------------------------------------------------
    @property
    def count(self) -> int:
        """Total number of documents in the store."""
        return self._index.ntotal

    # ------------------------------------------------------------------
    @property
    def is_empty(self) -> bool:
        """Return ``True`` when the index holds no documents."""
        return self._index.ntotal == 0
