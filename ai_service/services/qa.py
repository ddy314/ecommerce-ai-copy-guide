"""Intelligent Shopping Assistant — RAG-powered Q&A.

Orchestrates the full RAG pipeline: the user question is embedded, relevant
product chunks are retrieved from FAISS, and a context-augmented prompt is
sent to the LLM.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ai_service.llm.dispatcher import LLMDispatcher
from ai_service.models.request import ChatRequest
from ai_service.models.response import ChatResponse
from ai_service.rag.retriever import Retriever
from ai_service.utils.logger import logger
from ai_service.utils.prompt_loader import PromptLoader

_JSON_PATTERN = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output."""
    m = _JSON_PATTERN.search(text)
    return json.loads((m.group(1) if m else text).strip())


class ShoppingAssistant:
    """RAG-powered intelligent shopping Q&A.

    Relies on a :class:`Retriever` that has been pre-loaded with product data
    (see :meth:`Retriever.ingest`).  Each question triggers:

    1. Embed query
    2. FAISS search → top-K chunks
    3. Build context-augmented prompt
    4. DeepSeek generates answer

    Parameters
    ----------
    retriever : Retriever
        Pre-populated retriever instance.
    dispatcher : LLMDispatcher, optional
        Injected dispatcher.
    prompt_loader : PromptLoader, optional
        Injected prompt loader.
    """

    def __init__(
        self,
        retriever: Retriever,
        dispatcher: Optional[LLMDispatcher] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ) -> None:
        self._retriever = retriever
        self._dispatcher = dispatcher or LLMDispatcher()
        self._loader = prompt_loader or PromptLoader()

    # ------------------------------------------------------------------
    def ask(self, request: ChatRequest) -> ChatResponse:
        """Answer a user question using RAG.

        Parameters
        ----------
        request : ChatRequest
            User question and optional product-ID filter.

        Returns
        -------
        ChatResponse
            Answer, relevance flag, related products, and source chunks.
        """
        logger.info("ShoppingAssistant | question='{}'", request.question[:80])

        # 1. Retrieve context
        context, sources = self._retriever.retrieve(request.question)

        # 2. Render QA prompt
        prompt = self._loader.render(
            "qa",
            context=context,
            question=request.question,
        )

        # 3. LLM
        raw = self._dispatcher.generate(prompt)
        data = _extract_json(raw)

        logger.info("ShoppingAssistant done | has_relevant_info={}", data.get("has_relevant_info", False))
        return ChatResponse(
            answer=data.get("answer", raw),
            has_relevant_info=data.get("has_relevant_info", bool(context.strip())),
            related_products=data.get("related_products", []),
            sources=sources if sources else None,
        )
