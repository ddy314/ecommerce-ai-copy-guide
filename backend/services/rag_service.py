"""RAG 检索增强问答服务 - 深度数据驱动的智能问答

当用户提问时，自动从数据库检索匹配商品、评论、同类商品，
结合品牌知识库构建数据驱动的精准回答，而非模板回复。
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Optional

from sqlalchemy import select, or_, func

from backend.database import SessionLocal
from backend.models.knowledge_base import KnowledgeEntry, QARecord
from backend.models.product import Product
from backend.models.review import Review

logger = logging.getLogger(__name__)

# 多路召回路径权重
RECALL_PATH_WEIGHTS = {
    "exact_name": 1.0,
    "category_keyword": 0.85,
    "general_keyword": 0.7,
    "knowledge_base": 0.75,
    "brand_knowledge": 0.6,
}


# ===== 分类关键词映射（用于精准分类检测，防止跨分类匹配）=====
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "宠物用品": ["猫粮", "狗粮", "猫砂", "宠物窝", "猫罐头", "狗罐头", "猫条", "狗零食",
                "宠物玩具", "猫爬架", "狗链", "牵引绳", "宠物衣服", "猫", "狗", "宠物",
                "狗咬胶", "化毛膏", "营养膏", "宠物沐浴"],
    "化妆品": ["口红", "面霜", "面膜", "精华液", "防晒霜", "粉底", "眼影", "散粉",
              "乳液", "爽肤水", "卸妆", "彩妆", "护肤", "化妆品", "润唇膏", "腮红",
              "香水", "洁面", "面霜", "抗皱", "美白", "保湿"],
    "母婴用品": ["奶粉", "纸尿裤", "婴儿推车", "儿童玩具", "宝宝", "婴儿", "母婴",
                "奶瓶", "辅食", "婴儿车", "安全座椅", "学步车", "婴儿床", "湿巾",
                "幼儿", "新生儿", "孕妈"],
    "数码电子": ["耳机", "手机", "键盘", "鼠标", "音箱", "蓝牙", "充电宝", "数据线",
               "智能手表", "平板", "电脑", "数码", "摄像头", "路由器", "投影仪",
               "手机壳", "充电器", "U盘", "显示器"],
    "家居家电": ["台灯", "落地灯", "电风扇", "电水壶", "加湿器", "空气净化器",
               "挂烫机", "吸尘器", "取暖器", "扫地机器人", "洗碗机", "烤箱",
               "微波炉", "电饭煲", "空调", "冰箱", "洗衣机"],
    "办公家具": ["办公椅", "人体工学椅", "升降桌", "书架", "文件柜", "电脑桌",
               "会议桌", "办公桌", "书桌", "椅子", "职员椅"],
    "服装服饰": ["T恤", "衬衫", "卫衣", "牛仔裤", "连衣裙", "羽绒服", "外套",
               "裤子", "裙子", "毛衣", "风衣", "西装", "内衣", "袜子", "帽子"],
    "户外运动": ["背包", "露营椅", "帐篷", "睡袋", "瑜伽垫", "哑铃", "跑步鞋",
                "篮球", "足球", "羽毛球", "自行车", "滑板", "泳衣", "运动"],
    "生活用品": ["保温杯", "水杯", "马克杯", "雨伞", "收纳盒", "毛巾",
               "牙刷", "梳子", "镜子", "挂钩", "垃圾袋", "纸巾"],
}


# ===== 品牌知识库 =====
BRAND_KNOWLEDGE: dict[str, str] = {
    # 数码品牌
    "华为": "华为是全球领先的ICT基础设施和智能终端提供商，产品涵盖手机、电脑、可穿戴设备等，以技术创新和高品质著称。",
    "HUAWEI": "华为是全球领先的ICT基础设施和智能终端提供商，产品涵盖手机、电脑、可穿戴设备等，以技术创新和高品质著称。",
    "苹果": "Apple（苹果）是全球知名科技公司，以iPhone、Mac、AirPods等产品闻名，注重设计美学和用户体验。",
    "Apple": "Apple（苹果）是全球知名科技公司，以iPhone、Mac、AirPods等产品闻名，注重设计美学和用户体验。",
    "小米": "小米是以智能手机、智能硬件和IoT平台为核心的科技公司，以高性价比和生态链产品著称。",
    "Redmi": "Redmi是小米旗下的子品牌，主打高性价比手机和智能设备，面向年轻用户群体。",
    "漫步者": "漫步者（EDIFIER）是国内领先的音频设备品牌，产品涵盖耳机、音箱等，以音质出色和性价比高著称。",
    "JBL": "JBL是全球知名的音响品牌，隶属于哈曼国际，产品涵盖便携音箱、耳机等，以强劲低音和时尚设计著称。",
    "索尼": "索尼（SONY）是日本跨国综合企业，在消费电子、游戏、影音等领域有深厚积累，产品以高品质和创新著称。",
    "飞利浦": "飞利浦（Philips）是荷兰跨国品牌，在个人护理、家居照明、小家电等领域有广泛产品线，以可靠品质著称。",
    "BOSE": "Bose（博士）是美国知名音响品牌，以降噪技术和高品质音效闻名，产品涵盖耳机、音箱等。",
    # 家居家电品牌
    "苏泊尔": "苏泊尔（SUPOR）是中国领先的厨房小家电品牌，产品涵盖电饭煲、炒锅、压力锅等，以品质可靠和性价比高著称。",
    "欧普": "欧普照明（OPPLE）是中国领先的照明品牌，产品涵盖LED灯、台灯、吊灯等，以节能环保和设计感著称。",
    "雷士": "雷士照明（NVC）是中国知名照明品牌，产品涵盖商业照明和家居照明，以专业品质和高性价比著称。",
    # 家具品牌
    "全友": "全友家居（QuanU）是中国大型家具企业，产品涵盖板式家具、软体家具等，以环保材质和实用设计著称。",
    "爱果乐": "爱果乐（igrow）是专业儿童学习桌椅品牌，以人体工学设计和环保材料著称，深受家长信赖。",
    # 运动品牌
    "361度": "361度是中国知名体育用品品牌，产品涵盖运动鞋服及配件，以专业运动科技和高性价比著称。",
    "迪卡侬": "迪卡侬是法国大型体育用品零售商，自有品牌产品涵盖各类运动场景，以高性价比和全品类著称。",
    # 化妆品品牌
    "欧莱雅": "欧莱雅（L'Oreal）是全球最大的化妆品集团之一，产品涵盖护肤、彩妆、染发等，以科研创新和高品质著称。",
    "雅诗兰黛": "雅诗兰黛（Estee Lauder）是全球顶级护肤和彩妆品牌，以小棕瓶精华等明星产品闻名，主打抗衰老和修护。",
    "兰蔻": "兰蔻（Lancome）是法国欧莱雅集团旗下的高端美妆品牌，以精华液、粉底液等产品闻名，主打科技护肤。",
    "百雀羚": "百雀羚是中国经典护肤品牌，以草本护肤理念和高性价比著称，深受国人喜爱。",
    "自然堂": "自然堂是伽蓝集团旗下的护肤品牌，以喜马拉雅天然成分和高性价比著称，适合亚洲肌肤。",
    "珀莱雅": "珀莱雅是中国知名护肤品牌，以海洋科技护肤和双抗精华等明星产品著称，性价比极高。",
    "薇诺娜": "薇诺娜是专注敏感肌护理的品牌，以云南特有植物成分和皮肤科医学背景著称，适合问题肌肤。",
    "花西子": "花西子是东方美妆品牌，以东方美学设计和天然花卉成分著称，产品涵盖口红、散粉等彩妆。",
    "完美日记": "完美日记是国货彩妆品牌，以高性价比和时尚色彩著称，深受年轻消费者喜爱。",
    "SK-II": "SK-II是日本高端护肤品牌，以Pitera精华成分和神仙水等明星产品闻名，主打肌肤修护。",
    "海蓝之谜": "海蓝之谜（La Mer）是雅诗兰黛集团旗下的顶级护肤品牌，以神奇活性精萃和卓越修护效果著称。",
    # 母婴品牌
    "飞鹤": "飞鹤乳业是中国领先的婴幼儿奶粉品牌，以新鲜生牛乳配方和适合中国宝宝体质著称。",
    "伊利": "伊利是中国最大的乳制品企业，奶粉产品涵盖婴幼儿和成人系列，以品质安全著称。",
    "君乐宝": "君乐宝乳业是中国知名乳品品牌，以婴幼儿奶粉和酸奶产品著称，主打性价比和品质安全。",
    "美素佳儿": "美素佳儿是荷兰皇家菲仕兰旗下的婴幼儿奶粉品牌，以天然营养和易消化吸收著称。",
    "帮宝适": "帮宝适（Pampers）是宝洁旗下的纸尿裤品牌，以柔软舒适和超强吸收著称，全球销量领先。",
    "好奇": "好奇（Huggies）是金佰利旗下的纸尿裤品牌，以透气干爽和贴合设计著称，深受妈妈信赖。",
    "花王": "花王（Kao）是日本知名日用品品牌，纸尿裤产品以柔软透气和超强吸收著称，品质优异。",
    # 宠物品牌
    "皇家": "皇家（ROYAL CANIN）是法国知名宠物食品品牌，以科学配方和精准营养著称，产品涵盖猫粮狗粮。",
    "渴望": "渴望（Orijen）是加拿大高端宠物食品品牌，以高肉含量和天然食材著称，被公认为顶级猫粮狗粮之一。",
    "爱肯拿": "爱肯拿（Acana）是加拿大宠物食品品牌，以本地新鲜食材和低碳水配方著称，性价比优于渴望。",
    "伯纳天纯": "伯纳天纯是中国宠物食品品牌，以无谷配方和高肉含量著称，性价比不错。",
    "比瑞吉": "比瑞吉是国内知名宠物食品品牌，以北欧配方和天然食材著称，适合国产中高端选择。",
}


class RAGService:
    """RAG 知识库检索增强问答 - 深度数据驱动"""

    def search_knowledge(
        self, question: str, product_id: int | None = None, limit: int = 5
    ) -> list[dict]:
        """检索知识库中与问题最相关的条目"""
        with SessionLocal() as db:
            stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
            if product_id:
                stmt = stmt.where(
                    or_(
                        KnowledgeEntry.product_id == product_id,
                        KnowledgeEntry.product_id.is_(None),
                    )
                )

            entries = list(db.execute(stmt).scalars().all())
            if not entries:
                return []

            scored = []
            question_keywords = self._extract_keywords(question)
            for entry in entries:
                score = self._calculate_similarity(question, question_keywords, entry)
                if score > 0:
                    scored.append((score, entry))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, entry in scored[:limit]:
                data = entry.to_dict()
                data["score"] = round(score, 2)
                results.append(data)
            return results

    # ===== 核心：智能问答 =====

    def answer_question(
        self,
        question: str,
        product_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """深度数据驱动的智能问答（多路召回 + Rerank）

        策略：
        1. 多路召回：精确商品名、分类关键词、通用关键词、知识库、品牌知识库
        2. Rerank：按路径权重、匹配度、评分综合排序，选出最佳商品
        3. 检索商品知识库，补充规格/售后/FAQ 等信息
        4. 获取真实评论 + 同类推荐
        5. 根据问题类型构建数据驱动的精准回答
        """
        q_type = self._detect_question_type(question)

        # 获取商品数据
        product: Optional[Product] = None
        related_products: list[Product] = []
        reviews: list[Review] = []
        knowledge_context = ""

        with SessionLocal() as db:
            if product_id:
                product = db.get(Product, product_id)
            else:
                # 多路召回 + Rerank 选出最佳商品
                product = self._rerank_best_product(
                    db, self._multi_path_recall_products(db, question)
                )

            if product:
                # 获取真实评论
                reviews = list(db.execute(
                    select(Review)
                    .where(Review.product_id == product.id)
                    .order_by(Review.created_at.desc())
                    .limit(10)
                ).scalars().all())

                # 获取同类推荐商品
                related_products = list(db.execute(
                    select(Product).where(
                        Product.category == product.category,
                        Product.id != product.id,
                    ).order_by(Product.rating.desc()).limit(5)
                ).scalars().all())

                # 检索商品知识库，获取相关上下文
                knowledge_context = self._retrieve_knowledge_context(
                    db, question, product
                )

        # 构建回答
        if product:
            answer = self._build_data_driven_answer(
                question, q_type, product, reviews, related_products,
                knowledge_context=knowledge_context,
            )
            source = "data_rag"
        else:
            # 数据库没有匹配商品，尝试通用回答
            answer = self._build_no_match_answer(question, q_type)
            source = "fallback"

        # 记录问答
        try:
            with SessionLocal() as db:
                record = QARecord(
                    user_id=user_id,
                    product_id=product.id if product else product_id,
                    question=question,
                    answer=answer,
                    question_type=q_type,
                    source=source,
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"问答记录保存失败: {e}")

        # 构建相关推荐信息
        related_info = []
        for p in related_products[:3]:
            related_info.append({
                "id": p.id,
                "name": p.name,
                "price": p.price or 0,
                "rating": p.rating or 5.0,
                "category": p.category or "",
                "image_url": p.image_url or "",
            })

        # 构建主商品信息（供前端渲染可点击卡片）
        product_info = None
        if product:
            product_info = {
                "id": product.id,
                "name": product.name,
                "price": product.price or 0,
                "rating": product.rating or 5.0,
                "category": product.category or "",
                "image_url": product.image_url or "",
                "brand": self._get_real_brand(product),
            }

        return {
            "question": question,
            "answer": answer,
            "source": source,
            "product": product_info,
            "related_products": related_info,
        }

    def _detect_category(self, question: str) -> Optional[str]:
        """从问题中检测商品分类，防止跨分类匹配"""
        q_lower = question.lower()
        best_category = None
        best_score = 0
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in q_lower:
                    # 长关键词权重更高
                    score += len(kw)
            if score > best_score:
                best_score = score
                best_category = category
        
        # 只在有明确匹配时才返回分类
        if best_score >= 2:
            return best_category
        return None

    def _extract_primary_keywords(self, question: str) -> list[str]:
        """提取问题中的商品核心关键词（直接来自分类关键词表）"""
        q_lower = question.lower()
        primary_kws = []
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in q_lower and len(kw) >= 2:
                    primary_kws.append(kw)
        # 去重并按长度降序（长词优先）
        primary_kws = list(set(primary_kws))
        primary_kws.sort(key=len, reverse=True)
        return primary_kws

    def _search_product_by_question(self, db, question: str) -> Optional[Product]:
        """从问题关键词搜索数据库中最匹配的商品 - 带分类精准过滤

        检索优先级：
        0. 精确商品名匹配（用户直接粘贴商品名时）
        1. 核心关键词 + 分类匹配
        2. 通用关键词 + 分类匹配
        3. 全局关键词匹配
        """
        # ===== 0. 精确商品名匹配（最高优先级）=====
        # 当用户直接粘贴商品名或问题中包含较长的商品名片段时，
        # 优先在数据库中查找名称最接近的商品
        exact_match = self._try_exact_product_match(db, question)
        if exact_match:
            return exact_match

        # 1. 提取商品核心关键词（如"猫粮"、"口红"）
        primary_kws = self._extract_primary_keywords(question)
        
        # 2. 检测分类
        detected_category = self._detect_category(question)

        # 3. 如果有核心关键词，优先用核心关键词搜索
        if primary_kws:
            conditions = [Product.name.ilike(f"%{kw}%") for kw in primary_kws]
            
            if detected_category:
                # 在正确分类内用核心关键词搜索
                results = list(db.execute(
                    select(Product).where(
                        Product.category == detected_category,
                        or_(*conditions),
                    ).limit(50)
                ).scalars().all())
            else:
                results = list(db.execute(
                    select(Product).where(or_(*conditions)).limit(50)
                ).scalars().all())

            if results:
                # 按核心关键词匹配度排序
                def primary_score(p: Product) -> float:
                    score = 0.0
                    name_lower = (p.name or "").lower()
                    for kw in primary_kws:
                        if kw.lower() in name_lower:
                            score += len(kw) * 5.0  # 核心关键词权重极高
                    score += (p.rating or 0) * 0.1
                    return score
                results.sort(key=primary_score, reverse=True)
                return results[0]

        # 4. 核心关键词没找到，用通用关键词搜索
        keywords = self._extract_keywords(question)
        search_kws = [kw for kw in keywords if 2 <= len(kw) <= 6]
        if not search_kws:
            search_kws = keywords[:5]

        conditions = [Product.name.ilike(f"%{kw}%") for kw in search_kws[:10]]
        if not conditions:
            return None

        if detected_category:
            results = list(db.execute(
                select(Product).where(
                    Product.category == detected_category,
                    or_(*conditions),
                ).limit(50)
            ).scalars().all())
            if results:
                def kw_score(p: Product) -> float:
                    score = 0.0
                    name_lower = (p.name or "").lower()
                    for kw in search_kws:
                        if kw.lower() in name_lower:
                            score += len(kw) * 2.0
                    score += (p.rating or 0) * 0.1
                    return score
                results.sort(key=kw_score, reverse=True)
                return results[0]

        # 5. 全局搜索
        all_results = list(db.execute(
            select(Product).where(or_(*conditions)).limit(50)
        ).scalars().all())
        if not all_results:
            return None

        def global_score(p: Product) -> float:
            score = 0.0
            name_lower = (p.name or "").lower()
            for kw in search_kws:
                if kw.lower() in name_lower:
                    score += len(kw) * 2.0
            if detected_category and p.category == detected_category:
                score += 5.0
            score += (p.rating or 0) * 0.1
            return score

        all_results.sort(key=global_score, reverse=True)
        return all_results[0] if all_results else None

    # ===== 多路召回与 Rerank =====

    def _multi_path_recall_products(
        self, db, question: str
    ) -> list[tuple[Product, float, str]]:
        """多路召回候选商品

        返回 (product, raw_score, path_name) 列表，用于后续 Rerank。
        """
        candidates: list[tuple[Product, float, str]] = []
        q_lower = question.lower()
        detected_category = self._detect_category(question)
        primary_kws = self._extract_primary_keywords(question)
        keywords = self._extract_keywords(question)
        search_kws = [kw for kw in keywords if 2 <= len(kw) <= 6] or keywords[:5]

        # Path 1: 精确商品名匹配
        exact = self._try_exact_product_match(db, question)
        if exact:
            candidates.append((exact, 10.0, "exact_name"))

        # Path 2: 分类 + 核心关键词
        if primary_kws:
            conditions = [Product.name.ilike(f"%{kw}%") for kw in primary_kws]
            stmt = select(Product)
            if detected_category:
                stmt = stmt.where(
                    Product.category == detected_category,
                    or_(*conditions),
                )
            else:
                stmt = stmt.where(or_(*conditions))
            results = list(db.execute(stmt.limit(50)).scalars().all())
            for p in results:
                name_lower = (p.name or "").lower()
                score = sum(len(kw) * 5.0 for kw in primary_kws if kw.lower() in name_lower)
                score += (p.rating or 0) * 0.1
                candidates.append((p, score, "category_keyword"))

        # Path 3: 通用关键词全局召回
        if search_kws:
            conditions = [Product.name.ilike(f"%{kw}%") for kw in search_kws[:10]]
            results = list(db.execute(
                select(Product).where(or_(*conditions)).limit(50)
            ).scalars().all())
            for p in results:
                name_lower = (p.name or "").lower()
                score = sum(len(kw) * 2.0 for kw in search_kws if kw.lower() in name_lower)
                if detected_category and p.category == detected_category:
                    score += 5.0
                score += (p.rating or 0) * 0.1
                candidates.append((p, score, "general_keyword"))

        # Path 4: 品牌知识库触发商品召回
        matched_brands = [
            brand for brand in BRAND_KNOWLEDGE
            if brand.lower() in q_lower
        ]
        if matched_brands:
            brand_conditions = [
                Product.name.ilike(f"%{brand}%") for brand in matched_brands
            ]
            results = list(db.execute(
                select(Product).where(or_(*brand_conditions)).limit(30)
            ).scalars().all())
            for p in results:
                score = 3.0 + (p.rating or 0) * 0.1
                candidates.append((p, score, "brand_knowledge"))

        return candidates

    def _rerank_best_product(
        self, db, candidates: list[tuple[Product, float, str]]
    ) -> Optional[Product]:
        """对多路召回结果进行融合排序，返回最佳商品"""
        if not candidates:
            return None

        # 按商品 ID 聚合多路得分
        product_scores: dict[int, tuple[Product, float]] = {}
        for product, raw_score, path in candidates:
            weight = RECALL_PATH_WEIGHTS.get(path, 0.5)
            fused_score = raw_score * weight
            if product.id in product_scores:
                # 取最高得分的召回路径，并叠加少量分数体现多路径命中
                existing = product_scores[product.id][1]
                product_scores[product.id] = (
                    product,
                    max(existing, fused_score) + 0.3,
                )
            else:
                product_scores[product.id] = (product, fused_score)

        # 排序并返回最佳商品
        ranked = sorted(
            product_scores.values(), key=lambda x: x[1], reverse=True
        )
        best = ranked[0]
        logger.info(
            f"Rerank 最佳商品: {best[0].name[:40]}, 融合得分={best[1]:.2f}, "
            f"候选数={len(ranked)}"
        )
        return best[0]

    def _retrieve_knowledge_context(
        self, db, question: str, product: Product
    ) -> str:
        """检索商品知识库并返回相关文本上下文"""
        entries = list(db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.is_active == True,
                or_(
                    KnowledgeEntry.product_id == product.id,
                    KnowledgeEntry.product_id.is_(None),
                ),
            )
        ).scalars().all())
        if not entries:
            return ""

        question_kws = self._extract_keywords(question)
        scored = []
        for entry in entries:
            score = self._calculate_similarity(question, question_kws, entry)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_entries = [entry for _, entry in scored[:3]]
        if not top_entries:
            return ""

        parts = []
        for entry in top_entries:
            parts.append(f"【{entry.category}】{entry.title}: {entry.content}")
        return "\n".join(parts)

    def _try_exact_product_match(self, db, question: str) -> Optional[Product]:
        """尝试从问题中提取商品名并精确匹配数据库中的商品

        当用户直接粘贴完整商品名（如"兰蔻塑颜三重密集焕颜面霜15ml*3新老款随机"）
        并询问价格、评价等时，优先找到精确匹配的商品，而非按分类关键词模糊搜索。

        策略：
        1. 从问题中去除常见疑问句式，提取潜在商品名
        2. 用提取的字符串在数据库中做 ilike 精确搜索
        3. 按名称匹配度排序（覆盖率最高的优先）
        """
        # 去除常见疑问词和句式，提取潜在商品名
        cleaned = question.strip()

        # 移除常见问答句式
        qa_patterns = [
            r"多少钱", r"价格", r"贵不贵", r"便宜", r"划算", r"性价比",
            r"怎么样", r"好不好", r"评价", r"评论", r"口碑", r"评分",
            r"推荐", r"品牌", r"牌子", r"功能", r"效果", r"尺寸", r"规格",
            r"退换", r"售后", r"保修", r"值不值得", r"值不值",
            r"请问", r"一下", r"吗", r"呢", r"吧", r"啊",
            r"这个", r"那个", r"这款", r"那款", r"了解",
            r"介绍", r"告诉", r"知道", r"对比", r"比较",
            r"？", r"\?", r"是", r"的", r"了", r"有",
        ]
        for pattern in qa_patterns:
            cleaned = re.sub(pattern, "", cleaned)

        cleaned = cleaned.strip()

        # 如果清理后剩余文本太短，不可能是商品名
        if len(cleaned) < 4:
            return None

        # 从原始问题中提取所有可能的连续商品名片段（中文+英文+数字+常见符号）
        # 商品名通常包含：中文、英文、数字、空格、*、-、ml、g、kg 等单位
        potential_names = self._extract_potential_product_names(question)
        if not potential_names:
            return None

        # 对每个潜在商品名，在数据库中搜索
        best_match: Optional[Product] = None
        best_score: float = 0.0

        for name in potential_names:
            if len(name) < 4:
                continue
            # 用 ilike 搜索名称包含该片段的商品
            try:
                candidates = list(db.execute(
                    select(Product).where(
                        Product.name.ilike(f"%{name}%")
                    ).limit(20)
                ).scalars().all())
            except Exception:
                continue

            for p in candidates:
                p_name = (p.name or "").lower()
                name_lower = name.lower()
                # 计算覆盖率：商品名中有多少字符被查询片段覆盖
                if name_lower in p_name:
                    # 查询片段完全包含在商品名中
                    coverage = len(name) / max(len(p.name or ""), 1)
                    # 覆盖率越高越好（说明用户问的就是这个商品）
                    score = coverage * 10.0 + len(name) * 0.5
                elif p_name in name_lower:
                    # 商品名完全包含在查询片段中（用户粘贴了更长的文本）
                    coverage = len(p.name or "") / max(len(name), 1)
                    score = coverage * 8.0 + len(p.name or "") * 0.3
                else:
                    # 部分匹配，计算字符级重叠
                    overlap = sum(1 for c in name_lower if c in p_name)
                    score = overlap * 0.3

                if score > best_score:
                    best_score = score
                    best_match = p

        # 只有匹配分数足够高时才返回（避免误匹配）
        if best_match and best_score >= 3.0:
            logger.info(
                f"精确商品名匹配成功: question='{question[:50]}', "
                f"matched='{best_match.name[:50]}', score={best_score:.2f}"
            )
            return best_match

        return None

    def _extract_potential_product_names(self, question: str) -> list[str]:
        """从问题中提取潜在的商品名片段

        商品名通常是一串连续的中英文数字组合，可能包含规格信息如 15ml、25g 等。
        我们提取所有长度 >= 4 的连续片段作为候选。
        """
        # 去除常见疑问句式，避免它们被包含在商品名片段中
        text = question
        # 按疑问词分割，取最长的非疑问词片段
        split_patterns = [
            r"多少钱", r"价格是多少", r"价格是", r"怎么样", r"好不好",
            r"评价如何", r"口碑如何", r"推荐", r"品牌是",
            r"功能是", r"效果是", r"是多少", r"贵不贵",
            r"性价比", r"值不值得", r"值不值", r"划算吗",
            r"请问", r"能告诉", r"告诉我", r"我想了解",
            r"？", r"\?", r"吗", r"呢", r"啊", r"吧",
        ]

        fragments = [text]
        for pattern in split_patterns:
            new_fragments = []
            for frag in fragments:
                parts = re.split(pattern, frag)
                new_fragments.extend(parts)
            fragments = new_fragments

        # 过滤、去空、去停用词
        stop_fragments = {"这个", "那个", "这款", "那款", "的", "了", "是", "在", "我"}
        candidates = []
        for frag in fragments:
            frag = frag.strip()
            if len(frag) >= 4 and frag not in stop_fragments:
                candidates.append(frag)

        # 也尝试原始问题中提取连续的商品名词块
        # 商品名通常包含中文字符、英文字母、数字、空格和常见符号
        raw_chunks = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9][\u4e00-\u9fa5a-zA-Z0-9\s\*\-\+\.\(\)（）mlMgLg克升片条个套装入包]*[\u4e00-\u9fa5a-zA-Z0-9)]", question)
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if len(chunk) >= 6 and chunk not in candidates:
                candidates.append(chunk)

        # 按长度降序排序（长名优先匹配，更精确）
        candidates.sort(key=len, reverse=True)
        return candidates

    def _build_data_driven_answer(
        self,
        question: str,
        q_type: str,
        product: Product,
        reviews: list[Review],
        related: list[Product],
        knowledge_context: str = "",
    ) -> str:
        """基于真实商品数据构建回答"""

        if q_type == "price":
            return self._answer_price(product, related, question)
        elif q_type == "recommend":
            return self._answer_recommend(product, related, question, knowledge_context)
        elif q_type == "brand":
            return self._answer_brand(product, question)
        elif q_type == "function":
            return self._answer_function(product, reviews, question, knowledge_context)
        elif q_type == "size":
            return self._answer_size(product, question, knowledge_context)
        elif q_type == "review":
            return self._answer_review(product, reviews, question)
        elif q_type == "after_sale":
            return self._answer_after_sale(product, question, knowledge_context)
        elif q_type == "compare":
            return self._answer_compare(product, related, question)
        else:
            return self._answer_general(
                product, reviews, related, question, knowledge_context
            )

    # ===== 各类型问题的回答构建 =====

    def _answer_price(self, product: Product, related: list[Product], question: str) -> str:
        """价格/性价比问题 - 用真实价格数据回答"""
        price = product.price or 0
        rating = product.rating or 5.0
        review_count = product.review_count or 0

        # 计算同类价格区间
        if related:
            prices = [p.price or 0 for p in related]
            avg_price = sum(prices) / len(prices) if prices else 0
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            price_range = f"同类商品价格区间为 ¥{min_price:.0f} ~ ¥{max_price:.0f}，均价约 ¥{avg_price:.0f}"
        else:
            price_range = ""

        # 性价比判断
        if price > 0 and related:
            avg_price = sum(p.price or 0 for p in related) / len(related)
            if price < avg_price * 0.8 and rating >= 4.5:
                value_assessment = f"这款商品定价 ¥{price:.0f}，低于同类均价 ¥{avg_price:.0f}，评分高达 {rating} 分，性价比非常突出！"
            elif price < avg_price:
                value_assessment = f"定价 ¥{price:.0f} 略低于同类均价 ¥{avg_price:.0f}，配合 {rating} 分的评分，性价比不错。"
            elif price > avg_price * 1.3:
                value_assessment = f"定价 ¥{price:.0f} 略高于同类均价 ¥{avg_price:.0f}，但评分 {rating} 分，如果您追求品质可以考虑。"
            else:
                value_assessment = f"定价 ¥{price:.0f}，处于同类商品正常价格区间，评分 {rating} 分，整体性价比合理。"
        else:
            value_assessment = f"该商品定价 ¥{price:.0f}，评分 {rating} 分，累计 {review_count} 条评价。"

        parts = [value_assessment]
        if price_range:
            parts.append(price_range)

        # 添加同类推荐
        if related:
            cheaper = [p for p in related if (p.price or 0) < price]
            if cheaper:
                best = cheaper[0]
                parts.append(f"如果您预算有限，推荐看看「{best.name}」，仅需 ¥{best.price or 0:.0f}，评分 {best.rating or 5.0} 分。")

        return "\n".join(parts)

    def _answer_recommend(
        self, product: Product, related: list[Product], question: str, knowledge_context: str = ""
    ) -> str:
        """推荐/导购问题 - 用真实商品数据推荐，语气更自然"""
        brand = self._get_real_brand(product)
        price = product.price or 0
        rating = product.rating or 5.0
        review_count = product.review_count or 0

        parts = [f"根据您的需求，我为您挑选了「{product.name}」："]
        parts.append(f"• 价格：¥{price:.0f}")
        parts.append(f"• 评分：{rating} 分（{review_count} 条评价）")
        if brand and brand not in ("苏宁自营", "", "无", "未知", "通用"):
            parts.append(f"• 品牌：{brand}")
        if product.selling_points:
            parts.append(f"• 亮点：{product.selling_points[:100]}")
        parts.append(f"• 分类：{product.category or '综合'}")

        if knowledge_context:
            parts.append(f"\n商品知识：\n{knowledge_context}")

        # 推荐理由
        if rating >= 4.5 and review_count >= 10:
            parts.append(f"\n推荐理由：这款商品评分和口碑都很出色，是同类中的热门选择。")
        elif price > 0 and related:
            avg_price = sum(p.price or 0 for p in related) / len(related) if related else price
            if price <= avg_price * 0.9:
                parts.append(f"\n推荐理由：价格低于同类均价，性价比较高。")
            else:
                parts.append(f"\n推荐理由：综合评分稳定，适合大多数用户选择。")

        if related:
            parts.append(f"\n同分类其他优质选择：")
            for i, p in enumerate(related[:3], 1):
                parts.append(
                    f"  {i}. 「{p.name}」¥{p.price or 0:.0f} | {p.rating or 5.0}分 | {p.review_count or 0}条评价"
                )

        parts.append(f"\n想要更精准推荐的话，可以告诉我您的预算、品牌偏好或主要用途～")
        return "\n".join(parts)

    def _get_real_brand(self, product: Product) -> str:
        """从商品数据中提取真实品牌名"""
        brand = product.brand or ""
        if brand in ("苏宁自营", "", "无", "未知"):
            name = product.name or ""
            # 优先检查商品名开头部分（通常品牌在名称最前面）
            name_start = name[:20]  # 只检查前20个字符
            
            # 先检查"/"分隔的品牌（如"EDIFIER/漫步者"）
            if "/" in name_start:
                parts = name_start.split("/")
                for part in parts:
                    for brand_key in BRAND_KNOWLEDGE:
                        if brand_key.lower() in part.lower():
                            return brand_key
            
            # 再检查整个名称开头
            for brand_key in BRAND_KNOWLEDGE:
                if brand_key.lower() in name_start.lower():
                    return brand_key
        return brand or "通用"

    def _answer_brand(self, product: Product, question: str) -> str:
        """品牌相关问题 - 从品牌知识库检索"""
        brand = self._get_real_brand(product)

        if brand in ("苏宁自营", "", "无", "未知", "通用"):
            return f"这款「{product.name}」暂无明确品牌信息。该商品属于{product.category or '综合'}分类，定价 ¥{product.price or 0:.0f}，评分 {product.rating or 5.0} 分。"

        # 从品牌知识库查找
        brand_info = None
        for brand_key, info in BRAND_KNOWLEDGE.items():
            if brand_key.lower() in brand.lower() or brand.lower() in brand_key.lower():
                brand_info = info
                break

        parts = [f"「{product.name}」的品牌是{brand}。"]

        if brand_info:
            parts.append(f"\n品牌介绍：{brand_info}")
        else:
            parts.append(f"\n该品牌属于{product.category or '综合'}领域，这款产品定价 ¥{product.price or 0:.0f}，评分 {product.rating or 5.0} 分，累计 {product.review_count or 0} 条用户评价。")

        # 添加评价总结
        rating = product.rating or 5.0
        if rating >= 4.7:
            parts.append(f"用户评价方面，{rating} 分的高评分说明消费者对该品牌产品整体非常满意。")
        elif rating >= 4.3:
            parts.append(f"用户评价方面，{rating} 分的评分表明该品牌产品获得了较好的口碑。")
        else:
            parts.append(f"用户评价方面，{rating} 分的评分处于中等水平，建议您结合具体需求判断。")

        return "\n".join(parts)

    def _answer_function(
        self, product: Product, reviews: list[Review], question: str, knowledge_context: str = ""
    ) -> str:
        """功能/使用问题 - 用卖点+评论+知识库回答"""
        parts = [f"关于「{product.name}」的功能："]

        if knowledge_context:
            parts.append(f"\n商品知识参考：\n{knowledge_context}")

        if product.selling_points:
            parts.append(f"\n核心卖点：{product.selling_points}")

        # 从评论中提取功能相关反馈
        if reviews:
            func_reviews = []
            for r in reviews[:10]:
                content = r.content or ""
                if any(kw in content for kw in ["功能", "效果", "好用", "方便", "实用", "体验", "质量", "做工", "材质"]):
                    func_reviews.append(f"  • {content[:80]}")

            if func_reviews:
                parts.append(f"\n用户使用反馈：")
                parts.extend(func_reviews[:3])

        parts.append(f"\n商品评分 {product.rating or 5.0} 分，{product.review_count or 0} 条评价，整体口碑{'优秀' if (product.rating or 0) >= 4.5 else '良好' if (product.rating or 0) >= 4.0 else '一般'}。")

        return "\n".join(parts)

    def _answer_size(
        self, product: Product, question: str, knowledge_context: str = ""
    ) -> str:
        """尺寸/规格问题"""
        parts = [f"关于「{product.name}」的规格信息："]

        if knowledge_context:
            parts.append(f"商品知识参考：\n{knowledge_context}")

        if product.specs:
            parts.append(f"规格参数：{product.specs}")

        # 从商品名提取尺寸信息
        size_match = re.search(r'(\d+\.?\d*)\s*(cm|CM|厘米|mm|毫米|寸|英寸|kg|公斤|斤|L|升|ml|毫升|GB|TB|W|瓦)', product.name or "")
        if size_match:
            parts.append(f"从商品名称可见规格标识：{size_match.group(0)}")

        parts.append(f"\n该商品属于{product.category or '综合'}分类，定价 ¥{product.price or 0:.0f}。如有具体尺寸疑问，可以在商品详情页查看完整的规格参数表。")

        return "\n".join(parts)

    def _answer_review(self, product: Product, reviews: list[Review], question: str) -> str:
        """评价/口碑问题 - 用真实评论回答"""
        parts = [f"「{product.name}」的用户评价总结："]

        rating = product.rating or 5.0
        review_count = product.review_count or 0
        parts.append(f"综合评分：{rating} 分（共 {review_count} 条评价）")

        if rating >= 4.7:
            parts.append("评价等级：优秀，绝大多数用户给出了好评。")
        elif rating >= 4.3:
            parts.append("评价等级：良好，大部分用户满意。")
        elif rating >= 4.0:
            parts.append("评价等级：中等偏上，有一定比例的中差评。")
        else:
            parts.append("评价等级：一般，建议谨慎选择。")

        if reviews:
            # 按评分分类
            positive = [r for r in reviews if r.rating >= 4]
            negative = [r for r in reviews if r.rating <= 2]

            if positive:
                parts.append(f"\n好评精选（共 {len(positive)} 条）：")
                for r in positive[:2]:
                    parts.append(f"  • {r.content[:80]}")

            if negative:
                parts.append(f"\n差评参考（共 {len(negative)} 条）：")
                for r in negative[:1]:
                    parts.append(f"  • {r.content[:80]}")

        return "\n".join(parts)

    def _answer_after_sale(
        self, product: Product, question: str, knowledge_context: str = ""
    ) -> str:
        """售后问题：结合知识库，避免千篇一律"""
        parts = [f"关于「{product.name}」的售后政策："]

        if knowledge_context:
            parts.append(f"\n商品专属说明：\n{knowledge_context}")

        # 根据问题关键词调整回答侧重点
        q_lower = question.lower()
        if any(kw in q_lower for kw in ["退", "换", "无理由"]):
            parts.append(
                "\n退换货服务：\n"
                "• 支持 7 天无理由退换货（需保持商品完好）；\n"
                "• 质量问题 30 天内可申请退换，运费由商家承担；\n"
                "• 非质量问题的退换货，一般需要您承担退回运费。"
            )
        elif any(kw in q_lower for kw in ["保修", "质保", "维修", "坏", "故障"]):
            parts.append(
                "\n保修/质保服务：\n"
                "• 提供一年质保服务（部分商品以详情页说明为准）；\n"
                "• 全国联保，可就近选择授权售后点；\n"
                "• 保留好订单和发票，可加快售后处理。"
            )
        elif any(kw in q_lower for kw in ["运费", "邮费", "快递"]):
            parts.append(
                "\n运费说明：\n"
                "• 因质量问题产生的退换货，退回运费由商家承担；\n"
                "• 7 天无理由退换货，退回运费一般由买家承担；\n"
                "• 具体以商品详情页公示为准。"
            )
        elif any(kw in q_lower for kw in ["发票", "电子发票"]):
            parts.append(
                "\n发票服务：\n"
                "• 下单时可在备注栏填写发票信息；\n"
                "• 支持开具电子普通发票；\n"
                "• 如需增值税专用发票，请联系商家客服。"
            )
        else:
            parts.append(
                "\n平台通用售后保障：\n"
                "• 支持 7 天无理由退换货；\n"
                "• 质量问题 30 天内包退换；\n"
                "• 提供一年质保服务；\n"
                "• 全国联保，支持就近售后。"
            )

        parts.append(
            f"\n该商品定价 ¥{product.price or 0:.0f}，属于{product.category or '综合'}分类。"
            f"如需进一步协助，可以在订单详情页提交售后申请，或随时问我。"
        )
        return "\n".join(parts)

    def _answer_compare(self, product: Product, related: list[Product], question: str) -> str:
        """比较问题 - 用同类商品数据对比"""
        parts = [f"为您对比「{product.name}」与同类商品："]
        parts.append(f"\n当前商品：")
        parts.append(f"  • 名称：{product.name}")
        parts.append(f"  • 价格：¥{product.price or 0:.0f}")
        parts.append(f"  • 评分：{product.rating or 5.0} 分")
        parts.append(f"  • 评价数：{product.review_count or 0} 条")

        if related:
            parts.append(f"\n同类对比：")
            for i, p in enumerate(related[:3], 1):
                price_diff = ""
                if product.price and p.price:
                    diff = p.price - product.price
                    if diff > 0:
                        price_diff = f"（贵 ¥{diff:.0f}）"
                    elif diff < 0:
                        price_diff = f"（便宜 ¥{abs(diff):.0f}）"
                parts.append(
                    f"  {i}. 「{p.name}」¥{p.price or 0:.0f}{price_diff} | {p.rating or 5.0}分 | {p.review_count or 0}条评价"
                )

            # 给出建议
            best_value = min(related[:3], key=lambda p: (p.price or 999999) / max(p.rating or 1, 1))
            parts.append(f"\n综合考虑价格和评分，「{best_value.name}」性价比更高一些。")

        return "\n".join(parts)

    def _answer_general(
        self, product: Product, reviews: list[Review], related: list[Product],
        question: str, knowledge_context: str = ""
    ) -> str:
        """通用问题 - 综合所有数据，回答更自然"""
        brand = self._get_real_brand(product)
        price = product.price or 0
        rating = product.rating or 5.0
        review_count = product.review_count or 0

        parts = [f"为您介绍一下「{product.name}」："]
        parts.append(f"• 分类：{product.category or '综合'}")
        if brand and brand not in ("苏宁自营", "", "无", "未知", "通用"):
            parts.append(f"• 品牌：{brand}")
        parts.append(f"• 价格：¥{price:.0f}")
        parts.append(f"• 评分：{rating} 分（{review_count} 条评价）")

        if product.selling_points:
            parts.append(f"• 亮点：{product.selling_points[:100]}")

        if knowledge_context:
            parts.append(f"\n商品知识参考：\n{knowledge_context}")

        if reviews:
            # 优先展示一条有内容的代表性评论
            best_review = max(reviews[:5], key=lambda r: len(r.content or "")) if reviews else None
            if best_review and best_review.content:
                parts.append(f"\n用户评价摘录：")
                parts.append(f"  「{best_review.content[:100]}」")

        # 根据评分给出购买建议
        if rating >= 4.5 and review_count >= 10:
            parts.append(f"\n综合来看，这款商品评分高、评价多，口碑不错，值得考虑～")
        elif rating >= 4.0:
            parts.append(f"\n这款商品整体评价尚可，您可以根据自己的需求再对比看看。")
        else:
            parts.append(f"\n这款商品评分一般，建议您多看看评价细节后再做决定。")

        parts.append(f"\n还想了解价格、功能、售后或与其他商品对比的话，随时问我！")

        return "\n".join(parts)

    def _build_no_match_answer(self, question: str, q_type: str) -> str:
        """数据库未匹配到商品时的回答：更温暖、更具引导性"""
        q_lower = question.lower()

        # 品牌问题：结合品牌知识库给出介绍，并推荐相关商品
        for brand_key, info in BRAND_KNOWLEDGE.items():
            if brand_key.lower() in q_lower:
                return (
                    f"关于 {brand_key}：{info}\n\n"
                    f"我们平台上也有不少 {brand_key} 的商品，"
                    f"您可以直接告诉我具体想了解的型号或品类（比如「{brand_key} 耳机」），我帮您挑几款合适的～"
                )

        # 通用购物引导
        if any(kw in question for kw in ["怎么买", "如何下单", "怎么下单", "怎么购买", "如何购买"]):
            return (
                "购物其实很简单，跟着我一步步来：\n"
                "1. 在「商品浏览」页找到心仪商品，或直接在搜索框输入关键词；\n"
                "2. 点击商品卡片查看详情、价格和真实评价；\n"
                "3. 选择数量后点击「加入购物车」或「立即购买」；\n"
                "4. 进入购物车确认商品和收货地址，提交订单并完成支付即可。\n\n"
                "如果您不确定买哪款，也可以告诉我预算和用途，我来帮您推荐！"
            )

        # 售后/平台规则
        if any(kw in question for kw in ["运费", "发票", "退换货", "售后", "保修", "质保"]):
            return (
                "关于平台服务，您可以放心：\n"
                "• 大部分商品支持 7 天无理由退换货；\n"
                "• 质量问题可在 30 天内申请退换；\n"
                "• 如需发票，可在下单时备注或联系商家客服；\n"
                "• 具体售后政策以商品详情页说明为准。\n\n"
                "如果您想咨询某款商品的售后细节，请把商品名称发给我，我帮您查询。"
            )

        # 问候语
        if any(kw in q_lower for kw in ["你好", "在吗", "有人吗", "hello", "hi", "嗨", "您好"]):
            return (
                "您好呀！我是您的智能导购助手，专门帮您省心购物～\n"
                "我可以做的事：\n"
                "• 根据您的需求推荐合适的商品\n"
                "• 查询商品价格、评价和卖点\n"
                "• 对比几款相似商品，帮您做选择\n"
                "• 解答品牌、功能、售后等问题\n\n"
                "请直接告诉我您想买什么，比如「推荐一款 200 元以内的蓝牙耳机」，我马上帮您找！"
            )

        # 根据问题类型给出更针对性的引导
        if q_type == "price":
            return (
                "我没找到完全匹配的商品来报价，您可以换个说法试试：\n"
                "• 直接说商品名称，如「华为 FreeBuds 多少钱」\n"
                "• 说预算和需求，如「300 元以内有什么好用的音箱」\n\n"
                "我就能从商品库中调出真实价格帮您对比。"
            )

        if q_type == "recommend":
            return (
                "我很乐意帮您推荐！为了更精准，您可以这样描述：\n"
                "• 用途 + 预算，例如「学生党，想买 500 元以内的平板」\n"
                "• 品牌偏好 + 品类，例如「小米的电饭煲推荐哪款」\n\n"
                "我会结合商品库里的真实数据和评价给您建议。"
            )

        if q_type == "review":
            return (
                "我暂时没检索到对应商品的真实评价，您可以：\n"
                "• 发送准确的商品名称，如「iPhone 15 评价怎么样」\n"
                "• 或者告诉我品类，如「口碑好的猫粮有哪些」\n\n"
                "我会从已有评价中帮您总结优缺点。"
            )

        # 兜底：拉取几个热门分类做引导
        try:
            with SessionLocal() as db:
                top_cats = list(db.execute(
                    select(Product.category, func.count(Product.id).label("cnt"))
                    .where(Product.category.isnot(None))
                    .group_by(Product.category)
                    .order_by(desc("cnt"))
                    .limit(5)
                ).all())
                cat_hints = "、".join([c[0] for c in top_cats if c[0]]) or "数码电子、家居家电、化妆品、宠物用品"
        except Exception:
            cat_hints = "数码电子、家居家电、化妆品、宠物用品"

        return (
            "抱歉，我暂时没从商品库中找到与您的问题直接匹配的商品。\n\n"
            "您可以尝试以下方式：\n"
            "• 发送具体商品名称，例如「兰蔻小黑瓶精华」\n"
            "• 描述需求和预算，例如「推荐一款性价比高的扫地机器人」\n"
            "• 询问品牌信息，例如「索尼耳机怎么样」\n\n"
            f"目前平台覆盖较全的品类有：{cat_hints}。\n"
            "告诉我您想买什么，我马上帮您找！"
        )

    # ===== 辅助方法 =====

    def _detect_question_type(self, question: str) -> str:
        """检测问题类型"""
        q = question.lower()

        # 推荐类
        if any(kw in q for kw in ["推荐", "有什么", "哪些", "哪个好", "求推荐", "适合", "建议买"]):
            return "recommend"

        # 价格类
        if any(kw in q for kw in ["多少钱", "价格", "贵不贵", "便宜", "划算", "性价比", "预算", "值得", "值不值"]):
            return "price"

        # 品牌类
        if any(kw in q for kw in ["品牌", "牌子", "厂家", "生产商", "怎么样", "好不好"]):
            # 检查是否包含品牌名
            for brand in BRAND_KNOWLEDGE:
                if brand.lower() in q:
                    return "brand"
            if any(kw in q for kw in ["品牌", "牌子"]):
                return "brand"

        # 评价类
        if any(kw in q for kw in ["评价", "评论", "口碑", "好评", "差评", "评分", "几分", "怎么样"]):
            return "review"

        # 比较类
        if any(kw in q for kw in ["对比", "比较", "哪个好", "区别", "差异", "vs"]):
            return "compare"

        # 尺寸类
        if any(kw in q for kw in ["多高", "多大", "尺寸", "大小", "重量", "多重", "尺码", "码数", "规格", "容量"]):
            return "size"

        # 功能类
        if any(kw in q for kw in ["功能", "作用", "怎么用", "使用", "操作", "安装", "材质", "材料", "面料", "续航", "电池", "充电", "防水", "效果"]):
            return "function"

        # 售后类
        if any(kw in q for kw in ["退", "换", "售后", "保修", "运费", "发票", "质保"]):
            return "after_sale"

        return "general"

    def _extract_keywords(self, text: str) -> list[str]:
        """提取关键词 - 基于分词片段和已知商品词汇表"""
        stop_words = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "什么", "怎么", "可以", "吗", "呢", "吧", "啊", "请问", "一下", "想", "需要", "这个", "那个", "哪个", "这种", "那种",
                       "推荐", "一款", "知道", "告诉", "关于", "你好",
                       "比较", "相对", "觉得", "认为", "感觉", "希望", "想要", "需要",
                       "适合", "用来", "有没有", "能不能", "好不好", "怎么样"}
        
        # 先用正则提取所有中文/英文/数字片段
        raw_segments = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", text)
        
        keywords = set()
        for seg in raw_segments:
            if len(seg) <= 1:
                continue
            # 英文/数字直接加入
            if re.match(r'^[a-zA-Z0-9]+$', seg):
                if seg.lower() not in stop_words:
                    keywords.add(seg)
                continue
            # 中文：加入完整的分词片段（通常是有意义的词如"蓝牙耳机"、"性价比"）
            if seg not in stop_words:
                keywords.add(seg)
        
        # 额外匹配已知商品关键词表中的词
        all_category_kws = set()
        for kws in CATEGORY_KEYWORDS.values():
            all_category_kws.update(kws)
        for kw in all_category_kws:
            if kw in text and len(kw) >= 2:
                keywords.add(kw)
        
        # 额外匹配品牌名
        for brand in BRAND_KNOWLEDGE:
            if brand.lower() in text.lower():
                keywords.add(brand)
        
        return list(keywords)
    
    def _calculate_similarity(self, question: str, question_keywords: list[str], entry: KnowledgeEntry) -> float:
        """计算问题与知识条目的相似度"""
        score = 0.0
        entry_text = f"{entry.title} {entry.content}"
        for kw in question_keywords:
            if kw in entry_text:
                score += 0.3
            if entry.keywords:
                try:
                    entry_kws = json.loads(entry.keywords)
                    if kw in entry_kws:
                        score += 0.5
                except (json.JSONDecodeError, TypeError):
                    pass
        if question in entry.content:
            score += 0.5
        for kw in question_keywords:
            if kw in entry.title:
                score += 0.2
        return score

    # ===== 知识库管理（保留原有功能） =====

    def add_knowledge(
        self, product_id: int | None, category: str, title: str, content: str, keywords: list[str] | None = None
    ) -> dict:
        with SessionLocal() as db:
            entry = KnowledgeEntry(
                product_id=product_id,
                category=category,
                title=title,
                content=content,
                keywords=json.dumps(keywords or [], ensure_ascii=False),
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry.to_dict()

    def update_knowledge(
        self, entry_id: int, product_id: int | None = None, category: str | None = None,
        title: str | None = None, content: str | None = None, keywords: list[str] | None = None,
    ) -> dict | None:
        with SessionLocal() as db:
            entry = db.get(KnowledgeEntry, entry_id)
            if not entry:
                return None
            if product_id is not None:
                entry.product_id = product_id
            if category is not None:
                entry.category = category
            if title is not None:
                entry.title = title
            if content is not None:
                entry.content = content
            if keywords is not None:
                entry.keywords = json.dumps(keywords, ensure_ascii=False)
            db.commit()
            db.refresh(entry)
            return entry.to_dict()

    def list_knowledge(
        self,
        product_id: int | None = None,
        category: str | None = None,
        keyword: str | None = None,
    ) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
            if product_id:
                stmt = stmt.where(KnowledgeEntry.product_id == product_id)
            if category:
                stmt = stmt.where(KnowledgeEntry.category == category)
            stmt = stmt.order_by(KnowledgeEntry.created_at.desc())
            entries = list(db.execute(stmt).scalars().all())
            result = [e.to_dict() for e in entries]
            if keyword and keyword.strip():
                kw = keyword.strip().lower()
                result = [
                    r for r in result
                    if kw in (r.get("title") or "").lower()
                    or kw in (r.get("content") or "").lower()
                    or any(kw in (k or "").lower() for k in (r.get("keywords") or []))
                ]
            return result

    def list_knowledge_categories(self) -> list[str]:
        """返回知识库中所有不重复的知识类型"""
        with SessionLocal() as db:
            stmt = select(KnowledgeEntry.category).distinct().where(KnowledgeEntry.is_active == True)
            rows = list(db.execute(stmt).scalars().all())
            return [r for r in rows if r]

    def delete_knowledge(self, entry_id: int) -> bool:
        with SessionLocal() as db:
            entry = db.get(KnowledgeEntry, entry_id)
            if entry:
                db.delete(entry)
                db.commit()
                return True
            return False

    def auto_build_from_product(self, product: Product) -> int:
        count = 0
        with SessionLocal() as db:
            if product.specs:
                existing = db.execute(
                    select(KnowledgeEntry).where(
                        KnowledgeEntry.product_id == product.id,
                        KnowledgeEntry.category == "spec",
                    )
                ).scalar_one_or_none()
                if not existing:
                    entry = KnowledgeEntry(
                        product_id=product.id,
                        category="spec",
                        title=f"{product.name} - 规格参数",
                        content=product.specs,
                        keywords=json.dumps(["规格", "参数", "尺寸"], ensure_ascii=False),
                    )
                    db.add(entry)
                    count += 1

            if product.selling_points:
                existing = db.execute(
                    select(KnowledgeEntry).where(
                        KnowledgeEntry.product_id == product.id,
                        KnowledgeEntry.category == "faq",
                    )
                ).scalar_one_or_none()
                if not existing:
                    entry = KnowledgeEntry(
                        product_id=product.id,
                        category="faq",
                        title=f"{product.name} - 核心卖点",
                        content=product.selling_points,
                        keywords=json.dumps(["卖点", "特点", "优势"], ensure_ascii=False),
                    )
                    db.add(entry)
                    count += 1

            existing = db.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.product_id == product.id,
                    KnowledgeEntry.category == "after_sale",
                )
            ).scalar_one_or_none()
            if not existing:
                entry = KnowledgeEntry(
                    product_id=product.id,
                    category="after_sale",
                    title=f"{product.name} - 售后政策",
                    content="支持7天无理由退换货，质量问题30天内包退换，提供一年质保服务。",
                    keywords=json.dumps(["退换", "售后", "保修", "质保"], ensure_ascii=False),
                )
                db.add(entry)
                count += 1

            db.commit()
        return count

    def get_qa_stats(self) -> dict:
        with SessionLocal() as db:
            total = db.execute(select(QARecord)).scalars().all()
            type_counts = Counter(r.question_type for r in total)
            source_counts = Counter(r.source for r in total)
            question_words = []
            for r in total:
                question_words.extend(self._extract_keywords(r.question))
            hot_keywords = Counter(question_words).most_common(15)
            return {
                "total_questions": len(total),
                "total": len(total),
                "type_distribution": dict(type_counts),
                "source_distribution": dict(source_counts),
                "top_keywords": [{"keyword": k, "count": v} for k, v in hot_keywords],
                # 兼容旧字段名
                "by_type": dict(type_counts),
                "by_source": dict(source_counts),
                "hot_keywords": [{"keyword": k, "count": v} for k, v in hot_keywords],
            }

    def get_qa_records(self, limit: int = 50) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(QARecord).order_by(QARecord.created_at.desc()).limit(limit)
            records = list(db.execute(stmt).scalars().all())
            return [r.to_dict() for r in records]
