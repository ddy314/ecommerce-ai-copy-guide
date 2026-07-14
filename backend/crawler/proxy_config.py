"""快代理隧道代理配置"""
import os

# 快代理隧道代理配置
PROXY_HOST = os.getenv("PROXY_HOST", "c126.kdlttps.com")
PROXY_BACKUP_HOST = os.getenv("PROXY_BACKUP_HOST", "c125.kdlttps.com")
PROXY_PORT = os.getenv("PROXY_PORT", "15818")
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "t18391813951910")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "gadt1qmp")

# 构建代理URL
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"
PROXY_BACKUP_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_BACKUP_HOST}:{PROXY_PORT}"

# 代理字典（供 requests 使用）
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL,
}

PROXIES_BACKUP = {
    "http": PROXY_BACKUP_URL,
    "https": PROXY_BACKUP_URL,
}

# 速率限制
MAX_REQUESTS_PER_MINUTE = 280  # 留余量，低于300
MAX_CONCURRENT = 4  # 低于5
REQUEST_DELAY = 0.3  # 每次请求间隔秒数


def get_proxies(use_backup: bool = False) -> dict:
    """获取代理配置"""
    return PROXIES_BACKUP if use_backup else PROXIES


def test_proxy() -> bool:
    """测试代理是否可用"""
    import requests
    try:
        r = requests.get(
            "https://www.baidu.com/",
            proxies=get_proxies(),
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        return r.status_code == 200
    except Exception:
        return False
