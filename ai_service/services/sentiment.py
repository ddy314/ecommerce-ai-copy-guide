"""Review sentiment analysis service.

Takes a list of user reviews, sends them to the LLM in a structured prompt,
and returns sentiment distribution, key complaints/praises, and an AI summary.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ai_service.llm.dispatcher import LLMDispatcher
from ai_service.models.request import SentimentRequest
from ai_service.models.response import SentimentResponse
from ai_service.utils.logger import logger
from ai_service.utils.prompt_loader import PromptLoader

_JSON_PATTERN = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM output."""
    m = _JSON_PATTERN.search(text)
    return json.loads((m.group(1) if m else text).strip())


class SentimentAnalyser:
    """Analyse the sentiment of product reviews.

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
    def analyse(self, request: SentimentRequest) -> SentimentResponse:
        """Run sentiment analysis on a list of reviews.

        Parameters
        ----------
        request : SentimentRequest
            Contains the list of review strings.

        Returns
        -------
        SentimentResponse
            Structured sentiment report.
        """
        logger.info("SentimentAnalyser | {} reviews", len(request.reviews))

        # Build a numbered review list for the prompt
        review_text = "\n".join(
            f"{i}. {r}" for i, r in enumerate(request.reviews, 1)
        )

        prompt = self._loader.render("sentiment", reviews=review_text)

        raw = self._dispatcher.generate(prompt)
        data = _extract_json(raw)

        logger.info(
            "SentimentAnalyser done | pos={} neg={} total={}",
            data.get("positive_rate", "?"),
            data.get("negative_rate", "?"),
            data.get("total_count", "?"),
        )
        return SentimentResponse(
            positive_rate=data.get("positive_rate", "0.00%"),
            negative_rate=data.get("negative_rate", "0.00%"),
            neutral_rate=data.get("neutral_rate", "0.00%"),
            total_count=data.get("total_count", len(request.reviews)),
            key_complaints=data.get("key_complaints", []),
            key_praises=data.get("key_praises", []),
            summary=data.get("summary", raw),
        )
