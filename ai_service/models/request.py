"""Pydantic request models for every AI service endpoint.

Each model validates the input payload automatically via FastAPI's
dependency-injection system.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Copywriting
# ---------------------------------------------------------------------------

class TitleRequest(BaseModel):
    """Input for the product-title generator."""

    product_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="原始产品名称，如「无线蓝牙耳机」。",
    )
    features: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="产品核心卖点，用逗号或句号分隔。",
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="产品所属类目，如「数码配件」。",
    )


class DescriptionRequest(BaseModel):
    """Input for the product-description generator."""

    product_name: str = Field(..., min_length=1, max_length=200)
    features: str = Field(..., min_length=1, max_length=1000)
    specifications: str = Field(
        default="",
        max_length=1000,
        description="产品规格参数，如「重量：250g，材质：铝合金」。",
    )
    target_audience: str = Field(
        default="通用",
        max_length=200,
        description="目标人群，如「上班族 / 运动爱好者」。",
    )
    category: str = Field(..., min_length=1, max_length=100)


# ---------------------------------------------------------------------------
# Intelligent Shopping Assistant (RAG)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Input for the RAG-powered shopping assistant."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="用户自然语言问题。",
    )
    product_ids: Optional[List[str]] = Field(
        default=None,
        description="可选的产品 ID 列表以缩小搜索范围。",
    )


# ---------------------------------------------------------------------------
# Sentiment Analysis
# ---------------------------------------------------------------------------

class SentimentRequest(BaseModel):
    """Input for review sentiment analysis."""

    reviews: List[str] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="用户评论列表，每条评论为一段文本。",
    )


# ---------------------------------------------------------------------------
# Product Recommendation
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    """Input for embedding-based product recommendation."""

    product_name: str = Field(..., min_length=1, max_length=200)
    features: str = Field(..., min_length=1, max_length=1000)
    category: str = Field(..., min_length=1, max_length=100)
    top_n: int = Field(
        default=5,
        ge=1,
        le=20,
        description="返回的推荐产品数量。",
    )


# ---------------------------------------------------------------------------
# Livestream Script
# ---------------------------------------------------------------------------

class LivestreamRequest(BaseModel):
    """Input for the livestream script generator."""

    product_name: str = Field(..., min_length=1, max_length=200)
    features: str = Field(..., min_length=1, max_length=1000)
    promotion: str = Field(
        default="",
        max_length=500,
        description="优惠信息，如「限时特价 199 元，买一送一」。",
    )
    target_audience: str = Field(
        default="通用",
        max_length=200,
        description="目标观众人群。",
    )
    category: str = Field(..., min_length=1, max_length=100)
