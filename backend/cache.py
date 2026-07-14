"""Redis 缓存层"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


class CacheService:
    """缓存服务封装"""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._available = None

    @property
    def client(self) -> redis.Redis | None:
        if self._available is False:
            return None
        try:
            client = get_redis()
            if self._available is None:
                client.ping()
                self._available = True
            return client
        except redis.ConnectionError as e:
            logger.warning(f"Redis 连接失败，缓存功能降级: {e}")
            self._available = False
            return None
        except Exception as e:
            logger.warning(f"Redis 不可用: {e}")
            self._available = False
            return None

    def get(self, key: str) -> Any | None:
        if not self.client:
            return None
        try:
            data = self.client.get(key)
            if data is None:
                return None
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
        except Exception as e:
            logger.debug(f"缓存读取失败: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self.client:
            return
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            self.client.setex(key, ttl or self.default_ttl, serialized)
        except Exception as e:
            logger.debug(f"缓存写入失败: {e}")

    def delete(self, key: str) -> None:
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        if not self.client:
            return False
        try:
            return self.client.exists(key) > 0
        except Exception:
            return False

    # 缓存键命名规范
    @staticmethod
    def product_key(product_id: str) -> str:
        return f"product:{product_id}"

    @staticmethod
    def reviews_key(product_id: str) -> str:
        return f"reviews:{product_id}"

    @staticmethod
    def copy_key(product_id: str, tone: str) -> str:
        return f"copy:{product_id}:{tone}"

    @staticmethod
    def recommend_key(user_need_hash: str) -> str:
        return f"recommend:{user_need_hash}"

    @staticmethod
    def sentiment_key(product_id: str) -> str:
        return f"sentiment:{product_id}"
