"""Pydantic response models for every AI service endpoint.

Every API response is serialised through these models, ensuring a
consistent and typed contract between the AI service and the backend.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Copywriting
# ---------------------------------------------------------------------------

class TitleResponse(BaseModel):
    """Output of the product-title generator."""

    titles: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="生成的优化标题列表（5条）。",
    )


class DescriptionResponse(BaseModel):
    """Output of the product-description generator."""

    description: str = Field(
        ...,
        min_length=1,
        description="Markdown 格式的完整产品描述。",
    )


# ---------------------------------------------------------------------------
# Intelligent Shopping Assistant (RAG)
# ---------------------------------------------------------------------------

class ChatResponse(BaseModel):
    """Output of the RAG-powered shopping assistant."""

    answer: str = Field(..., description="基于知识库的回答。")
    has_relevant_info: bool = Field(
        ...,
        description="知识库中是否存在相关信息。",
    )
    related_products: List[str] = Field(
        default_factory=list,
        description="相关产品名称列表。",
    )
    sources: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="检索到的知识库片段（含相关度分数）。",
    )


# ---------------------------------------------------------------------------
# Sentiment Analysis
# ---------------------------------------------------------------------------

class SentimentResponse(BaseModel):
    """Output of the review sentiment analyser."""

    positive_rate: str = Field(..., description="正面评价率，如 '65.50%'。")
    negative_rate: str = Field(..., description="负面评价率，如 '12.30%'。")
    neutral_rate: str = Field(..., description="中性评价率，如 '22.20%'。")
    total_count: int = Field(..., ge=0, description="评论总数。")
    key_complaints: List[str] = Field(
        default_factory=list,
        description="核心投诉关键词。",
    )
    key_praises: List[str] = Field(
        default_factory=list,
        description="核心好评关键词。",
    )
    summary: str = Field(..., description="AI 综合情感分析总结。")


# ---------------------------------------------------------------------------
# Product Recommendation
# ---------------------------------------------------------------------------

class RecommendedProduct(BaseModel):
    """A single recommended product."""

    product_name: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    features: Optional[str] = None
    category: Optional[str] = None


class RecommendResponse(BaseModel):
    """Output of the product recommendation engine."""

    recommendations: List[RecommendedProduct] = Field(
        default_factory=list,
        description="推荐产品列表（按相似度降序）。",
    )


# ---------------------------------------------------------------------------
# Livestream Script
# ---------------------------------------------------------------------------

class LivestreamResponse(BaseModel):
    """Output of the livestream script generator."""

    script: str = Field(..., description="完整直播脚本。")
    estimated_total_duration: str = Field(
        ...,
        description="预估总时长，如 '4分30秒'。",
    )
    key_talking_points: List[str] = Field(
        default_factory=list,
        description="核心话术要点。",
    )


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error response for the AI service."""

    detail: str = Field(..., description="Human-readable error message.")
    code: str = Field(default="INTERNAL_ERROR", description="Machine-readable error code.")
