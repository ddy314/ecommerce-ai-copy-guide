"""购物车与订单模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class CartItem(Base):
    """购物车"""
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, comment="用户ID")
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), comment="商品ID")
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="数量")
    selected: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否选中")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "selected": self.selected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Order(Base):
    """订单"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, comment="订单号")
    user_id: Mapped[int] = mapped_column(Integer, comment="用户ID")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="订单状态: pending/paid/shipped/completed/cancelled/returning/returned")
    total_amount: Mapped[float] = mapped_column(Float, default=0, comment="总金额")
    pay_method: Mapped[str] = mapped_column(String(20), nullable=True, comment="支付方式: wechat/alipay")
    address_snapshot: Mapped[str] = mapped_column(Text, nullable=True, comment="收货地址快照(JSON)")
    items_snapshot: Mapped[str] = mapped_column(Text, nullable=True, comment="商品快照(JSON)")
    remark: Mapped[str] = mapped_column(String(500), nullable=True, comment="备注")
    # 物流与售后
    tracking_no: Mapped[str] = mapped_column(String(100), nullable=True, comment="发货快递单号")
    return_tracking_no: Mapped[str] = mapped_column(String(100), nullable=True, comment="退货快递单号")
    exchange_tracking_no: Mapped[str] = mapped_column(String(100), nullable=True, comment="换货新快递单号")
    return_status: Mapped[str] = mapped_column(String(20), nullable=True, comment="售后状态: none/returning/refunded/exchanged")
    return_reason: Mapped[str] = mapped_column(String(500), nullable=True, comment="退换货原因")
    return_applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    return_completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "order_no": self.order_no,
            "user_id": self.user_id,
            "status": self.status,
            "total_amount": self.total_amount,
            "pay_method": self.pay_method,
            "address_snapshot": json.loads(self.address_snapshot) if self.address_snapshot else None,
            "items_snapshot": json.loads(self.items_snapshot) if self.items_snapshot else None,
            "remark": self.remark,
            "tracking_no": self.tracking_no,
            "return_tracking_no": self.return_tracking_no,
            "exchange_tracking_no": self.exchange_tracking_no,
            "return_status": self.return_status,
            "return_reason": self.return_reason,
            "return_applied_at": self.return_applied_at.isoformat() if self.return_applied_at else None,
            "return_completed_at": self.return_completed_at.isoformat() if self.return_completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "items": [item.to_dict() for item in self.items] if self.items else [],
        }


class OrderItem(Base):
    """订单商品"""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), comment="订单ID")
    product_id: Mapped[int] = mapped_column(Integer, comment="商品ID")
    product_name: Mapped[str] = mapped_column(String(500), comment="商品名称快照")
    price: Mapped[float] = mapped_column(Float, default=0, comment="购买时价格")
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="数量")
    image_url: Mapped[str] = mapped_column(String(500), nullable=True, default="", comment="商品图片快照")

    order = relationship("Order", back_populates="items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "price": self.price,
            "quantity": self.quantity,
            "image_url": self.image_url or "",
        }
