"""RAG 知识库模型 - 存储商品知识向量化数据"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class KnowledgeEntry(Base):
    """知识库条目 - 商品参数/规格/售后/FAQ 向量化存储"""
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=True, comment="关联商品ID")
    category: Mapped[str] = mapped_column(String(50), comment="知识类型: spec/faq/after_sale/policy")
    title: Mapped[str] = mapped_column(String(500), comment="条目标题")
    content: Mapped[str] = mapped_column(Text, comment="知识内容")
    keywords: Mapped[str] = mapped_column(Text, nullable=True, comment="关键词(JSON)")
    vector_data: Mapped[str] = mapped_column(Text, nullable=True, comment="简化向量数据(JSON)")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "product_id": self.product_id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "keywords": json.loads(self.keywords) if self.keywords else [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QARecord(Base):
    """用户问答记录 - 记录用户提问和AI回答"""
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True, comment="用户ID")
    product_id: Mapped[int] = mapped_column(Integer, nullable=True, comment="关联商品ID")
    question: Mapped[str] = mapped_column(Text, comment="用户问题")
    answer: Mapped[str] = mapped_column(Text, comment="AI回答")
    question_type: Mapped[str] = mapped_column(String(50), default="auto", comment="问题类型")
    source: Mapped[str] = mapped_column(String(50), default="rag", comment="回答来源: rag/template/mock")
    helpful: Mapped[int] = mapped_column(Integer, default=0, comment="有用数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "question": self.question,
            "answer": self.answer,
            "question_type": self.question_type,
            "source": self.source,
            "helpful": self.helpful,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
