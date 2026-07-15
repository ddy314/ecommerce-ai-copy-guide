"""数据库连接与会话管理"""

from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

load_dotenv()
logger = logging.getLogger(__name__)


def _resolve_database_url() -> str:
    """解析数据库 URL，PostgreSQL 不可用时降级到 SQLite"""
    configured_url = os.getenv("DATABASE_URL", "")

    # 如果没有配置，直接用 SQLite
    if not configured_url:
        logger.info("未配置 DATABASE_URL，使用 SQLite: ./ecommerce_ai.db")
        return "sqlite:///./ecommerce_ai.db"

    # 如果配置的是 SQLite，直接用
    if configured_url.startswith("sqlite"):
        return configured_url

    # 如果配置的是 PostgreSQL，检查项目实际使用的 psycopg v3 驱动是否可用
    if configured_url.startswith("postgresql"):
        try:
            import psycopg  # noqa: F401

            # 尝试连接
            engine = create_engine(configured_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            logger.info("使用 PostgreSQL 数据库")
            return configured_url
        except ImportError:
            logger.warning("psycopg 未安装，降级使用 SQLite: ./ecommerce_ai.db")
            return "sqlite:///./ecommerce_ai.db"
        except Exception as e:
            logger.warning(f"PostgreSQL 连接失败 ({e})，降级使用 SQLite: ./ecommerce_ai.db")
            return "sqlite:///./ecommerce_ai.db"

    # 其他情况使用配置的 URL
    return configured_url


DATABASE_URL = _resolve_database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # SQLite 启用外键约束
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=os.getenv("APP_ENV", "development") == "development",
    )

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """创建所有表并执行兼容性迁移"""
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # 1. 先补齐所有缺失的数据库字段（避免后续数据迁移因字段不存在而失败）
    _add_password_plain_column()
    _add_product_media_columns()
    _add_review_media_columns()
    _add_product_published_column()
    _add_order_extra_columns()
    _add_display_id_columns()
    _add_review_user_id_column()
    # 2. 数据迁移：将残留明文密码哈希化并清空明文
    _hash_existing_plain_passwords()
    # 3. 规范化已有订单编号
    _normalize_order_numbers()


def _add_password_plain_column() -> None:
    """为已有 users 表添加 password_plain 字段（如果不存在）"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("users")]
            if "password_plain" not in columns:
                with engine.connect() as conn:
                    if DATABASE_URL.startswith("sqlite"):
                        conn.execute(
                            text("ALTER TABLE users ADD COLUMN password_plain VARCHAR(100)")
                        )
                    else:
                        conn.execute(
                            text("ALTER TABLE users ADD COLUMN password_plain VARCHAR(100)")
                        )
                    conn.commit()
                logger.info("已为 users 表添加 password_plain 字段")
    except Exception as e:
        logger.warning(f"添加 password_plain 字段失败: {e}")


def _add_display_id_columns() -> None:
    """为已有 users 和 products 表添加 display_id 字段并回填缺失值（如果不存在）"""
    from backend.models.user import User
    from backend.models.product import Product

    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)

        if "users" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("users")]
            if "display_id" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN display_id VARCHAR(64)"))
                    conn.commit()
                logger.info("已为 users 表添加 display_id 字段")

        if "products" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("products")]
            if "display_id" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE products ADD COLUMN display_id VARCHAR(64)"))
                    conn.commit()
                logger.info("已为 products 表添加 display_id 字段")

        # 回填缺失的 display_id（基于当前数据库计数顺序生成，避免未提交事务导致重复）
        with SessionLocal() as db:
            from datetime import datetime

            user_updated = 0
            users = (
                db.query(User).filter((User.display_id.is_(None)) | (User.display_id == "")).all()
            )
            if users:
                today = datetime.now().strftime("%Y%m%d")
                base_user_count = db.query(User).filter(User.display_id.like(f"{today}%")).count()
                for i, user in enumerate(users):
                    user.display_id = f"{today}{base_user_count + i + 1:07d}"
                    user_updated += 1
                db.commit()
                logger.info(f"已回填 {user_updated} 个用户的 display_id")

            product_updated = 0
            products = (
                db.query(Product)
                .filter((Product.display_id.is_(None)) | (Product.display_id == ""))
                .all()
            )
            if products:
                base_product_count = db.query(Product).count()
                for i, product in enumerate(products):
                    product.display_id = f"{base_product_count + i + 1:05d}"
                    product_updated += 1
                db.commit()
                logger.info(f"已回填 {product_updated} 个商品的 display_id")
    except Exception as e:
        logger.warning(f"添加 display_id 字段失败: {e}")


def _add_product_media_columns() -> None:
    """为已有 products 表添加 image_urls / videos 字段（如果不存在）"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)

        if "products" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("products")]
            with engine.connect() as conn:
                if "image_urls" not in columns:
                    if DATABASE_URL.startswith("sqlite"):
                        conn.execute(text("ALTER TABLE products ADD COLUMN image_urls JSON"))
                    else:
                        conn.execute(text("ALTER TABLE products ADD COLUMN image_urls JSONB"))
                    logger.info("已为 products 表添加 image_urls 字段")
                if "videos" not in columns:
                    if DATABASE_URL.startswith("sqlite"):
                        conn.execute(text("ALTER TABLE products ADD COLUMN videos JSON"))
                    else:
                        conn.execute(text("ALTER TABLE products ADD COLUMN videos JSONB"))
                    logger.info("已为 products 表添加 videos 字段")
                conn.commit()
    except Exception as e:
        logger.warning(f"添加 product media 字段失败: {e}")


def _add_review_media_columns() -> None:
    """为已有 reviews 表添加 image_urls / videos 字段（如果不存在）"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)

        if "reviews" not in inspector.get_table_names():
            return

        columns = [c["name"] for c in inspector.get_columns("reviews")]
        with engine.connect() as conn:
            if "image_urls" not in columns:
                if DATABASE_URL.startswith("sqlite"):
                    conn.execute(text("ALTER TABLE reviews ADD COLUMN image_urls JSON"))
                else:
                    conn.execute(text("ALTER TABLE reviews ADD COLUMN image_urls JSONB"))
                logger.info("已为 reviews 表添加 image_urls 字段")
            if "videos" not in columns:
                if DATABASE_URL.startswith("sqlite"):
                    conn.execute(text("ALTER TABLE reviews ADD COLUMN videos JSON"))
                else:
                    conn.execute(text("ALTER TABLE reviews ADD COLUMN videos JSONB"))
                logger.info("已为 reviews 表添加 videos 字段")
            conn.commit()
    except Exception as e:
        logger.warning(f"添加 review media 字段失败: {e}")


def _add_order_extra_columns() -> None:
    """为已有 orders 表添加物流、售后与状态时间字段（如果不存在）"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)

        if "orders" not in inspector.get_table_names():
            return

        columns = [c["name"] for c in inspector.get_columns("orders")]
        is_pg = not DATABASE_URL.startswith("sqlite")

        with engine.connect() as conn:
            col_defs = [
                ("tracking_no", "VARCHAR(100)"),
                ("return_tracking_no", "VARCHAR(100)"),
                ("return_status", "VARCHAR(20)"),
                ("return_reason", "VARCHAR(500)"),
                ("return_applied_at", "TIMESTAMP" if is_pg else "DateTime"),
                ("return_completed_at", "TIMESTAMP" if is_pg else "DateTime"),
                ("paid_at", "TIMESTAMP" if is_pg else "DateTime"),
                ("shipped_at", "TIMESTAMP" if is_pg else "DateTime"),
                ("completed_at", "TIMESTAMP" if is_pg else "DateTime"),
                ("cancelled_at", "TIMESTAMP" if is_pg else "DateTime"),
            ]
            for col_name, col_type in col_defs:
                if col_name not in columns:
                    try:
                        conn.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        logger.info(f"已为 orders 表添加 {col_name} 字段")
                    except Exception as col_e:
                        logger.warning(f"添加 orders.{col_name} 字段失败: {col_e}")
    except Exception as e:
        logger.warning(f"添加订单扩展字段失败: {e}")


def _add_product_published_column() -> None:
    """为已有 products 表添加 is_published 字段，并将现有 NULL 回填为 True"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)

        if "products" not in inspector.get_table_names():
            return

        columns = [c["name"] for c in inspector.get_columns("products")]
        with engine.connect() as conn:
            if "is_published" not in columns:
                conn.execute(text("ALTER TABLE products ADD COLUMN is_published BOOLEAN"))
                conn.commit()
                logger.info("已为 products 表添加 is_published 字段")

        with SessionLocal() as db:
            from backend.models.product import Product

            updated = (
                db.query(Product)
                .filter(Product.is_published.is_(None))
                .update({"is_published": True}, synchronize_session=False)
            )
            db.commit()
            if updated:
                logger.info(f"已回填 {updated} 个商品的 is_published 为 True")
    except Exception as e:
        logger.warning(f"添加/回填 is_published 字段失败: {e}")


def _add_review_user_id_column() -> None:
    """为已有 reviews 表添加 user_id 字段（如果不存在）"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)

        if "reviews" not in inspector.get_table_names():
            return

        columns = [c["name"] for c in inspector.get_columns("reviews")]
        if "user_id" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE reviews ADD COLUMN user_id INTEGER"))
                conn.commit()
            logger.info("已为 reviews 表添加 user_id 字段")
    except Exception as e:
        logger.warning(f"添加 reviews.user_id 字段失败: {e}")


def _hash_existing_plain_passwords() -> None:
    """将现有 users.password_plain 明文密码哈希化到 password_hash，并清空 password_plain。

    说明：
    - 该函数不再依赖 User ORM 的 password_plain 属性，以便在模型移除该字段后仍可安全执行迁移。
    - 找到 password_plain 非空的用户，用 hash_password 重新哈希后写入 password_hash，并清空明文。
    """
    try:
        from sqlalchemy import inspect, text
        from backend.services.auth_service import hash_password

        inspector = inspect(engine)
        if "users" not in inspector.get_table_names():
            return

        columns = [c["name"] for c in inspector.get_columns("users")]
        if "password_plain" not in columns:
            return

        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, password_plain FROM users "
                    "WHERE password_plain IS NOT NULL AND password_plain != ''"
                )
            ).fetchall()
            if not rows:
                return

            updated = 0
            for user_id, plain in rows:
                plain_text = (plain or "").strip()
                if not plain_text:
                    continue
                new_hash = hash_password(plain_text)
                conn.execute(
                    text(
                        "UPDATE users SET password_hash = :h, password_plain = NULL WHERE id = :id"
                    ),
                    {"h": new_hash, "id": user_id},
                )
                updated += 1

            conn.commit()
            if updated:
                logger.info(f"已将 {updated} 个用户的明文密码迁移为哈希存储并清空明文")
    except Exception as e:
        logger.warning(f"明文密码迁移失败: {e}")


def _normalize_order_numbers() -> None:
    """将数据库中不符合规范的订单编号统一为：YYYYMMDDHHMMSS<商品展示ID><5位序号>"""
    import json
    import re

    from backend.models.shopping import Order
    from backend.models.product import Product

    try:
        from sqlalchemy import inspect

        inspector = inspect(engine)
        if "orders" not in inspector.get_table_names():
            return

        valid_pattern = re.compile(r"^\d{14}\d{5}\d{5}$")

        with SessionLocal() as db:
            orders = db.query(Order).order_by(Order.id).all()
            if not orders:
                return

            used_nos = set()
            counters: dict[str, int] = {}
            updated = 0

            for order in orders:
                if valid_pattern.match(order.order_no or ""):
                    used_nos.add(order.order_no)
                    continue

                display_id = "00000"
                try:
                    items = json.loads(order.items_snapshot or "[]")
                    if items and isinstance(items, list):
                        first_pid = items[0].get("product_id")
                        product = db.get(Product, first_pid) if first_pid else None
                        display_id = (
                            product.display_id
                            if product and product.display_id
                            else f"{int(first_pid):05d}"
                        )
                except Exception:
                    pass

                ts = (
                    order.created_at.strftime("%Y%m%d%H%M%S")
                    if order.created_at
                    else datetime.now().strftime("%Y%m%d%H%M%S")
                )
                base = f"{ts}{display_id}"
                seq = counters.get(base, 1)
                while True:
                    new_no = f"{base}{seq:05d}"
                    if new_no not in used_nos:
                        break
                    seq += 1

                order.order_no = new_no
                used_nos.add(new_no)
                counters[base] = seq + 1
                updated += 1

            db.commit()
            if updated:
                logger.info(f"已规范化 {updated} 个订单编号")
    except Exception as e:
        logger.warning(f"规范化订单编号失败: {e}")
