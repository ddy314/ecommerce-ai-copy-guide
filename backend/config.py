from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration loaded from environment variables."""

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = ""
    redis_url: str = ""
    ai_provider: str = ""
    ai_model: str = ""

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8000")),
            database_url=os.getenv("DATABASE_URL", ""),
            redis_url=os.getenv("REDIS_URL", ""),
            ai_provider=os.getenv("AI_PROVIDER", ""),
            ai_model=os.getenv("AI_MODEL", ""),
        )

    def public_summary(self) -> dict[str, str | bool | int]:
        return {
            "environment": self.app_env,
            "host": self.app_host,
            "port": self.app_port,
            "database_configured": bool(self.database_url),
            "redis_configured": bool(self.redis_url),
            "ai_provider": self.ai_provider or "mock",
            "ai_model": self.ai_model or "deterministic-template",
        }
