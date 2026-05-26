"""AKShare-based news data source for Chinese A-stocks.

Provides ``get_news_akshare`` (per-ticker) and ``get_global_news_akshare``
(macro / market-wide) compatible with the VENDOR_METHODS interface.

Data sources (per-ticker news):
  1. 东方财富 (East Money) via AKShare — stock_news_em
  2. 新浪财经 (Sina Finance) via direct HTTP — finance.sina.com.cn
  3. 同花顺 (THS) via AKShare — stock_news_sh

Global/macro news:
  1. CCTV 财经新闻 via AKShare
  2. 东方财富 沪深300 news
  3. 新浪财经 macro headlines
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd
import requests

from .ticker_utils import normalize_a_stock_ticker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-ticker news — Source 1: East Money via AKShare
# ---------------------------------------------------------------------------
def _news_eastmoney(code: str, limit: int = 20) -> list:
    """Fetch per-ticker news from 东方财富 via AKShare."""
    items = []
    try:
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return items
        title_col = next((c for c in df.columns if "标题" in str(c) or "title" in str(c).lower()), None)
        content_col = next((c for c in df.columns if "内容" in str(c) or "content" in str(c).lower()), None)
        source_col = next((c for c in df.columns if "来源" in str(c) or "source" in str(c).lower()), None)
        date_col = next((c for c in df.columns if "时间" in str(c) or "日期" in str(c) or "date" in str(c).lower()), None)

        for _, row in df.head(limit).iterrows():
            parts = []
            if title_col and pd.notna(row.get(title_col)):
                parts.append(f"Title: {row[title_col]}")
            if content_col and pd.notna(row.get(content_col)):
                parts.append(f"Content: {str(row[content_col])[:500]}")
            if source_col and pd.notna(row.get(source_col)):
                parts.append(f"Source: {row[source_col]}")
            if date_col and pd.notna(row.get(date_col)):
                parts.append(f"Date: {row[date_col]}")
            if parts:
                items.append(("[东方财富]", "\n".join(parts)))
    except Exception as exc:
        logger.debug("EM news failed for %s: %s", code, exc)
    return items


# ---------------------------------------------------------------------------
# Per-ticker news — Source 2: Sina Finance via HTTP
# ---------------------------------------------------------------------------
def _news_sina(code: str, limit: int = 15) -> list:
    """Fetch per-ticker news from 新浪财经 via HTTP API."""
    items = []
    try:
        # Sina stock news API
        url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{code}.phtml"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn",
        })
        resp.encoding = "gbk"
        import re
        # Parse news titles from HTML
        titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]{10,})</a>', resp.text)
        for href, title in titles[:limit]:
            title = title.strip()
            if len(title) > 5:
                items.append(("[新浪财经]", f"Title: {title}\nURL: {href}"))
    except Exception as exc:
        logger.debug("Sina news failed for %s: %s", code, exc)
    return items


# ---------------------------------------------------------------------------
# Per-ticker news — Source 3: THS via AKShare
# ---------------------------------------------------------------------------
def _news_ths(code: str, limit: int = 10) -> list:
    """Fetch per-ticker news from 同花顺 via AKShare."""
    items = []
    try:
        df = ak.stock_news_sh(symbol=code)
        if df is None or df.empty:
            return items
        title_col = next((c for c in df.columns if "标题" in str(c) or "title" in str(c).lower() or "新闻标题" in str(c)), None)
        content_col = next((c for c in df.columns if "内容" in str(c) or "content" in str(c).lower() or "新闻内容" in str(c)), None)
        date_col = next((c for c in df.columns if "时间" in str(c) or "date" in str(c).lower() or "发布时间" in str(c)), None)

        for _, row in df.head(limit).iterrows():
            parts = []
            if title_col and pd.notna(row.get(title_col)):
                parts.append(f"Title: {row[title_col]}")
            if content_col and pd.notna(row.get(content_col)):
                parts.append(f"Content: {str(row[content_col])[:500]}")
            if date_col and pd.notna(row.get(date_col)):
                parts.append(f"Date: {row[date_col]}")
            if parts:
                items.append(("[同花顺]", "\n".join(parts)))
    except Exception as exc:
        logger.debug("THS news failed for %s: %s", code, exc)
    return items


def get_news_akshare(
    ticker: str, start_date: str, end_date: str
) -> str:
    """Fetch stock-specific news from multiple sources (EM → Sina → THS → 选股宝)."""
    code = normalize_a_stock_ticker(ticker)

    all_items = []
    # Source 1: East Money
    all_items.extend(_news_eastmoney(code))
    # Source 2: Sina Finance
    all_items.extend(_news_sina(code))
    # Source 3: THS
    all_items.extend(_news_ths(code))
    # Source 4: Xuangubao flash news (backup)
    if len(all_items) < 5:
        try:
            from .direct_sources.xuangubao import get_xuangubao_flash_news
            flash = get_xuangubao_flash_news(limit=10)
            for item in flash[:5]:
                all_items.append(("[选股宝]", f"Title: {item.get('title', '')}\n{item.get('summary', '')}"))
        except Exception as exc:
            logger.debug("Xuangubao backup news failed: %s", exc)

    if not all_items:
        return f"No news found for A-stock '{ticker}'"

    # Filter by date range if possible
    filtered = []
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    for source_tag, text in all_items:
        # Simple date filter: check if any date-like string falls in range
        import re
        dates_found = re.findall(r"20\d{2}[-/]\d{2}[-/]\d{2}", text)
        if dates_found:
            try:
                d = pd.to_datetime(dates_found[0])
                if start_dt <= d <= end_dt:
                    filtered.append((source_tag, text))
                    continue
            except Exception:
                pass
        # If no date found or out of range, include anyway (recent news)
        filtered.append((source_tag, text))

    lines = [f"{source_tag}\n{text}" for source_tag, text in filtered[:25]]

    header = f"# News for {ticker} from {start_date} to {end_date}\n"
    header += f"# Total articles: {len(lines)} (from {len(set(s for s,_ in all_items))} sources)\n\n"
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

    # --- Sina Finance macro headlines ---
    if len(all_items) < limit:
        try:
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                "pageid": "153", "lid": "2516", "num": limit,
                "versionNumber": "1.2.4",
            }
            resp = requests.get(url, params=params, timeout=10)
            j = resp.json()
            data = j.get("result", {}).get("data", [])
            for item in data[:limit - len(all_items)]:
                title = item.get("title", "")
                ctime = item.get("ctime", "")
                if title:
                    all_items.append(f"[新浪财经] {ctime} - {title}")
        except Exception as exc:
            logger.debug("Sina macro news failed: %s", exc)

    # --- Xuangubao flash news (backup) ---
    if len(all_items) < limit:
        try:
            from .direct_sources.xuangubao import get_xuangubao_flash_news
            flash = get_xuangubao_flash_news(limit=limit - len(all_items))
            for item in flash[:limit - len(all_items)]:
                title = item.get("title", "")
                ts = item.get("created_at", 0)
                ts_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
                if title:
                    all_items.append(f"[选股宝] {ts_str} - {title}")
        except Exception as exc:
            logger.debug("Xuangubao macro news failed: %s", exc)

    if not all_items:
        return f"No macro news available for A-stock market around {curr_date}"

    header = f"# A-Stock Macro News (lookback {lookback} days from {curr_date})\n"
    header += f"# Total articles: {len(all_items)}\n\n"
    return header + "\n\n---\n\n".join(all_items)
