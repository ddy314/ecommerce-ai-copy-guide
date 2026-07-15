"""认证服务 - JWT Token + 密码哈希"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import logging
import secrets

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "ecommerce-ai-secret-key-2026")
JWT_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """密码哈希 - 使用 salt + sha256"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        salt, stored_hash = password_hash.split("$")
        computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return hmac.compare_digest(computed, stored_hash)
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    """创建 JWT Token (简化版)"""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,
        "iat": int(time.time()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = _base64_encode(payload_json)
    signature = _sign(f"{payload_b64}")
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> dict | None:
    """验证 Token，返回 payload 或 None"""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = _sign(payload_b64)
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload_json = _base64_decode(payload_b64)
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception as e:
        logger.debug(f"Token 验证失败: {e}")
        return None


def _base64_encode(data: str) -> str:
    import base64
    return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")


def _base64_decode(data: str) -> str:
    import base64
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode()).decode()


def _sign(data: str) -> str:
    return hmac.new(JWT_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def get_user_from_request(request) -> dict | None:
    """从 Flask request 中提取用户信息"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return verify_token(token)
    return None


def require_auth(request) -> tuple[dict | None, dict | None]:
    """验证认证，返回 (user_payload, error_response)"""
    user = get_user_from_request(request)
    if not user:
        return None, {"error": "unauthorized", "message": "请先登录"}
    return user, None


def require_merchant(request) -> tuple[dict | None, dict | None]:
    """验证商家权限"""
    user, error = require_auth(request)
    if error:
        return None, error
    if user.get("role") != "merchant":
        return None, {"error": "forbidden", "message": "需要商家权限"}
    return user, None
