"""评论模型"""
from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Review(Base):
    """评论表"""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), comment="关联商品ID")
    platform_review_id: Mapped[str] = mapped_column(String(100), nullable=True, default=lambda: uuid.uuid4().hex[:16], comment="平台评论ID")
    content: Mapped[str] = mapped_column(Text, comment="评论内容")
    rating: Mapped[int] = mapped_column(Integer, default=5, comment="评分（1-5）")
    user_name: Mapped[str] = mapped_column(String(100), nullable=True, default="匿名用户", comment="用户名")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    product = relationship("Product", back_populates="reviews")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "content": self.content,
            "rating": self.rating,
            "author": self.user_name or "匿名用户",
            "user_name": self.user_name or "匿名用户",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
