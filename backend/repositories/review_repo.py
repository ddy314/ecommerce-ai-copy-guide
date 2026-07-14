"""评论数据仓库"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.models.review import Review


class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_product(self, product_id: int, limit: int = 200) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_contents(self, product_id: int, limit: int = 200) -> list[str]:
        reviews = self.get_by_product(product_id, limit)
        return [r.content for r in reviews if r.content]

    def count_by_product(self, product_id: int) -> int:
        return (
            self.db.execute(
                select(func.count(Review.id)).where(Review.product_id == product_id)
            ).scalar()
            or 0
        )

    def get_all_contents(self, limit: int = 500) -> list[str]:
        stmt = select(Review.content).order_by(Review.created_at.desc()).limit(limit)
        return [r[0] for r in self.db.execute(stmt).all() if r[0]]
