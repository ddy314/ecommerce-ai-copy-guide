"""生成任务模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class GenerationTask(Base):
    """生成任务表"""

    __tablename__ = "generation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(50), comment="任务类型（copy/guide/review_analysis/live_script）")
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=True, comment="关联商品")
    input_params: Mapped[str] = mapped_column(Text, comment="输入参数（JSON）")
    output_result: Mapped[str] = mapped_column(Text, comment="输出结果（JSON）")
    status: Mapped[str] = mapped_column(String(20), default="completed", comment="状态（pending/completed/failed）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    product = relationship("Product", back_populates="generation_tasks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "product_id": self.product_id,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
