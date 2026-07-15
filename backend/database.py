"""SQLAlchemy engine and session lifecycle.

Schema evolution belongs to Alembic under ``migrations/``. ``init_db`` remains a
small compatibility helper for tests and first-run local SQLite databases.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()
logger = logging.getLogger(__name__)


def _resolve_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL", "")
    if not configured_url:
        instance_dir = Path(__file__).resolve().parents[1] / "instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        database_path = instance_dir / "ecommerce_ai.db"
        logger.info("未配置 DATABASE_URL，使用 SQLite: %s", database_path)
        return f"sqlite:///{database_path}"
    if configured_url.startswith("postgresql://"):
        return configured_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return configured_url


DATABASE_URL = _resolve_database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


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
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def init_db() -> None:
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
