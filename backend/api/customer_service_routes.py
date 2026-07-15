"""客服消息路由 - 用户与商家对话"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import select, desc, func

from backend.database import SessionLocal
from backend.models.user import User
from backend.models.product import Product
from backend.models.customer_service import CustomerServiceMessage
from backend.services.auth_service import require_auth, require_merchant
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)

cs_bp = Blueprint("customer_service", __name__)
rag_service = RAGService()


def _message_to_dict(
    msg: CustomerServiceMessage,
    user_map: dict | None = None,
    merchant_map: dict | None = None,
    product_map: dict | None = None,
) -> dict:
    user = (user_map or {}).get(msg.user_id)
    merchant = (merchant_map or {}).get(msg.sender_id) if msg.sender_id else None
    product = (product_map or {}).get(msg.product_id) if msg.product_id else None
    return {
        "id": msg.id,
        "user_id": msg.user_id,
        "product_id": msg.product_id,
        "sender_id": msg.sender_id,
        "sender_role": msg.sender_role,
        "content": msg.content,
        "is_read": msg.is_read,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "user_nickname": user.nickname if user else "",
        "user_display_id": user.display_id if user else "",
        "user_avatar_url": user.avatar if user else "",
        "merchant_nickname": merchant.nickname if merchant else "",
        "merchant_avatar_url": merchant.avatar if merchant else "",
        "product_name": product.name if product else "",
        "product_display_id": product.display_id if product else "",
    }


@cs_bp.post("/cs/messages")
def create_message():
    """用户创建客服消息"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    product_id = data.get("product_id")

    if not content:
        return jsonify({"error": "invalid_input", "message": "消息内容不能为空"}), 400

    try:
        with SessionLocal() as db:
            if product_id:
                product = db.get(Product, product_id)
                if not product:
                    return jsonify({"error": "not_found", "message": "商品不存在"}), 404

            msg = CustomerServiceMessage(
                user_id=user_payload["user_id"],
                product_id=product_id,
                sender_role="user",
                content=content,
                is_read=False,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # AI 智能客服自动回复
            try:
                rag_result = rag_service.answer_question(
                    question=content,
                    product_id=product_id,
                    user_id=user_payload["user_id"],
                )
                ai_content = rag_result.get("answer", "")
                if ai_content:
                    ai_msg = CustomerServiceMessage(
                        user_id=user_payload["user_id"],
                        product_id=product_id,
                        sender_role="ai",
                        content=ai_content,
                        is_read=True,
                    )
                    db.add(ai_msg)
                    db.commit()
            except Exception as ai_err:
                logger.warning(f"AI 客服回复生成失败: {ai_err}")

            user = db.get(User, user_payload["user_id"])
            product_map = {}
            if msg.product_id:
                product = db.get(Product, msg.product_id)
                if product:
                    product_map[msg.product_id] = product

            return jsonify({"message": "发送成功", "data": _message_to_dict(msg, {user.id: user}, {}, product_map)}), 201
    except Exception as e:
        logger.error(f"发送客服消息失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.get("/cs/messages/my")
def my_messages():
    """用户获取自己的客服消息"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            messages = list(db.execute(
                select(CustomerServiceMessage)
                .where(CustomerServiceMessage.user_id == user_payload["user_id"])
                .order_by(CustomerServiceMessage.created_at)
            ).scalars().all())

            user = db.get(User, user_payload["user_id"])
            user_map = {user.id: user} if user else {}

            merchant_ids = {m.sender_id for m in messages if m.sender_id}
            merchant_map = {}
            if merchant_ids:
                merchants = list(db.execute(
                    select(User).where(User.id.in_(merchant_ids))
                ).scalars().all())
                merchant_map = {m.id: m for m in merchants}

            product_ids = {m.product_id for m in messages if m.product_id}
            product_map = {}
            if product_ids:
                products = list(db.execute(
                    select(Product).where(Product.id.in_(product_ids))
                ).scalars().all())
                product_map = {p.id: p for p in products}

            return jsonify({
                "messages": [_message_to_dict(m, user_map, merchant_map, product_map) for m in messages],
            })
    except Exception as e:
        logger.error(f"获取客服消息失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.get("/cs/merchant/threads")
def merchant_threads():
    """商家获取客服会话列表（每个用户最新一条）"""
    merchant, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            subquery = (
                db.query(
                    CustomerServiceMessage.user_id,
                    func.max(CustomerServiceMessage.created_at).label("last_time"),
                )
                .group_by(CustomerServiceMessage.user_id)
                .subquery()
            )
            latest = list(db.execute(
                select(CustomerServiceMessage)
                .join(
                    subquery,
                    (CustomerServiceMessage.user_id == subquery.c.user_id)
                    & (CustomerServiceMessage.created_at == subquery.c.last_time),
                )
                .order_by(desc(CustomerServiceMessage.created_at))
            ).scalars().all())

            user_ids = {m.user_id for m in latest}
            users = {}
            if user_ids:
                users = {
                    u.id: u
                    for u in db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
                }

            result = []
            for msg in latest:
                user = users.get(msg.user_id)
                if not user:
                    continue
                unread_count = db.execute(
                    select(func.count(CustomerServiceMessage.id))
                    .where(
                        CustomerServiceMessage.user_id == msg.user_id,
                        CustomerServiceMessage.sender_role == "user",
                        CustomerServiceMessage.is_read == False,
                    )
                ).scalar() or 0
                result.append({
                    "user_id": msg.user_id,
                    "user_nickname": user.nickname or user.username,
                    "user_display_id": user.display_id or "",
                    "user_avatar_url": user.avatar or "",
                    "last_message": msg.content,
                    "last_time": msg.created_at.isoformat() if msg.created_at else None,
                    "unread_count": unread_count,
                    "product_id": msg.product_id,
                })

            return jsonify({"threads": result})
    except Exception as e:
        logger.error(f"获取客服会话列表失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.get("/cs/merchant/threads/<int:user_id>")
def merchant_thread_detail(user_id: int):
    """商家获取与某用户的完整对话，并标记用户未读消息为已读"""
    merchant, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            messages = list(db.execute(
                select(CustomerServiceMessage)
                .where(CustomerServiceMessage.user_id == user_id)
                .order_by(CustomerServiceMessage.created_at)
            ).scalars().all())

            user = db.get(User, user_id)
            user_map = {user_id: user} if user else {}

            merchant_ids = {m.sender_id for m in messages if m.sender_id}
            merchant_map = {}
            if merchant_ids:
                merchants = list(db.execute(
                    select(User).where(User.id.in_(merchant_ids))
                ).scalars().all())
                merchant_map = {m.id: m for m in merchants}

            product_ids = {m.product_id for m in messages if m.product_id}
            product_map = {}
            if product_ids:
                products = list(db.execute(
                    select(Product).where(Product.id.in_(product_ids))
                ).scalars().all())
                product_map = {p.id: p for p in products}

            # 标记用户发送的未读消息为已读
            unread_user_messages = [
                m for m in messages
                if m.sender_role == "user" and not m.is_read
            ]
            for m in unread_user_messages:
                m.is_read = True
            if unread_user_messages:
                db.commit()

            return jsonify({
                "messages": [_message_to_dict(m, user_map, merchant_map, product_map) for m in messages],
            })
    except Exception as e:
        logger.error(f"获取客服对话详情失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.post("/cs/merchant/threads/<int:user_id>/reply")
def merchant_reply(user_id: int):
    """商家回复用户"""
    merchant, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    product_id = data.get("product_id")

    if not content:
        return jsonify({"error": "invalid_input", "message": "回复内容不能为空"}), 400

    try:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            if not user:
                return jsonify({"error": "not_found", "message": "用户不存在"}), 404

            # 当前登录的商家账号也是一个 User 记录
            merchant_user = db.get(User, merchant["user_id"])
            if not merchant_user:
                return jsonify({"error": "not_found", "message": "商家账号不存在"}), 404

            latest = db.execute(
                select(CustomerServiceMessage)
                .where(CustomerServiceMessage.user_id == user_id)
                .order_by(desc(CustomerServiceMessage.created_at))
            ).scalars().first()
            product_id = product_id or (latest.product_id if latest else None)

            if product_id:
                product = db.get(Product, product_id)
                if not product:
                    return jsonify({"error": "not_found", "message": "商品不存在"}), 404

            msg = CustomerServiceMessage(
                user_id=user_id,
                product_id=product_id,
                sender_id=merchant_user.id,
                sender_role="merchant",
                content=content,
                is_read=True,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            product_map = {}
            if msg.product_id:
                product = db.get(Product, msg.product_id)
                if product:
                    product_map[msg.product_id] = product

            return jsonify({
                "message": "回复成功",
                "data": _message_to_dict(msg, {user_id: user}, {merchant_user.id: merchant_user}, product_map),
            }), 201
    except Exception as e:
        logger.error(f"商家回复失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.patch("/cs/messages/<int:message_id>/read")
def mark_read(message_id: int):
    """标记消息为已读"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            msg = db.get(CustomerServiceMessage, message_id)
            if not msg:
                return jsonify({"error": "not_found", "message": "消息不存在"}), 404

            if user_payload.get("role") == "user" and msg.user_id != user_payload["user_id"]:
                return jsonify({"error": "forbidden", "message": "无权操作"}), 403

            msg.is_read = True
            db.commit()

            return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"标记消息已读失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.get("/cs/merchant/profile")
def merchant_profile():
    """获取商家信息（用于用户端客服展示商家头像）"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            merchant = db.execute(
                select(User).where(User.role == "merchant").order_by(User.id)
            ).scalars().first()
            if not merchant:
                return jsonify({"error": "not_found", "message": "暂无商家信息"}), 404
            return jsonify({"merchant": merchant.to_dict()})
    except Exception as e:
        logger.error(f"获取商家信息失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@cs_bp.get("/cs/merchant/unread-count")
def merchant_unread_count():
    """商家未读用户消息数"""
    merchant, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            count = db.execute(
                select(func.count(CustomerServiceMessage.id))
                .where(
                    CustomerServiceMessage.sender_role == "user",
                    CustomerServiceMessage.is_read == False,
                )
            ).scalar() or 0

            return jsonify({"count": count})
    except Exception as e:
        logger.error(f"获取未读消息数失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500
