"""爬虫管理路由 - 苏宁易购商品爬取"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from backend.services.auth_service import require_merchant
from backend.crawler.crawl_manager import crawl_manager
from backend.database import SessionLocal
from backend.models.product import Product
from sqlalchemy import func

logger = logging.getLogger(__name__)

crawl_bp = Blueprint("crawl", __name__)

# 预设搜索关键词（与苏宁爬虫的关键词映射一致）
PRESET_KEYWORDS = {
    "数码电子": ["蓝牙耳机", "无线耳机", "手机", "机械键盘", "无线鼠标", "蓝牙音箱"],
    "生活用品": ["保温杯", "水杯"],
    "家居家电": ["台灯", "落地灯"],
    "办公家具": ["办公椅", "人体工学椅", "升降桌"],
    "服装服饰": ["T恤", "衬衫"],
    "户外运动": ["背包", "露营椅", "帐篷"],
}


@crawl_bp.get("/crawl/test")
def api_test_crawl():
    """测试爬虫连接（访问苏宁首页）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        import requests
        r = requests.get(
            "https://www.suning.com/",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        ok = r.status_code == 200
        return jsonify({
            "crawl_ok": ok,
            "platform": "suning",
            "message": "苏宁易购可访问" if ok else "苏宁易购访问失败",
            "status_code": r.status_code,
        })
    except Exception as e:
        return jsonify({"crawl_ok": False, "message": f"连接失败: {str(e)}"}), 500


@crawl_bp.get("/crawl/preset-keywords")
def api_preset_keywords():
    """获取预设搜索关键词"""
    return jsonify({"keywords": PRESET_KEYWORDS})


@crawl_bp.post("/crawl/start")
def api_start_crawl():
    """启动爬虫任务"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    keywords = data.get("keywords", [])
    pages_per_keyword = int(data.get("pages_per_keyword", 2))

    if not keywords:
        return jsonify({"error": "invalid_input", "message": "请提供搜索关键词"}), 400

    if pages_per_keyword < 1 or pages_per_keyword > 5:
        pages_per_keyword = 2

    if len(keywords) > 20:
        keywords = keywords[:20]

    task_id = crawl_manager.create_task(keywords, pages_per_keyword)
    crawl_manager.run_task(task_id)

    return jsonify({
        "message": "爬虫任务已启动",
        "task_id": task_id,
        "keywords": keywords,
        "pages_per_keyword": pages_per_keyword,
        "platform": "suning",
    }), 202


@crawl_bp.get("/crawl/status/<task_id>")
def api_crawl_status(task_id: str):
    """查询爬虫任务状态"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    task = crawl_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "not_found", "message": "任务不存在"}), 404

    return jsonify(task.to_dict())


@crawl_bp.get("/crawl/tasks")
def api_crawl_tasks():
    """获取所有爬虫任务列表"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    return jsonify({"tasks": crawl_manager.list_tasks()})


@crawl_bp.post("/crawl/preset")
def api_start_preset_crawl():
    """一键爬取预设关键词"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    categories = data.get("categories", [])
    pages_per_keyword = int(data.get("pages_per_keyword", 2))

    if not categories:
        categories = list(PRESET_KEYWORDS.keys())

    keywords = []
    for cat in categories:
        if cat in PRESET_KEYWORDS:
            keywords.extend(PRESET_KEYWORDS[cat])

    if not keywords:
        return jsonify({"error": "invalid_input", "message": "未找到有效关键词"}), 400

    task_id = crawl_manager.create_task(keywords, pages_per_keyword)
    crawl_manager.run_task(task_id)

    return jsonify({
        "message": f"已启动爬虫任务，共 {len(keywords)} 个关键词",
        "task_id": task_id,
        "keywords": keywords,
        "platform": "suning",
    }), 202


@crawl_bp.get("/crawl/stats")
def api_crawl_stats():
    """获取已爬取商品的统计信息"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    with SessionLocal() as db:
        total = db.query(func.count(Product.id)).scalar() or 0
        suning_count = db.query(func.count(Product.id)).filter(
            Product.platform == "suning"
        ).scalar() or 0

        cat_stats = db.query(
            Product.category, func.count(Product.id)
        ).filter(
            Product.platform == "suning"
        ).group_by(Product.category).all()

        return jsonify({
            "total_products": total,
            "suning_products": suning_count,
            "categories": {cat: cnt for cat, cnt in cat_stats if cat},
            "platform": "suning",
        })


@crawl_bp.post("/vector/build")
def api_build_vector_index():
    """构建/更新向量索引（从数据库全量商品构建）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    from backend.services.vector_index import vector_index
    from sqlalchemy import select

    with SessionLocal() as db:
        products = list(db.execute(
            select(Product)
        ).scalars().all())

    count = vector_index.build_index(products)
    return jsonify({
        "message": "向量索引构建成功",
        "indexed_count": count,
        "status": vector_index.get_status(),
    })


@crawl_bp.get("/vector/status")
def api_vector_status():
    """获取向量索引状态"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    from backend.services.vector_index import vector_index
    return jsonify(vector_index.get_status())
