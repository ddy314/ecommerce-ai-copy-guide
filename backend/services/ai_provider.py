"""AI 服务抽象层 - 支持 Mock 和真实模型切换"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

from backend.schemas.requests import (
    CopyGenerationRequest,
    CrossRecommendRequest,
    GuideQARequest,
    GuideRecommendationRequest,
    LiveScriptRequest,
    ReviewAnalysisRequest,
)


class AIProvider(ABC):
    """AI 服务提供者接口"""

    @abstractmethod
    def generate_copy(self, payload: CopyGenerationRequest) -> dict:
        ...

    @abstractmethod
    def recommend(self, payload: GuideRecommendationRequest) -> dict:
        ...

    @abstractmethod
    def guide_qa(self, payload: GuideQARequest) -> dict:
        ...

    @abstractmethod
    def cross_recommend(self, payload: CrossRecommendRequest) -> dict:
        ...

    @abstractmethod
    def analyze_reviews(self, payload: ReviewAnalysisRequest) -> dict:
        ...

    @abstractmethod
    def generate_live_script(self, payload: LiveScriptRequest) -> dict:
        ...


def get_ai_provider() -> AIProvider:
    """根据环境变量获取 AI 服务提供者。

    默认优先使用 DeepSeek；未配置或配置为 mock 时使用 Mock AI 作为备用。
    OpenAI 作为可选兼容提供者保留。
    """
    provider = os.getenv("AI_PROVIDER", "deepseek").lower().strip()

    if provider == "openai":
        from backend.services.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if provider in ("deepseek", ""):
        from backend.services.deepseek_provider import DeepSeekProvider
        from backend.services.ai_mock import MockAIService

        api_key = os.getenv("AI_API_KEY", "")
        if not api_key:
            logger.warning("未配置 AI_API_KEY，使用 Mock AI 作为备用")
            return MockAIService()

        try:
            return DeepSeekProvider()
        except Exception as e:
            logger.warning(f"初始化 DeepSeek 失败，使用 Mock AI 作为备用: {e}")
            return MockAIService()

    # mock 或其他未知值均回退 Mock
    from backend.services.ai_mock import MockAIService
    return MockAIService()
