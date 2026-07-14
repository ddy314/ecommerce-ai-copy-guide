"""FastAPI 服务器 - 镜像全部 Flask 接口

启动: uvicorn backend.fastapi_app:app --reload --port 8001
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
import uuid

from backend.database import SessionLocal, init_db
from backend.models.product import Product
from backend.models.review import Review
from backend.models.user import User, UserAddress, UserFavorite, BrowseHistory
from backend.models.shopping import CartItem, Order, OrderItem
from backend.models.knowledge_base import KnowledgeEntry, QARecord
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
    get_user_from_request,
)
from backend.services.rag_service import RAGService
from backend.services.file_upload import FileUploadService
from backend.services.ai_provider import get_ai_provider
from backend.schemas.requests import (
    CopyGenerationRequest,
    CrossRecommendRequest,
    GuideQARequest,
    GuideRecommendationRequest,
    LiveScriptRequest,
    ReviewAnalysisRequest,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

app = FastAPI(
    title="电商AI商品文案生成与智能导购助手",
    description="Flask + FastAPI 双后端 - FastAPI 镜像版本",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = get_ai_provider()
rag_service = RAGService()
file_service = FileUploadService()


# ===== 依赖注入 =====

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request) -> dict:
    """从请求中提取用户信息"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload:
            return payload
    raise HTTPException(status_code=401, detail="请先登录")


def get_merchant_user(request: Request) -> dict:
    """验证商家权限"""
    user = get_current_user(request)
    if user.get("role") != "merchant":
        raise HTTPException(status_code=403, detail="需要商家权限")
    return user


# ===== 请求模型 =====

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str = ""


class CheckUsernameRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1


class UpdateCartRequest(BaseModel):
    quantity: int | None = None
    selected: bool | None = None


class CreateOrderRequest(BaseModel):
    address_id: int | None = None
    pay_method: str = "wechat"
    remark: str = ""
    item_ids: list[int] = []


class AddressRequest(BaseModel):
    name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    is_default: bool = False


class UpdateProfileRequest(BaseModel):
    nickname: str | None = None
    avatar: str | None = None
    phone: str | None = None
    email: str | None = None


class AskQuestionRequest(BaseModel):
    question: str
    product_id: int | None = None


class ProductCreateRequest(BaseModel):
    name: str
    category: str = ""
    price: float = 0
    original_price: float = 0
    specs: str = ""
    selling_points: str = ""
    image_url: str = ""
    source: str = "manual"
    source_url: str = ""


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    price: float | None = None
    original_price: float | None = None
    specs: str | None = None
    selling_points: str | None = None
    image_url: str | None = None
    source_url: str | None = None


class KnowledgeCreateRequest(BaseModel):
    product_id: int | None = None
    category: str = "faq"
    title: str
    content: str
    keywords: list[str] = []


class SubmitReviewRequest(BaseModel):
    product_id: int
    content: str
    rating: int = 5


# ===== 健康检查 =====

@app.get("/health")
def health():
    return {"status": "ok", "service": "ecommerce-ai-copy-guide", "version": "0.2.0", "runtime": "FastAPI"}


@app.get("/api/capabilities")
def capabilities():
    provider_name = ai_service.__class__.__name__
    return {
        "mode": "openai" if "OpenAI" in provider_name else "mock",
        "provider": provider_name,
        "features": [
            {"key": "copy_generation", "name": "商品文案生成", "endpoint": "/api/copy/generate"},
            {"key": "shopping_guide", "name": "智能导购推荐", "endpoint": "/api/guide/recommend"},
            {"key": "guide_qa", "name": "智能导购问答", "endpoint": "/api/guide/qa"},
            {"key": "cross_recommend", "name": "跨商品关联推荐", "endpoint": "/api/guide/cross-recommend"},
            {"key": "review_analysis", "name": "评论情感分析", "endpoint": "/api/reviews/analyze"},
            {"key": "live_script", "name": "直播脚本生成", "endpoint": "/api/scripts/live"},
        ],
    }


# ===== 模块一：商品文案智能生成 =====

@app.post("/api/copy/generate")
def generate_copy(payload: CopyGenerationRequest):
    return ai_service.generate_copy(payload)


# ===== 模块二：智能导购与推荐问答 =====

@app.post("/api/guide/recommend")
def recommend(payload: GuideRecommendationRequest):
    return ai_service.recommend(payload)


@app.post("/api/guide/qa")
def guide_qa(payload: GuideQARequest):
    return ai_service.guide_qa(payload)


@app.post("/api/guide/cross-recommend")
def cross_recommend(payload: CrossRecommendRequest):
    return ai_service.cross_recommend(payload)


# ===== 模块三：用户评论情感分析 =====

@app.post("/api/reviews/analyze")
def analyze_reviews(payload: ReviewAnalysisRequest):
    return ai_service.analyze_reviews(payload)


# ===== 模块四：直播/短视频脚本自动生成 =====

@app.post("/api/scripts/live")
def generate_live_script(payload: LiveScriptRequest):
    return ai_service.generate_live_script(payload)


# ===== 认证 =====

@app.post("/api/auth/login")
def login(req: LoginRequest):
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="账号不存在")
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="密码错误")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用")
        if req.role and req.role != user.role:
            raise HTTPException(status_code=403, detail=f"该账号是{'商家管理员' if user.role == 'merchant' else '普通用户'}，请切换身份登录")

        token = create_token(user.id, user.username, user.role)
        user_data = user.to_dict()
        user_data["token"] = token
        return {"message": "登录成功", "user": user_data, "token": token}


@app.post("/api/auth/register")
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="账号长度至少3位")

    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="账号已存在")

        user = User(username=req.username, password_hash=hash_password(req.password), nickname=req.nickname or req.username, role="user")
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_token(user.id, user.username, user.role)
        return {"message": "注册成功", "user": user.to_dict(), "token": token}


@app.post("/api/auth/check-username")
def check_username(req: CheckUsernameRequest):
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="账号不存在")
        return {"exists": True, "message": "账号验证通过", "hint": f"找回账号：{user.nickname or user.username}"}


@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="账号不存在")
        user.password_hash = hash_password(req.new_password)
        db.commit()
        return {"message": "密码重置成功，请使用新密码登录"}


@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        u = db.get(User, user["user_id"])
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"user": u.to_dict()}


@app.put("/api/auth/profile")
def update_profile(req: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        u = db.get(User, user["user_id"])
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        if req.nickname is not None:
            u.nickname = req.nickname
        if req.avatar is not None:
            u.avatar = req.avatar
        if req.phone is not None:
            u.phone = req.phone
        if req.email is not None:
            u.email = req.email
        db.commit()
        db.refresh(u)
        return {"message": "资料更新成功", "user": u.to_dict()}


# ===== 商品查询 =====

@app.get("/api/products")
def list_products(category: str = "", keyword: str = "", page: int = 1, page_size: int = 20):
    with SessionLocal() as db:
        stmt = select(Product)
        if keyword:
            stmt = stmt.where(Product.name.contains(keyword))
        if category:
            stmt = stmt.where(Product.category == category)
        all_products = list(db.execute(stmt).scalars().all())
        total = len(all_products)
        products = all_products[(page - 1) * page_size: page * page_size]
        categories = list(set(p.category for p in all_products if p.category))
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        return {"total": total, "page": page, "page_size": page_size, "total_pages": total_pages, "categories": categories, "products": [p.to_dict() for p in products]}


@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        data = product.to_dict()
        data["reviews"] = [r.to_dict() for r in product.reviews[:50]]
        return data


# ===== 商家管理 =====

@app.get("/api/merchant/products")
def merchant_list_products(keyword: str = "", category: str = "", page: int = 1, page_size: int = 20, user: dict = Depends(get_merchant_user)):
    return list_products(category, keyword, page, page_size)


@app.post("/api/merchant/products")
def merchant_create_product(req: ProductCreateRequest, user: dict = Depends(get_merchant_user)):
    with SessionLocal() as db:
        product = Product(
            name=req.name, category=req.category, price=req.price,
            original_price=req.original_price or None, specs=req.specs,
            selling_points=req.selling_points, image_url=req.image_url,
            source=req.source, source_url=req.source_url,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        try:
            rag_service.auto_build_from_product(product)
        except Exception as e:
            logger.warning(f"知识库自动构建失败: {e}")
        return {"message": "商品创建成功", "product": product.to_dict()}


@app.put("/api/merchant/products/{product_id}")
def merchant_update_product(product_id: int, req: ProductUpdateRequest, user: dict = Depends(get_merchant_user)):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        for field in ["name", "category", "specs", "selling_points", "image_url", "source_url"]:
            val = getattr(req, field, None)
            if val is not None:
                setattr(product, field, val)
        if req.price is not None:
            product.price = req.price
        if req.original_price is not None:
            product.original_price = req.original_price or None
        db.commit()
        db.refresh(product)
        try:
            rag_service.auto_build_from_product(product)
        except Exception:
            pass
        return {"message": "商品更新成功", "product": product.to_dict()}


@app.delete("/api/merchant/products/{product_id}")
def merchant_delete_product(product_id: int, user: dict = Depends(get_merchant_user)):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        db.delete(product)
        db.commit()
        return {"message": "商品已删除"}


# ===== 知识库管理 =====

@app.get("/api/merchant/knowledge")
def list_knowledge(product_id: int | None = None, category: str = "", user: dict = Depends(get_merchant_user)):
    entries = rag_service.list_knowledge(product_id=product_id, category=category if category else None)
    return {"entries": entries, "total": len(entries)}


@app.post("/api/merchant/knowledge")
def add_knowledge(req: KnowledgeCreateRequest, user: dict = Depends(get_merchant_user)):
    entry = rag_service.add_knowledge(product_id=req.product_id, category=req.category, title=req.title, content=req.content, keywords=req.keywords)
    return {"message": "知识条目添加成功", "entry": entry}


@app.delete("/api/merchant/knowledge/{entry_id}")
def delete_knowledge(entry_id: int, user: dict = Depends(get_merchant_user)):
    if rag_service.delete_knowledge(entry_id):
        return {"message": "知识条目已删除"}
    raise HTTPException(status_code=404, detail="知识条目不存在")


@app.post("/api/merchant/knowledge/auto-build/{product_id}")
def auto_build_knowledge(product_id: int, user: dict = Depends(get_merchant_user)):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        count = rag_service.auto_build_from_product(product)
        return {"message": f"已自动构建 {count} 条知识条目", "created": count}


@app.get("/api/merchant/qa/stats")
def qa_stats(user: dict = Depends(get_merchant_user)):
    return rag_service.get_qa_stats()


@app.get("/api/merchant/qa/records")
def qa_records(limit: int = 50, user: dict = Depends(get_merchant_user)):
    records = rag_service.get_qa_records(limit)
    return {"records": records, "total": len(records)}


# ===== 购物车 =====

@app.get("/api/user/cart")
def get_cart(user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        items = list(db.execute(select(CartItem).where(CartItem.user_id == user["user_id"])).scalars().all())
        cart_data = []
        total = 0.0
        for item in items:
            product = db.get(Product, item.product_id)
            if not product:
                continue
            item_data = item.to_dict()
            item_data["product"] = product.to_dict()
            if item.selected:
                total += product.price * item.quantity
            cart_data.append(item_data)
        return {"items": cart_data, "total": round(total, 2), "count": len(cart_data)}


@app.post("/api/user/cart")
def add_to_cart(req: AddToCartRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        product = db.get(Product, req.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        existing = db.execute(select(CartItem).where(CartItem.user_id == user["user_id"], CartItem.product_id == req.product_id)).scalar_one_or_none()
        if existing:
            existing.quantity += req.quantity
            db.commit()
            db.refresh(existing)
            return {"message": "数量已更新", "item": existing.to_dict()}
        item = CartItem(user_id=user["user_id"], product_id=req.product_id, quantity=req.quantity)
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"message": "已加入购物车", "item": item.to_dict()}


@app.put("/api/user/cart/{item_id}")
def update_cart(item_id: int, req: UpdateCartRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        item = db.get(CartItem, item_id)
        if not item or item.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="购物车项不存在")
        if req.quantity is not None:
            if req.quantity <= 0:
                db.delete(item)
                db.commit()
                return {"message": "已移除"}
            item.quantity = req.quantity
        if req.selected is not None:
            item.selected = req.selected
        db.commit()
        db.refresh(item)
        return {"message": "已更新", "item": item.to_dict()}


@app.delete("/api/user/cart/{item_id}")
def remove_cart(item_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        item = db.get(CartItem, item_id)
        if not item or item.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="购物车项不存在")
        db.delete(item)
        db.commit()
        return {"message": "已移除"}


# ===== 订单 =====

@app.post("/api/user/orders")
def create_order(req: CreateOrderRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        stmt = select(CartItem).where(CartItem.user_id == user["user_id"], CartItem.selected == True)
        if req.item_ids:
            stmt = stmt.where(CartItem.id.in_(req.item_ids))
        cart_items = list(db.execute(stmt).scalars().all())
        if not cart_items:
            raise HTTPException(status_code=400, detail="购物车没有选中商品")

        address = db.get(UserAddress, req.address_id) if req.address_id else None
        if not address:
            address = db.execute(select(UserAddress).where(UserAddress.user_id == user["user_id"], UserAddress.is_default == True)).scalar_one_or_none()
        if not address:
            raise HTTPException(status_code=400, detail="请先添加收货地址")

        total_amount = 0.0
        order_items_data = []
        for ci in cart_items:
            product = db.get(Product, ci.product_id)
            if not product:
                continue
            total_amount += product.price * ci.quantity
            order_items_data.append({"product_id": product.id, "product_name": product.name, "price": product.price, "quantity": ci.quantity, "image_url": product.image_url or ""})

        if not order_items_data:
            raise HTTPException(status_code=400, detail="没有有效商品")

        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        order = Order(order_no=order_no, user_id=user["user_id"], status="pending", total_amount=round(total_amount, 2), pay_method=req.pay_method, address_snapshot=json.dumps(address.to_dict(), ensure_ascii=False), items_snapshot=json.dumps(order_items_data, ensure_ascii=False), remark=req.remark)
        db.add(order)
        db.flush()
        for oi_data in order_items_data:
            db.add(OrderItem(order_id=order.id, **oi_data))
        for ci in cart_items:
            db.delete(ci)
        db.commit()
        db.refresh(order)
        return {"message": "订单创建成功", "order": order.to_dict()}


@app.post("/api/user/orders/{order_id}/pay")
def pay_order(order_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order or order.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order.status != "pending":
            raise HTTPException(status_code=400, detail="订单状态不允许支付")
        order.status = "paid"
        order.paid_at = datetime.now()
        db.commit()
        db.refresh(order)
        return {"message": "支付成功", "order": order.to_dict()}


@app.post("/api/user/orders/{order_id}/cancel")
def cancel_order(order_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order or order.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order.status not in ("pending", "paid"):
            raise HTTPException(status_code=400, detail="当前状态不可取消")
        order.status = "cancelled"
        db.commit()
        return {"message": "订单已取消"}


@app.post("/api/user/orders/{order_id}/confirm")
def confirm_order(order_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order or order.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order.status != "shipped":
            raise HTTPException(status_code=400, detail="当前状态不可确认收货")
        order.status = "completed"
        order.completed_at = datetime.now()
        db.commit()
        return {"message": "已确认收货"}


@app.get("/api/user/orders")
def list_orders(status: str = "", page: int = 1, page_size: int = 20, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        stmt = select(Order).where(Order.user_id == user["user_id"])
        if status:
            stmt = stmt.where(Order.status == status)
        stmt = stmt.order_by(desc(Order.created_at))
        all_orders = list(db.execute(stmt).scalars().all())
        total = len(all_orders)
        orders = all_orders[(page - 1) * page_size: page * page_size]
        return {"total": total, "page": page, "orders": [o.to_dict() for o in orders]}


@app.get("/api/user/orders/{order_id}")
def get_order_detail(order_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if not order or order.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="订单不存在")
        return {"order": order.to_dict()}


# ===== 收货地址 =====

@app.get("/api/user/addresses")
def list_addresses(user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        addresses = list(db.execute(select(UserAddress).where(UserAddress.user_id == user["user_id"]).order_by(desc(UserAddress.is_default))).scalars().all())
        return {"addresses": [a.to_dict() for a in addresses]}


@app.post("/api/user/addresses")
def add_address(req: AddressRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        if req.is_default:
            for a in db.execute(select(UserAddress).where(UserAddress.user_id == user["user_id"], UserAddress.is_default == True)).scalars().all():
                a.is_default = False
        address = UserAddress(user_id=user["user_id"], name=req.name, phone=req.phone, province=req.province, city=req.city, district=req.district, detail=req.detail, is_default=req.is_default)
        db.add(address)
        db.commit()
        db.refresh(address)
        return {"message": "地址添加成功", "address": address.to_dict()}


@app.put("/api/user/addresses/{address_id}")
def update_address(address_id: int, req: AddressRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        address = db.get(UserAddress, address_id)
        if not address or address.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="地址不存在")
        for field in ["name", "phone", "province", "city", "district", "detail"]:
            setattr(address, field, getattr(req, field))
        if req.is_default:
            for a in db.execute(select(UserAddress).where(UserAddress.user_id == user["user_id"], UserAddress.is_default == True)).scalars().all():
                a.is_default = False
        address.is_default = req.is_default
        db.commit()
        db.refresh(address)
        return {"message": "地址更新成功", "address": address.to_dict()}


@app.delete("/api/user/addresses/{address_id}")
def delete_address(address_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        address = db.get(UserAddress, address_id)
        if not address or address.user_id != user["user_id"]:
            raise HTTPException(status_code=404, detail="地址不存在")
        db.delete(address)
        db.commit()
        return {"message": "地址已删除"}


# ===== 收藏 =====

@app.get("/api/user/favorites")
def list_favorites(user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        favs = list(db.execute(select(UserFavorite).where(UserFavorite.user_id == user["user_id"])).scalars().all())
        result = []
        for fav in favs:
            product = db.get(Product, fav.product_id)
            if product:
                result.append(product.to_dict())
        return {"favorites": result, "total": len(result)}


@app.post("/api/user/favorites/{product_id}")
def toggle_favorite(product_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        existing = db.execute(select(UserFavorite).where(UserFavorite.user_id == user["user_id"], UserFavorite.product_id == product_id)).scalar_one_or_none()
        if existing:
            db.delete(existing)
            db.commit()
            return {"message": "已取消收藏", "is_favorite": False}
        db.add(UserFavorite(user_id=user["user_id"], product_id=product_id))
        db.commit()
        return {"message": "已收藏", "is_favorite": True}


# ===== 浏览记录 =====

@app.post("/api/user/history/{product_id}")
def add_history(product_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        db.add(BrowseHistory(user_id=user["user_id"], product_id=product_id))
        db.commit()
        return {"message": "已记录"}


@app.get("/api/user/history")
def list_history(limit: int = 20, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        histories = list(db.execute(select(BrowseHistory).where(BrowseHistory.user_id == user["user_id"]).order_by(desc(BrowseHistory.created_at)).limit(limit)).scalars().all())
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
        return {"history": result}


# ===== RAG 智能问答 =====

@app.post("/api/user/qa/ask")
def ask_question(req: AskQuestionRequest, user: dict = Depends(get_current_user)):
    return rag_service.answer_question(question=req.question, product_id=req.product_id, user_id=user["user_id"])


@app.get("/api/user/qa/history")
def qa_history(limit: int = 50, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        records = list(db.execute(select(QARecord).where(QARecord.user_id == user["user_id"]).order_by(desc(QARecord.created_at)).limit(limit)).scalars().all())
        return {"records": [r.to_dict() for r in records]}


# ===== 评论文件上传 =====

@app.post("/api/user/reviews/upload")
async def upload_reviews(file: UploadFile = File(...), product_name: str = Form(""), user: dict = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    try:
        file_data = await file.read()
        reviews = file_service.parse_reviews_file(file.filename, file_data)
        if not reviews:
            raise HTTPException(status_code=400, detail="文件中没有找到有效评论")

        payload = ReviewAnalysisRequest(product_name=product_name or file.filename, reviews=reviews)
        result = ai_service.analyze_reviews(payload)
        return {"message": f"成功解析 {len(reviews)} 条评论", "file_name": file.filename, "review_count": len(reviews), "analysis": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/user/reviews/submit")
def submit_review(req: SubmitReviewRequest, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        review = Review(product_id=req.product_id, author=user.get("username", "匿名用户"), rating=req.rating, content=req.content)
        db.add(review)
        db.commit()
        db.refresh(review)
        return {"message": "评论提交成功", "review": review.to_dict()}


# ===== 启动事件 =====

@app.on_event("startup")
def startup():
    try:
        init_db()
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.warning(f"数据库初始化失败: {e}")

    # 创建默认账号
    try:
        with SessionLocal() as db:
            if not db.execute(select(User).where(User.username == "merchant")).scalar_one_or_none():
                db.add(User(username="merchant", password_hash=hash_password("merchant123"), nickname="商家管理员", role="merchant"))
                logger.info("已创建默认商家账号: merchant / merchant123")
            if not db.execute(select(User).where(User.username == "user")).scalar_one_or_none():
                db.add(User(username="user", password_hash=hash_password("user123"), nickname="测试用户", role="user"))
                logger.info("已创建默认用户账号: user / user123")
            db.commit()
    except Exception as e:
        logger.warning(f"默认账号创建失败: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
