"""种子数据初始化 - 创建测试商品和评论"""
from __future__ import annotations

import logging
from backend.database import SessionLocal, init_db
from backend.models.product import Product
from backend.models.review import Review
from backend.models.user import User
from backend.services.auth_service import hash_password

logger = logging.getLogger(__name__)

SEED_PRODUCTS = [
    {
        "name": "云感护腰人体工学办公椅",
        "category": "办公家具",
        "price": 599.0,
        "original_price": 899.0,
        "specs": "坐高45-55cm可调|扶手4D调节|腰托自适应|承重150kg|网布材质",
        "selling_points": "自适应腰托分区支撑，4D扶手多角度调节，透气网布久坐不闷",
        "image_url": "",
        "brand": "云感",
    },
    {
        "name": "静音无线蓝牙耳机 Pro",
        "category": "数码电子",
        "price": 299.0,
        "original_price": 499.0,
        "specs": "蓝牙5.3|主动降噪|续航32小时|IPX4防水|动圈13mm",
        "selling_points": "主动降噪沉浸体验，32小时超长续航，IPX4防水运动无忧",
        "image_url": "",
        "brand": "音素",
    },
    {
        "name": "智能升降办公桌电动款",
        "category": "办公家具",
        "price": 1299.0,
        "original_price": 1899.0,
        "specs": "桌面尺寸120x60cm|升降范围70-120cm|承重80kg|电机静音|记忆4档",
        "selling_points": "一键升降站坐交替，静音电机平稳顺滑，4档记忆高度",
        "image_url": "",
        "brand": "立课",
    },
    {
        "name": "304不锈钢保温杯大容量",
        "category": "生活用品",
        "price": 89.0,
        "original_price": 129.0,
        "specs": "容量500ml|304不锈钢|保温12小时|真空双层|杯盖硅胶密封",
        "selling_points": "12小时长效保温，304食品级不锈钢，真空双层防烫",
        "image_url": "",
        "brand": "暖途",
    },
    {
        "name": "机械键盘青轴RGB背光",
        "category": "数码电子",
        "price": 199.0,
        "original_price": 299.0,
        "specs": "青轴段落感|104键全键无冲|RGB背光|Type-C可换线|键帽PBT",
        "selling_points": "青轴清脆手感，RGB全色背光，PBT键帽耐磨不掉字",
        "image_url": "",
        "brand": "键客",
    },
    {
        "name": "纯棉宽松短袖T恤男女同款",
        "category": "服装服饰",
        "price": 59.0,
        "original_price": 99.0,
        "specs": "100%纯棉|克重220g|版型宽松|尺码S-3XL|多色可选",
        "selling_points": "220g重磅纯棉不透肉，宽松版型百搭不挑人，多色多码可选",
        "image_url": "",
        "brand": "简棉",
    },
    {
        "name": "便携折叠露营椅超轻量",
        "category": "户外运动",
        "price": 149.0,
        "original_price": 229.0,
        "specs": "重量1.2kg|承重120kg|铝合金骨架|收纳后48cm|面料600D牛津布",
        "selling_points": "1.2kg超轻量便携，铝合金骨架稳固承重，一键展开收纳",
        "image_url": "",
        "brand": "山野",
    },
    {
        "name": "LED智能护眼台灯触控调光",
        "category": "家居家电",
        "price": 129.0,
        "original_price": 199.0,
        "specs": "色温2700-6500K|亮度无极调节|显色指数Ra95|USB供电|触控开关",
        "selling_points": "Ra95高显色无频闪护眼，色温亮度无极调节，USB供电即插即用",
        "image_url": "",
        "brand": "明视",
    },
]

SEED_REVIEWS = {
    "云感护腰人体工学办公椅": [
        ("这椅子腰托很舒服，坐一天腰不酸了", 5, "打工人小王"),
        ("安装简单，10分钟搞定，网布透气性好", 5, "办公室达人"),
        ("扶手调节范围大，打字手臂有支撑", 4, "码农小李"),
        ("价格偏贵但物有所值，比之前那把好太多", 4, "理性消费者"),
        ("包装有点破损，但产品没受影响", 3, "买家小张"),
    ],
    "静音无线蓝牙耳机 Pro": [
        ("降噪效果超出预期，地铁上听歌很清晰", 5, "通勤族"),
        ("续航很给力，充一次用了一周", 5, "音乐爱好者"),
        ("佩戴舒适，跑步不掉", 4, "运动达人"),
        ("左耳偶尔断连，重新配对后恢复", 3, "数码评测员"),
    ],
    "智能升降办公桌电动款": [
        ("升降很平稳，声音不大，办公室用没问题", 5, "产品经理老陈"),
        ("站立办公后腰好多了，值得投资", 5, "久坐受害者"),
        ("桌面板材有轻微划痕，客服补了50元", 3, "细节控"),
    ],
    "机械键盘青轴RGB背光": [
        ("青轴手感太爽了，打字像弹琴", 5, "键盘发烧友"),
        ("RGB灯效很炫，晚上打字特别带感", 5, "夜猫子"),
        ("声音有点大，室友有意见", 3, "合租打工人"),
        ("PBT键帽质感很好，不会打油", 4, "外设党"),
    ],
}


def seed_database():
    """初始化数据库并写入种子数据"""
    logger.info("开始初始化数据库...")
    init_db()
    logger.info("数据库表创建完成")

    with SessionLocal() as db:
        # 创建默认用户
        if not db.query(User).filter_by(username="merchant").first():
            db.add(User(
                username="merchant",
                password_hash=hash_password("merchant123"),
                nickname="商家管理员",
                role="merchant",
            ))
            logger.info("创建默认商家账号: merchant / merchant123")

        if not db.query(User).filter_by(username="user").first():
            db.add(User(
                username="user",
                password_hash=hash_password("user123"),
                nickname="测试用户",
                role="user",
            ))
            logger.info("创建默认用户账号: user / user123")

        # 创建商品
        existing_count = db.query(Product).count()
        if existing_count == 0:
            for p_data in SEED_PRODUCTS:
                product = Product(
                    name=p_data["name"],
                    category=p_data["category"],
                    price=p_data["price"],
                    original_price=p_data["original_price"],
                    specs=p_data["specs"],
                    selling_points=p_data["selling_points"],
                    image_url=p_data.get("image_url", ""),
                    brand=p_data.get("brand", ""),
                    platform="manual",
                )
                db.add(product)
                db.flush()  # 获取 product.id

                # 添加评论
                reviews = SEED_REVIEWS.get(p_data["name"], [])
                for content, rating, author in reviews:
                    review = Review(
                        product_id=product.id,
                        content=content,
                        rating=rating,
                        user_name=author,
                    )
                    db.add(review)

                # 更新评论数
                product.review_count = len(reviews)
                if reviews:
                    product.rating = sum(r[1] for r in reviews) / len(reviews)

            logger.info(f"已创建 {len(SEED_PRODUCTS)} 个商品及其评论")
        else:
            logger.info(f"数据库已有 {existing_count} 个商品，跳过种子数据")

        db.commit()

    logger.info("种子数据初始化完成！")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    seed_database()
