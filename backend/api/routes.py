from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from backend.schemas.requests import (
    CopyGenerationRequest,
    CopyGenerationResponse,
    CrossRecommendRequest,
    CrossRecommendResponse,
    ErrorResponse,
    GuideQARequest,
    GuideQAResponse,
    GuideRecommendationRequest,
    GuideRecommendationResponse,
    LiveScriptRequest,
    LiveScriptResponse,
    ReviewAnalysisRequest,
    ReviewAnalysisResponse,
)
from backend.services.ai_provider import get_ai_provider
from backend.database import get_db_context
from backend.models.product import Product
from backend.models.review import Review
from backend.models.generation_task import GenerationTask
from backend.models.recommendation_log import RecommendationLog
from backend.cache import CacheService

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)
service = get_ai_provider()
cache = CacheService()


def _parse_payload(model):
    try:
        return model.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        error_response = ErrorResponse(
            error="validation_error",
            message="请求参数校验失败",
            details=exc.errors(),
        )
        return jsonify(error_response.model_dump()), 400


@api_bp.get("/capabilities")
def capabilities():
    provider_name = service.__class__.__name__
    return jsonify({
        "mode": "openai" if "OpenAI" in provider_name else "mock",
        "provider": provider_name,
        "features": [
            {"key": "copy_generation", "name": "商品文案生成", "endpoint": "/api/copy/generate"},
            {"key": "shopping_guide", "name": "智能导购推荐", "endpoint": "/api/guide/recommend"},
            {"key": "guide_qa", "name": "智能导购问答", "endpoint": "/api/guide/qa"},
            {"key": "cross_recommend", "name": "跨商品关联推荐", "endpoint": "/api/guide/cross-recommend"},
            {"key": "review_analysis", "name": "评论情感分析", "endpoint": "/api/reviews/analyze"},
            {"key": "live_script", "name": "直播脚本生成", "endpoint": "/api/scripts/live"},
        ],
    })


# ===== 模块一：商品文案智能生成 =====

@api_bp.post("/copy/generate")
def generate_copy():
    payload = _parse_payload(CopyGenerationRequest)
    if isinstance(payload, tuple):
        return payload

    # 尝试从缓存获取
    cache_key = CacheService.copy_key(payload.product_name, payload.style)
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"文案缓存命中: {payload.product_name}")
        return jsonify(cached)

    result = service.generate_copy(payload)
    response = CopyGenerationResponse(**result)
    data = response.model_dump()

    # 写入缓存
    cache.set(cache_key, data, ttl=7200)

    # 记录生成任务
    try:
        with get_db_context() as db:
            task = GenerationTask(
                task_type="copy",
                input_params=json.dumps(payload.model_dump(), ensure_ascii=False),
                output_result=json.dumps(data, ensure_ascii=False),
            )
            db.add(task)
    except Exception as e:
        logger.warning(f"任务记录失败: {e}")

    return jsonify(data)


# ===== 模块二：智能导购与推荐问答 =====

@api_bp.post("/guide/recommend")
def recommend():
    payload = _parse_payload(GuideRecommendationRequest)
    if isinstance(payload, tuple):
        return payload

    result = service.recommend(payload)
    response = GuideRecommendationResponse(**result)
    data = response.model_dump()

    # 记录推荐日志
    try:
        with get_db_context() as db:
            log = RecommendationLog(
                user_need=payload.user_need,
                budget=payload.budget,
                recommended_product=result.get("recommended_product", ""),
                reason=result.get("reason", ""),
                alternatives=json.dumps(result.get("alternatives", []), ensure_ascii=False),
            )
            db.add(log)
    except Exception as e:
        logger.warning(f"推荐记录失败: {e}")

    return jsonify(data)


@api_bp.post("/guide/qa")
def guide_qa():
    """智能导购问答 - 回答尺码、功能、搭配等问题"""
    payload = _parse_payload(GuideQARequest)
    if isinstance(payload, tuple):
        return payload

    # 如果有 product_id，从数据库加载商品信息补充上下文
    body = request.get_json(silent=True) or {}
    product_id_val = body.get("product_id")
    if product_id_val:
        try:
            from backend.database import SessionLocal
            from backend.repositories.product_repo import ProductRepository
            with SessionLocal() as db:
                repo = ProductRepository(db)
                product = repo.get_by_id(int(product_id_val))
                if product:
                    if not payload.product_name:
                        payload = payload.model_copy(update={"product_name": product.name})
                    if not payload.product_specs and product.specs:
                        payload = payload.model_copy(update={"product_specs": product.specs})
                    if not payload.category and product.category:
                        payload = payload.model_copy(update={"category": product.category})
        except Exception as e:
            logger.warning(f"商品信息加载失败: {e}")

    result = service.guide_qa(payload)
    response = GuideQAResponse(**result)
    return jsonify(response.model_dump())


@api_bp.post("/guide/cross-recommend")
def cross_recommend():
    """跨商品关联推荐 - 根据用户偏好推荐关联商品"""
    payload = _parse_payload(CrossRecommendRequest)
    if isinstance(payload, tuple):
        return payload

    # 尝试从缓存获取
    cache_key = f"cross:{payload.product_name}:{':'.join(payload.user_preferences)}"
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"跨商品推荐缓存命中: {payload.product_name}")
        return jsonify(cached)

    result = service.cross_recommend(payload)
    response = CrossRecommendResponse(**result)
    data = response.model_dump()

    cache.set(cache_key, data, ttl=1800)
    return jsonify(data)


# ===== 模块三：用户评论情感分析 =====

@api_bp.post("/reviews/analyze")
def analyze_reviews():
    payload = _parse_payload(ReviewAnalysisRequest)
    if isinstance(payload, tuple):
        return payload

    # 如果传了 product_id，尝试从数据库获取评论
    body = request.get_json(silent=True) or {}
    product_id_val = body.get("product_id")
    if product_id_val:
        cache_key = CacheService.sentiment_key(str(product_id_val))
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"评论分析缓存命中: product_id={product_id_val}")
            return jsonify(cached)

        # 从数据库加载真实评论
        try:
            from backend.database import SessionLocal
            from backend.repositories.review_repo import ReviewRepository
            with SessionLocal() as db:
                repo = ReviewRepository(db)
                reviews = repo.get_by_product(int(product_id_val), limit=50)
                if reviews:
                    payload = payload.model_copy(update={
                        "reviews": [r.content for r in reviews],
                        "product_name": payload.product_name or f"商品#{product_id_val}",
                    })
        except Exception as e:
            logger.warning(f"评论加载失败: {e}")

    result = service.analyze_reviews(payload)
    response = ReviewAnalysisResponse(**result)
    data = response.model_dump()

    # 缓存分析结果
    if product_id_val:
        cache.set(CacheService.sentiment_key(str(product_id_val)), data, ttl=3600)

    return jsonify(data)


# ===== 模块四：直播/短视频脚本自动生成 =====

@api_bp.post("/scripts/live")
def generate_live_script():
    payload = _parse_payload(LiveScriptRequest)
    if isinstance(payload, tuple):
        return payload

    result = service.generate_live_script(payload)
    response = LiveScriptResponse(**result)
    return jsonify(response.model_dump())


# ===== 数据查询 API =====

@api_bp.get("/products")
def list_products():
    """获取商品列表（支持Redis缓存 + 分页）"""
    from backend.database import SessionLocal
    from backend.repositories.product_repo import ProductRepository

    category = request.args.get("category")
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    limit = page_size
    offset = (page - 1) * page_size

    cache_key = f"products:list:{category or 'all'}:{keyword or ''}:{page}:{page_size}"

    cached = cache.get(cache_key)
    if cached:
        logger.info(f"商品列表缓存命中: {cache_key}")
        return jsonify(cached)

    with SessionLocal() as db:
        repo = ProductRepository(db)
        if keyword:
            products = repo.search(keyword, limit, offset)
            total = len(repo.search(keyword, limit=9999, offset=0))
        else:
            products = repo.list_all(category, limit, offset)
            total = repo.count(category)

        categories = repo.list_categories()
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        # 每个分类的商品数量
        category_counts = {}
        for cat in categories:
            category_counts[cat] = repo.count(cat)

        result = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "categories": categories,
            "category_counts": category_counts,
            "products": [p.to_dict() for p in products],
        }

    cache.set(cache_key, result, ttl=1800)
    return jsonify(result)


@api_bp.get("/products/<int:product_id>")
def get_product(product_id: int):
    """获取商品详情（支持Redis缓存）"""
    from backend.database import SessionLocal
    from backend.repositories.product_repo import ProductRepository

    cache_key = CacheService.product_key(str(product_id))
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"商品详情缓存命中: product_id={product_id}")
        return jsonify(cached)

    with SessionLocal() as db:
        repo = ProductRepository(db)
        product = repo.get_with_reviews(product_id)
        if not product:
            return jsonify({"error": "not_found", "message": "商品不存在"}), 404
        data = product.to_dict()
        data["reviews"] = [r.to_dict() for r in product.reviews[:50]]

    cache.set(cache_key, data, ttl=3600)
    return jsonify(data)


@api_bp.get("/products/<int:product_id>/reviews")
def get_product_reviews(product_id: int):
    """获取商品评论（支持Redis缓存）"""
    from backend.database import SessionLocal
    from backend.repositories.review_repo import ReviewRepository

    limit = int(request.args.get("limit", 100))

    cache_key = CacheService.reviews_key(str(product_id))
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"评论缓存命中: product_id={product_id}")
        return jsonify(cached)

    with SessionLocal() as db:
        repo = ReviewRepository(db)
        reviews = repo.get_by_product(product_id, limit)
        result = {
            "product_id": product_id,
            "total": len(reviews),
            "reviews": [r.to_dict() for r in reviews],
        }

    cache.set(cache_key, result, ttl=3600)
    return jsonify(result)


@api_bp.get("/stats")
def get_stats():
    """获取数据统计信息"""
    from backend.database import SessionLocal
    from backend.repositories.product_repo import ProductRepository

    cache_key = "stats:overview"
    cached = cache.get(cache_key)
    if cached:
        logger.info("统计数据缓存命中")
        return jsonify(cached)

    with SessionLocal() as db:
        repo = ProductRepository(db)
        total_products = repo.count()
        categories = repo.list_categories()

        category_stats = {}
        for cat in categories:
            products = repo.list_all(cat, limit=1000)
            category_stats[cat] = {
                "count": len(products),
                "avg_price": sum(p.price for p in products if p.price) / max(1, len([p for p in products if p.price])),
                "min_price": min((p.price for p in products if p.price), default=0),
                "max_price": max((p.price for p in products if p.price), default=0),
            }

        result = {
            "total_products": total_products,
            "total_categories": len(categories),
            "categories": categories,
            "category_stats": category_stats,
        }

    cache.set(cache_key, result, ttl=600)
    return jsonify(result)


@api_bp.post("/cache/clear")
def clear_cache():
    """清除缓存（管理接口）"""
    try:
        if cache.client:
            cache.client.flushdb()
            return jsonify({"message": "缓存已清除", "success": True})
        return jsonify({"message": "Redis不可用", "success": False}), 503
    except Exception as e:
        return jsonify({"message": f"清除缓存失败: {str(e)}", "success": False}), 500
