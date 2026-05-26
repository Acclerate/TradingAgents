"""Xueqiu (雪球) direct API access.

Bypasses AKShare to directly call Xueqiu REST APIs with cookie-based
authentication. More reliable than AKShare's indirect approach.

Reference: LeekHub/leek-fund src/shared/xueqiu-helper.ts + src/explorer/newsService.ts
"""

import logging
from typing import Optional

import requests

from .anti_scraping import random_headers

logger = logging.getLogger(__name__)

_XUEQIU_BASE = "https://xueqiu.com"
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36"
)

# Module-level cookie cache
_cookies: Optional[str] = None


def xueqiu_get_token() -> str:
    """Fetch authentication cookies from Xueqiu homepage.

    Xueqiu requires a valid session cookie (xq_a_token) to access APIs.
    This function visits the homepage and extracts Set-Cookie headers.

    Returns:
        Cookie string for subsequent API requests.
    """
    global _cookies

    try:
        resp = requests.get(
            f"{_XUEQIU_BASE}/",
            headers={"User-Agent": _DEFAULT_UA},
            timeout=10,
        )
        cookie_headers = resp.headers.get("set-cookie", "")
        if not cookie_headers:
            # Try raw headers
            raw = resp.raw.headers.getlist("Set-Cookie") if hasattr(resp.raw, "headers") else []
            cookie_headers = "; ".join(raw) if raw else ""

        parts = []
        for h in cookie_headers.split(","):
            segment = h.split(";")[0].strip()
            if segment and not segment.endswith("="):
                parts.append(segment)

        if parts:
            _cookies = "; ".join(parts) + ";"
        else:
            # Fallback: use device_id only
            import random
            import string
            device_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=13))
            _cookies = f"device_id={device_id}"

    except Exception as exc:
        logger.warning("Xueqiu token fetch failed: %s", exc)
        import random
        import string
        device_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=13))
        _cookies = f"device_id={device_id}"

    return _cookies


def _get_headers() -> dict:
    """Get headers with current cookies for Xueqiu API requests."""
    cookies = _cookies or xueqiu_get_token()
    return {
        **random_headers("xueqiu"),
        "Cookie": cookies,
        "Host": "xueqiu.com",
        "X-Requested-With": "XMLHttpRequest",
    }


def xueqiu_get_user_timeline(user_id: str, page: int = 1) -> list[dict]:
    """Fetch a Xueqiu user's recent posts/timeline.

    Args:
        user_id: Xueqiu user ID.
        page: Page number (1-based).

    Returns:
        List of post dicts with 'title', 'text', 'created_at', etc.
    """
    url = f"{_XUEQIU_BASE}/v4/statuses/user_timeline.json"
    params = {"page": page, "user_id": user_id}

    try:
        headers = _get_headers()
        resp = requests.get(url, params=params, headers=headers, timeout=10)

        if resp.status_code == 400 or resp.status_code == 403:
            # Token expired, refresh and retry
            xueqiu_get_token()
            headers = _get_headers()
            resp = requests.get(url, params=params, headers=headers, timeout=10)

        resp.raise_for_status()
        statuses = resp.json().get("statuses", [])

        results = []
        for s in statuses:
            results.append({
                "id": s.get("id", ""),
                "user_id": s.get("user_id", ""),
                "title": s.get("title", ""),
                "text": s.get("text", ""),
                "created_at": s.get("created_at", 0),
                "retweet_count": s.get("retweet_count", 0),
                "reply_count": s.get("reply_count", 0),
                "like_count": s.get("like_count", 0),
                "source": "雪球",
            })
        return results

    except Exception as exc:
        logger.warning("Xueqiu timeline fetch failed for user %s: %s", user_id, exc)
        return []


def xueqiu_get_user_info(user_id: str) -> Optional[dict]:
    """Fetch Xueqiu user profile info.

    Args:
        user_id: Xueqiu user ID.

    Returns:
        Dict with user info or None.
    """
    url = f"{_XUEQIU_BASE}/statuses/original/show.json"
    params = {"user_id": user_id}

    try:
        headers = _get_headers()
        resp = requests.get(url, params=params, headers=headers, timeout=10)

        if resp.status_code in (400, 403):
            xueqiu_get_token()
            headers = _get_headers()
            resp = requests.get(url, params=params, headers=headers, timeout=10)

        resp.raise_for_status()
        return resp.json().get("data", {}).get("user")
    except Exception as exc:
        logger.debug("Xueqiu user info failed for %s: %s", user_id, exc)
        return None
