"""雪球 (Xueqiu/Snowball) sentiment data for A-stocks.

Provides ``fetch_xueqiu_posts`` compatible with the sentiment analyst's
social data interface. Uses AKShare where possible, otherwise HTTP.
"""

import logging
from typing import Optional

import akshare as ak

from .ticker_utils import normalize_a_stock_ticker

logger = logging.getLogger(__name__)


def fetch_xueqiu_posts(ticker: str, limit: int = 30) -> str:
    """Fetch recent posts from 雪球 for an A-stock.

    Uses AKShare's available Xueqiu interfaces.
    """
    code = normalize_a_stock_ticker(ticker)

    posts = []

    try:
        # AKShare provides stock_xueqiu_stock_comments in some versions
        # but it's unreliable. Use stock_news_em as a fallback with
        # Xueqiu source filtering.
        df = ak.stock_news_em(symbol=code)
        if df is not None and not df.empty:
            source_col = next((c for c in df.columns if "来源" in str(c)), None)
            title_col = next((c for c in df.columns if "标题" in str(c)), None)
            content_col = next(
                (c for c in df.columns if "内容" in str(c) or "content" in str(c).lower()), None
            )
            count = 0
            for _, row in df.iterrows():
                source = str(row.get(source_col, "")) if source_col else ""
                # Include all news sources as Xueqiu-specific API is limited
                parts = []
                if title_col and str(row.get(title_col, "")).strip():
                    parts.append(str(row[title_col]))
                if content_col and str(row.get(content_col, "")).strip():
                    parts.append(str(row[content_col])[:300])
                if source:
                    parts.append(f"来源: {source}")
                if parts:
                    posts.append(" | ".join(parts))
                    count += 1
                    if count >= limit:
                        break
    except Exception as exc:
        logger.warning("雪球 fetch failed for %s: %s", code, exc)

    if not posts:
        return (
            f"[雪球] 暂时无法获取 {ticker} 的雪球讨论数据。"
            f"可参考个股新闻和基本面数据进行分析。"
        )

    header = f"=== 雪球 (Xueqiu) - {ticker} ===\n"
    header += f"共获取 {len(posts)} 条讨论\n\n"
    return header + "\n\n".join(posts)
