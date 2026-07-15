"""HTTP API blueprints exposed by the Flask application."""

from flask import Blueprint

from backend.api.auth_routes import auth_bp
from backend.api.crawl_routes import crawl_bp
from backend.api.customer_service_routes import cs_bp
from backend.api.merchant_routes import merchant_bp
from backend.api.routes import api_bp
from backend.api.user_routes import user_bp

BLUEPRINTS: tuple[Blueprint, ...] = (
    api_bp,
    auth_bp,
    merchant_bp,
    user_bp,
    crawl_bp,
    cs_bp,
)

__all__ = ["BLUEPRINTS"]
