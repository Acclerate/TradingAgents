"""AKShare-based news data source for Chinese A-stocks.

Provides ``get_news_akshare`` (per-ticker) and ``get_global_news_akshare``
(macro / market-wide) compatible with the VENDOR_METHODS interface.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd

from .ticker_utils import normalize_a_stock_ticker

logger = logging.getLogger(__name__)


def get_news_akshare(
    ticker: str, start_date: str, end_date: str
) -> str:
    """Fetch stock-specific news from 东方财富 via AKShare."""
    code = normalize_a_stock_ticker(ticker)
    try:
        df = ak.stock_news_em(symbol=code)
    except Exception as exc:
        return f"Error fetching news for {ticker} via AKShare: {exc}"

    if df is None or df.empty:
        return f"No news found for A-stock '{ticker}'"

    # Filter by date range if date column exists
    date_col = None
    for c in df.columns:
        if "时间" in str(c) or "日期" in str(c) or "date" in str(c).lower():
            date_col = c
            break

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]

    # Format output
    lines = []
    title_col = None
    content_col = None
    source_col = None
    for c in df.columns:
        if "标题" in str(c) or "title" in str(c).lower():
            title_col = c
        elif "内容" in str(c) or "content" in str(c).lower():
            content_col = c
        elif "来源" in str(c) or "source" in str(c).lower():
            source_col = c

    for _, row in df.head(20).iterrows():
        parts = []
        if title_col and pd.notna(row.get(title_col)):
            parts.append(f"Title: {row[title_col]}")
        if content_col and pd.notna(row.get(content_col)):
            content = str(row[content_col])[:500]
            parts.append(f"Content: {content}")
        if source_col and pd.notna(row.get(source_col)):
            parts.append(f"Source: {row[source_col]}")
        if date_col and pd.notna(row.get(date_col)):
            parts.append(f"Date: {row[date_col]}")
        if parts:
            lines.append("\n".join(parts))

    if not lines:
        # Fallback: dump raw CSV
        return f"# News for {ticker}\n\n" + df.to_csv(index=False)

    header = f"# News for {ticker} from {start_date} to {end_date}\n"
    header += f"# Total articles: {len(lines)}\n\n"
    return header + "\n\n---\n\n".join(lines)


def get_global_news_akshare(
    curr_date: str,
    look_back_days: Optional[int] = None,
    limit: Optional[int] = None,
) -> str:
    """Fetch macro / market-wide news for A-stock context.

    Uses CCTV financial news via AKShare as the primary source.
    """
    curr_dt = pd.to_datetime(curr_date)
    lookback = look_back_days or 7
    limit = limit or 10
    start_dt = curr_dt - timedelta(days=lookback)

    all_items = []

    # --- CCTV financial news ---
    try:
        df = ak.news_cctv(date=curr_dt.strftime("%Y%m%d"))
        if df is not None and not df.empty:
            for _, row in df.head(limit).iterrows():
                title = row.get("title", "")
                content = str(row.get("content", ""))[:500]
                date_val = row.get("date", "")
                all_items.append(f"[CCTV财经] {date_val} - {title}\n{content}")
    except Exception as exc:
        logger.warning("CCTV news fetch failed: %s", exc)

    # --- Major market news via stock_news_em for CSI 300 constituent ---
    if len(all_items) < limit:
        try:
            df = ak.stock_news_em(symbol="000300")
            if df is not None and not df.empty:
                for _, row in df.head(limit - len(all_items)).iterrows():
                    title_col = next(
                        (c for c in df.columns if "标题" in str(c)), None
                    )
                    content_col = next(
                        (c for c in df.columns if "内容" in str(c) or "content" in str(c).lower()), None
                    )
                    title = row[title_col] if title_col else ""
                    content = str(row[content_col])[:500] if content_col else ""
                    all_items.append(f"[市场新闻] {title}\n{content}")
        except Exception as exc:
            logger.warning("Market news fetch failed: %s", exc)

    if not all_items:
        return f"No macro news available for A-stock market around {curr_date}"

    header = f"# A-Stock Macro News (lookback {lookback} days from {curr_date})\n"
    header += f"# Total articles: {len(all_items)}\n\n"
    return header + "\n\n---\n\n".join(all_items)
