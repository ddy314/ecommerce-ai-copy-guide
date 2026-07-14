from __future__ import annotations

from pydantic import BaseModel, Field


# ===== 模块一：商品文案智能生成 =====

class CopyGenerationRequest(BaseModel):
    product_name: str = Field(min_length=1, examples=["云感护腰办公椅"])
    audience: str = Field(default="都市白领", min_length=1)
    style: str = Field(default="简洁", description="文案风格：简洁/高端/活泼/专业")
    selling_points: list[str] = Field(default_factory=list, max_length=8)
    category: str = Field(default="", description="商品类目，辅助生成")


class CopyGenerationResponse(BaseModel):
    product_name: str
    style: str
    title: str
    selling_points: list[str]
    detail_copy: str
    ad_slogan: str


# ===== 模块二：智能导购与推荐问答 =====

class GuideRecommendationRequest(BaseModel):
    user_need: str = Field(min_length=1, examples=["预算 300 元以内，送给经常加班的朋友"])
    budget: str = Field(default="未限定")
    products: list[str] = Field(default_factory=list, max_length=10)


class GuideRecommendationResponse(BaseModel):
    user_need: str
    budget: str
    recommended_product: str
    reason: str
    alternatives: list[str]
    guide_message: str


class GuideQARequest(BaseModel):
    """智能导购问答请求"""
    question: str = Field(min_length=1, examples=["这款椅子适合多高的人坐？"])
    product_name: str = Field(default="", description="商品名称")
    product_specs: str = Field(default="", description="商品规格信息")
    category: str = Field(default="", description="商品类目")
    question_type: str = Field(
        default="auto",
        description="问题类型：size(尺码)/function(功能)/matching(搭配)/auto(自动识别)",
    )


class GuideQAResponse(BaseModel):
    question: str
    question_type: str
    answer: str
    related_tips: list[str] = Field(default_factory=list)


class CrossRecommendRequest(BaseModel):
    """跨商品关联推荐请求"""
    product_name: str = Field(min_length=1, description="当前浏览商品")
    category: str = Field(default="", description="商品类目")
    user_preferences: list[str] = Field(
        default_factory=list, description="用户偏好标签，如['性价比','便携','颜值']"
    )
    budget: str = Field(default="未限定")


class CrossRecommendItem(BaseModel):
    product_name: str
    reason: str
    match_score: int = Field(description="匹配度 0-100")


class CrossRecommendResponse(BaseModel):
    current_product: str
    user_preferences: list[str]
    recommendations: list[CrossRecommendItem]


# ===== 模块三：用户评论情感分析 =====

class ReviewAnalysisRequest(BaseModel):
    product_name: str = Field(default="示例商品")
    reviews: list[str] = Field(min_length=1, max_length=50)
    product_id: int | None = Field(default=None, description="数据库商品ID，用于加载真实评论")


class SentimentCounts(BaseModel):
    positive: int
    neutral: int
    negative: int


class SentimentDetail(BaseModel):
    """情感细分：好评/差评/吐槽点"""
    positive_reviews: list[str] = Field(default_factory=list, description="好评摘录")
    negative_reviews: list[str] = Field(default_factory=list, description="差评摘录")
    complaints: list[str] = Field(default_factory=list, description="吐槽点（具体问题）")


class ReviewAnalysisResponse(BaseModel):
    product_name: str
    total: int
    sentiment: SentimentCounts
    sentiment_detail: SentimentDetail
    top_keywords: list[str]
    pain_points: list[str]
    optimization_suggestions: list[str]


# ===== 模块四：直播/短视频脚本自动生成 =====

class LiveScriptRequest(BaseModel):
    product_name: str = Field(min_length=1)
    duration_minutes: int = Field(default=5, ge=1, le=120)
    tone: str = Field(default="热情自然", min_length=1)
    highlights: list[str] = Field(default_factory=list, max_length=8)
    product_specs: str = Field(default="", description="商品规格参数")
    target_audience: str = Field(default="", description="目标受众")


class LiveScriptSegment(BaseModel):
    name: str
    minutes: int
    script: str
    action_hint: str = Field(default="", description="动作/场景提示")


class ProductExplanationStep(BaseModel):
    """产品讲解流程步骤"""
    step: int
    title: str
    script: str
    key_points: list[str] = Field(default_factory=list)


class LiveScriptResponse(BaseModel):
    product_name: str
    duration_minutes: int
    tone: str
    segments: list[LiveScriptSegment]
    explanation_flow: list[ProductExplanationStep] = Field(
        default_factory=list, description="产品讲解流程"
    )
    interaction_questions: list[str]
    conversion_scripts: list[str] = Field(
        default_factory=list, description="转化话术（促单/限时优惠等）"
    )


# ===== 通用 =====

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[dict] | None = None
