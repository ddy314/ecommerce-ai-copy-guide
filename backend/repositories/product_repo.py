"""商品数据仓库"""
from __future__ import annotations

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

from backend.models.product import Product
from backend.models.review import Review


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)

    def get_by_platform_id(self, platform: str, product_id: str) -> Product | None:
        stmt = select(Product).where(
            Product.platform == platform,
            Product.product_id == product_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def search(self, keyword: str, limit: int = 20, offset: int = 0) -> list[Product]:
        stmt = (
            select(Product)
            .where(or_(Product.name.contains(keyword), Product.category.contains(keyword)))
            .order_by(Product.review_count.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self, category: str | None = None, limit: int = 50, offset: int = 0) -> list[Product]:
        stmt = select(Product).order_by(Product.created_at.desc())
        if category:
            stmt = stmt.where(Product.category == category)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def list_categories(self) -> list[str]:
        stmt = (
            select(Product.category)
            .distinct()
            .where(Product.category.isnot(None))
            .order_by(Product.category)
        )
        return [r[0] for r in self.db.execute(stmt).all()]

    def count(self, category: str | None = None) -> int:
        stmt = select(func.count(Product.id))
        if category:
            stmt = stmt.where(Product.category == category)
        return self.db.execute(stmt).scalar() or 0

    def get_with_reviews(self, product_id: int) -> Product | None:
        stmt = (
            select(Product)
            .options(joinedload(Product.reviews))
            .where(Product.id == product_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_reviews(self, product_id: int, limit: int = 100) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_review_count(self, product_id: int) -> None:
        count = self.db.execute(
            select(func.count(Review.id)).where(Review.product_id == product_id)
        ).scalar() or 0
        product = self.db.get(Product, product_id)
        if product:
            product.review_count = count
            self.db.commit()
