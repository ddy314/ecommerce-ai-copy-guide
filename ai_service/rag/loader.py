"""Document loader and text splitter for the RAG pipeline.

Loads product data from structured dicts (passed by the backend or read from
JSON files) and splits long texts into overlapping chunks suitable for
embedding and retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from langchain.text_splitter import RecursiveCharacterTextSplitter

from ai_service.config.settings import get_settings
from ai_service.utils.logger import logger


class DocumentLoader:
    """Load and normalise product documents from structured data.

    Supports two sources:

    1. **In-memory data** — a list of dicts passed directly by the backend.
    2. **JSON file** — a path to a ``.json`` file containing an array of
       product objects.

    Each document is flattened into a human-readable text representation
    before being chunked.

    Parameters
    ----------
    settings : Settings, optional
        Application settings (injected).  Defaults to the cached singleton.
    """

    # -- fields used when flattening a product dict into text ------------------
    _FIELD_LABELS: Dict[str, str] = {
        "name": "产品名称",
        "category": "类目",
        "description": "描述",
        "features": "特点",
        "specifications": "规格",
        "price": "价格",
        "brand": "品牌",
        "target_audience": "适用人群",
        "usage_scenario": "使用场景",
        "reviews_summary": "用户评价摘要",
    }

    # ------------------------------------------------------------------
    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    def load_from_dicts(self, products: List[Dict[str, Any]]) -> List[str]:
        """Convert a list of product dicts into flattened text documents.

        Parameters
        ----------
        products : list[dict]
            Each dict represents one product.

        Returns
        -------
        list[str]
            One text string per product, ready for chunking.
        """
        logger.info("Loading {} products from in-memory dicts", len(products))
        docs = [self._flatten(p) for p in products]
        logger.debug("Flattened {} documents, total chars={}", len(docs), sum(len(d) for d in docs))
        return docs

    # ------------------------------------------------------------------
    def load_from_json(self, file_path: str) -> List[str]:
        """Load products from a JSON file.

        Parameters
        ----------
        file_path : str
            Path to a ``.json`` file containing a list of product objects.

        Returns
        -------
        list[str]
            Flattened text documents.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Product JSON not found: {path}")

        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of product objects")

        logger.info("Loaded {} products from {}", len(data), path)
        return self.load_from_dicts(data)

    # ------------------------------------------------------------------
    def _flatten(self, product: Dict[str, Any]) -> str:
        """Flatten a single product dict into a readable text block.

        Parameters
        ----------
        product : dict
            Product key-value pairs.

        Returns
        -------
        str
            Natural-language representation of the product.
        """
        lines: List[str] = []
        for key, label in self._FIELD_LABELS.items():
            value = product.get(key)
            if value:
                lines.append(f"{label}：{value}")
        # Include any extra fields not in the standard label map
        for key, value in product.items():
            if key not in self._FIELD_LABELS and value:
                lines.append(f"{key}：{value}")
        return "\n".join(lines)


class TextSplitter:
    """Split long documents into smaller, overlapping chunks.

    Thin wrapper around LangChain's ``RecursiveCharacterTextSplitter`` with
    project-specific defaults.

    Parameters
    ----------
    settings : Settings, optional
        Application settings (injected).
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._settings.CHUNK_SIZE,
            chunk_overlap=self._settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "，", " ", ""],
            length_function=len,
        )

    # ------------------------------------------------------------------
    def split(self, documents: List[str]) -> List[str]:
        """Split a list of documents into chunks.

        Parameters
        ----------
        documents : list[str]
            Raw document texts.

        Returns
        -------
        list[str]
            Chunked texts (may be longer than the input list).
        """
        all_chunks: List[str] = []
        for doc in documents:
            chunks = self._splitter.split_text(doc)
            all_chunks.extend(chunks)
        logger.info(
            "Split {} documents → {} chunks (chunk_size={} overlap={})",
            len(documents),
            len(all_chunks),
            self._settings.CHUNK_SIZE,
            self._settings.CHUNK_OVERLAP,
        )
        return all_chunks
