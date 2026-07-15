"""用户前台路由 - 购物车/订单/地址/收藏/RAG问答/评论上传"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from sqlalchemy import select, desc

from backend.api.auth_routes import (
    _save_uploaded_file,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
)
from backend.database import SessionLocal
from backend.models.product import Product
from backend.models.review import Review
from backend.models.user import UserAddress, UserFavorite, BrowseHistory
from backend.models.shopping import CartItem, Order, OrderItem
from backend.services.auth_service import require_auth
from backend.services.rag_service import RAGService
from backend.services.file_upload import FileUploadService
from backend.services.ai_provider import get_ai_provider
from backend.schemas.requests import ReviewAnalysisRequest
from backend.utils.helpers import generate_order_no

logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__)
rag_service = RAGService()
file_service = FileUploadService()
ai_service = get_ai_provider()


def _safe_int(val, default=None):
    """安全转换为 int"""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ===== 购物车 =====

@user_bp.get("/user/cart")
def get_cart():
    """获取购物车"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            items = list(db.execute(
                select(CartItem).where(CartItem.user_id == user_payload["user_id"])
            ).scalars().all())

            cart_data = []
            total = 0.0
            for item in items:
                product = db.get(Product, item.product_id)
                if not product:
                    continue
                item_data = item.to_dict()
                # 将商品信息扁平化到顶层，方便前端直接使用
                item_data["product_name"] = product.name
                item_data["product_price"] = product.price or 0
                item_data["product_image"] = product.image_url or ""
                item_data["product_category"] = product.category or ""
                item_data["product"] = product.to_dict()
                if item.selected:
                    total += (product.price or 0) * item.quantity
                cart_data.append(item_data)

            return jsonify({"items": cart_data, "total": round(total, 2), "count": len(cart_data)})
    except Exception as e:
        logger.error(f"获取购物车失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/cart")
def add_to_cart():
    """加入购物车"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    product_id = _safe_int(data.get("product_id"))
    quantity = _safe_int(data.get("quantity"), 1) or 1

    if not product_id:
        return jsonify({"error": "invalid_input", "message": "缺少商品ID"}), 400

    try:
        with SessionLocal() as db:
            product = db.get(Product, product_id)
            if not product:
                return jsonify({"error": "not_found", "message": "商品不存在"}), 404

            # 检查是否已在购物车
            existing = db.execute(
                select(CartItem).where(
                    CartItem.user_id == user_payload["user_id"],
                    CartItem.product_id == product_id,
                )
            ).scalar_one_or_none()

            if existing:
                existing.quantity += quantity
                db.commit()
                db.refresh(existing)
                item_data = existing.to_dict()
                return jsonify({"message": "数量已更新", "item": item_data})
            else:
                item = CartItem(
                    user_id=user_payload["user_id"],
                    product_id=product_id,
                    quantity=quantity,
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                item_data = item.to_dict()
                return jsonify({"message": "已加入购物车", "item": item_data}), 201
    except Exception as e:
        logger.error(f"加入购物车失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.put("/user/cart/<int:item_id>")
def update_cart_item(item_id: int):
    """更新购物车项"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}

    try:
        with SessionLocal() as db:
            item = db.get(CartItem, item_id)
            if not item or item.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "购物车项不存在"}), 404

            if "quantity" in data:
                qty = _safe_int(data["quantity"], 1)
                if qty is not None and qty <= 0:
                    db.delete(item)
                    db.commit()
                    return jsonify({"message": "已移除"})
                if qty is not None:
                    item.quantity = qty
            if "selected" in data:
                item.selected = bool(data["selected"])

            db.commit()
            db.refresh(item)
            item_data = item.to_dict()
            return jsonify({"message": "已更新", "item": item_data})
    except Exception as e:
        logger.error(f"更新购物车失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.delete("/user/cart/<int:item_id>")
def remove_cart_item(item_id: int):
    """移除购物车项"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            item = db.get(CartItem, item_id)
            if not item or item.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "购物车项不存在"}), 404

            db.delete(item)
            db.commit()
            return jsonify({"message": "已移除"})
    except Exception as e:
        logger.error(f"移除购物车项失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.delete("/user/cart")
def clear_cart():
    """清空购物车"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            items = list(db.execute(
                select(CartItem).where(CartItem.user_id == user_payload["user_id"])
            ).scalars().all())
            for item in items:
                db.delete(item)
            db.commit()
            return jsonify({"message": "购物车已清空"})
    except Exception as e:
        logger.error(f"清空购物车失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 订单 =====

@user_bp.post("/user/orders")
def create_order():
    """创建订单（模拟下单）"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    address_id = _safe_int(data.get("address_id"))
    pay_method = data.get("pay_method", "wechat")
    remark = data.get("remark", "")
    item_ids = data.get("item_ids", [])

    try:
        with SessionLocal() as db:
            # 获取购物车选中项
            stmt = select(CartItem).where(
                CartItem.user_id == user_payload["user_id"],
                CartItem.selected.is_(True),
            )
            if item_ids:
                stmt = stmt.where(CartItem.id.in_(item_ids))

            cart_items = list(db.execute(stmt).scalars().all())
            if not cart_items:
                return jsonify({"error": "empty_cart", "message": "购物车没有选中商品"}), 400

            # 获取地址
            address = None
            if address_id:
                address = db.get(UserAddress, address_id)
            if not address:
                address = db.execute(
                    select(UserAddress).where(
                        UserAddress.user_id == user_payload["user_id"],
                        UserAddress.is_default.is_(True),
                    )
                ).scalar_one_or_none()
            if not address:
                return jsonify({"error": "no_address", "message": "请先添加收货地址"}), 400

            # 计算总金额
            total_amount = 0.0
            order_items_data = []
            for ci in cart_items:
                product = db.get(Product, ci.product_id)
                if not product:
                    continue
                total_amount += (product.price or 0) * ci.quantity
                order_items_data.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "price": product.price or 0,
                    "quantity": ci.quantity,
                    "image_url": product.image_url or "",
                })

            if not order_items_data:
                return jsonify({"error": "empty_cart", "message": "没有有效商品"}), 400

            # 创建订单
            first_product_id = cart_items[0].product_id
            order_no = generate_order_no(db, first_product_id)
            order = Order(
                order_no=order_no,
                user_id=user_payload["user_id"],
                status="pending",
                total_amount=round(total_amount, 2),
                pay_method=pay_method,
                address_snapshot=json.dumps(address.to_dict(), ensure_ascii=False),
                items_snapshot=json.dumps(order_items_data, ensure_ascii=False),
                remark=remark,
            )
            db.add(order)
            db.flush()

            for oi_data in order_items_data:
                oi = OrderItem(
                    order_id=order.id,
                    product_id=oi_data["product_id"],
                    product_name=oi_data["product_name"],
                    price=oi_data["price"],
                    quantity=oi_data["quantity"],
                    image_url=oi_data["image_url"],
                )
                db.add(oi)

            # 清除已下单的购物车项
            for ci in cart_items:
                db.delete(ci)

            db.commit()
            db.refresh(order)
            order_data = order.to_dict()

            return jsonify({"message": "订单创建成功", "order": order_data}), 201
    except Exception as e:
        logger.error(f"创建订单失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/orders/<int:order_id>/pay")
def pay_order(order_id: int):
    """模拟支付"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order or order.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status != "pending":
                return jsonify({"error": "invalid_status", "message": "订单状态不允许支付"}), 400

            order.status = "paid"
            order.paid_at = datetime.now()
            db.commit()
            db.refresh(order)
            order_data = order.to_dict()

            return jsonify({"message": "支付成功", "order": order_data})
    except Exception as e:
        logger.error(f"支付订单失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/orders/<int:order_id>/cancel")
def cancel_order(order_id: int):
    """取消订单"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order or order.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status not in ("pending", "paid"):
                return jsonify({"error": "invalid_status", "message": "当前状态不可取消"}), 400

            order.status = "cancelled"
            order.cancelled_at = datetime.now()
            db.commit()
            return jsonify({"message": "订单已取消"})
    except Exception as e:
        logger.error(f"取消订单失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/orders/<int:order_id>/confirm")
def confirm_order(order_id: int):
    """确认收货"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order or order.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status != "shipped":
                return jsonify({"error": "invalid_status", "message": "当前状态不可确认收货"}), 400

            order.status = "completed"
            order.completed_at = datetime.now()
            db.commit()
            db.refresh(order)
            return jsonify({"message": "确认收货成功", "order": order.to_dict()})
    except Exception as e:
        logger.error(f"确认收货失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.get("/user/orders")
def list_orders():
    """订单列表"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    status = request.args.get("status", "")
    page = _safe_int(request.args.get("page"), 1) or 1
    page_size = _safe_int(request.args.get("page_size"), 20) or 20

    try:
        with SessionLocal() as db:
            stmt = select(Order).where(Order.user_id == user_payload["user_id"])
            if status:
                stmt = stmt.where(Order.status == status)
            stmt = stmt.order_by(desc(Order.created_at))

            all_orders = list(db.execute(stmt).scalars().all())
            total = len(all_orders)
            total_pages = max(1, (total + page_size - 1) // page_size)
            orders = all_orders[(page - 1) * page_size: page * page_size]
            orders_data = [o.to_dict() for o in orders]

            return jsonify({
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "orders": orders_data,
            })
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.get("/user/orders/<int:order_id>")
def get_order_detail(order_id: int):
    """订单详情"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order or order.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            order_data = order.to_dict()
            return jsonify({"order": order_data})
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/orders/<int:order_id>/apply-return")
def apply_return(order_id: int):
    """用户申请退换货"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    return_type = (data.get("return_type") or "return").strip()
    reason = (data.get("reason") or "").strip()

    if not reason:
        return jsonify({"error": "invalid_input", "message": "请填写退换货原因"}), 400
    if return_type not in ("return", "exchange"):
        return jsonify({"error": "invalid_input", "message": "退换货类型错误"}), 400

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order or order.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status in ("pending", "cancelled"):
                return jsonify({"error": "invalid_status", "message": "当前订单状态不可申请退换货"}), 400

            order.status = "returning"
            order.return_status = "returning"
            order.return_reason = f"[{return_type == 'return' and '退货' or '换货'}] {reason}"
            order.return_applied_at = datetime.now()
            db.commit()
            db.refresh(order)
            return jsonify({"message": "退换货申请已提交", "order": order.to_dict()})
    except Exception as e:
        logger.error(f"申请退换货失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/orders/<int:order_id>/return-tracking")
def fill_return_tracking(order_id: int):
    """用户填写退货快递单号"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    tracking_no = (data.get("tracking_no") or "").strip()

    if not tracking_no:
        return jsonify({"error": "invalid_input", "message": "请填写退货快递单号"}), 400

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order or order.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status != "returning":
                return jsonify({"error": "invalid_status", "message": "当前订单不在退换货中"}), 400

            order.return_tracking_no = tracking_no
            db.commit()
            db.refresh(order)
            return jsonify({"message": "退货快递单号已提交", "order": order.to_dict()})
    except Exception as e:
        logger.error(f"填写退货单号失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 收货地址 =====

@user_bp.get("/user/addresses")
def list_addresses():
    """地址列表"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            addresses = list(db.execute(
                select(UserAddress).where(UserAddress.user_id == user_payload["user_id"])
                .order_by(desc(UserAddress.is_default))
            ).scalars().all())

            return jsonify({"addresses": [a.to_dict() for a in addresses]})
    except Exception as e:
        logger.error(f"获取地址列表失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/addresses")
def add_address():
    """添加地址"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    # 兼容前端 recipient 和后端 name 字段
    name = data.get("name") or data.get("recipient") or ""
    phone = data.get("phone", "")
    province = data.get("province", "")
    city = data.get("city", "")
    district = data.get("district", "")
    detail = data.get("detail", "")

    if not name or not phone or not detail:
        return jsonify({"error": "invalid_input", "message": "收货人、手机号和详细地址不能为空"}), 400

    try:
        with SessionLocal() as db:
            if data.get("is_default"):
                existing_defaults = db.execute(
                    select(UserAddress).where(
                        UserAddress.user_id == user_payload["user_id"],
                        UserAddress.is_default.is_(True),
                    )
                ).scalars().all()
                for addr in existing_defaults:
                    addr.is_default = False

            address = UserAddress(
                user_id=user_payload["user_id"],
                name=name,
                phone=phone,
                province=province,
                city=city,
                district=district,
                detail=detail,
                is_default=bool(data.get("is_default", False)),
            )
            db.add(address)
            db.commit()
            db.refresh(address)
            addr_data = address.to_dict()

            return jsonify({"message": "地址添加成功", "address": addr_data}), 201
    except Exception as e:
        logger.error(f"添加地址失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.put("/user/addresses/<int:address_id>")
def update_address(address_id: int):
    """更新地址"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}

    try:
        with SessionLocal() as db:
            address = db.get(UserAddress, address_id)
            if not address or address.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "地址不存在"}), 404

            field_map = {"name": "name", "recipient": "name", "phone": "phone", "province": "province", "city": "city", "district": "district", "detail": "detail"}
            for frontend_field, backend_field in field_map.items():
                if frontend_field in data:
                    setattr(address, backend_field, data[frontend_field])
            if "is_default" in data:
                if data["is_default"]:
                    others = db.execute(
                        select(UserAddress).where(
                            UserAddress.user_id == user_payload["user_id"],
                            UserAddress.is_default.is_(True),
                        )
                    ).scalars().all()
                    for o in others:
                        o.is_default = False
                address.is_default = bool(data["is_default"])

            db.commit()
            db.refresh(address)
            addr_data = address.to_dict()
            return jsonify({"message": "地址更新成功", "address": addr_data})
    except Exception as e:
        logger.error(f"更新地址失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.delete("/user/addresses/<int:address_id>")
def delete_address(address_id: int):
    """删除地址"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            address = db.get(UserAddress, address_id)
            if not address or address.user_id != user_payload["user_id"]:
                return jsonify({"error": "not_found", "message": "地址不存在"}), 404

            db.delete(address)
            db.commit()
            return jsonify({"message": "地址已删除"})
    except Exception as e:
        logger.error(f"删除地址失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 收藏 =====

@user_bp.get("/user/favorites")
def list_favorites():
    """收藏列表"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            favs = list(db.execute(
                select(UserFavorite).where(UserFavorite.user_id == user_payload["user_id"])
            ).scalars().all())

            result = []
            for fav in favs:
                product = db.get(Product, fav.product_id)
                if product:
                    result.append(product.to_dict())

            return jsonify({"favorites": result, "total": len(result)})
    except Exception as e:
        logger.error(f"获取收藏列表失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/favorites/<int:product_id>")
def toggle_favorite(product_id: int):
    """切换收藏状态"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            existing = db.execute(
                select(UserFavorite).where(
                    UserFavorite.user_id == user_payload["user_id"],
                    UserFavorite.product_id == product_id,
                )
            ).scalar_one_or_none()

            if existing:
                db.delete(existing)
                db.commit()
                return jsonify({"message": "已取消收藏", "is_favorite": False})
            else:
                fav = UserFavorite(
                    user_id=user_payload["user_id"],
                    product_id=product_id,
                )
                db.add(fav)
                db.commit()
                return jsonify({"message": "已收藏", "is_favorite": True}), 201
    except Exception as e:
        logger.error(f"切换收藏失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 浏览记录 =====

@user_bp.post("/user/history/<int:product_id>")
def add_history(product_id: int):
    """添加浏览记录"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            history = BrowseHistory(
                user_id=user_payload["user_id"],
                product_id=product_id,
            )
            db.add(history)
            db.commit()
            return jsonify({"message": "已记录"})
    except Exception as e:
        logger.error(f"添加浏览记录失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.get("/user/history")
def list_history():
    """浏览记录"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    limit = _safe_int(request.args.get("limit"), 20) or 20

    try:
        with SessionLocal() as db:
            histories = list(db.execute(
                select(BrowseHistory).where(BrowseHistory.user_id == user_payload["user_id"])
                .order_by(desc(BrowseHistory.created_at))
                .limit(limit)
            ).scalars().all())

            result = []
            seen = set()
            for h in histories:
                if h.product_id in seen:
                    continue
                seen.add(h.product_id)
                product = db.get(Product, h.product_id)
                if product:
                    p = product.to_dict()
                    p["viewed_at"] = h.created_at.isoformat() if h.created_at else None
                    result.append(p)

            return jsonify({"history": result})
    except Exception as e:
        logger.error(f"获取浏览记录失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== RAG 智能问答 =====

@user_bp.post("/user/qa/ask")
def ask_question():
    """用户提问 - RAG 增强"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    product_id = _safe_int(data.get("product_id"))

    if not question:
        return jsonify({"error": "invalid_input", "message": "问题不能为空"}), 400

    try:
        result = rag_service.answer_question(
            question=question,
            product_id=product_id,
            user_id=user_payload["user_id"],
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"RAG问答失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/qa/stream")
def qa_stream():
    """SSE 流式问答 - 逐行推送回答"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    product_id = _safe_int(data.get("product_id"))

    if not question:
        return jsonify({"error": "invalid_input", "message": "问题不能为空"}), 400

    def generate():
        try:
            result = rag_service.answer_question(
                question=question,
                product_id=product_id,
                user_id=user_payload["user_id"],
            )

            answer = result.get("answer", "")
            product_info = result.get("product")
            related = result.get("related_products", [])

            # 先推送商品卡片数据
            if product_info:
                yield f"data: {json.dumps({'type': 'product', 'data': product_info}, ensure_ascii=False)}\n\n"
                time.sleep(0.05)

            if related:
                yield f"data: {json.dumps({'type': 'related', 'data': related}, ensure_ascii=False)}\n\n"
                time.sleep(0.05)

            # 逐行推送回答文本
            lines = answer.split("\n")
            for i, line in enumerate(lines):
                chunk = {"type": "text", "content": line}
                if i < len(lines) - 1:
                    chunk["content"] += "\n"
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                time.sleep(0.08)

            # 推送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"SSE问答失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@user_bp.get("/user/qa/history")
def qa_history():
    """用户问答历史"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    from backend.models.knowledge_base import QARecord
    limit = _safe_int(request.args.get("limit"), 50) or 50

    try:
        with SessionLocal() as db:
            records = list(db.execute(
                select(QARecord).where(QARecord.user_id == user_payload["user_id"])
                .order_by(desc(QARecord.created_at))
                .limit(limit)
            ).scalars().all())

            return jsonify({"records": [r.to_dict() for r in records]})
    except Exception as e:
        logger.error(f"获取问答历史失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 评论文件上传 =====

@user_bp.post("/user/reviews/upload")
def upload_reviews_file():
    """上传评论文件进行情感分析"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    if "file" not in request.files:
        return jsonify({"error": "no_file", "message": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "no_filename", "message": "文件名不能为空"}), 400

    product_name = request.form.get("product_name", file.filename)

    try:
        file_data = file.read()
        reviews = file_service.parse_reviews_file(file.filename, file_data)

        if not reviews:
            return jsonify({"error": "empty", "message": "文件中没有找到有效评论"}), 400

        payload = ReviewAnalysisRequest(
            product_name=product_name,
            reviews=reviews,
        )
        result = ai_service.analyze_reviews(payload)

        return jsonify({
            "message": f"成功解析 {len(reviews)} 条评论",
            "file_name": file.filename,
            "review_count": len(reviews),
            "analysis": result,
        })

    except ValueError as e:
        return jsonify({"error": "parse_error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"评论文件上传失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": f"处理失败: {str(e)}"}), 500


@user_bp.post("/user/reviews/submit")
def submit_review():
    """提交商品评论（支持图片/视频）"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    product_id = _safe_int(data.get("product_id"))
    content = data.get("content", "").strip()
    rating = _safe_int(data.get("rating"), 5) or 5
    image_urls = data.get("image_urls") or []
    videos = data.get("videos") or []

    if not product_id:
        return jsonify({"error": "invalid_input", "message": "商品ID不能为空"}), 400

    try:
        with SessionLocal() as db:
            review = Review(
                product_id=product_id,
                user_name=user_payload.get("username", "匿名用户"),
                user_id=user_payload.get("user_id"),
                rating=rating,
                content=content,
                image_urls=image_urls if image_urls else None,
                videos=videos if videos else None,
            )
            db.add(review)
            db.commit()
            db.refresh(review)
            review_data = review.to_dict()

            return jsonify({"message": "评论提交成功", "review": review_data}), 201
    except Exception as e:
        logger.error(f"提交评论失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@user_bp.post("/user/reviews/upload-media")
def upload_review_media():
    """上传评价图片或视频"""
    user_payload, error = require_auth(request)
    if error:
        return jsonify(error), 401

    if "file" not in request.files:
        return jsonify({"error": "no_file", "message": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "no_filename", "message": "文件名不能为空"}), 400

    try:
        ext = os.path.splitext(file.filename)[1].lower()
        is_video = ext in ALLOWED_VIDEO_EXTENSIONS
        subdir = "review_videos" if is_video else "review_images"
        allowed = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
        url = _save_uploaded_file(file, subdir, allowed)
        return jsonify({"url": url, "type": "video" if is_video else "image"})
    except ValueError as e:
        return jsonify({"error": "invalid_file", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"评价媒体上传失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": "上传失败"}), 500
