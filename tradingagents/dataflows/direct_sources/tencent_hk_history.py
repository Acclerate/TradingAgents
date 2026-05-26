"""Tencent Finance historical data for Hong Kong stocks.

Direct HTTP access to web.ifzq.gtimg.cn for forward-adjusted daily OHLCV.

Reference: LeekHub/leek-fund src/shared/aiStockHistoryData.ts
"""

import logging
from typing import Optional
from urllib.parse import quote

import pandas as pd
import requests

from .anti_scraping import random_headers, retry_with_backoff

logger = logging.getLogger(__name__)

_BASE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def _normalize_symbol(stock_id: str) -> Optional[str]:
    """Normalize an HK stock ID to Tencent fqkline format.

    Numeric codes: pad to 5 digits lowercase → hk00700
    Index codes: uppercase → hkHSI
    """
    if not stock_id or len(stock_id) < 3:
        return None

    lower = stock_id.lower()
    suffix = stock_id[2:] if lower.startswith("hk") else stock_id

    if suffix.isdigit():
        return f"hk{suffix.zfill(5)}"
    if suffix:
        return f"hk{suffix.upper()}"
    return None


def _range_to_max_bars(range_label: str) -> int:
    """Convert a range label to maximum bars to request."""
    return {
        "1w": 15,
        "1m": 35,
        "3m": 100,
        "6m": 160,
        "1y": 320,
    }.get(range_label, 100)


@retry_with_backoff(source="tencent", retries=2, delay_base=1.0)
def tencent_get_hk_hist(
    symbol: str,
    start: str,
    end: str,
    max_bars: int = 320,
) -> pd.DataFrame:
    """Fetch forward-adjusted daily OHLCV for an HK stock via Tencent.

    Args:
        symbol: HK stock ID (e.g. "hk00700", "hkHSI", "00700").
        start: Start date as YYYY-MM-DD.
        end: End date as YYYY-MM-DD.
        max_bars: Maximum number of bars to return.

    Returns:
        DataFrame with Date, Open, Close, High, Low, Volume columns.
    """
    sym = _normalize_symbol(symbol)
    if not sym:
        return pd.DataFrame()

    param_str = f"{sym},day,{start},{end},{max_bars},qfq"
    url = f"{_BASE_URL}?param={quote(param_str)}"

    resp = requests.get(url, headers=random_headers("tencent"), timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # Navigate the nested response structure
    stock_data = data.get("data", {})
    day_list = None
    for key in (sym, sym.upper(), sym.lower()):
        entry = stock_data.get(key)
        if entry and "day" in entry:
            day_list = entry["day"]
            break

    if not day_list:
        # Try the "qfqday" key as fallback
        for key in (sym, sym.upper(), sym.lower()):
            entry = stock_data.get(key)
            if entry and "qfqday" in entry:
                day_list = entry["qfqday"]
                break

    if not day_list:
        return pd.DataFrame()

    # Each entry: [date, open, close, high, low, volume]
    rows = []
    for entry in day_list:
        if not isinstance(entry, (list, tuple)) or len(entry) < 6:
            continue
        try:
            rows.append({
                "Date": entry[0],
                "Open": float(entry[1]),
                "Close": float(entry[2]),
                "High": float(entry[3]),
                "Low": float(entry[4]),
                "Volume": float(entry[5]),
            })
        except (ValueError, IndexError):
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df
