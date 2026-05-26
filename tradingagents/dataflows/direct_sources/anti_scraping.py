"""Anti-scraping utilities for direct data source requests.

Provides User-Agent rotation, rate limiting, retry with exponential backoff,
and common header generation. Inspired by LeekHub/leek-fund's randHeader().
"""

import logging
import random
import time
import threading
from functools import wraps
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-Agent pool — Chrome / Firefox / Edge across platforms
# ---------------------------------------------------------------------------
_UA_POOL = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Safari (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Generic older Chrome
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
]

# Referer presets for common data sources
_REFERER_MAP = {
    "sina": "http://finance.sina.com.cn/",
    "sina_futures": "https://finance.sina.com.cn/futures/",
    "tencent": "https://gu.qq.com/",
    "eastmoney": "https://www.eastmoney.com/",
    "xueqiu": "https://xueqiu.com/",
    "xuangubao": "https://xuangubao.com/",
    "boc": "https://www.boc.cn/",
    "sohu": "https://q.stock.sohu.com/",
}


def random_ua() -> str:
    """Return a random User-Agent string."""
    return random.choice(_UA_POOL)


def random_headers(referer: str = "sina") -> dict:
    """Generate randomized HTTP headers with appropriate Referer.

    Args:
        referer: Key in _REFERER_MAP or a full URL.
    """
    ua = random_ua()
    ref = _REFERER_MAP.get(referer, referer)
    return {
        "User-Agent": ua,
        "Referer": ref,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }


# ---------------------------------------------------------------------------
# Token-bucket rate limiter (thread-safe)
# ---------------------------------------------------------------------------
class RateLimiter:
    """Simple token-bucket rate limiter.

    Args:
        rate: Maximum requests per second.
    """

    def __init__(self, rate: float = 5.0):
        self._rate = rate
        self._interval = 1.0 / rate
        self._lock = threading.Lock()
        self._last_time = 0.0

    def wait(self):
        """Block until a request slot is available."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_time
            if elapsed < self._interval:
                time.sleep(self._interval - elapsed)
            self._last_time = time.monotonic()


# Module-level rate limiter instances (one per major source)
_sina_limiter = RateLimiter(rate=5.0)
_tencent_limiter = RateLimiter(rate=5.0)
_eastmoney_limiter = RateLimiter(rate=3.0)
_default_limiter = RateLimiter(rate=5.0)

LIMITERS = {
    "sina": _sina_limiter,
    "tencent": _tencent_limiter,
    "eastmoney": _eastmoney_limiter,
}


def get_limiter(source: str = "default") -> RateLimiter:
    """Get the rate limiter for a given source."""
    return LIMITERS.get(source, _default_limiter)


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------
def retry_with_backoff(
    func: Optional[Callable] = None,
    *,
    retries: int = 3,
    delay_base: float = 1.0,
    max_delay: float = 30.0,
    source: str = "default",
):
    """Decorator that retries a function with exponential backoff.

    Args:
        retries: Maximum number of retry attempts.
        delay_base: Base delay in seconds (doubles each retry).
        max_delay: Maximum delay cap.
        source: Rate limiter source key.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            limiter = get_limiter(source)
            last_exc = None
            for attempt in range(retries + 1):
                try:
                    limiter.wait()
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < retries:
                        delay = min(delay_base * (2 ** attempt), max_delay)
                        logger.debug(
                            "%s attempt %d/%d failed: %s — retrying in %.1fs",
                            fn.__name__, attempt + 1, retries + 1, exc, delay,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
