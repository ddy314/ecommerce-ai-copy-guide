"""Copywriting services — product title and description generation.

Both services follow the same pattern: load a prompt template, render it
with the product data, send to the LLM, and parse the JSON response.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ai_service.llm.dispatcher import LLMDispatcher
from ai_service.models.request import DescriptionRequest, TitleRequest
from ai_service.models.response import DescriptionResponse, TitleResponse
from ai_service.utils.logger import logger
from ai_service.utils.prompt_loader import PromptLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_PATTERN = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Extract a JSON object from an LLM response.

    Tries `````json … ``` `` fences first, then falls back to raw parsing.

    Parameters
    ----------
    text : str
        Raw LLM output.

    Returns
    -------
    dict
        Parsed JSON.

    Raises
    ------
    ValueError
        If no valid JSON object can be extracted.
    """
    m = _JSON_PATTERN.search(text)
    json_str = m.group(1) if m else text
    return json.loads(json_str.strip())


# ---------------------------------------------------------------------------
# Title Generator
# ---------------------------------------------------------------------------

class TitleGenerator:
    """Generate optimised e-commerce product titles.

    Parameters
    ----------
    dispatcher : LLMDispatcher, optional
        Injected dispatcher.  A default instance is created if omitted.
    prompt_loader : PromptLoader, optional
        Injected prompt loader.
    """

    def __init__(
        self,
        dispatcher: Optional[LLMDispatcher] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ) -> None:
        self._dispatcher = dispatcher or LLMDispatcher()
        self._loader = prompt_loader or PromptLoader()

    # ------------------------------------------------------------------
    def generate(self, request: TitleRequest) -> TitleResponse:
        """Generate five optimised product titles.

        Parameters
        ----------
        request : TitleRequest
            Product-name, features, and category.

        Returns
        -------
        TitleResponse
            List of generated titles.
        """
        logger.info(
            "TitleGenerator | product='{}' category='{}'",
            request.product_name,
            request.category,
        )

        prompt = self._loader.render(
            "title",
            product_name=request.product_name,
            features=request.features,
            category=request.category,
        )

        raw = self._dispatcher.generate(prompt)
        data = _extract_json(raw)
        titles = data.get("titles", [])

        logger.info("TitleGenerator done | {} titles generated", len(titles))
        return TitleResponse(titles=titles[:5])


# ---------------------------------------------------------------------------
# Description Generator
# ---------------------------------------------------------------------------

class DescriptionGenerator:
    """Generate a professional product description in Markdown.

    Parameters
    ----------
    dispatcher : LLMDispatcher, optional
        Injected dispatcher.
    prompt_loader : PromptLoader, optional
        Injected prompt loader.
    """

    def __init__(
        self,
        dispatcher: Optional[LLMDispatcher] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ) -> None:
        self._dispatcher = dispatcher or LLMDispatcher()
        self._loader = prompt_loader or PromptLoader()

    # ------------------------------------------------------------------
    def generate(self, request: DescriptionRequest) -> DescriptionResponse:
        """Generate a product description.

        Parameters
        ----------
        request : DescriptionRequest
            Full product info.

        Returns
        -------
        DescriptionResponse
            Markdown product description.
        """
        logger.info(
            "DescriptionGenerator | product='{}'",
            request.product_name,
        )

        prompt = self._loader.render(
            "description",
            product_name=request.product_name,
            features=request.features,
            specifications=request.specifications or "暂无",
            target_audience=request.target_audience or "通用",
            category=request.category,
        )

        raw = self._dispatcher.generate(prompt)
        data = _extract_json(raw)

        description = data.get("description", raw)

        logger.info("DescriptionGenerator done | {} chars", len(description))
        return DescriptionResponse(description=description)
