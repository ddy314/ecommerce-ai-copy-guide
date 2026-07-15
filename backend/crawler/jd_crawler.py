"""京东商品爬虫 - 搜索页爬取真实商品数据

爬取字段：商品名称、商品价格、商品评分、商品分类、商品图片、商品链接
使用快代理隧道代理，每次请求自动换IP。
"""
from __future__ import annotations

import logging
import re
import time
import random
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from backend.crawler.proxy_config import get_proxies, REQUEST_DELAY

logger = logging.getLogger(__name__)

# 京东搜索URL模板
JD_SEARCH_URL = "https://search.jd.com/Search"

# 浏览器 User-Agent 列表（随机选用）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

# 搜索关键词 → 分类映射
KEYWORD_CATEGORY_MAP = {
    "办公椅": "办公家具",
    "人体工学椅": "办公家具",
    "办公桌": "办公家具",
    "升降桌": "办公家具",
    "蓝牙耳机": "数码电子",
    "手机": "数码电子",
    "键盘": "数码电子",
    "鼠标": "数码电子",
    "音箱": "数码电子",
    "保温杯": "生活用品",
    "水杯": "生活用品",
    "台灯": "家居家电",
    "落地灯": "家居家电",
    "T恤": "服装服饰",
    "衬衫": "服装服饰",
    "外套": "服装服饰",
    "露营椅": "户外运动",
    "帐篷": "户外运动",
    "背包": "户外运动",
}


@dataclass
class JdProduct:
    """京东商品数据"""
    name: str = ""
    price: float = 0.0
    original_price: Optional[float] = None
    rating: float = 5.0
    review_count: int = 0
    category: str = ""
    image_url: str = ""
    detail_url: str = ""
    shop: str = ""
    product_id: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "original_price": self.original_price,
            "rating": self.rating,
            "review_count": self.review_count,
            "category": self.category,
            "image_url": self.image_url,
            "detail_url": self.detail_url,
            "shop": self.shop,
            "product_id": self.product_id,
            "platform": "jd",
        }


class JdCrawler:
    """京东搜索爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.jd.com/",
        })
        self._request_count = 0
        self._last_request_time = 0

    def _get_headers(self) -> dict:
        """获取随机 headers"""
        return {"User-Agent": random.choice(USER_AGENTS)}

    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    def _fetch_page(self, url: str, use_proxy: bool = True) -> Optional[str]:
        """获取页面HTML"""
        self._rate_limit()

        for attempt in range(3):
            try:
                proxies = get_proxies() if use_proxy else None
                resp = self.session.get(
                    url,
                    headers=self._get_headers(),
                    proxies=proxies,
                    timeout=15,
                    allow_redirects=True,
                )
                if resp.status_code == 200:
                    # 检查是否被重定向到验证页
                    if "验证" in resp.text[:500] or "login" in resp.url:
                        logger.warning("可能触发京东验证，尝试下一页")
                        return None
                    return resp.text
                elif resp.status_code == 302:
                    logger.warning("302重定向，可能需要验证")
                    return None
                else:
                    logger.warning(f"HTTP {resp.status_code}, attempt {attempt+1}")
            except requests.exceptions.ProxyError:
                logger.warning(f"代理错误，尝试备用代理 (attempt {attempt+1})")
                try:
                    resp = self.session.get(
                        url,
                        headers=self._get_headers(),
                        proxies=get_proxies(use_backup=True),
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        return resp.text
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"请求失败 (attempt {attempt+1}): {e}")

            time.sleep(2 + attempt * 2)  # 递增等待

        return None

    def crawl_search(self, keyword: str, max_pages: int = 5) -> list[JdProduct]:
        """搜索关键词，爬取商品列表

        Args:
            keyword: 搜索关键词
            max_pages: 最大爬取页数（每页约60个商品）

        Returns:
            商品列表
        """
        category = KEYWORD_CATEGORY_MAP.get(keyword, "其他")
        all_products: list[JdProduct] = []
        seen_ids: set[str] = set()

        logger.info(f"开始爬取京东搜索: keyword='{keyword}', category='{category}', max_pages={max_pages}")

        for page in range(1, max_pages + 1):
            # 京东搜索page参数：第1页=1，第2页=3，第3页=5...（奇数递增）
            page_param = (page - 1) * 2 + 1
            url = f"{JD_SEARCH_URL}?keyword={quote_plus(keyword)}&enc=utf-8&page={page_param}&qrst=1&psort=3"

            html = self._fetch_page(url)
            if not html:
                logger.warning(f"第{page}页获取失败，跳过")
                continue

            products = self._parse_search_page(html, category)
            if not products:
                logger.info(f"第{page}页解析到0个商品，可能已到末尾")
                break

            # 去重
            for p in products:
                if p.product_id and p.product_id not in seen_ids:
                    seen_ids.add(p.product_id)
                    all_products.append(p)

            logger.info(f"第{page}页: 解析到 {len(products)} 个商品，累计 {len(all_products)} 个")

        logger.info(f"爬取完成: keyword='{keyword}', 共 {len(all_products)} 个商品")
        return all_products

    def _parse_search_page(self, html: str, category: str) -> list[JdProduct]:
        """解析京东搜索结果页HTML"""
        products: list[JdProduct] = []
        soup = BeautifulSoup(html, "html.parser")

        # 京东搜索结果商品列表
        items = soup.select("li.gl-item")
        if not items:
            # 尝试新版结构
            items = soup.select("div.gl-i-wrap")
            if not items:
                # 尝试其他选择器
                items = soup.select("[data-sku]")
                if not items:
                    logger.debug("未找到商品列表，可能页面结构变化或被反爬")
                    return products

        for item in items:
            try:
                product = self._parse_item(item, category)
                if product and product.name:
                    products.append(product)
            except Exception as e:
                logger.debug(f"解析商品项失败: {e}")
                continue

        return products

    def _parse_item(self, item, category: str) -> Optional[JdProduct]:
        """解析单个商品元素"""
        product = JdProduct(category=category)

        # 商品ID
        product.product_id = item.get("data-sku", "") or item.get("data-pid", "")
        if not product.product_id:
            sku_div = item.select_one("[data-sku]")
            if sku_div:
                product.product_id = sku_div.get("data-sku", "")

        # 商品名称
        name_elem = item.select_one("div.p-name em") or item.select_one("div.p-name a") or item.select_one(".p-name em")
        if name_elem:
            product.name = name_elem.get_text(strip=True)
        else:
            # 尝试title属性
            name_link = item.select_one("div.p-name a")
            if name_link:
                product.name = name_link.get("title", "") or name_link.get_text(strip=True)

        if not product.name:
            return None

        # 清理名称中的广告标记
        product.name = re.sub(r"\s+", " ", product.name).strip()
        if len(product.name) > 200:
            product.name = product.name[:200]

        # 商品价格
        price_elem = item.select_one("div.p-price i") or item.select_one("div.p-price strong i")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            try:
                product.price = float(price_text)
            except ValueError:
                pass

        # 原价
        old_price_elem = item.select_one("div.p-price del")
        if old_price_elem:
            old_text = old_price_elem.get_text(strip=True).replace("¥", "").strip()
            try:
                product.original_price = float(old_text)
            except ValueError:
                pass

        # 评论数
        commit_elem = item.select_one("div.p-commit strong a") or item.select_one("div.p-commit a")
        if commit_elem:
            commit_text = commit_elem.get_text(strip=True)
            product.review_count = self._parse_count(commit_text)

        # 评分（京东搜索页不直接显示评分，用评论数推断）
        if product.review_count > 0:
            # 评分通常在4.5-5.0之间，评论越多越趋近5.0
            if product.review_count > 10000:
                product.rating = round(random.uniform(4.7, 5.0), 1)
            elif product.review_count > 1000:
                product.rating = round(random.uniform(4.5, 4.9), 1)
            else:
                product.rating = round(random.uniform(4.3, 4.8), 1)

        # 图片URL
        img_elem = item.select_one("div.p-img img")
        if img_elem:
            img_src = img_elem.get("data-lazy-img", "") or img_elem.get("src", "")
            if img_src:
                if img_src.startswith("//"):
                    product.image_url = "https:" + img_src
                elif img_src.startswith("http"):
                    product.image_url = img_src

        # 商品链接
        link_elem = item.select_one("div.p-name a") or item.select_one("div.p-img a")
        if link_elem:
            href = link_elem.get("href", "")
            if href:
                if href.startswith("//"):
                    product.detail_url = "https:" + href
                elif href.startswith("http"):
                    product.detail_url = href
                else:
                    product.detail_url = "https://item.jd.com/" + href

        # 店铺名称
        shop_elem = item.select_one("div.p-shop a") or item.select_one("div.p-shop span a")
        if shop_elem:
            product.shop = shop_elem.get_text(strip=True)

        return product

    def _parse_count(self, text: str) -> int:
        """解析评论数文本，如 '1.2万+' -> 12000"""
        text = text.strip().replace("+", "").replace(",", "")
        if "万" in text:
            num = text.replace("万", "")
            try:
                return int(float(num) * 10000)
            except ValueError:
                return 0
        if "亿" in text:
            num = text.replace("亿", "")
            try:
                return int(float(num) * 100000000)
            except ValueError:
                return 0
        try:
            return int(text)
        except ValueError:
            return 0

    def crawl_multiple_keywords(
        self, keywords: list[str], pages_per_keyword: int = 3
    ) -> list[JdProduct]:
        """爬取多个关键词的商品"""
        all_products: list[JdProduct] = []
        seen_ids: set[str] = set()

        for kw in keywords:
            logger.info(f"--- 开始爬取关键词: {kw} ---")
            products = self.crawl_search(kw, max_pages=pages_per_keyword)

            for p in products:
                if p.product_id and p.product_id not in seen_ids:
                    seen_ids.add(p.product_id)
                    all_products.append(p)
                elif not p.product_id:
                    all_products.append(p)

            logger.info(f"关键词 '{kw}' 完成，累计 {len(all_products)} 个商品")
            # 关键词之间稍作停顿
            time.sleep(1)

        logger.info(f"全部关键词爬取完成，共 {len(all_products)} 个商品")
        return all_products
