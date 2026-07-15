"""DeepSeek AI 服务提供者

DeepSeek API 兼容 OpenAI SDK，因此复用 OpenAIProvider 的提示词与解析逻辑，
仅固定 base_url 与默认模型。环境变量中可覆盖：
- AI_API_KEY: DeepSeek API Key
- AI_BASE_URL: 可选，默认 https://api.deepseek.com/v1
- AI_MODEL: 可选，默认 deepseek-v4-pro
"""
from __future__ import annotations

import os

from backend.services.openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """基于 DeepSeek API 的 AI 服务"""

    def __init__(self):
        # 强制使用 DeepSeek 默认 endpoint；若用户显式配置了 AI_BASE_URL 则优先使用
        os.environ.setdefault("AI_BASE_URL", "https://api.deepseek.com/v1")
        os.environ.setdefault("AI_MODEL", "deepseek-v4-pro")
        super().__init__()
