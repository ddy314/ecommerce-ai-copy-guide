"""爬虫管理服务 - 爬取数据入库 + 任务进度追踪 + 评论生成"""
from __future__ import annotations

import logging
import threading
import time
import random
from datetime import datetime, timedelta
from typing import Optional

from backend.database import SessionLocal
from backend.models.product import Product
from backend.models.review import Review

logger = logging.getLogger(__name__)

# ===== 评论生成模板 =====
REVIEW_TEMPLATES_POSITIVE = [
    "宝贝收到了，质量很好，物流也快，非常满意！",
    "用了几天感觉不错，性价比高，推荐购买。",
    "包装精美，做工精致，和描述一致，好评！",
    "第二次购买了，品质一如既往的好，值得信赖。",
    "物流速度快，包装完好，产品质感很好。",
    "价格实惠，质量超出预期，会回购的。",
    "手感不错，细节处理到位，满意的一次购物。",
    "朋友推荐的，果然好用，五星好评！",
    "收到货很惊喜，比图片还好看，非常喜欢。",
    "质量对得起这个价格，客服态度也很好。",
    "做工精良，材质舒适，使用体验很好。",
    "发货快，包装严实，产品没有瑕疵，好评。",
    "试用了几天，效果很好，值得入手。",
    "性价比超高，比实体店便宜很多，推荐！",
    "设计很人性化，使用方便，颜值也很高。",
]

REVIEW_TEMPLATES_NEUTRAL = [
    "东西一般般吧，对得起这个价格。",
    "还可以，就是物流有点慢。",
    "基本满足需求，没什么特别的感觉。",
    "质量一般，勉强能用，期望不要太高。",
    "包装有点简陋，东西还行。",
    "功能正常，但做工有待提升。",
    "用了一周，感觉一般，不功不过吧。",
    "颜色和图片有点色差，其他还好。",
]

REVIEW_TEMPLATES_NEGATIVE = [
    "质量不太行，用了一次就坏了，失望。",
    "和描述差距太大，图片是假的吧。",
    "物流太慢了，等了快两周才到。",
    "做工粗糙，有毛边，不值这个价。",
    "客服态度差，退货流程麻烦。",
    "用了两天就出问题了，质量堪忧。",
    "尺寸不合适，描述不清楚，不推荐。",
    "材质一般，有异味，放了好几天才散。",
]

USER_NAMES = [
    "张***", "李***", "王***", "刘***", "陈***", "杨***", "黄***", "赵***",
    "吴***", "周***", "徐***", "孙***", "马***", "朱***", "胡***", "郭***",
    "林***", "何***", "高***", "罗***", "郑***", "梁***", "谢***", "宋***",
    "用户7382", "用户2910", "用户5631", "用户8472", "用户3905", "用户6218",
    "mini***", "sky***", "blue***", "happy***", "cool***", "super***",
]


def generate_reviews(product_id: int, review_count: int, rating: float) -> list[Review]:
    """为商品生成评论"""
    reviews = []
    if review_count == 0:
        review_count = random.randint(1, 3)

    if rating >= 4.5:
        pos_ratio, neu_ratio = 0.85, 0.10
    elif rating >= 4.0:
        pos_ratio, neu_ratio = 0.70, 0.20
    elif rating >= 3.5:
        pos_ratio, neu_ratio = 0.50, 0.30
    else:
        pos_ratio, neu_ratio = 0.30, 0.30

    num_reviews = min(review_count, 20)
    if num_reviews == 0:
        num_reviews = 1

    for _ in range(num_reviews):
        r = random.random()
        if r < pos_ratio:
            content = random.choice(REVIEW_TEMPLATES_POSITIVE)
            review_rating = random.randint(4, 5)
        elif r < pos_ratio + neu_ratio:
            content = random.choice(REVIEW_TEMPLATES_NEUTRAL)
            review_rating = 3
        else:
            content = random.choice(REVIEW_TEMPLATES_NEGATIVE)
            review_rating = random.randint(1, 2)

        days_ago = random.randint(1, 180)
        created = datetime.now() - timedelta(days=days_ago)

        reviews.append(Review(
            product_id=product_id,
            content=content,
            rating=review_rating,
            user_name=random.choice(USER_NAMES),
            created_at=created,
        ))

    return reviews


class CrawlTask:
    """爬虫任务状态"""

    def __init__(self, task_id: str, keywords: list[str], pages_per_keyword: int = 2):
        self.task_id = task_id
        self.keywords = keywords
        self.pages_per_keyword = pages_per_keyword
        self.status: str = "pending"
        self.progress: int = 0
        self.total_found: int = 0
        self.total_saved: int = 0
        self.current_keyword: str = ""
        self.errors: list[str] = []
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.message: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "total_found": self.total_found,
            "total_saved": self.total_saved,
            "current_keyword": self.current_keyword,
            "keywords": self.keywords,
            "errors": self.errors,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "message": self.message,
        }


class CrawlManager:
    """爬虫任务管理器"""

    def __init__(self):
        self._tasks: dict[str, CrawlTask] = {}
        self._lock = threading.Lock()

    def create_task(self, keywords: list[str], pages_per_keyword: int = 2) -> str:
        task_id = f"crawl_{int(time.time())}_{len(self._tasks)}"
        task = CrawlTask(task_id, keywords, pages_per_keyword)
        with self._lock:
            self._tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Optional[CrawlTask]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [t.to_dict() for t in sorted(self._tasks.values(), key=lambda x: x.task_id, reverse=True)]

    def run_task(self, task_id: str):
        thread = threading.Thread(target=self._execute, args=(task_id,), daemon=True)
        thread.start()

    def _execute(self, task_id: str):
        """实际执行爬虫"""
        from backend.crawler.suning_crawler import SuningCrawler

        task = self._tasks.get(task_id)
        if not task:
            return

        task.status = "running"
        task.started_at = datetime.now().isoformat()
        task.message = "正在初始化爬虫..."

        try:
            crawler = SuningCrawler()
            total_keywords = len(task.keywords)

            for i, keyword in enumerate(task.keywords):
                task.current_keyword = keyword
                task.message = f"正在爬取关键词: {keyword} ({i+1}/{total_keywords})"
                task.progress = int(i / total_keywords * 100)

                try:
                    products = crawler.crawl_search(keyword, max_pages=task.pages_per_keyword)
                    task.total_found += len(products)

                    saved = self._save_products(products)
                    task.total_saved += saved
                    task.message = f"关键词 '{keyword}' 完成: 找到 {len(products)} 个, 入库 {saved} 个"

                except Exception as e:
                    error_msg = f"关键词 '{keyword}' 爬取失败: {str(e)}"
                    task.errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            task.progress = 100
            task.status = "completed"
            task.message = f"爬取完成: 共找到 {task.total_found} 个商品, 入库 {task.total_saved} 个"
            task.finished_at = datetime.now().isoformat()

        except Exception as e:
            task.status = "failed"
            task.message = f"爬虫任务失败: {str(e)}"
            task.errors.append(str(e))
            task.finished_at = datetime.now().isoformat()
            logger.error(f"爬虫任务失败: {e}", exc_info=True)

    def _save_products(self, products: list) -> int:
        """将爬取的商品保存到数据库 + 生成评论"""
        saved = 0
        with SessionLocal() as db:
            for p in products:
                try:
                    if p.product_id:
                        existing = db.query(Product).filter_by(
                            platform="suning", product_id=p.product_id
                        ).first()
                        if existing:
                            existing.price = p.price
                            existing.rating = p.rating
                            existing.image_url = p.image_url
                            existing.updated_at = datetime.now()
                            db.commit()
                            saved += 1
                            continue

                    product = Product(
                        platform="suning",
                        product_id=p.product_id,
                        name=p.name,
                        category=p.category,
                        price=p.price,
                        original_price=p.original_price,
                        image_url=p.image_url,
                        detail_url=p.detail_url,
                        source_url=p.detail_url,
                        specs="",
                        selling_points=p.sell_point,
                        brand=p.shop,
                        sales_count=random.randint(10, 5000),
                        rating=p.rating,
                        review_count=p.review_count if p.review_count > 0 else random.randint(1, 20),
                    )
                    db.add(product)
                    db.flush()

                    # 生成评论
                    reviews = generate_reviews(product.id, product.review_count, p.rating)
                    for r in reviews:
                        db.add(r)

                    db.commit()
                    saved += 1

                except Exception as e:
                    db.rollback()
                    logger.warning(f"商品入库失败: {e}")
                    continue

        logger.info(f"商品入库完成: {saved}/{len(products)} 个成功")
        return saved


# 全局单例
crawl_manager = CrawlManager()
