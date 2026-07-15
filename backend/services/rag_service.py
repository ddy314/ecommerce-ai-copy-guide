"""RAG 检索增强问答服务 - 深度数据驱动的智能问答

当用户提问时，自动从数据库检索匹配商品、评论、同类商品，
结合品牌知识库构建数据驱动的精准回答，而非模板回复。

双阶段混合检索：规则过滤(Stage 1) + 向量重排序(Stage 2)
AI 大模型回答：检索到商品数据后，调用 LLM 生成自然语言回答。
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from typing import Optional, Generator

from sqlalchemy import select, or_, func

from backend.database import SessionLocal
from backend.models.knowledge_base import KnowledgeEntry, QARecord
from backend.models.product import Product
from backend.models.review import Review
from backend.services.vector_index import vector_index

logger = logging.getLogger(__name__)


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
        """深度数据驱动的智能问答

        策略：
        1. 若有 product_id，直接获取该商品完整数据
        2. 若无 product_id，从问题中提取关键词搜索数据库匹配商品
        3. 获取商品完整信息 + 真实评论 + 同类推荐
        4. 根据问题类型构建数据驱动的精准回答
        5. 品牌相关问题自动检索品牌知识库
        """
        q_type = self._detect_question_type(question)

        # 获取商品数据
        product: Optional[Product] = None
        related_products: list[Product] = []
        reviews: list[Review] = []

        with SessionLocal() as db:
            if product_id:
                product = db.get(Product, product_id)
            else:
                # 从问题中搜索匹配商品
                product = self._search_product_by_question(db, question)

            if product:
                # 获取真实评论
                reviews = list(db.execute(
                    select(Review)
                    .where(Review.product_id == product.id)
                    .order_by(Review.created_at.desc())
                    .limit(10)
                ).scalars().all())

                # 获取同类推荐商品 - 使用主商品名称中的核心关键词，避免推荐不同品类的商品
                primary_kws = self._extract_primary_keywords(question)
                price_limit = self._extract_price_constraint(question)
                price_range = self._extract_price_range(question) if not price_limit else None
                spec_constraints = self._extract_spec_constraints(question)

                # 从主商品名称中提取最具体的商品类型关键词
                # 例如：主商品是"奶粉"，则推荐商品名称也必须包含"奶粉"
                product_type_kws = []
                product_name_lower = (product.name or "").lower()
                for kw in primary_kws:
                    if kw.lower() in product_name_lower:
                        product_type_kws.append(kw)

                # 如果没有从主商品名中找到关键词，退化为所有核心关键词
                search_kws_for_related = product_type_kws if product_type_kws else primary_kws

                if search_kws_for_related:
                    # 优先用最具体的关键词（最长的）筛选
                    search_kws_for_related.sort(key=len, reverse=True)
                    # 取前2个最具体的关键词，用AND逻辑（必须同时包含）
                    top_kws = search_kws_for_related[:2]
                    kw_filter = [Product.name.ilike(f"%{kw}%") for kw in top_kws]
                    from sqlalchemy import and_ as sql_and
                    related_products = list(db.execute(
                        select(Product).where(
                            Product.category == product.category,
                            Product.id != product.id,
                            sql_and(*kw_filter),
                        ).order_by(Product.rating.desc()).limit(10)
                    ).scalars().all())
                    # 如果AND过滤后结果太少，降级为OR
                    if len(related_products) < 2 and len(top_kws) > 1:
                        kw_conditions = [Product.name.ilike(f"%{kw}%") for kw in top_kws]
                        related_products = list(db.execute(
                            select(Product).where(
                                Product.category == product.category,
                                Product.id != product.id,
                                or_(*kw_conditions),
                            ).order_by(Product.rating.desc()).limit(10)
                        ).scalars().all())
                else:
                    related_products = list(db.execute(
                        select(Product).where(
                            Product.category == product.category,
                            Product.id != product.id,
                        ).order_by(Product.rating.desc()).limit(10)
                    ).scalars().all())

                # 应用价格约束
                if price_limit:
                    price_filtered = [p for p in related_products if (p.price or 0) <= price_limit]
                    if price_filtered:
                        related_products = price_filtered
                elif price_range:
                    price_filtered = [p for p in related_products if price_range[0] <= (p.price or 0) <= price_range[1]]
                    if price_filtered:
                        related_products = price_filtered

                # 应用规格约束
                related_products = self._apply_spec_filter(related_products, spec_constraints)
                # 截取前5个
                related_products = related_products[:5]

        # 构建回答
        if product:
            answer = self._build_data_driven_answer(
                question, q_type, product, reviews, related_products
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

    def _extract_price_constraint(self, question: str) -> Optional[float]:
        """从问题中提取价格上限约束

        支持：
        - "300元以内" / "300以内" / "300元以下" / "300元一下"（常见错别字）
        - "不超过500" / "500块以下" / "500以内"
        - "预算300" / "预算300元"
        - "200-500元" (取下限200，因为是预算下限)
        - "低于300" / "小于300"
        """
        # 先做错别字纠正常见误写
        normalized = question.replace("一下", "以下")

        # 匹配 "数字+元/块 + 以内/以下/内" 或 "不超过/预算 + 数字"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:元|块钱?|RMB|￥)\s*(?:以内|以下|内|之内)',
            r'(?:不超过|不高于|最多|预算)\s*(\d+(?:\.\d+)?)',
            r'(?:以内|以下|内|之内)\s*(\d+(?:\.\d+)?)\s*(?:元|块钱?)',
            r'(\d+(?:\.\d+)?)\s*[-~到]\s*\d+(?:\.\d+)?\s*(?:元|块钱?)',  # 范围取下限
            r'低于\s*(\d+(?:\.\d+)?)',
            r'小于\s*(\d+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            m = re.search(pattern, normalized)
            if m:
                try:
                    return float(m.group(1))
                except (ValueError, IndexError):
                    pass
        return None

    def _extract_price_range(self, question: str) -> Optional[tuple[float, float]]:
        """从问题中提取价格范围约束（用于"左右"类查询）

        支持：
        - "300元左右" → (240, 360) ±20%
        - "500块左右" → (400, 600)
        - "大约200元" / "大概200元" / "约200元"
        - "200-400元" → (200, 400) 直接范围
        """
        normalized = question.replace("一下", "以下")

        # 1. "数字 + 元/块 + 左右/上下/差不多"
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|块钱?|RMB|￥)\s*(?:左右|上下|差不多|前后)', normalized)
        if m:
            center = float(m.group(1))
            return (center * 0.7, center * 1.3)

        # 2. "左右/大约/大概/约 + 数字 + 元"
        m = re.search(r'(?:左右|大约|大概|约|差不多)\s*(\d+(?:\.\d+)?)\s*(?:元|块钱?)', normalized)
        if m:
            center = float(m.group(1))
            return (center * 0.7, center * 1.3)

        # 3. "数字-数字 + 元" 明确范围
        m = re.search(r'(\d+(?:\.\d+)?)\s*[-~到]\s*(\d+(?:\.\d+)?)\s*(?:元|块钱?)', normalized)
        if m:
            return (float(m.group(1)), float(m.group(2)))

        return None

    def _extract_spec_constraints(self, question: str) -> list[str]:
        """从问题中提取规格/年龄段等约束关键词

        这些关键词必须在商品名称中出现，否则不匹配。
        例如：
        - 奶粉: "0-6个月" → 商品名必须包含"0-6"或"1段"或"新生儿"
        - 服装: "XL码" → 商品名必须包含"XL"
        - 人群: "老人用的" → 商品名包含"老人/老年/长辈"
        """
        constraints = []

        # 婴儿奶粉段数/年龄
        # "0-6个月" / "0~6个月" → 匹配 1段 或 0-6
        age_patterns = [
            (r'0\s*[-~到]\s*(?:6|3)\s*个?月', ['1段', '0-6', '0~6', '0-3', '0~3', '新生儿', '初生']),
            (r'(?:6|3)\s*[-~到]\s*12\s*个?月', ['2段', '6-12', '6~12', '较大']),
            (r'1?\s*[-~到]\s*3?\s*岁', ['3段', '12-36', '12~36', '1-3', '幼儿']),
            (r'1段', ['1段']),
            (r'2段', ['2段']),
            (r'3段', ['3段']),
            (r'新生儿', ['新生儿', '初生', '1段']),
            (r'婴儿', ['婴儿', '1段', '2段']),
        ]
        for pattern, required_kws in age_patterns:
            if re.search(pattern, question):
                constraints.extend(required_kws)
                break  # 只匹配一个年龄段

        # 适龄人群约束
        # "适合老人用" → 商品名包含"老人/老年/长辈"
        # "学生用的" → 商品名包含"学生/校园"
        # "儿童/小孩用" → 商品名包含"儿童/小孩/幼"
        audience_patterns = [
            (r'(?:老人|老年|长辈|爷爷|奶奶)', ['老人', '老年', '长辈', '中老年', '父母']),
            (r'(?:学生|学生党|宿舍|校园)', ['学生', '校园', '宿舍', '学生党']),
            (r'(?:儿童|小孩|孩子|幼儿|宝宝)', ['儿童', '小孩', '孩子', '幼儿', '宝宝', '婴儿']),
            (r'(?:孕妇|孕妈|怀孕)', ['孕妇', '孕妈', '怀孕', '妈咪']),
            (r'(?:男士|男人|男生)', ['男士', '男', '先生']),
            (r'(?:女士|女人|女生)', ['女士', '女', '小姐', '姑娘']),
            (r'(?:运动|健身|跑步)', ['运动', '健身', '跑步']),
            (r'(?:商务|办公|职场)', ['商务', '办公', '职场']),
        ]
        for pattern, required_kws in audience_patterns:
            if re.search(pattern, question):
                constraints.extend(required_kws)
                break  # 人群只匹配一个

        # 服装尺码
        size_patterns = [
            r'[Xx]+[LlSs]', r'\d+码', r'均码',
        ]
        for pattern in size_patterns:
            m = re.search(pattern, question)
            if m:
                constraints.append(m.group(0).upper())

        return constraints

    def _apply_spec_filter(self, products: list[Product], spec_constraints: list[str]) -> list[Product]:
        """过滤商品列表，只保留名称中包含任一规格约束的商品"""
        if not spec_constraints:
            return products
        filtered = []
        for p in products:
            name_lower = (p.name or "").lower()
            # 商品名只需包含任一约束关键词即可
            if any(c.lower() in name_lower for c in spec_constraints):
                filtered.append(p)
        # 如果过滤后为空，返回原始列表（降级策略，避免无结果）
        return filtered if filtered else products

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

    def _vector_rerank(
        self,
        question: str,
        candidates: list[Product],
        keywords: list[str],
        spec_constraints: list[str],
        detected_category: Optional[str] = None,
    ) -> Optional[Product]:
        """第二阶段：向量语义重排序

        对规则过滤后的候选集做向量相似度排序，取最佳匹配。
        如果向量索引不可用或为空，降级为关键词加权排序。

        综合评分 = 向量相似度 × 0.6 + 关键词匹配度 × 0.3 + 评分 × 0.1
        """
        if not candidates:
            return None

        # 尝试向量重排序
        try:
            candidate_ids = [p.id for p in candidates]
            # 构造用于向量搜索的查询文本（拼接关键词增强语义）
            query_text = question
            if keywords:
                query_text = question + " " + " ".join(keywords[:3])

            vector_results = vector_index.search(
                query=query_text,
                candidate_ids=candidate_ids,
                top_k=len(candidates),
            )

            if vector_results:
                # 建立 product_id → similarity 映射
                sim_map = {r["product_id"]: r["similarity"] for r in vector_results}

                # 综合评分：向量相似度(60%) + 关键词匹配(30%) + 评分(10%)
                def combined_score(p: Product) -> float:
                    vec_sim = sim_map.get(p.id, 0.0)
                    kw_score = 0.0
                    name_lower = (p.name or "").lower()
                    for kw in keywords:
                        if kw.lower() in name_lower:
                            kw_score += len(kw) * 2.0
                    for sc in spec_constraints:
                        if sc.lower() in name_lower:
                            kw_score += 10.0
                    if detected_category and p.category == detected_category:
                        kw_score += 5.0
                    rating_score = (p.rating or 0) * 0.1
                    return vec_sim * 0.6 + min(kw_score, 30.0) * 0.3 + rating_score * 0.1

                candidates.sort(key=combined_score, reverse=True)
                logger.info(
                    f"向量重排序完成: {len(candidates)} 个候选, "
                    f"最佳: {candidates[0].name[:30]} (sim={sim_map.get(candidates[0].id, 0):.3f})"
                )
                return candidates[0]

        except Exception as e:
            logger.warning(f"向量重排序失败，降级为关键词排序: {e}")

        # 降级：纯关键词加权排序
        def fallback_score(p: Product) -> float:
            score = 0.0
            name_lower = (p.name or "").lower()
            for kw in keywords:
                if kw.lower() in name_lower:
                    score += len(kw) * 5.0
            for sc in spec_constraints:
                if sc.lower() in name_lower:
                    score += 10.0
            if detected_category and p.category == detected_category:
                score += 5.0
            score += (p.rating or 0) * 0.1
            return score

        candidates.sort(key=fallback_score, reverse=True)
        return candidates[0]

    def _search_product_by_question(self, db, question: str) -> Optional[Product]:
        """从问题关键词搜索数据库中最匹配的商品 - 带分类精准过滤

        检索优先级：
        0. 精确商品名匹配（用户直接粘贴商品名时）
        1. 核心关键词 + 分类匹配
        2. 通用关键词 + 分类匹配
        3. 全局关键词匹配

        所有层级均会应用价格上限、价格范围和规格约束过滤。
        """
        # ===== 提取约束条件 =====
        price_limit = self._extract_price_constraint(question)
        price_range = self._extract_price_range(question) if not price_limit else None
        spec_constraints = self._extract_spec_constraints(question)

        # ===== 0. 精确商品名匹配（最高优先级）=====
        # 当用户直接粘贴商品名或问题中包含较长的商品名片段时，
        # 优先在数据库中查找名称最接近的商品
        exact_match = self._try_exact_product_match(db, question)
        if exact_match:
            # 即使精确匹配也要检查价格约束
            ep = exact_match.price or 0
            if price_limit and ep > price_limit:
                pass  # 价格超出上限，继续搜索
            elif price_range and not (price_range[0] <= ep <= price_range[1]):
                pass  # 价格不在范围内，继续搜索
            else:
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

            # 应用价格约束过滤
            if price_limit:
                price_filtered = [p for p in results if (p.price or 0) <= price_limit]
                if price_filtered:
                    results = price_filtered
            elif price_range:
                price_filtered = [p for p in results if price_range[0] <= (p.price or 0) <= price_range[1]]
                if price_filtered:
                    results = price_filtered

            # 应用规格约束过滤（年龄段、尺码等）
            results = self._apply_spec_filter(results, spec_constraints)

            if results:
                # ===== 第二阶段：向量语义重排序 =====
                # 用向量相似度对候选集做语义排序，替代纯关键词匹配度排序
                best = self._vector_rerank(question, results, primary_kws, spec_constraints)
                if best:
                    return best

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
            # 应用价格约束
            if price_limit:
                price_filtered = [p for p in results if (p.price or 0) <= price_limit]
                if price_filtered:
                    results = price_filtered
            elif price_range:
                price_filtered = [p for p in results if price_range[0] <= (p.price or 0) <= price_range[1]]
                if price_filtered:
                    results = price_filtered
            # 应用规格约束
            results = self._apply_spec_filter(results, spec_constraints)
            if results:
                # ===== 第二阶段：向量语义重排序 =====
                best = self._vector_rerank(question, results, search_kws, spec_constraints)
                if best:
                    return best

        # 5. 全局搜索
        all_results = list(db.execute(
            select(Product).where(or_(*conditions)).limit(50)
        ).scalars().all())
        # 应用价格约束
        if price_limit:
            price_filtered = [p for p in all_results if (p.price or 0) <= price_limit]
            if price_filtered:
                all_results = price_filtered
        elif price_range:
            price_filtered = [p for p in all_results if price_range[0] <= (p.price or 0) <= price_range[1]]
            if price_filtered:
                all_results = price_filtered
        # 应用规格约束
        all_results = self._apply_spec_filter(all_results, spec_constraints)
        if not all_results:
            return None

        # ===== 第二阶段：向量语义重排序 =====
        best = self._vector_rerank(question, all_results, search_kws, spec_constraints, detected_category)
        return best

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

    def _generate_ai_answer(
        self,
        question: str,
        q_type: str,
        product: Product,
        reviews: list[Review],
        related: list[Product],
    ) -> str:
        """调用 AI 大模型生成自然语言回答

        将检索到的商品数据、评论、推荐商品作为上下文，
        调用 LLM 生成口语化、有温度的导购回答。
        如果 LLM 不可用，降级为模板回答。
        """
        # 构建上下文数据
        context_parts = [f"用户问题：{question}"]
        context_parts.append(f"问题类型：{q_type}")

        # 主商品信息
        context_parts.append(f"\n【主推商品】")
        context_parts.append(f"名称：{product.name}")
        context_parts.append(f"价格：¥{product.price or 0:.0f}")
        context_parts.append(f"评分：{product.rating or 5.0}分（{product.review_count or 0}条评价）")
        context_parts.append(f"品牌：{self._get_real_brand(product)}")
        context_parts.append(f"分类：{product.category or '综合'}")
        if product.selling_points:
            context_parts.append(f"卖点：{product.selling_points[:200]}")
        if product.specs:
            context_parts.append(f"规格：{product.specs[:200]}")

        # 用户评论摘要
        if reviews:
            context_parts.append(f"\n【用户评价摘录】")
            for r in reviews[:3]:
                rating_text = f"{r.rating}星" if r.rating else ""
                context_parts.append(f"- {rating_text}：{r.content[:80] if r.content else '无评论内容'}")

        # 推荐商品
        if related:
            context_parts.append(f"\n【同类推荐商品】")
            for p in related[:5]:
                context_parts.append(f"- {p.name} | ¥{p.price or 0:.0f} | {p.rating or 5.0}分")

        context = "\n".join(context_parts)

        # 系统提示
        system_prompt = """你是一位专业的电商导购助手，擅长根据用户需求推荐合适的商品。
请基于提供的商品数据，用自然、亲切的语气回答用户问题。

要求：
1. 回答要口语化、有温度，像朋友聊天一样
2. 直接给出推荐商品的核心信息（名称、价格、评分）
3. 突出商品的卖点和优势
4. 如果有同类推荐，简要提及2-3个备选
5. 回答控制在200字以内，简洁有力
6. 不要编造数据，只使用提供的商品信息"""

        user_prompt = f"{context}\n\n请根据以上商品数据回答用户的问题。"

        try:
            from openai import OpenAI
            api_key = os.getenv("AI_API_KEY", "")
            base_url = os.getenv("AI_BASE_URL", "")
            model = os.getenv("AI_MODEL", "gpt-4o-mini")

            if not api_key:
                # 没有配置 API Key，降级为模板回答
                return self._build_data_driven_answer(question, q_type, product, reviews, related)

            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = OpenAI(**kwargs)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )
            ai_answer = response.choices[0].message.content or ""

            # 追加推荐商品卡片（供前端渲染）
            if related:
                ai_answer += self._format_related_table(related)

            return ai_answer.strip()

        except Exception as e:
            logger.warning(f"AI 大模型调用失败，降级为模板回答: {e}")
            return self._build_data_driven_answer(question, q_type, product, reviews, related)

    def _generate_ai_answer_stream(
        self,
        question: str,
        q_type: str,
        product: Product,
        reviews: list[Review],
        related: list[Product],
    ) -> Generator[str, None, None]:
        """调用 AI 大模型流式生成回答（逐 token yield）

        如果 LLM 不可用，降级为模板回答的非流式输出。
        """
        # 构建上下文数据
        context_parts = [f"用户问题：{question}"]
        context_parts.append(f"问题类型：{q_type}")

        context_parts.append(f"\n【主推商品】")
        context_parts.append(f"名称：{product.name}")
        context_parts.append(f"价格：¥{product.price or 0:.0f}")
        context_parts.append(f"评分：{product.rating or 5.0}分（{product.review_count or 0}条评价）")
        context_parts.append(f"品牌：{self._get_real_brand(product)}")
        context_parts.append(f"分类：{product.category or '综合'}")
        if product.selling_points:
            context_parts.append(f"卖点：{product.selling_points[:200]}")
        if product.specs:
            context_parts.append(f"规格：{product.specs[:200]}")

        if reviews:
            context_parts.append(f"\n【用户评价摘录】")
            for r in reviews[:3]:
                rating_text = f"{r.rating}星" if r.rating else ""
                context_parts.append(f"- {rating_text}：{r.content[:80] if r.content else '无评论内容'}")

        if related:
            context_parts.append(f"\n【同类推荐商品】")
            for p in related[:5]:
                context_parts.append(f"- {p.name} | ¥{p.price or 0:.0f} | {p.rating or 5.0}分")

        context = "\n".join(context_parts)

        system_prompt = """你是一位专业的电商导购助手，擅长根据用户需求推荐合适的商品。
请基于提供的商品数据，用自然、亲切的语气回答用户问题。

要求：
1. 回答要口语化、有温度，像朋友聊天一样
2. 直接给出推荐商品的核心信息（名称、价格、评分）
3. 突出商品的卖点和优势
4. 如果有同类推荐，简要提及2-3个备选
5. 回答控制在200字以内，简洁有力
6. 不要编造数据，只使用提供的商品信息"""

        user_prompt = f"{context}\n\n请根据以上商品数据回答用户的问题。"

        try:
            from openai import OpenAI
            api_key = os.getenv("AI_API_KEY", "")
            base_url = os.getenv("AI_BASE_URL", "")
            model = os.getenv("AI_MODEL", "gpt-4o-mini")

            if not api_key:
                # 没有配置 API Key，降级为模板回答
                answer = self._build_data_driven_answer(question, q_type, product, reviews, related)
                for chunk in answer:
                    yield chunk
                return

            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = OpenAI(**kwargs)

            # 使用 stream=True 流式调用
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            # 流式结束后追加推荐商品卡片
            if related:
                yield self._format_related_table(related)

        except Exception as e:
            logger.warning(f"AI 大模型流式调用失败，降级为模板回答: {e}")
            answer = self._build_data_driven_answer(question, q_type, product, reviews, related)
            for chunk in answer:
                yield chunk

    def answer_question_stream(
        self,
        question: str,
        product_id: int | None = None,
        user_id: int | None = None,
    ) -> Generator[dict, None, None]:
        """流式问答 - 先推送商品数据，再流式推送 AI 回答

        Yields:
            dict: {"type": "product"/"related"/"text"/"done"/"error", ...}
        """
        q_type = self._detect_question_type(question)

        product: Optional[Product] = None
        related_products: list[Product] = []
        reviews: list[Review] = []

        with SessionLocal() as db:
            if product_id:
                product = db.get(Product, product_id)
            else:
                product = self._search_product_by_question(db, question)

            if product:
                reviews = list(db.execute(
                    select(Review)
                    .where(Review.product_id == product.id)
                    .order_by(Review.created_at.desc())
                    .limit(10)
                ).scalars().all())

                # 获取同类推荐
                primary_kws = self._extract_primary_keywords(question)
                price_limit = self._extract_price_constraint(question)
                price_range = self._extract_price_range(question) if not price_limit else None
                spec_constraints = self._extract_spec_constraints(question)

                product_type_kws = []
                product_name_lower = (product.name or "").lower()
                for kw in primary_kws:
                    if kw.lower() in product_name_lower:
                        product_type_kws.append(kw)

                search_kws_for_related = product_type_kws if product_type_kws else primary_kws

                if search_kws_for_related:
                    search_kws_for_related.sort(key=len, reverse=True)
                    top_kws = search_kws_for_related[:2]
                    kw_filter = [Product.name.ilike(f"%{kw}%") for kw in top_kws]
                    from sqlalchemy import and_ as sql_and
                    related_products = list(db.execute(
                        select(Product).where(
                            Product.category == product.category,
                            Product.id != product.id,
                            sql_and(*kw_filter),
                        ).order_by(Product.rating.desc()).limit(10)
                    ).scalars().all())
                    if len(related_products) < 2 and len(top_kws) > 1:
                        kw_conditions = [Product.name.ilike(f"%{kw}%") for kw in top_kws]
                        related_products = list(db.execute(
                            select(Product).where(
                                Product.category == product.category,
                                Product.id != product.id,
                                or_(*kw_conditions),
                            ).order_by(Product.rating.desc()).limit(10)
                        ).scalars().all())
                else:
                    related_products = list(db.execute(
                        select(Product).where(
                            Product.category == product.category,
                            Product.id != product.id,
                        ).order_by(Product.rating.desc()).limit(10)
                    ).scalars().all())

                if price_limit:
                    price_filtered = [p for p in related_products if (p.price or 0) <= price_limit]
                    if price_filtered:
                        related_products = price_filtered
                elif price_range:
                    price_filtered = [p for p in related_products if price_range[0] <= (p.price or 0) <= price_range[1]]
                    if price_filtered:
                        related_products = price_filtered

                related_products = self._apply_spec_filter(related_products, spec_constraints)
                related_products = related_products[:5]

        # 推送主商品数据
        if product:
            yield {
                "type": "product",
                "data": {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price or 0,
                    "rating": product.rating or 5.0,
                    "category": product.category or "",
                    "image_url": product.image_url or "",
                    "brand": self._get_real_brand(product),
                },
            }

        # 推送推荐商品数据
        if related_products:
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
            yield {"type": "related", "data": related_info}

        # 流式推送 AI 回答
        full_answer = ""
        if product:
            for text_chunk in self._generate_ai_answer_stream(
                question, q_type, product, reviews, related_products
            ):
                full_answer += text_chunk
                yield {"type": "text", "content": text_chunk}
        else:
            full_answer = self._build_no_match_answer(question, q_type)
            yield {"type": "text", "content": full_answer}

        # 记录问答
        try:
            with SessionLocal() as db:
                record = QARecord(
                    user_id=user_id,
                    product_id=product.id if product else product_id,
                    question=question,
                    answer=full_answer,
                    question_type=q_type,
                    source="ai_rag",
                )
                db.add(record)
                db.commit()
        except Exception as e:
            logger.warning(f"问答记录保存失败: {e}")

        yield {"type": "done"}

    def _build_data_driven_answer(
        self,
        question: str,
        q_type: str,
        product: Product,
        reviews: list[Review],
        related: list[Product],
    ) -> str:
        """基于真实商品数据构建回答"""

        if q_type == "price":
            return self._answer_price(product, related, question)
        elif q_type == "recommend":
            return self._answer_recommend(product, related, question)
        elif q_type == "brand":
            return self._answer_brand(product, question)
        elif q_type == "function":
            return self._answer_function(product, reviews, question)
        elif q_type == "size":
            return self._answer_size(product, question)
        elif q_type == "review":
            return self._answer_review(product, reviews, question)
        elif q_type == "after_sale":
            return self._answer_after_sale(product, question)
        elif q_type == "compare":
            return self._answer_compare(product, related, question)
        else:
            return self._answer_general(product, reviews, related, question)

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

    def _format_related_table(self, related: list[Product]) -> str:
        """将推荐商品格式化为卡片列表（前端解析为卡片展示）"""
        if not related:
            return ""
        lines = ["\n[PRODUCT_CARDS]"]
        for p in related[:5]:
            name = p.name or ""
            price = f"¥{p.price or 0:.0f}"
            rating = f"{p.rating or 5.0}"
            reviews = f"{p.review_count or 0}"
            # 用 ||| 分隔字段
            lines.append(f"{name}|||{price}|||{rating}|||{reviews}")
        lines.append("[/PRODUCT_CARDS]")
        return "\n".join(lines)

    def _answer_recommend(self, product: Product, related: list[Product], question: str) -> str:
        """推荐/导购问题 - 用真实商品数据推荐"""
        parts = [f"根据您的需求，为您推荐「{product.name}」："]
        parts.append(f"• 价格：¥{product.price or 0:.0f}")
        parts.append(f"• 评分：{product.rating or 5.0} 分（{product.review_count or 0} 条评价）")
        if product.brand:
            parts.append(f"• 品牌：{self._get_real_brand(product)}")
        if product.selling_points:
            parts.append(f"• 亮点：{product.selling_points[:100]}")
        parts.append(f"• 分类：{product.category or '综合'}")

        if related:
            parts.append(f"\n**同分类其他优质选择：**")
            parts.append(self._format_related_table(related))

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

    def _answer_function(self, product: Product, reviews: list[Review], question: str) -> str:
        """功能/使用问题 - 用卖点+评论回答"""
        parts = [f"关于「{product.name}」的功能："]

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

    def _answer_size(self, product: Product, question: str) -> str:
        """尺寸/规格问题"""
        parts = [f"关于「{product.name}」的规格信息："]

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

    def _answer_after_sale(self, product: Product, question: str) -> str:
        """售后问题"""
        return (
            f"「{product.name}」售后政策：\n"
            f"• 支持 7 天无理由退换货\n"
            f"• 质量问题 30 天内包退换\n"
            f"• 提供一年质保服务\n"
            f"• 全国联保，支持就近售后\n\n"
            f"该商品定价 ¥{product.price or 0:.0f}，属于{product.category or '综合'}分类。"
            f"如有售后问题，请联系客服或提交售后申请。"
        )

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

    def _answer_general(self, product: Product, reviews: list[Review], related: list[Product], question: str) -> str:
        """通用问题 - 综合所有数据回答"""
        parts = [f"关于「{product.name}」："]
        parts.append(f"• 分类：{product.category or '综合'}")
        parts.append(f"• 品牌：{self._get_real_brand(product)}")
        parts.append(f"• 价格：¥{product.price or 0:.0f}")
        parts.append(f"• 评分：{product.rating or 5.0} 分（{product.review_count or 0} 条评价）")

        if product.selling_points:
            parts.append(f"• 亮点：{product.selling_points[:100]}")

        if reviews:
            # 展示1条代表性评论
            best_review = max(reviews[:5], key=lambda r: len(r.content or "")) if reviews else None
            if best_review and best_review.content:
                parts.append(f"\n用户评价摘录：")
                parts.append(f"  「{best_review.content[:100]}」")

        parts.append(f"\n如果您想了解更多细节，可以直接问我价格、功能、评价等方面的问题！")

        return "\n".join(parts)

    def _build_no_match_answer(self, question: str, q_type: str) -> str:
        """数据库未匹配到商品时的回答"""
        # 检查是否是品牌问题
        for brand_key, info in BRAND_KNOWLEDGE.items():
            if brand_key in question:
                return f"关于{brand_key}：\n{info}\n\n如果您想了解具体商品，可以告诉我商品名称或分类，我帮您查找！"

        # 检查是否是通用购物问题
        if any(kw in question for kw in ["怎么买", "如何下单", "怎么下单", "怎么购买"]):
            return "您可以：\n1. 在「商品浏览」页面浏览所有商品\n2. 点击商品卡片查看详情\n3. 选择数量后点击「加入购物车」或「立即购买」\n4. 在购物车页面确认后提交订单\n\n有什么其他问题可以随时问我！"

        if any(kw in question for kw in ["你好", "在吗", "有人吗", "hello", "hi"]):
            return "您好！我是智能导购助手，可以为您：\n• 推荐合适的商品\n• 查询商品价格和评价\n• 对比同类商品\n• 解答品牌相关问题\n\n请问有什么可以帮您？"

        return (
            f"很抱歉，我暂时没有在商品库中找到与您问题直接相关的商品。\n"
            f"您可以尝试：\n"
            f"• 告诉我具体的商品名称（如「蓝牙耳机」）\n"
            f"• 说出您的需求（如「推荐一款200元以内的保温杯」）\n"
            f"• 询问某个品牌的信息（如「华为这个品牌怎么样」）\n\n"
            f"我会从商品数据库中为您找到最匹配的商品并给出详细解答！"
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

    def list_knowledge(self, product_id: int | None = None, category: str | None = None) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
            if product_id:
                stmt = stmt.where(KnowledgeEntry.product_id == product_id)
            if category:
                stmt = stmt.where(KnowledgeEntry.category == category)
            stmt = stmt.order_by(KnowledgeEntry.created_at.desc())
            entries = list(db.execute(stmt).scalars().all())
            return [e.to_dict() for e in entries]

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
