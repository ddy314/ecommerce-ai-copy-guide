#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""构建Redis缓存"""
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def build_redis_cache():
    """将商品数据缓存到Redis"""
    import redis
    
    # Redis连接
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # 加载商品数据
    data_file = Path("products_data.json")
    if not data_file.exists():
        logger.error("找不到 products_data.json")
        return
    
    with open(data_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    
    logger.info(f"加载 {len(products)} 个商品数据")
    
    # 缓存每个商品详情
    cached_count = 0
    for product in products:
        product_id = product.get("product_id")
        if product_id:
            key = f"product:{product_id}"
            r.set(key, json.dumps(product, ensure_ascii=False), ex=3600)
            cached_count += 1
    
    # 缓存分类列表
    categories = {}
    for product in products:
        cat = product.get("category", "其他")
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    r.set("categories:list", json.dumps(categories, ensure_ascii=False), ex=3600)
    logger.info(f"✓ 缓存分类列表: {len(categories)} 个分类")
    
    # 缓存统计数据
    stats = {
        "total_products": len(products),
        "categories": list(categories.keys()),
        "category_counts": categories
    }
    r.set("stats:overview", json.dumps(stats, ensure_ascii=False), ex=600)
    logger.info(f"✓ 缓存统计数据")
    
    logger.info(f"✓ Redis缓存完成! 共缓存 {cached_count} 个商品")

if __name__ == "__main__":
    build_redis_cache()