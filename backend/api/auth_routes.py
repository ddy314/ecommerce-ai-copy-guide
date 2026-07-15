"""认证路由 - 登录/注册/找回密码/头像上传"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request, send_from_directory, current_app
from sqlalchemy import select
from werkzeug.utils import secure_filename

from backend.database import SessionLocal
from backend.models.user import User
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
)
from backend.utils.helpers import generate_user_display_id

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

# 允许的图片扩展名
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


# MIME 类型到标准扩展名的映射（用于无扩展名或扩展名异常时的兜底判断）
_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}


def _extension_from_mime(content_type: str | None) -> str | None:
    return _MIME_TO_EXT.get((content_type or "").lower().split(";")[0].strip())


def _allowed_file(file, allowed_extensions: set[str]) -> bool:
    """判断文件是否允许上传：优先扩展名，其次 MIME 类型。"""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext in allowed_extensions:
        return True
    # 扩展名不在白名单时，根据 MIME 类型兜底判断
    mime_ext = _extension_from_mime(file.content_type)
    return mime_ext is not None and mime_ext in allowed_extensions


def _ensure_upload_dir(subdir: str) -> str:
    upload_folder = current_app.config.get("UPLOAD_FOLDER") or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "uploads"
    )
    path = os.path.join(upload_folder, subdir)
    os.makedirs(path, exist_ok=True)
    return path


def _file_extension(file) -> str:
    """获取文件的标准扩展名：优先文件名扩展名，其次 MIME 类型。"""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext:
        return ext
    mime_ext = _extension_from_mime(file.content_type)
    if mime_ext:
        return mime_ext
    return ""


def _save_uploaded_file(file, subdir: str, allowed_extensions: set[str]) -> str:
    """保存上传文件，返回相对 URL 路径"""
    if not file or not file.filename:
        raise ValueError("未选择文件")
    if not _allowed_file(file, allowed_extensions):
        raise ValueError(f"不支持的文件格式，支持: {', '.join(allowed_extensions)}")

    ext = _file_extension(file)
    filename = secure_filename(file.filename)
    # secure_filename 可能丢失扩展名，确保扩展名存在
    if ext and not filename.lower().endswith(ext):
        filename = f"{filename}{ext}"

    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    save_dir = _ensure_upload_dir(subdir)
    save_path = os.path.join(save_dir, unique_name)
    file.save(save_path)
    return f"/uploads/{subdir}/{unique_name}"


@auth_bp.post("/auth/login")
def login():
    """用户登录"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "invalid_input", "message": "账号和密码不能为空"}), 400

    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            return jsonify({"error": "not_found", "message": "账号不存在"}), 404

        if not verify_password(password, user.password_hash):
            return jsonify({"error": "wrong_password", "message": "密码错误"}), 401

        if not user.is_active:
            return jsonify({"error": "disabled", "message": "账号已被禁用"}), 403

        # 验证角色匹配
        if role and role != user.role:
            return jsonify({
                "error": "role_mismatch",
                "message": f"该账号是{'商家管理员' if user.role == 'merchant' else '普通用户'}，请切换身份登录"
            }), 403

        token = create_token(user.id, user.username, user.role)
        user_data = user.to_dict()
        user_data["token"] = token

        return jsonify({
            "message": "登录成功",
            "user": user_data,
            "token": token,
        })


@auth_bp.post("/auth/register")
def register():
    """用户注册（仅普通用户）"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    nickname = data.get("nickname", "").strip()

    if not username or not password:
        return jsonify({"error": "invalid_input", "message": "账号和密码不能为空"}), 400
    if len(password) < 6:
        return jsonify({"error": "weak_password", "message": "密码长度至少6位"}), 400
    if len(username) < 3:
        return jsonify({"error": "invalid_username", "message": "账号长度至少3位"}), 400

    with SessionLocal() as db:
        existing = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if existing:
            return jsonify({"error": "exists", "message": "账号已存在"}), 409

        user = User(
            username=username,
            password_hash=hash_password(password),
            nickname=nickname or username,
            role="user",
        )
        db.add(user)
        user.display_id = generate_user_display_id(db)
        db.commit()
        db.refresh(user)

        token = create_token(user.id, user.username, user.role)

        return jsonify({
            "message": "注册成功",
            "user": user.to_dict(),
            "token": token,
        })


@auth_bp.post("/auth/check-username")
def check_username():
    """检查用户名是否存在（找回密码第一步）"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()

    if not username:
        return jsonify({"error": "invalid_input", "message": "请输入账号"}), 400

    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            return jsonify({"exists": False, "message": "账号不存在"}), 404

        return jsonify({
            "exists": True,
            "message": "账号验证通过",
            "hint": f"找回账号：{user.nickname or user.username}",
        })


@auth_bp.post("/auth/reset-password")
def reset_password():
    """重置密码"""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    new_password = data.get("new_password", "")

    if not username or not new_password:
        return jsonify({"error": "invalid_input", "message": "账号和新密码不能为空"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "weak_password", "message": "密码长度至少6位"}), 400

    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            return jsonify({"error": "not_found", "message": "账号不存在"}), 404

        user.password_hash = hash_password(new_password)
        db.commit()

        return jsonify({"message": "密码重置成功，请使用新密码登录"})


@auth_bp.get("/auth/me")
def get_current_user():
    """获取当前登录用户信息"""
    from backend.services.auth_service import get_user_from_request

    user_payload = get_user_from_request(request)
    if not user_payload:
        return jsonify({"error": "unauthorized", "message": "请先登录"}), 401

    with SessionLocal() as db:
        user = db.get(User, user_payload["user_id"])
        if not user:
            return jsonify({"error": "not_found", "message": "用户不存在"}), 404

        return jsonify({"user": user.to_dict()})


@auth_bp.post("/auth/logout")
def logout():
    """退出登录"""
    return jsonify({"message": "已退出登录"})


@auth_bp.put("/auth/profile")
def update_profile():
    """更新用户资料"""
    from backend.services.auth_service import require_auth

    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}

    with SessionLocal() as db:
        user = db.get(User, user_payload["user_id"])
        if not user:
            return jsonify({"error": "not_found", "message": "用户不存在"}), 404

        if "nickname" in data:
            user.nickname = data["nickname"]
        if "avatar" in data:
            user.avatar = data["avatar"]
        if "phone" in data:
            user.phone = data["phone"]
        if "email" in data:
            user.email = data["email"]

        db.commit()
        db.refresh(user)

        return jsonify({"message": "资料更新成功", "user": user.to_dict()})


@auth_bp.post("/auth/avatar")
def upload_avatar():
    """上传用户头像"""
    from backend.services.auth_service import require_auth

    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    if "file" not in request.files:
        return jsonify({"error": "no_file", "message": "请上传头像文件"}), 400

    file = request.files["file"]
    try:
        avatar_url = _save_uploaded_file(file, "avatars", ALLOWED_IMAGE_EXTENSIONS)
    except ValueError as e:
        return jsonify({"error": "invalid_file", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"头像上传失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": "头像上传失败"}), 500

    with SessionLocal() as db:
        user = db.get(User, user_payload["user_id"])
        if not user:
            return jsonify({"error": "not_found", "message": "用户不存在"}), 404

        user.avatar = avatar_url
        db.commit()
        db.refresh(user)

        return jsonify({"message": "头像上传成功", "avatar": avatar_url, "user": user.to_dict()})


@auth_bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    """提供上传文件访问"""
    upload_folder = current_app.config.get("UPLOAD_FOLDER") or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "uploads"
    )
    return send_from_directory(upload_folder, filename)
