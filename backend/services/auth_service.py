"""Authentication adapter backed by Werkzeug and Flask-JWT-Extended."""
from __future__ import annotations

import hashlib
import hmac
import logging

from flask_jwt_extended import create_access_token, decode_token, get_jwt, verify_jwt_in_request
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash new passwords with Werkzeug's maintained password API."""
    return generate_password_hash(password, method="scrypt")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify current hashes while retaining compatibility with legacy salt hashes."""
    if password_hash.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(password_hash, password)
    try:
        salt, stored_hash = password_hash.split("$", 1)
        computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return hmac.compare_digest(computed, stored_hash)
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    """Create a standards-compliant signed JWT with application claims."""
    return create_access_token(
        identity=str(user_id),
        additional_claims={"user_id": user_id, "username": username, "role": role},
    )


def verify_token(token: str) -> dict | None:
    """Decode a JWT through Flask-JWT-Extended."""
    try:
        payload = decode_token(token)
        return {
            "user_id": int(payload["sub"]),
            "username": payload.get("username", ""),
            "role": payload.get("role", "user"),
        }
    except Exception as e:
        logger.debug(f"Token 验证失败: {e}")
        return None

def get_user_from_request(request) -> dict | None:
    """Verify the bearer token and expose the existing payload shape to routes."""
    del request
    try:
        verify_jwt_in_request()
        payload = get_jwt()
        return {
            "user_id": int(payload["sub"]),
            "username": payload.get("username", ""),
            "role": payload.get("role", "user"),
        }
    except Exception as exc:
        logger.debug("Token 验证失败: %s", exc)
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
