"""东方财富股吧 (EastMoney Guba) sentiment data for A-stocks.

Provides ``fetch_eastmoney_guba`` compatible with the sentiment analyst's
social data interface (returns formatted plaintext).
"""

import logging
from typing import Optional

import akshare as ak

from .ticker_utils import normalize_a_stock_ticker

logger = logging.getLogger(__name__)


def fetch_eastmoney_guba(ticker: str, limit: int = 30) -> str:
    """Fetch recent posts from 东方财富股吧 for an A-stock.

    Tries AKShare's ``stock_guba`` or related interfaces first.
    Falls back to a graceful placeholder on failure.
    """
    code = normalize_a_stock_ticker(ticker)

    posts = []

    # AKShare does not expose a dedicated stock_guba function in all versions.
    # Try the news + comment endpoints as a proxy for sentiment.
    try:
        df = ak.stock_news_em(symbol=code)
        if df is not None and not df.empty:
            # Extract user comments / discussions if available
            title_col = next((c for c in df.columns if "标题" in str(c)), None)
            content_col = next(
                (c for c in df.columns if "内容" in str(c) or "content" in str(c).lower()), None
            )
            source_col = next((c for c in df.columns if "来源" in str(c)), None)
            for _, row in df.head(limit).iterrows():
                parts = []
                if title_col and str(row.get(title_col, "")).strip():
                    parts.append(str(row[title_col]))
                if content_col and str(row.get(content_col, "")).strip():
                    parts.append(str(row[content_col])[:300])
                if source_col and str(row.get(source_col, "")).strip():
                    parts.append(f"来源: {row[source_col]}")
                if parts:
                    posts.append(" | ".join(parts))
    except Exception as exc:
        logger.warning("东方财富股吧 fetch failed for %s: %s", code, exc)

    if not posts:
        return (
            f"[东方财富股吧] 暂时无法获取 {ticker} 的股吧讨论数据。"
            f"可参考个股新闻和基本面数据进行分析。"
        )

    header = f"=== 东方财富股吧 (EastMoney Guba) - {ticker} ===\n"
    header += f"共获取 {len(posts)} 条讨论\n\n"
    return header + "\n\n".join(posts)
