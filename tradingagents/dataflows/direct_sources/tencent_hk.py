"""Tencent Finance data source for Hong Kong stocks.

Direct HTTP access to qt.gtimg.cn for HK stock real-time data and
proxy.finance.qq.com for stock search.

Reference: LeekHub/leek-fund src/shared/tencentStock.ts
"""

import json
import logging
from datetime import datetime
from typing import Optional

import requests

from .anti_scraping import random_headers, retry_with_backoff
from .encoding_utils import decode_gbk

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://proxy.finance.qq.com/ifzqgtimg/appstock/smartbox/search/get"
_QUOTE_URL = "https://qt.gtimg.cn/q="


def _format_number(val, digits=2):
    try:
        return f"{float(val):.{digits}f}"
    except (ValueError, TypeError):
        return "--"


# ---------------------------------------------------------------------------
# Stock search
# ---------------------------------------------------------------------------
@retry_with_backoff(source="tencent", retries=2, delay_base=1.0)
def tencent_search_stock(keyword: str) -> list[dict]:
    """Search stocks via Tencent Finance.

    Returns results for A-stocks, HK stocks, and US stocks.

    Args:
        keyword: Search keyword (name or code).

    Returns:
        List of dicts with 'code', 'name', 'market' fields.
        market values: 'sh', 'sz', 'bj' (A-stock), 'hk' (HK), 'us' (US).
    """
    if not keyword:
        return []

    resp = requests.get(
        _SEARCH_URL,
        params={"q": keyword},
        headers=random_headers("tencent"),
        timeout=10,
    )

    stock_arr = resp.json().get("data", {}).get("stock", [])
    results = []
    for item in stock_arr:
        if len(item) < 4:
            continue
        results.append({
            "code": item[1].lower(),
            "name": item[2],
            "market": item[0],
            "abbreviation": item[3],
        })
    return results


# ---------------------------------------------------------------------------
# HK stock real-time data
# ---------------------------------------------------------------------------
@retry_with_backoff(source="tencent", retries=3, delay_base=1.0)
def tencent_get_hk_stocks(codes: list[str]) -> list[dict]:
    """Fetch real-time quotes for HK stocks via Tencent Finance.

    Args:
        codes: List of HK stock codes (e.g. ["hk00700", "hkHSI"]).

    Returns:
        List of dicts with standardized fields.
    """
    if not codes:
        return []

    # Tencent requires 'r_' prefix for each code
    query_codes = ",".join(f"r_{code}" for code in codes)
    url = f"{_QUOTE_URL}{query_codes}&fmt=json"

    resp = requests.get(
        url,
        headers=random_headers("tencent"),
        timeout=10,
    )

    # Decode GBK response
    text = decode_gbk(resp.content)
    data = json.loads(text)

    results = []
    for code in codes:
        normalized_code = code.lower()
        r_key = f"r_{code}"
        item = data.get(r_key)

        if not item:
            results.append({"code": normalized_code, "name": "NODATA", "type": "nodata"})
            continue

        # Tencent HK stock field indices (from leek-fund):
        # 1=name, 3=price, 4=yestclose, 5=open, 33=high, 34=low,
        # 36=volume, 37=amount, 30=time
        name = item[1] if len(item) > 1 else code
        price = item[3] if len(item) > 3 else "0"
        yestclose = item[4] if len(item) > 4 else "0"
        open_ = item[5] if len(item) > 5 else "0"
        high = item[33] if len(item) > 33 else "0"
        low = item[34] if len(item) > 34 else "0"
        volume = item[36] if len(item) > 36 else "0"
        amount = item[37] if len(item) > 37 else "0"
        time_ = item[30] if len(item) > 30 else ""

        try:
            updown = f"{float(price) - float(yestclose):.2f}"
        except (ValueError, TypeError):
            updown = "0.00"

        try:
            pct = ((float(price) - float(yestclose)) / float(yestclose)) * 100
            sign = "+" if pct >= 0 else "-"
            percent = f"{sign}{abs(pct):.2f}"
        except (ValueError, TypeError, ZeroDivisionError):
            percent = "0.00"

        results.append({
            "code": normalized_code,
            "name": name,
            "open": _format_number(open_),
            "yestclose": _format_number(yestclose),
            "price": _format_number(price),
            "high": _format_number(high),
            "low": _format_number(low),
            "volume": volume,
            "amount": amount,
            "time": str(time_),
            "type": "hk_stock",
            "updown": updown,
            "percent": percent,
        })

    return results


# ---------------------------------------------------------------------------
# Vendor-compatible wrapper
# ---------------------------------------------------------------------------
def get_hk_stock_data_tencent(symbol: str, start_date: str, end_date: str) -> str:
    """Fetch HK stock data via Tencent (vendor-compatible interface).

    Returns historical data if available, otherwise real-time snapshot.
    """
    from .tencent_hk_history import tencent_get_hk_hist

    # Try historical data first
    code = symbol.lower().replace(".", "")
    if not code.startswith("hk"):
        code = f"hk{code}"

    try:
        df = tencent_get_hk_hist(code, start_date, end_date)
        if df is not None and not df.empty:
            header = f"# HK Stock data for {symbol} from {start_date} to {end_date}\n"
            header += f"# Source: Tencent Finance (前复权)\n"
            header += f"# Total records: {len(df)}\n\n"
            return header + df.to_csv(index=False)
    except Exception as exc:
        logger.debug("Tencent HK history failed for %s: %s", symbol, exc)

    # Fall back to real-time snapshot
    try:
        results = tencent_get_hk_stocks([code])
        if results and results[0].get("type") != "nodata":
            r = results[0]
            lines = [
                f"# HK Stock real-time snapshot for {symbol}",
                f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                f"Name: {r.get('name', '')}",
                f"Price: {r.get('price', '')}",
                f"Change: {r.get('updown', '')} ({r.get('percent', '')}%)",
                f"Open: {r.get('open', '')}",
                f"High: {r.get('high', '')}",
                f"Low: {r.get('low', '')}",
                f"Volume: {r.get('volume', '')}",
                f"Time: {r.get('time', '')}",
            ]
            return "\n".join(lines)
    except Exception as exc:
        logger.warning("Tencent HK real-time fetch failed for %s: %s", symbol, exc)

    return f"Error fetching HK stock data for {symbol} via Tencent direct source"
