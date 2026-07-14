"""Text embedding service using SentenceTransformer models.

Provides a singleton-style embedder that loads the model once and exposes
batch-friendly encoding methods.  The embedding dimension is auto-detected
from the model.
"""

from __future__ import annotations

from typing import List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from ai_service.config.settings import get_settings
from ai_service.utils.logger import logger


class EmbeddingService:
    """Encode texts into dense vectors using a SentenceTransformer model.

    The model is loaded lazily on the first call to :meth:`encode` so that
    the service can be instantiated at import time without hitting disk.

    Parameters
    ----------
    settings : Settings, optional
        Application settings (injected).

    Examples
    --------
    >>> svc = EmbeddingService()
    >>> vectors = svc.encode(["产品 A", "产品 B"])
    >>> vectors.shape
    (2, 384)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model: Optional[SentenceTransformer] = None

    # ------------------------------------------------------------------
    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load (and cache) the SentenceTransformer model."""
        if self._model is None:
            logger.info(
                "Loading embedding model '{}' on device '{}' …",
                self._settings.EMBEDDING_MODEL,
                self._settings.EMBEDDING_DEVICE,
            )
            self._model = SentenceTransformer(
                self._settings.EMBEDDING_MODEL,
                device=self._settings.EMBEDDING_DEVICE,
            )
            logger.info(
                "Embedding model loaded | dim={}",
                self._model.get_sentence_embedding_dimension(),
            )
        return self._model

    # ------------------------------------------------------------------
    def encode(
        self,
        texts: Union[str, List[str]],
        *,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        """Encode one or more texts into embeddings.

        Parameters
        ----------
        texts : str or list[str]
            Single text or a list of texts.
        show_progress_bar : bool
            Whether to display a tqdm progress bar.

        Returns
        -------
        np.ndarray
            Embedding vectors of shape ``(n_texts, dim)``.  Always a 2-D array
            even when a single string is passed.
        """
        if isinstance(texts, str):
            texts = [texts]

        logger.debug("Encoding {} texts …", len(texts))

        embeddings: np.ndarray = self.model.encode(
            texts,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=True,  # cosine similarity ≡ dot product
        )
        return embeddings

    # ------------------------------------------------------------------
    @property
    def dimension(self) -> int:
        """Return the embedding dimension of the loaded model.

        Returns
        -------
        int
            Vector size (e.g. 384, 768, …).
        """
        return self.model.get_sentence_embedding_dimension()
