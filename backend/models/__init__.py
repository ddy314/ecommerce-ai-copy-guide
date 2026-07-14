from backend.models.product import Product
from backend.models.review import Review
from backend.models.generation_task import GenerationTask
from backend.models.recommendation_log import RecommendationLog
from backend.models.user import User, UserAddress, UserFavorite, BrowseHistory
from backend.models.shopping import CartItem, Order, OrderItem
from backend.models.knowledge_base import KnowledgeEntry, QARecord
from backend.models.customer_service import CustomerServiceMessage

__all__ = [
    "Product",
    "Review",
    "GenerationTask",
    "RecommendationLog",
    "User",
    "UserAddress",
    "UserFavorite",
    "BrowseHistory",
    "CartItem",
    "Order",
    "OrderItem",
    "KnowledgeEntry",
    "QARecord",
    "CustomerServiceMessage",
]
