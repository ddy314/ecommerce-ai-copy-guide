"""AI 服务抽象层 - 支持 Mock 和真实模型切换"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

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
    """根据环境变量获取 AI 服务提供者"""
    provider = os.getenv("AI_PROVIDER", "mock")
    if provider == "openai":
        from backend.services.openai_provider import OpenAIProvider
        return OpenAIProvider()
    else:
        from backend.services.ai_mock import MockAIService
        return MockAIService()
