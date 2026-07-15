"""Framework extensions configured once and bound by the application factory."""

from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from backend.config import AppConfig

jwt = JWTManager()


def init_extensions(app: Flask, config: AppConfig) -> None:
    app.config.update(
        JWT_SECRET_KEY=config.jwt_secret,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=24),
        JWT_TOKEN_LOCATION=["headers"],
    )
    jwt.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": list(config.cors_origins)}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=600,
    )
