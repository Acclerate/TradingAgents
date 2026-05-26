"""Xuangubao (选股宝) flash news data source.

Direct HTTP access to baoer-api.xuangubao.com.cn for real-time market news.

Reference: LeekHub/leek-fund src/webview/xuangubao-news.ts
"""

import logging
from datetime import datetime

import requests

from .anti_scraping import random_headers, retry_with_backoff

logger = logging.getLogger(__name__)

_API_URL = "https://baoer-api.xuangubao.com.cn/api/v6/message/newsflash"

# Subject IDs for different news categories
_SUBJECT_IDS = [9, 10, 723, 35, 469]


@retry_with_backoff(retries=2, delay_base=1.0)
def get_xuangubao_flash_news(limit: int = 20) -> list[dict]:
    """Fetch flash news from Xuangubao.

    Args:
        limit: Maximum number of news items to return.

    Returns:
        List of dicts with 'title', 'summary', 'created_at' fields.
    """
    all_items = []
    for subj_id in _SUBJECT_IDS:
        try:
            resp = requests.get(
                _API_URL,
                params={
                    "limit": min(limit, 20),
                    "subj_ids": str(subj_id),
                    "platform": "pcweb",
                },
                headers=random_headers("xuangubao"),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("data", {}).get("messages", [])

            for msg in messages:
                item = {
                    "title": msg.get("title", ""),
                    "summary": msg.get("summary", ""),
                    "created_at": msg.get("created_at", 0),
                    "id": msg.get("id", ""),
                    "source": "选股宝",
                }
                all_items.append(item)

        except Exception as exc:
            logger.debug("Xuangubao subj_id=%d failed: %s", subj_id, exc)

    # Sort by creation time (newest first), deduplicate by id
    seen = set()
    unique = []
    for item in sorted(all_items, key=lambda x: x["created_at"], reverse=True):
        if item["id"] not in seen:
            seen.add(item["id"])
            unique.append(item)

    return unique[:limit]


def get_xuangubao_news_formatted(limit: int = 20) -> str:
    """Get formatted Xuangubao flash news for agent consumption."""
    items = get_xuangubao_flash_news(limit)
    if not items:
        return "No flash news available from 选股宝"

    lines = [
        f"# 选股宝异动快讯 (Xuangubao Flash News)",
        f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Total items: {len(items)}\n",
    ]

    for item in items:
        ts = datetime.fromtimestamp(item["created_at"]).strftime("%Y-%m-%d %H:%M") if item["created_at"] else ""
        title = item["title"]
        summary = item["summary"]
        lines.append(f"[{ts}] {title}")
        if summary:
            lines.append(f"  {summary}")
        lines.append("")

    return "\n".join(lines)
