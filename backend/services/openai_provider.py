"""OpenAI AI 服务提供者"""
from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

from backend.schemas.requests import (
    CopyGenerationRequest,
    CrossRecommendRequest,
    GuideQARequest,
    GuideRecommendationRequest,
    LiveScriptRequest,
    ReviewAnalysisRequest,
)
from backend.services.ai_provider import AIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """基于 OpenAI API 的 AI 服务"""

    def __init__(self):
        api_key = os.getenv("AI_API_KEY", "")
        base_url = os.getenv("AI_BASE_URL", "")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")

        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            raise

    def _parse_json(self, text: str) -> dict | None:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def generate_copy(self, payload: CopyGenerationRequest) -> dict:
        system_prompt = "你是一位专业的电商文案策划师，擅长撰写吸引人的商品文案。"
        user_prompt = f"""请为以下商品生成营销文案：

商品名称：{payload.product_name}
目标人群：{payload.audience}
文案风格：{payload.style}（可选：简洁/高端/活泼/专业）
商品卖点：{', '.join(payload.selling_points) if payload.selling_points else '请根据商品名称推断'}

请按以下 JSON 格式返回（不要返回其他内容）：
{{
  "title": "商品标题（30字以内，包含核心卖点）",
  "selling_points": ["卖点1描述", "卖点2描述", "卖点3描述"],
  "detail_copy": "详情页文案（100-200字，突出使用场景和优势）",
  "ad_slogan": "广告语（15字以内，朗朗上口）"
}}"""

        result_text = self._chat(system_prompt, user_prompt)
        data = self._parse_json(result_text)
        if not data:
            from backend.services.ai_mock import MockAIService
            return MockAIService().generate_copy(payload)

        return {
            "product_name": payload.product_name,
            "style": payload.style,
            "title": data.get("title", ""),
            "selling_points": data.get("selling_points", []),
            "detail_copy": data.get("detail_copy", ""),
            "ad_slogan": data.get("ad_slogan", ""),
        }

    def recommend(self, payload: GuideRecommendationRequest) -> dict:
        system_prompt = "你是一位专业的电商导购顾问，擅长根据用户需求推荐合适的商品。"
        user_prompt = f"""用户需求：{payload.user_need}
预算：{payload.budget}
候选商品：{', '.join(payload.products) if payload.products else '请根据需求推荐'}

请按以下 JSON 格式返回：
{{
  "recommended_product": "首推商品名称",
  "reason": "推荐理由（50-100字）",
  "alternatives": ["备选商品1", "备选商品2"],
  "guide_message": "购买建议（30-50字）"
}}"""

        result_text = self._chat(system_prompt, user_prompt)
        data = self._parse_json(result_text)
        if not data:
            from backend.services.ai_mock import MockAIService
            return MockAIService().recommend(payload)

        return {
            "user_need": payload.user_need,
            "budget": payload.budget,
            "recommended_product": data.get("recommended_product", ""),
            "reason": data.get("reason", ""),
            "alternatives": data.get("alternatives", []),
            "guide_message": data.get("guide_message", ""),
        }

    def guide_qa(self, payload: GuideQARequest) -> dict:
        system_prompt = "你是一位专业的电商导购客服，擅长回答用户关于商品尺码、功能和搭配的问题。"
        user_prompt = f"""用户问题：{payload.question}
商品名称：{payload.product_name or '未指定'}
商品规格：{payload.product_specs or '未提供'}
商品类目：{payload.category or '未指定'}
问题类型：{payload.question_type}

请回答用户的问题，并按以下 JSON 格式返回：
{{
  "question_type": "size/function/matching",
  "answer": "详细回答（50-150字）",
  "related_tips": ["提示1", "提示2"]
}}"""

        result_text = self._chat(system_prompt, user_prompt)
        data = self._parse_json(result_text)
        if not data:
            from backend.services.ai_mock import MockAIService
            return MockAIService().guide_qa(payload)

        return {
            "question": payload.question,
            "question_type": data.get("question_type", payload.question_type),
            "answer": data.get("answer", ""),
            "related_tips": data.get("related_tips", []),
        }

    def cross_recommend(self, payload: CrossRecommendRequest) -> dict:
        system_prompt = "你是一位专业的电商推荐系统，擅长根据用户偏好做跨商品关联推荐。"
        user_prompt = f"""当前商品：{payload.product_name}
商品类目：{payload.category or '未指定'}
用户偏好：{', '.join(payload.user_preferences) if payload.user_preferences else '无特定偏好'}
预算：{payload.budget}

请推荐 3-4 个关联商品，按以下 JSON 格式返回：
{{
  "recommendations": [
    {{"product_name": "商品名", "reason": "推荐理由", "match_score": 85}},
    ...
  ]
}}"""

        result_text = self._chat(system_prompt, user_prompt)
        data = self._parse_json(result_text)
        if not data:
            from backend.services.ai_mock import MockAIService
            return MockAIService().cross_recommend(payload)

        return {
            "current_product": payload.product_name,
            "user_preferences": payload.user_preferences,
            "recommendations": data.get("recommendations", []),
        }

    def analyze_reviews(self, payload: ReviewAnalysisRequest) -> dict:
        system_prompt = "你是一位专业的用户评论分析师，擅长从评论中提取洞察。"
        reviews_text = "\n".join(f"- {r}" for r in payload.reviews[:50])
        user_prompt = f"""商品：{payload.product_name}

用户评论：
{reviews_text}

请分析以上评论，按以下 JSON 格式返回：
{{
  "sentiment": {{"positive": 正面数量, "neutral": 中性数量, "negative": 负面数量}},
  "sentiment_detail": {{
    "positive_reviews": ["好评摘录1", "好评摘录2"],
    "negative_reviews": ["差评摘录1", "差评摘录2"],
    "complaints": ["吐槽点1", "吐槽点2"]
  }},
  "top_keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "pain_points": ["痛点1", "痛点2", "痛点3"],
  "optimization_suggestions": ["建议1", "建议2", "建议3"]
}}"""

        result_text = self._chat(system_prompt, user_prompt)
        data = self._parse_json(result_text)
        if not data:
            from backend.services.ai_mock import MockAIService
            return MockAIService().analyze_reviews(payload)

        sentiment = data.get("sentiment", {"positive": 0, "neutral": 0, "negative": 0})
        total = sum(sentiment.values()) or len(payload.reviews)

        return {
            "product_name": payload.product_name,
            "total": total,
            "sentiment": sentiment,
            "sentiment_detail": data.get("sentiment_detail", {
                "positive_reviews": [],
                "negative_reviews": [],
                "complaints": [],
            }),
            "top_keywords": data.get("top_keywords", []),
            "pain_points": data.get("pain_points", []),
            "optimization_suggestions": data.get("optimization_suggestions", []),
        }

    def generate_live_script(self, payload: LiveScriptRequest) -> dict:
        system_prompt = "你是一位专业的直播运营策划师，擅长撰写直播脚本和产品讲解流程。"
        user_prompt = f"""商品：{payload.product_name}
直播时长：{payload.duration_minutes}分钟
直播语气：{payload.tone}
商品亮点：{', '.join(payload.highlights) if payload.highlights else '请根据商品推断'}
商品规格：{payload.product_specs or '未提供'}
目标受众：{payload.target_audience or '消费者'}

请生成直播脚本，按以下 JSON 格式返回：
{{
  "segments": [
    {{"name": "开场引入", "minutes": 1, "script": "开场话术", "action_hint": "动作提示"}},
    {{"name": "卖点讲解", "minutes": {payload.duration_minutes - 2}, "script": "讲解话术", "action_hint": "动作提示"}},
    {{"name": "互动答疑", "minutes": 1, "script": "答疑话术", "action_hint": "动作提示"}},
    {{"name": "转化收尾", "minutes": 1, "script": "转化话术", "action_hint": "动作提示"}}
  ],
  "explanation_flow": [
    {{"step": 1, "title": "产品定位与适用人群", "script": "讲解内容", "key_points": ["要点1", "要点2"]}},
    {{"step": 2, "title": "核心卖点逐一拆解", "script": "讲解内容", "key_points": ["要点1", "要点2"]}},
    ...
  ],
  "interaction_questions": ["问题1", "问题2", "问题3"],
  "conversion_scripts": ["促单话术1", "促单话术2"]
}}"""

        result_text = self._chat(system_prompt, user_prompt)
        data = self._parse_json(result_text)
        if not data:
            from backend.services.ai_mock import MockAIService
            return MockAIService().generate_live_script(payload)

        return {
            "product_name": payload.product_name,
            "duration_minutes": payload.duration_minutes,
            "tone": payload.tone,
            "segments": data.get("segments", []),
            "explanation_flow": data.get("explanation_flow", []),
            "interaction_questions": data.get("interaction_questions", []),
            "conversion_scripts": data.get("conversion_scripts", []),
        }
