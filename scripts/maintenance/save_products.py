#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""保存爬取的商品数据到数据库"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 数据文件（从爬虫输出保存）
DATA_FILE = "products_data.json"


def load_products_from_file():
    """从文件加载商品数据"""
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_to_database_simple(products: list):
    """简单方式保存到数据库（直接SQL）"""
    import psycopg2
    from psycopg2.extras import execute_values

    # 数据库连接配置
    conn = psycopg2.connect(
        host="localhost",
        database="ecommerce_ai",
        user="postgres",
        password="Lky060413"
    )

    cursor = conn.cursor()

    # 创建表（如果不存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            platform VARCHAR(50),
            product_id VARCHAR(100) UNIQUE,
            name VARCHAR(500),
            category VARCHAR(100),
            price DECIMAL(10, 2),
            brand VARCHAR(100),
            image_url TEXT,
            detail_url TEXT,
            specs TEXT,
            selling_points TEXT,
            sales_count INTEGER DEFAULT 0,
            rating DECIMAL(3, 2) DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    from datetime import datetime
    now = datetime.now()
    
    values = []
    for p in products:
        row = (
            p.get("platform", "jd"),
            p.get("product_id"),
            p.get("name", ""),
            p.get("category", "其他"),
            p.get("price"),
            p.get("brand"),
            p.get("image_url"),
            p.get("detail_url"),
            p.get("specs"),
            p.get("selling_points"),
            p.get("sales_count", 0),
            p.get("rating", 0),
            p.get("review_count", 0),
            now,  # created_at
            now,  # updated_at
        )
        values.append(row)

    # 批量插入（ON CONFLICT UPDATE）
    sql = """
        INSERT INTO products (platform, product_id, name, category, price, brand, 
                             image_url, detail_url, specs, selling_points, 
                             sales_count, rating, review_count, created_at, updated_at)
        VALUES %s
        ON CONFLICT (product_id) DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            price = EXCLUDED.price,
            brand = EXCLUDED.brand,
            image_url = EXCLUDED.image_url,
            specs = EXCLUDED.specs,
            selling_points = EXCLUDED.selling_points,
            updated_at = CURRENT_TIMESTAMP
    """

    execute_values(cursor, sql, values)
    conn.commit()

    # 统计
    cursor.execute("SELECT COUNT(*) FROM products")
    total = cursor.fetchone()[0]

    # 分类统计
    cursor.execute("SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY COUNT(*) DESC")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    logger.info(f"✓ 保存 {len(products)} 个商品到数据库")
    logger.info(f"✓ 数据库总商品数: {total}")
    logger.info("✓ 分类统计:")
    for cat, count in categories:
        logger.info(f"  {cat}: {count} 个")

    return total


if __name__ == "__main__":
    # 从命令行参数获取商品数据
    if len(sys.argv) > 1:
        products = json.loads(sys.argv[1])
    else:
        products = load_products_from_file()

    if products:
        save_to_database_simple(products)
    else:
        logger.warning("没有商品数据需要保存")
