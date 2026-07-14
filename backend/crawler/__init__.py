"""爬虫模块"""
from backend.crawler.suning_crawler import SuningCrawler, SuningProduct
from backend.crawler.crawl_manager import crawl_manager

__all__ = ["SuningCrawler", "SuningProduct", "crawl_manager"]
