"""商家管理路由 - 商品CRUD + 知识库管理 + 问答统计 + 订单管理"""
from __future__ import annotations

import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import select, desc

from backend.database import SessionLocal
from backend.models.product import Product
from backend.models.user import User
from backend.models.shopping import Order
from backend.services.auth_service import require_merchant, hash_password
from backend.services.rag_service import RAGService
from backend.utils.helpers import generate_product_display_id
from backend.api.auth_routes import _save_uploaded_file, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)

merchant_bp = Blueprint("merchant", __name__)
rag_service = RAGService()


# ===== 商品管理 =====

@merchant_bp.post("/merchant/products")
def create_product():
    """创建商品"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    required = ["name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": "invalid_input", "message": f"缺少必填字段: {field}"}), 400

    image_urls = data.get("image_urls") or []
    videos = data.get("videos") or []
    image_url = data.get("image_url", "")
    if not image_url and image_urls:
        image_url = image_urls[0]

    with SessionLocal() as db:
        product = Product(
            name=data["name"],
            category=data.get("category", ""),
            price=float(data.get("price", 0) or 0),
            original_price=float(data["original_price"]) if data.get("original_price") else None,
            specs=data.get("specs", ""),
            selling_points=data.get("selling_points", ""),
            image_url=image_url,
            image_urls=image_urls if image_urls else None,
            videos=videos if videos else None,
            source_url=data.get("source_url", ""),
            platform="manual",
            brand=data.get("brand", ""),
            is_published=bool(data.get("is_published", True)),
        )
        db.add(product)
        product.display_id = generate_product_display_id(db)
        db.commit()
        db.refresh(product)

        product_data = product.to_dict()

        # 自动构建知识库
        try:
            rag_service.auto_build_from_product(product)
        except Exception as e:
            logger.warning(f"知识库自动构建失败: {e}")

        return jsonify({"message": "商品创建成功", "product": product_data}), 201


@merchant_bp.put("/merchant/products/<int:product_id>")
def update_product(product_id: int):
    """更新商品"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}

    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            return jsonify({"error": "not_found", "message": "商品不存在"}), 404

        for field in ["name", "category", "specs", "selling_points", "source_url"]:
            if field in data:
                setattr(product, field, data[field])
        if "is_published" in data:
            product.is_published = bool(data["is_published"])
        if "price" in data:
            product.price = float(data["price"])
        if "original_price" in data:
            product.original_price = float(data["original_price"]) or None

        # 处理图片/视频列表，保持 image_url 与第一张图一致
        if "image_urls" in data:
            product.image_urls = data["image_urls"] or None
        if "videos" in data:
            product.videos = data["videos"] or None
        if "image_url" in data:
            product.image_url = data["image_url"]
        elif "image_urls" in data and data["image_urls"]:
            product.image_url = data["image_urls"][0]

        db.commit()
        db.refresh(product)
        product_data = product.to_dict()

        # 重建知识库
        try:
            rag_service.auto_build_from_product(product)
        except Exception as e:
            logger.warning(f"知识库重建失败: {e}")

        return jsonify({"message": "商品更新成功", "product": product_data})


@merchant_bp.delete("/merchant/products/<int:product_id>")
def delete_product(product_id: int):
    """删除商品"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            return jsonify({"error": "not_found", "message": "商品不存在"}), 404

        db.delete(product)
        db.commit()

        return jsonify({"message": "商品已删除"})


@merchant_bp.post("/merchant/products/upload")
def upload_product_media():
    """上传商品图片或视频，返回可访问 URL"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    if "file" not in request.files:
        return jsonify({"error": "no_file", "message": "请上传文件"}), 400

    file = request.files["file"]
    try:
        # 根据文件类型选择保存目录
        allowed = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
        subdir = "product_videos" if _video_file(file.filename) else "product_images"
        url = _save_uploaded_file(file, subdir, allowed)
        return jsonify({"url": url})
    except ValueError as e:
        return jsonify({"error": "invalid_file", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"商品媒体上传失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": "上传失败"}), 500


def _video_file(filename: str | None) -> bool:
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_VIDEO_EXTENSIONS


@merchant_bp.get("/merchant/products")
def list_merchant_products():
    """商家商品列表"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    keyword = request.args.get("keyword", "")
    category = request.args.get("category", "")

    with SessionLocal() as db:
        from backend.repositories.product_repo import ProductRepository
        repo = ProductRepository(db)

        stmt = select(Product)
        if keyword:
            stmt = stmt.where(Product.name.contains(keyword))
        if category:
            stmt = stmt.where(Product.category == category)

        total = len(list(db.execute(stmt).scalars().all()))
        total_pages = max(1, (total + page_size - 1) // page_size)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        products = list(db.execute(stmt).scalars().all())

        # 获取所有分类和各分类商品数（与用户端同步）
        all_categories = repo.list_categories()
        category_counts = {}
        for cat in all_categories:
            category_counts[cat] = repo.count(cat)

        return jsonify({
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "categories": all_categories,
            "category_counts": category_counts,
            "products": [p.to_dict() for p in products],
        })


# ===== 知识库管理 =====

@merchant_bp.get("/merchant/knowledge")
def list_knowledge():
    """知识库列表"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    product_id = request.args.get("product_id", type=int)
    category = request.args.get("category", "")
    keyword = request.args.get("keyword", "")
    entries = rag_service.list_knowledge(
        product_id=product_id,
        category=category if category else None,
        keyword=keyword if keyword else None,
    )
    return jsonify({"entries": entries, "total": len(entries)})


@merchant_bp.get("/merchant/knowledge/categories")
def list_knowledge_categories():
    """知识库类型列表"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    categories = rag_service.list_knowledge_categories()
    return jsonify({"categories": categories})


@merchant_bp.post("/merchant/knowledge")
def add_knowledge():
    """添加知识条目"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("content"):
        return jsonify({"error": "invalid_input", "message": "标题和内容不能为空"}), 400

    entry = rag_service.add_knowledge(
        product_id=data.get("product_id"),
        category=data.get("category", "faq"),
        title=data["title"],
        content=data["content"],
        keywords=data.get("keywords", []),
    )
    return jsonify({"message": "知识条目添加成功", "entry": entry}), 201


@merchant_bp.put("/merchant/knowledge/<int:entry_id>")
def update_knowledge(entry_id: int):
    """更新知识条目"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("content"):
        return jsonify({"error": "invalid_input", "message": "标题和内容不能为空"}), 400

    entry = rag_service.update_knowledge(
        entry_id=entry_id,
        product_id=data.get("product_id"),
        category=data.get("category"),
        title=data["title"],
        content=data["content"],
        keywords=data.get("keywords", []),
    )
    if entry:
        return jsonify({"message": "知识条目更新成功", "entry": entry})
    return jsonify({"error": "not_found", "message": "知识条目不存在"}), 404


@merchant_bp.delete("/merchant/knowledge/<int:entry_id>")
def delete_knowledge(entry_id: int):
    """删除知识条目"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    if rag_service.delete_knowledge(entry_id):
        return jsonify({"message": "知识条目已删除"})
    return jsonify({"error": "not_found", "message": "知识条目不存在"}), 404


@merchant_bp.post("/merchant/knowledge/auto-build/<int:product_id>")
def auto_build_knowledge(product_id: int):
    """为商品自动构建知识库"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            return jsonify({"error": "not_found", "message": "商品不存在"}), 404

        count = rag_service.auto_build_from_product(product)
        return jsonify({"message": f"已自动构建 {count} 条知识条目", "created": count})


# ===== 问答统计 =====

@merchant_bp.get("/merchant/qa/stats")
def qa_stats():
    """问答统计"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    stats = rag_service.get_qa_stats()
    return jsonify(stats)


@merchant_bp.get("/merchant/qa/records")
def qa_records():
    """问答记录列表"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    limit = int(request.args.get("limit", 50))
    records = rag_service.get_qa_records(limit)
    return jsonify({"records": records, "total": len(records)})


# ===== 收入综合检测面板 =====

@merchant_bp.get("/merchant/dashboard/revenue")
def merchant_revenue_dashboard():
    """收入综合检测面板"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            # 1. 总收入统计
            all_orders = list(db.execute(
                select(Order).where(Order.status.in_(["paid", "shipped", "completed"]))
            ).scalars().all())

            total_revenue = sum(o.total_amount or 0 for o in all_orders)
            total_orders = len(all_orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

            # 2. 按状态分类收入
            status_revenue = {}
            for o in all_orders:
                status_revenue[o.status] = status_revenue.get(o.status, 0) + (o.total_amount or 0)

            # 3. 按分类收入
            category_revenue = {}
            category_orders = {}
            for o in all_orders:
                for item in (o.items or []):
                    cat = item.product_name or "未分类"
                    # 用商品分类（从items_snapshot或关联查询）
                    if hasattr(item, 'category') and item.category:
                        cat = item.category
                    category_revenue[cat[:20]] = category_revenue.get(cat[:20], 0) + (item.price or 0) * (item.quantity or 1)
                    category_orders[cat[:20]] = category_orders.get(cat[:20], 0) + 1

            # 4. 按日期收入趋势（最近7天）
            from datetime import datetime, timedelta
            daily_revenue = []
            daily_orders = []
            for i in range(6, -1, -1):
                date = datetime.now() - timedelta(days=i)
                date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                date_end = date_start + timedelta(days=1)
                day_orders = [o for o in all_orders if o.created_at and date_start <= o.created_at < date_end]
                daily_revenue.append({
                    "date": date_start.strftime("%m-%d"),
                    "revenue": round(sum(o.total_amount or 0 for o in day_orders), 2),
                })
                daily_orders.append({
                    "date": date_start.strftime("%m-%d"),
                    "count": len(day_orders),
                })

            # 5. 商品流量统计（浏览量、评价数、销量 TOP 10）
            top_products = list(db.execute(
                select(Product).order_by(
                    desc(Product.sales_count)
                ).limit(10)
            ).scalars().all())

            product_traffic = []
            for p in top_products:
                product_traffic.append({
                    "id": p.id,
                    "name": p.name[:40] if p.name else "",
                    "category": p.category or "",
                    "price": p.price or 0,
                    "sales_count": p.sales_count or 0,
                    "review_count": p.review_count or 0,
                    "rating": p.rating or 0,
                    "traffic_score": (p.sales_count or 0) + (p.review_count or 0) // 10,
                })

            # 6. 分类商品数量统计
            category_counts = {}
            all_products = list(db.execute(select(Product)).scalars().all())
            for p in all_products:
                cat = p.category or "未分类"
                category_counts[cat] = category_counts.get(cat, 0) + 1

            # 7. 按分类销量
            category_sales = {}
            for p in all_products:
                cat = p.category or "未分类"
                category_sales[cat] = category_sales.get(cat, 0) + (p.sales_count or 0)

            # 8. QA问答统计
            from backend.models.knowledge_base import QARecord
            qa_total = len(list(db.execute(select(QARecord)).scalars().all()))

            return jsonify({
                "total_revenue": round(total_revenue, 2),
                "total_orders": total_orders,
                "avg_order_value": round(avg_order_value, 2),
                "status_revenue": status_revenue,
                "category_revenue": category_revenue,
                "daily_revenue": daily_revenue,
                "daily_orders": daily_orders,
                "top_products": product_traffic,
                "category_counts": category_counts,
                "category_sales": category_sales,
                "total_products": len(all_products),
                "total_qa": qa_total,
            })
    except Exception as e:
        logger.error(f"收入检测面板获取失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 订单管理 =====

@merchant_bp.get("/merchant/orders")
def merchant_list_orders():
    """商家查看所有订单（支持状态筛选、关键词搜索、分页）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    status = request.args.get("status", "")
    keyword = request.args.get("keyword", "").strip()

    try:
        with SessionLocal() as db:
            stmt = select(Order)
            if status:
                stmt = stmt.where(Order.status == status)

            # 关键词搜索：订单号、买家用户名、商品名称
            if keyword:
                from sqlalchemy import or_
                # 尝试按订单号或用户ID搜索
                user_id_filter = None
                if keyword.isdigit():
                    user_id_filter = Order.user_id == int(keyword)

                # 先按订单号过滤
                order_no_filter = Order.order_no.contains(keyword)

                # 再搜索用户名匹配的用户ID
                user_ids = [
                    u.id for u in db.execute(
                        select(User).where(
                            or_(User.username.contains(keyword), User.nickname.contains(keyword))
                        )
                    ).scalars().all()
                ]
                user_filter = Order.user_id.in_(user_ids) if user_ids else None

                filters = [order_no_filter]
                if user_id_filter is not None:
                    filters.append(user_id_filter)
                if user_filter is not None:
                    filters.append(user_filter)
                stmt = stmt.where(or_(*filters))

            total = len(list(db.execute(stmt).scalars().all()))
            total_pages = max(1, (total + page_size - 1) // page_size)
            stmt = stmt.order_by(desc(Order.created_at)).offset((page - 1) * page_size).limit(page_size)
            orders = list(db.execute(stmt).scalars().all())

            # 补充用户名
            user_ids = {o.user_id for o in orders}
            users = {}
            if user_ids:
                users = {
                    u.id: u
                    for u in db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
                }

            orders_data = []
            for o in orders:
                d = o.to_dict()
                user = users.get(o.user_id)
                d["username"] = user.nickname or user.username if user else None
                orders_data.append(d)

            # 状态统计
            status_counts = {}
            all_orders = list(db.execute(select(Order)).scalars().all())
            for o in all_orders:
                status_counts[o.status] = status_counts.get(o.status, 0) + 1

            return jsonify({
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "status_counts": status_counts,
                "orders": orders_data,
            })
    except Exception as e:
        logger.error(f"商家获取订单列表失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@merchant_bp.post("/merchant/orders/<int:order_id>/ship")
def merchant_ship_order(order_id: int):
    """商家发货，需填写快递单号"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    tracking_no = (data.get("tracking_no") or "").strip()

    if not tracking_no:
        return jsonify({"error": "invalid_input", "message": "请填写快递单号"}), 400

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status != "paid":
                return jsonify({"error": "invalid_status", "message": f"当前状态({order.status})不可发货，需已付款状态"}), 400

            order.status = "shipped"
            order.tracking_no = tracking_no
            order.shipped_at = datetime.now()
            db.commit()
            db.refresh(order)
            return jsonify({"message": "发货成功", "order": order.to_dict()})
    except Exception as e:
        logger.error(f"商家发货失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@merchant_bp.post("/merchant/orders/<int:order_id>/cancel")
def merchant_cancel_order(order_id: int):
    """商家取消订单"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status in ("completed", "cancelled"):
                return jsonify({"error": "invalid_status", "message": f"当前状态({order.status})不可取消"}), 400

            order.status = "cancelled"
            order.cancelled_at = datetime.now()
            db.commit()
            db.refresh(order)
            return jsonify({"message": "订单已取消", "order": order.to_dict()})
    except Exception as e:
        logger.error(f"商家取消订单失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@merchant_bp.post("/merchant/orders/<int:order_id>/complete-return")
def merchant_complete_return(order_id: int):
    """商家处理完成退换货"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    result_status = (data.get("result") or "refunded").strip()
    if result_status not in ("refunded", "exchanged"):
        result_status = "refunded"

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404

            if order.status != "returning":
                return jsonify({"error": "invalid_status", "message": f"当前状态({order.status})不可处理退换货"}), 400

            order.status = "returned"
            order.return_status = result_status
            order.return_completed_at = datetime.now()
            db.commit()
            db.refresh(order)
            return jsonify({"message": "退换货已处理完成", "order": order.to_dict()})
    except Exception as e:
        logger.error(f"处理退换货失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@merchant_bp.get("/merchant/orders/<int:order_id>")
def merchant_order_detail(order_id: int):
    """商家查看订单详情"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            if not order:
                return jsonify({"error": "not_found", "message": "订单不存在"}), 404
            return jsonify({"order": order.to_dict()})
    except Exception as e:
        logger.error(f"商家获取订单详情失败: {e}", exc_info=True)
        return jsonify({"error": "server_error", "message": str(e)}), 500


# ===== 用户管理 =====

@merchant_bp.get("/merchant/users")
def list_users():
    """获取所有用户列表（商家管理）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    role = request.args.get("role", "")
    keyword = request.args.get("keyword", "")

    with SessionLocal() as db:
        stmt = select(User)
        if role:
            stmt = stmt.where(User.role == role)
        if keyword:
            stmt = stmt.where(
                (User.username.contains(keyword)) | (User.nickname.contains(keyword))
            )

        stmt = stmt.order_by(User.created_at.desc())
        users = list(db.execute(stmt).scalars().all())

        return jsonify({
            "total": len(users),
            "users": [u.to_dict() for u in users],
        })


@merchant_bp.post("/merchant/users")
def create_user():
    """创建用户（商家管理）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    nickname = data.get("nickname", "").strip()
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "invalid_input", "message": "用户名和密码不能为空"}), 400
    if len(password) < 6:
        return jsonify({"error": "weak_password", "message": "密码长度至少6位"}), 400
    if role not in ("user", "merchant"):
        return jsonify({"error": "invalid_role", "message": "角色必须是 user 或 merchant"}), 400

    with SessionLocal() as db:
        existing = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if existing:
            return jsonify({"error": "exists", "message": "用户名已存在"}), 409

        new_user = User(
            username=username,
            password_hash=hash_password(password),
            nickname=nickname or username,
            role=role,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return jsonify({"message": "用户创建成功", "user": new_user.to_dict()}), 201


@merchant_bp.put("/merchant/users/<int:user_id>")
def update_user(user_id: int):
    """更新用户信息（商家管理）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    data = request.get_json(silent=True) or {}

    with SessionLocal() as db:
        target_user = db.get(User, user_id)
        if not target_user:
            return jsonify({"error": "not_found", "message": "用户不存在"}), 404

        if "nickname" in data:
            target_user.nickname = data["nickname"]
        if "password" in data and data["password"]:
            if len(data["password"]) < 6:
                return jsonify({"error": "weak_password", "message": "密码长度至少6位"}), 400
            target_user.password_hash = hash_password(data["password"])
        if "role" in data and data["role"] in ("user", "merchant"):
            target_user.role = data["role"]
        if "is_active" in data:
            target_user.is_active = bool(data["is_active"])
        if "phone" in data:
            target_user.phone = data["phone"]
        if "email" in data:
            target_user.email = data["email"]

        db.commit()
        db.refresh(target_user)

        return jsonify({"message": "用户更新成功", "user": target_user.to_dict()})


@merchant_bp.delete("/merchant/users/<int:user_id>")
def delete_user(user_id: int):
    """删除用户（商家管理）"""
    user, error = require_merchant(request)
    if error:
        return jsonify(error), 401

    # 不能删除自己
    if user_id == user["user_id"]:
        return jsonify({"error": "forbidden", "message": "不能删除自己的账号"}), 403

    with SessionLocal() as db:
        target_user = db.get(User, user_id)
        if not target_user:
            return jsonify({"error": "not_found", "message": "用户不存在"}), 404

        db.delete(target_user)
        db.commit()

        return jsonify({"message": "用户已删除"})
