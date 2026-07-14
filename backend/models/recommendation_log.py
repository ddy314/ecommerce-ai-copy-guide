"""推荐记录模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class RecommendationLog(Base):
    """推荐记录表"""

    __tablename__ = "recommendation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_need: Mapped[str] = mapped_column(Text, comment="用户需求")
    budget: Mapped[str] = mapped_column(String(200), nullable=True, comment="预算")
    recommended_product: Mapped[str] = mapped_column(String(500), comment="推荐商品")
    reason: Mapped[str] = mapped_column(Text, comment="推荐理由")
    alternatives: Mapped[str] = mapped_column(Text, nullable=True, comment="备选商品（JSON）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_need": self.user_need,
            "budget": self.budget,
            "recommended_product": self.recommended_product,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
