from __future__ import annotations

import logging
import sys

from flask import Flask, jsonify

from backend.api.routes import api_bp
from backend.api.auth_routes import auth_bp
from backend.api.merchant_routes import merchant_bp
from backend.api.user_routes import user_bp
from backend.api.crawl_routes import crawl_bp
from backend.config import AppConfig
from backend.docs.openapi import docs_bp
from backend.database import init_db

logger = logging.getLogger(__name__)


def setup_logging(app_config: AppConfig) -> None:
    """配置日志系统"""
    log_level = logging.DEBUG if app_config.app_env == "development" else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def _create_default_users():
    """创建默认测试账号"""
    try:
        from backend.database import SessionLocal
        from backend.models.user import User
        from backend.services.auth_service import hash_password
        from sqlalchemy import select

        with SessionLocal() as db:
            # 创建默认商家账号
            merchant = db.execute(
                select(User).where(User.username == "merchant")
            ).scalar_one_or_none()
            if not merchant:
                merchant = User(
                    username="merchant",
                    password_hash=hash_password("merchant123"),
                    password_plain="merchant123",
                    nickname="商家管理员",
                    role="merchant",
                )
                db.add(merchant)
                logger.info("已创建默认商家账号: merchant / merchant123")

            # 创建默认用户账号
            user = db.execute(
                select(User).where(User.username == "user")
            ).scalar_one_or_none()
            if not user:
                user = User(
                    username="user",
                    password_hash=hash_password("user123"),
                    password_plain="user123",
                    nickname="测试用户",
                    role="user",
                )
                db.add(user)
                logger.info("已创建默认用户账号: user / user123")

            db.commit()
    except Exception as e:
        logger.warning(f"默认账号创建失败: {e}")


def create_app(config: AppConfig | None = None) -> Flask:
    app_config = config or AppConfig.from_env()
    setup_logging(app_config)
    
    app = Flask(__name__)
    app.config["APP_CONFIG"] = app_config
    
    logger = logging.getLogger(__name__)
    logger.info(f"启动应用: env={app_config.app_env}, host={app_config.app_host}, port={app_config.app_port}")

    @app.get("/health")
    def health() -> tuple[dict[str, object], int]:
        return {
            "status": "ok",
            "service": "ecommerce-ai-copy-guide",
            "version": "0.2.0",
            "runtime": app_config.public_summary(),
        }, 200

    @app.errorhandler(404)
    def not_found(_error: Exception):
        logger.warning(f"404 Not Found: {_error}")
        return jsonify({
            "error": "not_found",
            "message": "请求的资源不存在"
        }), 404

    @app.errorhandler(500)
    def server_error(_error: Exception):
        logger.error(f"500 Internal Server Error: {_error}", exc_info=True)
        return jsonify({
            "error": "server_error",
            "message": "服务器内部错误"
        }), 500

    @app.errorhandler(400)
    def bad_request(_error: Exception):
        logger.warning(f"400 Bad Request: {_error}")
        return jsonify({
            "error": "bad_request",
            "message": "请求格式错误"
        }), 400

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return response

    # 初始化数据库表
    try:
        init_db()
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.warning(f"数据库初始化失败（可能需要手动建表）: {e}")

    # 创建默认商家账号（如果不存在）
    _create_default_users()

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(merchant_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(crawl_bp, url_prefix="/api")
    app.register_blueprint(docs_bp)
    logger.info("应用初始化完成，已注册全部蓝图: API + 认证 + 商家 + 用户")
    return app


app = create_app()

if __name__ == "__main__":
    config = AppConfig.from_env()
    logger.info(f"启动服务: {config.app_host}:{config.app_port}")
    app.run(host=config.app_host, port=config.app_port, debug=(config.app_env == "development"))
