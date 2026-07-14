"""商品模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Product(Base):
    """商品表"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=True, default="manual", comment="来源平台（jd/taobao/manual）")
    product_id: Mapped[str] = mapped_column(String(100), nullable=True, comment="平台商品ID（手动创建时为空）")
    name: Mapped[str] = mapped_column(String(500), comment="商品名称")
    category: Mapped[str] = mapped_column(String(200), nullable=True, default="", comment="商品类目")
    price: Mapped[float] = mapped_column(Float, nullable=True, default=0, comment="价格")
    original_price: Mapped[float] = mapped_column(Float, nullable=True, comment="原价")
    brand: Mapped[str] = mapped_column(String(200), nullable=True, default="", comment="品牌")
    selling_points: Mapped[str] = mapped_column(Text, nullable=True, default="", comment="卖点描述")
    image_url: Mapped[str] = mapped_column(String(500), nullable=True, default="", comment="主图URL")
    detail_url: Mapped[str] = mapped_column(String(500), nullable=True, default="", comment="详情URL")
    source_url: Mapped[str] = mapped_column(String(500), nullable=True, default="", comment="来源链接")
    specs: Mapped[str] = mapped_column(Text, nullable=True, default="", comment="规格参数")
    sales_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0, comment="销量")
    rating: Mapped[float] = mapped_column(Float, nullable=True, default=5.0, comment="评分")
    review_count: Mapped[int] = mapped_column(Integer, default=0, comment="评论数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    generation_tasks = relationship("GenerationTask", back_populates="product")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform or "manual",
            "product_id": self.product_id or "",
            "name": self.name,
            "category": self.category or "",
            "price": self.price or 0,
            "original_price": self.original_price,
            "brand": self.brand or "",
            "selling_points": self.selling_points or "",
            "image_url": self.image_url or "",
            "detail_url": self.detail_url or "",
            "source_url": self.source_url or "",
            "specs": self.specs or "",
            "sales_count": self.sales_count or 0,
            "rating": self.rating or 5.0,
            "review_count": self.review_count or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
