"""认证路由 - 登录/注册/找回密码"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models.user import User
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


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
