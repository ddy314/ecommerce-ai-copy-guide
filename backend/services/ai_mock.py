"""Mock AI 服务 - 基于规则和模板的确定性 AI 逻辑

无需外部 API 即可完整演示全部四大模块功能。
当配置了 AI_PROVIDER=openai 时，OpenAIProvider 将覆盖这些方法。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from backend.schemas.requests import (
    CopyGenerationRequest,
    CrossRecommendRequest,
    GuideQARequest,
    GuideRecommendationRequest,
    LiveScriptRequest,
    ReviewAnalysisRequest,
)


# ===== 情感词典 =====

POSITIVE_WORDS = {
    "好", "好用", "舒服", "舒适", "推荐", "喜欢", "稳定", "清爽", "划算", "精致",
    "快", "不错", "满意", "回购", "质量好", "性价比", "颜值", "包装", "物流快",
    "客服", "态度好", "正品", "物超所值", "结实", "轻薄", "流畅", "清晰", "护眼",
    "透气", "柔软", "顺滑", "高级感", "质感", "做工", "细节", "贴心", "实用",
}

NEGATIVE_WORDS = {
    "差", "差评", "慢", "贵", "坏", "退", "退货", "失望", "异味", "粗糙",
    "卡", "卡顿", "垃圾", "假货", "破损", "裂", "掉色", "缩水", "不合适",
    "不舒服", "硬", "扎", "噪音", "漏", "断", "松", "歪", "便宜", "劣质",
    "图片不符", "描述不符", "客服态度差", "不退款", "瑕疵", "起球", "褪色",
}

COMPLAINT_PATTERNS = {
    "物流": ["物流慢", "发货慢", "快递", "配送", "到货"],
    "包装": ["包装", "破损", "盒子", "塑封"],
    "质量": ["质量", "做工", "材质", "粗糙", "瑕疵", "掉色", "起球"],
    "尺寸": ["尺码", "大小", "偏小", "偏大", "不合适", "尺寸"],
    "售后": ["客服", "退款", "退货", "售后", "态度"],
    "使用体验": ["不舒服", "硬", "扎", "噪音", "卡顿", "漏水", "断"],
    "价格": ["贵", "不值", "降价", "价保"],
}

STYLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "简洁": {
        "title_prefix": "", "title_suffix": "", "separator": " | ",
        "slogan_pattern": "{product}，{point}。",
        "detail_style": "直接", "tone_words": ["精选", "核心", "实用"],
    },
    "高端": {
        "title_prefix": "", "title_suffix": " · 臻享版", "separator": " — ",
        "slogan_pattern": "致敬不凡，{product}以{point}重新定义品质生活。",
        "detail_style": "尊享", "tone_words": ["奢享", "臻选", "传世", "非凡"],
    },
    "活泼": {
        "title_prefix": "哇塞！", "title_suffix": "～", "separator": " ＋ ",
        "slogan_pattern": "有了{product}，{point}超开心！快冲鸭～",
        "detail_style": "场景化", "tone_words": ["超", "满满", "元气", "宝藏"],
    },
    "专业": {
        "title_prefix": "", "title_suffix": "（专业版）", "separator": " · ",
        "slogan_pattern": "经专业验证，{product}的{point}为{audience}提供可靠保障。",
        "detail_style": "数据化", "tone_words": ["经认证", "权威", "精准", "系统"],
    },
    "促销": {
        "title_prefix": "限时特惠！", "title_suffix": " 抢！", "separator": " | ",
        "slogan_pattern": "今日下单立享优惠，{product}让{point}触手可及！",
        "detail_style": "促销", "tone_words": ["限时", "特惠", "立减", "赠送"],
    },
}

QA_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "size": [
        {
            "keywords": ["多高", "身高", "高度", "适合多高"],
            "answer": "根据商品规格，建议身高 {spec} 的用户使用。如果您的身高在范围内，体验效果最佳。",
            "tips": ["身高处于范围中间值时舒适度最高", "建议参考商品详情页的尺寸表"],
        },
        {
            "keywords": ["多大", "尺寸", "大小", "规格"],
            "answer": "该商品的标准尺寸为 {spec}。建议购买前用卷尺测量使用空间，确保摆放合适。",
            "tips": ["注意区分产品尺寸和包装尺寸", "安装类产品需预留 5-10cm 操作空间"],
        },
        {
            "keywords": ["重", "重量", "多重"],
            "answer": "产品净重约 {spec}，属于同类产品中的常规重量，搬运和日常使用都很方便。",
            "tips": ["重量数据以实物为准，可能有微小偏差"],
        },
        {
            "keywords": ["尺码", "码数", "穿", "鞋码"],
            "answer": "建议参考尺码表选择。该商品偏{spec}，如果您介于两个尺码之间，建议选大一号。",
            "tips": ["不同批次可能存在 0.5 码偏差", "试穿后不满意支持 7 天无理由退换"],
        },
    ],
    "function": [
        {
            "keywords": ["功能", "作用", "能做什么", "用途"],
            "answer": "该商品的核心功能包括：{spec}。适用于{category}场景，能满足日常使用需求。",
            "tips": ["建议先了解核心功能再下单", "功能详情可查看商品详情页"],
        },
        {
            "keywords": ["怎么用", "使用", "操作", "安装"],
            "answer": "使用方法：{spec}。首次使用建议阅读说明书，如有疑问可联系客服获取视频指导。",
            "tips": ["安装类产品建议两人配合操作", "使用前请检查配件是否齐全"],
        },
        {
            "keywords": ["材质", "材料", "面料", "成分"],
            "answer": "该商品采用{spec}材质，{category}级别的品质标准，安全环保、经久耐用。",
            "tips": ["材质信息以吊牌标注为准", "敏感肌肤建议先局部试用"],
        },
        {
            "keywords": ["续航", "电池", "充电", "电量"],
            "answer": "电池续航约 {spec}，充电时间约 2-3 小时。建议首次使用前充满电以激活电池最佳性能。",
            "tips": ["长期不用建议每月充电一次", "避免在高温环境下充电"],
        },
        {
            "keywords": ["防水", "防摔", "防护"],
            "answer": "该产品支持{spec}级别的防护，可满足日常使用场景。请注意防护等级有上限，不建议超出标称范围使用。",
            "tips": ["防水不防蒸汽，洗澡时请取下", "防摔高度有限，仍建议小心使用"],
        },
    ],
    "matching": [
        {
            "keywords": ["搭配", "配什么", "穿搭", "组合"],
            "answer": "推荐搭配方案：{spec}。该商品属于{category}风格，可与简约系单品搭配出层次感。",
            "tips": ["同色系搭配更显高级", "配饰宜精不宜多"],
        },
        {
            "keywords": ["送", "礼物", "送礼", "适合送"],
            "answer": "这款商品非常适合作为{audience}的礼物。包装精美，寓意实用，收到的人会觉得贴心。",
            "tips": ["可选择礼盒装增加仪式感", "附上手写卡片更添温度"],
        },
        {
            "keywords": ["场景", "场合", "什么时候", "适合什么"],
            "answer": "该商品适合{spec}场景使用。无论是日常通勤还是特殊场合，都能发挥很好的作用。",
            "tips": ["正式场合建议选择经典配色", "休闲场合可尝试大胆搭配"],
        },
    ],
}

CROSS_RECOMMEND_MAP: dict[str, list[dict[str, Any]]] = {
    "办公椅": [
        {"product_name": "升降办公桌", "reason": "搭配升降桌实现站坐交替办公，保护腰椎", "match_score": 92},
        {"product_name": "护腰靠垫", "reason": "双倍护腰支撑，久坐不累", "match_score": 88},
        {"product_name": "显示器支架", "reason": "调整屏幕高度，配合人体工学椅纠正坐姿", "match_score": 85},
        {"product_name": "桌面收纳盒", "reason": "保持桌面整洁，提升办公效率", "match_score": 72},
    ],
    "手机": [
        {"product_name": "手机壳", "reason": "新机必备防护，防摔防刮", "match_score": 95},
        {"product_name": "无线充电器", "reason": "随放随充，告别线缆困扰", "match_score": 88},
        {"product_name": "蓝牙耳机", "reason": "搭配使用体验完整，通话听歌两不误", "match_score": 90},
        {"product_name": "手机支架", "reason": "解放双手，追剧视频更方便", "match_score": 78},
    ],
    "耳机": [
        {"product_name": "耳机收纳盒", "reason": "保护耳机免受磕碰，延长使用寿命", "match_score": 89},
        {"product_name": "手机", "reason": "好耳机配好音源，提升整体听感", "match_score": 85},
        {"product_name": "蓝牙音频接收器", "reason": "让有线设备秒变蓝牙，拓展使用场景", "match_score": 76},
    ],
    "键盘": [
        {"product_name": "鼠标", "reason": "键鼠套装搭配使用，办公游戏体验更完整", "match_score": 93},
        {"product_name": "鼠标垫", "reason": "提升鼠标精度，保护桌面", "match_score": 82},
        {"product_name": "手托", "reason": "缓解手腕疲劳，长时间打字更舒适", "match_score": 80},
    ],
}

KEYWORD_CATEGORIES = {
    "品质": ["质量", "做工", "材质", "质感", "精致", "粗糙"],
    "体验": ["舒服", "舒适", "好用", "方便", "不舒服", "难用"],
    "物流": ["物流", "快递", "发货", "到货", "配送"],
    "外观": ["颜值", "好看", "漂亮", "设计", "颜色"],
    "价格": ["性价比", "划算", "贵", "便宜", "值"],
    "功能": ["功能", "效果", "实用", "性能"],
}


class MockAIService:
    """确定性 AI 服务 - 基于规则、模板和词典的完整功能实现"""

    def capabilities(self) -> dict[str, object]:
        return {
            "mode": "mock",
            "features": [
                {"key": "copy_generation", "name": "商品文案生成", "endpoint": "/api/copy/generate"},
                {"key": "shopping_guide", "name": "智能导购推荐", "endpoint": "/api/guide/recommend"},
                {"key": "guide_qa", "name": "智能导购问答", "endpoint": "/api/guide/qa"},
                {"key": "cross_recommend", "name": "跨商品关联推荐", "endpoint": "/api/guide/cross-recommend"},
                {"key": "review_analysis", "name": "评论情感分析", "endpoint": "/api/reviews/analyze"},
                {"key": "live_script", "name": "直播脚本生成", "endpoint": "/api/scripts/live"},
            ],
        }

    # ===== 模块一：商品文案智能生成 =====

    def generate_copy(self, payload: CopyGenerationRequest) -> dict[str, object]:
        style = payload.style if payload.style in STYLE_TEMPLATES else "简洁"
        template = STYLE_TEMPLATES[style]
        points = payload.selling_points or self._infer_selling_points(payload.product_name, payload.category)
        audience = payload.audience or "用户"

        core_point = points[0] if points else payload.product_name
        title = self._build_title(payload.product_name, core_point, audience, template)
        selling_points = self._build_selling_points(points, template, audience)
        detail_copy = self._build_detail_copy(payload.product_name, points, audience, template)
        ad_slogan = template["slogan_pattern"].format(
            product=payload.product_name, point=core_point, audience=audience,
        )

        return {
            "product_name": payload.product_name,
            "style": style,
            "title": title,
            "selling_points": selling_points,
            "detail_copy": detail_copy,
            "ad_slogan": ad_slogan,
        }

    def _build_title(self, product: str, core_point: str, audience: str, template: dict) -> str:
        prefix = template["title_prefix"]
        suffix = template["title_suffix"]
        sep = template["separator"]
        tone_word = template["tone_words"][0]
        if template["detail_style"] == "直接":
            return f"{prefix}{product}{sep}{core_point}{suffix}"
        elif template["detail_style"] == "尊享":
            return f"{prefix}{product}{sep}{tone_word}{core_point}{suffix}"
        elif template["detail_style"] == "场景化":
            return f"{prefix}{product}{sep}{audience}的{tone_word}选择{suffix}"
        elif template["detail_style"] == "促销":
            return f"{prefix}{product}{sep}{tone_word}{core_point}{suffix}"
        else:
            return f"{prefix}{product}{sep}{tone_word}{core_point}方案{suffix}"

    def _build_selling_points(self, points: list[str], template: dict, audience: str) -> list[str]:
        tone_words = template["tone_words"]
        result = []
        for i, point in enumerate(points[:5]):
            tone = tone_words[i % len(tone_words)]
            if template["detail_style"] == "直接":
                result.append(f"{point}：直接解决核心需求")
            elif template["detail_style"] == "尊享":
                result.append(f"{tone}{point}：以匠心工艺呈现非凡品质体验")
            elif template["detail_style"] == "场景化":
                result.append(f"{tone}{point}：让{audience}的每一天都更轻松")
            elif template["detail_style"] == "促销":
                result.append(f"{tone}{point}：今日下单立享专属优惠")
            else:
                result.append(f"{tone}{point}：经专业验证，为{audience}提供可靠保障")
        return result

    def _build_detail_copy(self, product: str, points: list[str], audience: str, template: dict) -> str:
        tone_word = template["tone_words"][0]
        points_text = "、".join(points[:3]) if points else "品质保障"
        if template["detail_style"] == "直接":
            return (
                f"{product}，一款聚焦{audience}真实需求的产品。"
                f"核心优势：{points_text}。没有多余的设计，每一处细节都为解决实际问题而存在。"
                f"选择它，就是选择一种高效务实的生活方式。"
            )
        elif template["detail_style"] == "尊享":
            return (
                f"在{product}的设计哲学中，{tone_word}不仅是一种标准，更是一种态度。"
                f"甄选材质，{points_text}，每一处细节都经过反复打磨。"
                f"为{audience}打造的不仅是一件产品，更是一种对品质生活的执着追求。"
            )
        elif template["detail_style"] == "场景化":
            return (
                f"想象一下：{audience}用它的时候——{points_text}，满满的{tone_word}感！"
                f"无论是清晨还是深夜，{product}都能成为你生活里的{tone_word}伙伴。"
                f"好东西就该被看见，被使用，被喜爱。这不只是一件商品，更是你的生活小确幸～"
            )
        elif template["detail_style"] == "促销":
            return (
                f"限时特惠！{product}为你带来{points_text}。"
                f"原价高品质，今日下单享专属优惠。{audience}不容错过，"
                f"活动数量有限，先到先得，售完即止！"
            )
        else:
            return (
                f"{product}采用{tone_word}技术方案，{points_text}。"
                f"经过多轮测试验证，各项指标均达到行业领先水平。"
                f"专为{audience}设计，在性能、安全性、耐用性三个维度提供系统性保障。"
            )

    def _infer_selling_points(self, product_name: str, category: str) -> list[str]:
        hints = {
            "椅": ["护腰支撑", "透气坐垫", "稳固耐用"],
            "手机": ["高清屏幕", "长续航", "快速充电"],
            "耳机": ["降噪隔音", "音质出色", "佩戴舒适"],
            "键盘": ["机械手感", "背光设计", "防溅洒"],
            "鼠标": ["精准定位", "人体工学", "多设备切换"],
            "桌": ["承重稳固", "高度可调", "环保材质"],
            "灯": ["护眼无频闪", "亮度可调", "节能省电"],
            "杯": ["长效保温", "食品级材质", "密封防漏"],
            "T恤": ["纯棉透气", "宽松百搭", "不起球"],
            "露营": ["超轻便携", "稳固承重", "快速收纳"],
        }
        for keyword, pts in hints.items():
            if keyword in product_name or keyword in category:
                return pts
        return ["品质保障", "实用设计", "性价比之选"]

    # ===== 模块二：智能导购与推荐问答 =====

    def recommend(self, payload: GuideRecommendationRequest) -> dict[str, object]:
        products = payload.products or ["高性价比基础款", "品质升级款", "礼赠套装款"]
        primary = products[0]
        need = payload.user_need
        budget = payload.budget or "未限定"
        need_lower = need.lower()

        # 智能识别需求场景
        if any(w in need_lower for w in ["送", "礼", "朋友", "长辈", "生日"]):
            reason_focus = f"考虑到您是用来送礼，{primary}在包装和品质上都很出色，非常适合作为礼物。"
            guide_msg = "送礼建议优先选择礼盒装，并附上手写卡片增加仪式感。如需礼品包装服务，可在下单时备注。"
        elif any(w in need_lower for w in ["预算", "便宜", "性价比", "实惠"]):
            reason_focus = f"在您的预算范围内，{primary}是性价比最高的选择，核心功能齐全且价格亲民。"
            guide_msg = "建议关注平台的满减活动和优惠券，叠加使用可以进一步降低实际支付金额。"
        elif any(w in need_lower for w in ["品质", "高端", "最好", "顶级"]):
            reason_focus = f"从品质角度来看，{primary}在材质、做工和用户体验上都达到了较高水准。"
            guide_msg = "高品质商品通常提供更长的质保期和更完善的售后服务，建议下单前确认保修政策。"
        elif any(w in need_lower for w in ["日常", "家用", "自用"]):
            reason_focus = f"对于日常使用，{primary}在实用性和耐用性上表现均衡，是居家好帮手。"
            guide_msg = "日常使用建议关注产品的易清洁性和维护成本，选择便于打理的款式。"
        elif any(w in need_lower for w in ["学生", "宿舍", "便携"]):
            reason_focus = f"针对学生群体，{primary}在便携性和实用性上做了很好的平衡。"
            guide_msg = "学生用户可关注教育优惠政策，部分商品凭学生证可享受额外折扣。"
        else:
            reason_focus = f"综合您的需求，{primary}是最贴近您期望的选择。"
            guide_msg = "建议优先确认使用场景和核心需求，再比较售后政策和到货时效。如有规格疑问，可随时提问。"

        reason = (
            f"{reason_focus}"
            f"它在预算（{budget}）范围内，核心功能表现突出，"
            f"是综合体验和价格的最佳平衡点。"
        )
        alternatives = products[1:3] if len(products) > 1 else ["品质升级款", "轻量便携款"]
        return {
            "user_need": need,
            "budget": budget,
            "recommended_product": primary,
            "reason": reason,
            "alternatives": alternatives,
            "guide_message": guide_msg,
        }

    def guide_qa(self, payload: GuideQARequest) -> dict[str, object]:
        question = payload.question
        q_type = payload.question_type
        if q_type == "auto":
            q_type = self._detect_question_type(question)
        templates = QA_TEMPLATES.get(q_type, [])
        spec = payload.product_specs or ""
        audience = "收礼人" if any(w in question for w in ["送", "礼"]) else "用户"
        matched = None
        for tpl in templates:
            if any(kw in question for kw in tpl["keywords"]):
                matched = tpl
                break
        if matched:
            # 如果有真实specs就用，否则从商品名称推断
            if not spec:
                spec = self._infer_spec_from_name(payload.product_name, payload.category, q_type)
            answer = matched["answer"].format(
                spec=spec, category=payload.category or "日常", audience=audience,
            )
            tips = matched["tips"]
        else:
            answer = self._generate_generic_answer(question, payload, q_type)
            tips = self._generate_tips(payload, q_type)
        return {
            "question": question,
            "question_type": q_type,
            "answer": answer,
            "related_tips": tips,
        }

    def _infer_spec_from_name(self, name: str, category: str, q_type: str) -> str:
        """从商品名称和分类推断规格信息"""
        if not name:
            return "标准规格"
        name_lower = name.lower()

        # 尺码/规格类问题
        if q_type == "size":
            # 从名称提取尺寸信息
            import re
            size_match = re.search(r'(\d+\.?\d*)\s*(cm|CM|厘米|mm|毫米|寸|英寸|kg|公斤|斤|L|升|ml|毫升|GB|TB)', name)
            if size_match:
                return f"{size_match.group(1)}{size_match.group(2)}"

            # 按分类推断
            size_map = {
                "办公家具": "标准办公尺寸，座高约45-50cm可调",
                "服装服饰": "均码偏大，建议参考尺码表选择",
                "鞋靴箱包": "标准尺码，建议按日常码数选择",
                "数码电子": "标准尺寸，适合日常使用",
                "生活用品": "常规容量，满足日常需求",
                "家居家电": "标准规格，请参考详情页尺寸表",
            }
            return size_map.get(category, "标准规格")

        # 功能类问题
        if q_type == "function":
            func_map = {
                "数码电子": "蓝牙连接、长续航、快充",
                "办公家具": "人体工学设计、高度可调、稳固承重",
                "服装服饰": "透气舒适、耐洗不易变形",
                "生活用品": "保温保冷、食品级材质、密封防漏",
                "家居家电": "节能省电、多档调节、安全防护",
                "运动户外": "轻便耐用、防水防滑",
            }
            return func_map.get(category, "核心功能完善，满足日常使用")

        # 搭配类问题
        if q_type == "matching":
            return f"{category}风格，百搭实用"

        return "详见商品参数"

    def _detect_question_type(self, question: str) -> str:
        size_kw = ["多高", "多大", "尺寸", "大小", "重量", "多重", "尺码", "码", "规格", "长", "宽", "高", "容量", "能装多少"]
        func_kw = ["功能", "作用", "怎么用", "使用", "操作", "安装", "材质", "材料", "面料", "续航", "电池", "充电", "防水", "防摔", "效果", "好不好", "怎么样", "靠谱", "值不值", "值得买"]
        match_kw = ["搭配", "配什么", "穿搭", "组合", "送", "礼物", "送礼", "场景", "场合", "适合什么", "适合谁"]
        price_kw = ["多少钱", "价格", "贵不贵", "便宜", "划算", "性价比", "预算", "值得"]
        # 新增：价格类、比较类、推荐类
        for kw in size_kw:
            if kw in question:
                return "size"
        for kw in price_kw:
            if kw in question:
                return "price"
        for kw in func_kw:
            if kw in question:
                return "function"
        for kw in match_kw:
            if kw in question:
                return "matching"
        return "function"

    def _generate_generic_answer(self, question: str, payload: GuideQARequest, q_type: str) -> str:
        """生成有意义的通用回答 - 基于商品信息而非说'看详情页'"""
        product = payload.product_name or "该商品"
        category = payload.category or ""
        spec = payload.product_specs or ""

        # 根据问题类型生成不同回答
        if q_type == "price":
            return self._answer_price_question(question, payload)
        elif q_type == "size":
            return self._answer_size_question(question, payload)
        elif q_type == "function":
            return self._answer_function_question(question, payload)
        elif q_type == "matching":
            return self._answer_matching_question(question, payload)
        else:
            return self._answer_general_question(question, payload)

    def _answer_price_question(self, question: str, payload: GuideQARequest) -> str:
        """回答价格相关问题"""
        product = payload.product_name or "该商品"
        category = payload.category or ""
        # 根据分类给出价格参考
        price_ranges = {
            "数码电子": "100-3000元",
            "服装服饰": "30-300元",
            "鞋靴箱包": "80-500元",
            "家居家电": "50-2000元",
            "办公家具": "100-1500元",
            "生活用品": "15-150元",
            "运动户外": "50-800元",
            "美妆个护": "30-300元",
            "食品酒水": "10-200元",
        }
        price_range = price_ranges.get(category, "30-500元")
        return (
            f"{product}属于{category}类目，同类产品的价格区间通常在{price_range}。"
            f"性价比方面，建议您对比同分类下不同品牌的商品，关注促销活动期间的价格优惠。"
            f"如果您有明确的预算范围，我可以为您推荐该价位段的最佳选择。"
        )

    def _answer_size_question(self, question: str, payload: GuideQARequest) -> str:
        """回答尺寸规格问题"""
        product = payload.product_name or "该商品"
        category = payload.category or ""
        spec = payload.product_specs or self._infer_spec_from_name(product, category, "size")

        # 从商品名称提取尺寸
        import re
        size_match = re.search(r'(\d+\.?\d*)\s*(cm|CM|厘米|mm|毫米|寸|英寸|kg|公斤|斤|L|升|ml|毫升|GB|TB)', product)
        if size_match:
            return (
                f"根据{product}的产品信息，其规格为{size_match.group(0)}。"
                f"这个规格属于{category}类目的常规尺寸，适合大多数使用场景。"
                f"如果您需要更精确的尺寸数据，可以参考商品参数表中的详细信息。"
            )

        size_advice = {
            "办公家具": "标准办公椅座高约45-50cm，建议身高160-185cm的用户使用。桌面高度建议72-76cm。",
            "服装服饰": "建议参考尺码表中的胸围、肩宽数据选择。如果介于两个尺码之间，建议选大一号。",
            "鞋靴箱包": "建议按日常穿着码数选择。不同品牌可能存在0.5码偏差，建议试穿后不支持7天退换。",
            "数码电子": "标准尺寸设计，便于携带和日常使用。具体长宽高数据请参考商品参数。",
            "生活用品": "常规容量设计，满足日常使用需求。如需大容量版本，可查看同系列其他规格。",
            "家居家电": "标准规格，安装前请测量使用空间。建议预留5-10cm散热/操作空间。",
        }
        advice = size_advice.get(category, f"该商品为{category}类标准规格，适合常规使用场景。")
        return f"关于{product}的尺寸规格：{advice}"

    def _answer_function_question(self, question: str, payload: GuideQARequest) -> str:
        """回答功能使用问题"""
        product = payload.product_name or "该商品"
        category = payload.category or ""

        # 检查具体功能关键词
        if any(kw in question for kw in ["防水", "防摔"]):
            return f"{product}的防护性能取决于具体型号。一般{category}类产品具备基础防护功能，但不建议超出标称范围使用。如需高等级防护，建议选择专业型号。"

        if any(kw in question for kw in ["续航", "电池", "充电"]):
            return f"{product}作为{category}类电子产品，续航时间通常在4-8小时左右（具体取决于使用强度）。建议首次使用前充满电，长期不用时每月充电一次以保养电池。"

        if any(kw in question for kw in ["材质", "材料", "面料"]):
            material_map = {
                "服装服饰": "采用优质面料，透气舒适、亲肤不刺激，经过权威检测安全无甲醛。",
                "办公家具": "主体采用高强度钢材/合金框架，坐垫采用透气网布或高密度海绵，稳固耐用。",
                "生活用品": "采用食品级304不锈钢/PP材质，安全无毒，耐高温耐腐蚀。",
                "数码电子": "采用优质ABS/铝合金外壳，手感细腻，散热性能良好。",
                "家居家电": "采用环保材质，通过国家3C认证，安全可靠。",
            }
            material = material_map.get(category, "采用优质材料制造，经过严格品质检测。")
            return f"{product}的材质：{material}"

        if any(kw in question for kw in ["怎么用", "使用", "操作", "安装"]):
            usage_map = {
                "办公家具": "安装步骤简单，附带安装工具和说明书，约15-20分钟即可完成组装。建议两人配合操作。",
                "数码电子": "开机后按引导设置即可使用。首次使用建议充满电。如遇配对问题，长按电源键5秒重置。",
                "家居家电": "使用前请阅读说明书，注意电压要求。首次使用建议先空载运行测试。",
                "服装服饰": "建议首次穿着前先清洗。洗涤时请按洗水标指示，避免高温烘干。",
            }
            usage = usage_map.get(category, "请参考随附的使用说明书，如有疑问可联系客服获取视频指导。")
            return f"{product}的使用方法：{usage}"

        if any(kw in question for kw in ["怎么样", "好不好", "靠谱", "值不值", "值得买"]):
            # 评价性问题 - 给出基于分类的客观评价
            eval_map = {
                "数码电子": "该产品在同价位段表现不错，核心功能完善，日常使用完全够用。如果您对音质/画质有更高要求，可以考虑升级款。",
                "办公家具": "作为日常办公使用，这款产品的舒适度和支撑性都能满足需求。人体工学设计有效缓解久坐疲劳。",
                "服装服饰": "面料和做工在这个价位算是不错的，版型正常不偏码。日常穿搭或工作场合都适合。",
                "生活用品": "实用性强，材质安全，日常使用完全没问题。性价比较高，值得入手。",
                "家居家电": "功能实用，操作简单，能耗在可接受范围内。品牌售后有保障，适合家庭使用。",
                "运动户外": "轻便耐用，适合日常运动或户外活动使用。专业级别需求建议选择更高配置款。",
            }
            evaluation = eval_map.get(category, f"作为{category}类产品，整体表现中规中矩，性价比合理，满足日常使用需求。")
            return f"关于{product}：{evaluation}"

        # 默认功能回答
        func_map = {
            "数码电子": "支持蓝牙连接、长续航、快充等核心功能，满足日常使用需求。",
            "办公家具": "具备人体工学设计、高度可调、稳固承重等功能特点，有效提升办公舒适度。",
            "服装服饰": "透气舒适、耐洗不易变形，适合日常穿搭。",
            "生活用品": "保温保冷、食品级材质、密封防漏，满足日常使用场景。",
            "家居家电": "节能省电、多档调节、安全防护，操作简单方便。",
            "运动户外": "轻便耐用、防水防滑，适合各种户外场景。",
        }
        func_desc = func_map.get(category, "核心功能完善，满足日常使用需求。")
        return f"{product}的主要功能：{func_desc}"

    def _answer_matching_question(self, question: str, payload: GuideQARequest) -> str:
        """回答搭配/场景/送礼问题"""
        product = payload.product_name or "该商品"
        category = payload.category or ""

        if any(kw in question for kw in ["送", "礼物", "送礼"]):
            gift_map = {
                "数码电子": "非常适合作为礼物送出。电子产品实用性强，包装精美，收礼人会觉得贴心。建议选择礼盒装增加仪式感。",
                "办公家具": "适合送给需要长时间办公的朋友或家人，体现对他们健康的关心。实用且有品质感。",
                "服装服饰": "作为礼物建议选择经典百搭款式，附上精美包装和手写卡片，仪式感满满。",
                "生活用品": "适合作为实用礼物，尤其是高品质的保温杯/水杯，日常使用频率高，收礼人会觉得贴心。",
                "美妆个护": "非常适合作为礼物，尤其是送给女性朋友或长辈。建议选择套装款，更显心意。",
            }
            gift_advice = gift_map.get(category, f"这款{product}适合作为礼物送出，包装精美，实用性强。")
            return f"关于送礼：{gift_advice}"

        if any(kw in question for kw in ["搭配", "配什么", "穿搭"]):
            match_map = {
                "服装服饰": "建议搭配同色系的基础款单品，简约大方。配饰宜精不宜多，一双好鞋或一条腰带就能提升整体质感。",
                "数码电子": "可以搭配同品牌的配件使用，如保护壳、充电器、支架等，提升使用体验。",
                "办公家具": "建议搭配护腰靠垫、显示器支架使用，打造完整的健康办公环境。",
                "鞋靴箱包": "建议搭配同风格的服装和配饰，整体造型更协调。",
            }
            match_advice = match_map.get(category, f"建议搭配同分类的其他商品使用，效果更佳。")
            return f"搭配建议：{match_advice}"

        if any(kw in question for kw in ["场景", "场合", "适合什么"]):
            scene_map = {
                "数码电子": "适合通勤、运动、居家等多种场景使用。小巧便携，随时随地可用。",
                "办公家具": "适合办公室、书房、工作室等场景。长时间办公时提供舒适支撑。",
                "服装服饰": "适合日常通勤、休闲出行、朋友聚会等多种场合。经典款式百搭不挑人。",
                "运动户外": "适合户外运动、旅行露营、健身训练等场景。轻便耐用，方便携带。",
                "生活用品": "适合居家、办公、出行等多种场景。日常使用频率高，实用性强。",
            }
            scene_advice = scene_map.get(category, f"适合{category}相关的日常使用场景。")
            return f"使用场景：{scene_advice}"

        return f"{product}适合{category}相关场景使用，如果您有更具体的需求，可以告诉我，我为您详细推荐。"

    def _answer_general_question(self, question: str, payload: GuideQARequest) -> str:
        """回答一般性问题"""
        product = payload.product_name or "该商品"
        category = payload.category or ""
        return (
            f"{product}是一款{category}类产品。"
            f"如果您想了解具体的功能特点、尺寸规格、使用方法或搭配建议，"
            f"可以直接提问，我会为您详细解答。"
        )

    def _generate_tips(self, payload: GuideQARequest, q_type: str) -> list[str]:
        """根据问题类型生成相关提示"""
        category = payload.category or ""
        tips_map = {
            "size": [
                "建议购买前测量实际使用空间",
                "注意区分产品尺寸和包装尺寸",
                "安装类产品需预留5-10cm操作空间",
            ],
            "function": [
                "首次使用建议阅读说明书",
                "如有功能疑问可联系客服获取视频指导",
                "建议了解核心功能后再下单",
            ],
            "matching": [
                "同色系搭配更显高级",
                "配饰宜精不宜多",
                "选择经典款式更百搭",
            ],
            "price": [
                "建议对比同分类不同品牌的商品",
                "关注促销活动期间的价格优惠",
                "性价比不等于最低价，综合考量品质和售后",
            ],
        }
        return tips_map.get(q_type, ["如有其他问题，欢迎随时提问"])

    def cross_recommend(self, payload: CrossRecommendRequest) -> dict[str, object]:
        product = payload.product_name
        prefs = payload.user_preferences or []
        recommendations = []
        for keyword, items in CROSS_RECOMMEND_MAP.items():
            if keyword in product or keyword in payload.category:
                recommendations = [dict(item) for item in items]
                break
        if not recommendations:
            recommendations = [
                {"product_name": "同系列升级款", "reason": "同品牌升级版本，体验全面提升", "match_score": 82},
                {"product_name": "配件套装", "reason": "搭配核心配件，即买即用更省心", "match_score": 75},
                {"product_name": "延长保修服务", "reason": "额外保障，用得更安心", "match_score": 68},
            ]
        for rec in recommendations:
            if prefs:
                pref_boost = 0
                for pref in prefs:
                    if pref in rec["reason"] or pref in rec["product_name"]:
                        pref_boost += 8
                rec["match_score"] = min(99, rec["match_score"] + pref_boost)
            rec["reason"] = self._personalize_reason(rec["reason"], prefs, payload.budget)
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        return {
            "current_product": product,
            "user_preferences": prefs,
            "recommendations": recommendations[:4],
        }

    def _personalize_reason(self, reason: str, prefs: list[str], budget: str) -> str:
        if not prefs:
            return reason
        pref_text = "、".join(prefs[:3])
        if budget and budget != "未限定":
            return f"{reason}。符合您「{pref_text}」的偏好，且在{budget}预算范围内。"
        return f"{reason}。符合您「{pref_text}」的偏好。"

    # ===== 模块三：用户评论情感分析 =====

    def analyze_reviews(self, payload: ReviewAnalysisRequest) -> dict[str, object]:
        reviews = payload.reviews
        sentiments = [self._sentiment(r) for r in reviews]
        sentiment_counts = Counter(sentiments)
        positive_reviews = [r for r, s in zip(reviews, sentiments) if s == "positive"][:5]
        negative_reviews = [r for r, s in zip(reviews, sentiments) if s == "negative"][:5]
        complaints = self._extract_complaints(reviews)
        keywords = self._extract_keywords(reviews)
        pain_points = self._extract_pain_points(reviews, sentiments)
        suggestions = self._generate_suggestions(
            sentiment_counts, complaints, pain_points, keywords, len(reviews)
        )
        return {
            "product_name": payload.product_name,
            "total": len(reviews),
            "sentiment": {
                "positive": sentiment_counts["positive"],
                "neutral": sentiment_counts["neutral"],
                "negative": sentiment_counts["negative"],
            },
            "sentiment_detail": {
                "positive_reviews": positive_reviews,
                "negative_reviews": negative_reviews,
                "complaints": complaints,
            },
            "top_keywords": keywords,
            "pain_points": pain_points,
            "optimization_suggestions": suggestions,
        }

    def _sentiment(self, review: str) -> str:
        positive_score = sum(word in review for word in POSITIVE_WORDS)
        negative_score = sum(word in review for word in NEGATIVE_WORDS)
        if "不错" in review:
            positive_score += 1
        if positive_score > negative_score:
            return "positive"
        if negative_score > positive_score:
            return "negative"
        return "neutral"

    def _extract_complaints(self, reviews: list[str]) -> list[str]:
        complaints = []
        for review in reviews:
            for category, keywords in COMPLAINT_PATTERNS.items():
                for kw in keywords:
                    if kw in review:
                        complaint_text = self._extract_sentence(review, kw)
                        if complaint_text:
                            entry = f"[{category}] {complaint_text}"
                            if entry not in complaints:
                                complaints.append(entry)
                        break
        return complaints[:8]

    def _extract_sentence(self, text: str, keyword: str) -> str:
        sentences = re.split(r"[，。！？；,!?;]", text)
        for s in sentences:
            if keyword in s and len(s.strip()) > 2:
                return s.strip()
        return text[:30]

    def _extract_keywords(self, reviews: list[str]) -> list[str]:
        word_counts: Counter = Counter()
        for review in reviews:
            for word in POSITIVE_WORDS | NEGATIVE_WORDS:
                if word in review:
                    word_counts[word] += 1
            for cat_words in KEYWORD_CATEGORIES.values():
                for w in cat_words:
                    if w in review:
                        word_counts[w] += 1
        return [word for word, _ in word_counts.most_common(10)]

    def _extract_pain_points(self, reviews: list[str], sentiments: list[str]) -> list[str]:
        pain_points = []
        seen = set()
        for review, sentiment in zip(reviews, sentiments):
            if sentiment != "negative":
                continue
            for word in NEGATIVE_WORDS:
                if word in review and word not in seen:
                    context = self._extract_sentence(review, word)
                    pain_point = context if context else f'存在"{word}"问题'
                    if pain_point not in seen:
                        pain_points.append(pain_point)
                        seen.add(pain_point)
                    break
        return pain_points[:5]

    def _generate_suggestions(
        self, sentiment_counts: Counter, complaints: list[str],
        pain_points: list[str], keywords: list[str], total: int,
    ) -> list[str]:
        suggestions = []
        positive_pct = sentiment_counts["positive"] / max(total, 1) * 100
        negative_pct = sentiment_counts["negative"] / max(total, 1) * 100
        if positive_pct > 70:
            top_pos = [k for k in keywords if k in POSITIVE_WORDS][:3]
            if top_pos:
                suggestions.append(
                    f"好评率达{positive_pct:.0f}%，核心优势「{'、'.join(top_pos)}」应强化在详情页首屏和短视频口播中的呈现。"
                )
        elif negative_pct > 30:
            suggestions.append(
                f"差评率较高（{negative_pct:.0f}%），建议优先排查产品质量和描述一致性问题。"
            )
        complaint_categories = set()
        for c in complaints:
            if c.startswith("["):
                cat = c.split("]")[0][1:]
                complaint_categories.add(cat)
        category_advice = {
            "物流": "物流体验影响购物感受，建议优化发货时效和包装防护。",
            "包装": "包装问题频出，建议升级包装材料，增加防撞缓冲层。",
            "质量": "质量是核心竞争力，建议加强品控流程，对高频质量问题进行专项整改。",
            "尺寸": "尺寸信息不清晰导致退换，建议完善尺码表，增加实拍对比图。",
            "售后": "售后体验直接影响复购，建议优化客服响应速度和退换货流程。",
            "使用体验": "使用体验有改善空间，建议收集具体反馈迭代产品设计。",
            "价格": "价格敏感度较高，建议通过赠品、满减或会员价提升性价比感知。",
        }
        for cat in complaint_categories:
            if cat in category_advice:
                suggestions.append(category_advice[cat])
        if len(suggestions) < 3:
            suggestions.append("将高频好评词加入详情页首屏和短视频口播，增强购买信心。")
        if len(suggestions) < 4:
            suggestions.append("把差评痛点转化为售前提醒、FAQ 或售后承诺，降低预期落差。")
        if len(suggestions) < 5:
            suggestions.append("定期监控评论情感趋势，建立差评预警机制。")
        return suggestions[:5]

    # ===== 模块四：直播/短视频脚本自动生成 =====

    def generate_live_script(self, payload: LiveScriptRequest) -> dict[str, object]:
        product = payload.product_name
        duration = payload.duration_minutes
        tone = payload.tone
        highlights = payload.highlights or self._infer_selling_points(product, "")
        audience = payload.target_audience or "消费者"
        specs = payload.product_specs or ""
        segments = self._build_live_segments(product, duration, tone, highlights, audience)
        explanation_flow = self._build_explanation_flow(product, highlights, specs, audience)
        interaction_questions = self._build_interaction_questions(product, highlights, audience)
        conversion_scripts = self._build_conversion_scripts(product, tone, audience)
        return {
            "product_name": product,
            "duration_minutes": duration,
            "tone": tone,
            "segments": segments,
            "explanation_flow": explanation_flow,
            "interaction_questions": interaction_questions,
            "conversion_scripts": conversion_scripts,
        }

    def _build_live_segments(
        self, product: str, duration: int, tone: str, highlights: list[str], audience: str
    ) -> list[dict[str, object]]:
        if duration <= 5:
            opening_mins, closing_mins = 1, 1
        elif duration <= 15:
            opening_mins, closing_mins = 2, 2
        else:
            opening_mins, closing_mins = 3, 3
        demo_mins = max(duration - opening_mins - closing_mins, 1)
        tone_prefix = {
            "热情自然": "家人们", "专业严谨": "各位朋友",
            "轻松幽默": "小伙伴们", "亲切温馨": "亲爱的们",
        }.get(tone, "大家好")
        return [
            {
                "name": "开场引入", "minutes": opening_mins,
                "script": (
                    f"{tone_prefix}，欢迎来到直播间！今天给大家带来的是{product}。"
                    f"如果你是{audience}，这款产品一定不要划走。"
                    f"我们先看一个真实使用场景——（展示产品使用画面）。"
                    f"接下来我详细讲讲它到底好在哪里。"
                ),
                "action_hint": "手持产品近景展示，背景播放使用场景视频",
            },
            {
                "name": "卖点讲解", "minutes": demo_mins,
                "script": (
                    f"我们重点讲{product}的几个核心卖点。"
                    f"第一，{highlights[0] if highlights else '品质保障'}——（现场演示）。"
                    f"第二，{highlights[1] if len(highlights) > 1 else '实用设计'}——（对比展示）。"
                    f"第三，{highlights[2] if len(highlights) > 2 else '性价比'}——（数据说明）。"
                ),
                "action_hint": "逐个演示卖点，配合特写镜头和对比实验",
            },
            {
                "name": "互动答疑", "minutes": max(closing_mins - 1, 1),
                "script": (
                    f"看到弹幕有很多问题，我来集中回答。"
                    f"关于尺寸——看屏幕左下角的尺寸表。"
                    f"关于售后——支持7天无理由，质量问题包退换。"
                    f"还有问题打在公屏上，我一对一解答。"
                ),
                "action_hint": "切换到评论互动画面，展示尺寸表/售后政策",
            },
            {
                "name": "转化收尾", "minutes": 1,
                "script": (
                    f"今天{product}的价格是直播间专属福利。"
                    f"库存有限，卖完就恢复原价。"
                    f"想好了直接拍，不满意包退。3、2、1，上链接！"
                ),
                "action_hint": "展示购买链接，倒计时引导下单",
            },
        ]

    def _build_explanation_flow(
        self, product: str, highlights: list[str], specs: str, audience: str
    ) -> list[dict[str, object]]:
        return [
            {
                "step": 1, "title": "产品定位与适用人群",
                "script": f"首先介绍{product}是什么、为谁设计。专为{audience}打造。",
                "key_points": ["一句话说清产品定位", "明确目标用户画像", "点出核心痛点"],
            },
            {
                "step": 2, "title": "核心卖点逐一拆解",
                "script": f"逐个讲解卖点：{'; '.join(highlights[:3])}。每一点配合实物演示。",
                "key_points": ["每个卖点配一个演示动作", "用对比突出优势", "避免堆砌参数"],
            },
            {
                "step": 3, "title": "使用场景还原",
                "script": f"展示{audience}日常使用{product}的画面，让观众产生代入感。",
                "key_points": ["展示至少2个使用场景", "让观众产生代入感", "突出使用前后的变化"],
            },
            {
                "step": 4, "title": "规格参数与对比",
                "script": f"看规格参数：{specs or '核心参数已标注在屏幕上'}。和同类产品对比突出优势。",
                "key_points": ["参数用图表展示更直观", "和竞品对比突出差异", "强调认证和标准"],
            },
            {
                "step": 5, "title": "售后保障与信任建立",
                "script": f"最后说说售后。{product}支持7天无理由退换，质量问题终身保修。",
                "key_points": ["说清退换货政策", "展示品牌资质", "引导关注店铺"],
            },
        ]

    def _build_interaction_questions(
        self, product: str, highlights: list[str], audience: str
    ) -> list[str]:
        return [
            f"你最关注{product}的哪个功能？打在公屏上我针对性讲。",
            f"有拿不准尺码/规格的吗？告诉我你的情况，我帮你推荐。",
            f"觉得这个价格怎么样？想要什么赠品？弹幕告诉我。",
            f"之前用过同类产品的，对比一下体验差异？",
            f"还有什么想了解的？接下来5分钟集中答疑。",
        ]

    def _build_conversion_scripts(self, product: str, tone: str, audience: str) -> list[str]:
        return [
            f"今天直播间专属价，比日常省XX元。库存只有XX件，抢完恢复原价。",
            f"现在下单额外送{product}配件礼包，仅限今天直播间下单的用户。",
            f"3分钟内下单的，再加赠运费险。不满意包退，退货不用你出运费。",
            f"已经有XX位家人下单了。还在犹豫的，先拍下锁定优惠，不满意随时退。",
            f"最后30秒！没付款的抓紧，链接马上关闭。",
        ]
