"""通用辅助函数"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.product import Product
from backend.models.user import User
from backend.models.shopping import Order


def generate_product_display_id(db: Session) -> str:
    count = db.query(Product).count()
    return f"{count + 1:05d}"


def generate_user_display_id(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(User).filter(User.display_id.like(f"{today}%")).count()
    return f"{today}{count + 1:07d}"


def generate_order_no(db: Session, product_id: int) -> str:
    now = datetime.now()
    product = db.query(Product).filter(Product.id == product_id).first()
    product_display = product.display_id if product and product.display_id else f"{product_id:05d}"
    seq = db.query(Order).filter(Order.order_no.like(f"{now.strftime('%Y%m%d%H%M%S')}{product_display}%")).count() + 1
    return f"{now.strftime('%Y%m%d%H%M%S')}{product_display}{seq:05d}"
