"""Sina Finance real-time stock data source.

Direct HTTP access to hq.sinajs.cn for A-stocks, US stocks, domestic futures,
and international futures. No AKShare dependency.

Reference: LeekHub/leek-fund src/explorer/stockService.ts
"""

import logging
import re
from datetime import datetime
from typing import Optional

import requests

from .anti_scraping import random_headers, retry_with_backoff
from .encoding_utils import decode_gb18030

logger = logging.getLogger(__name__)

_HQ_URL = "https://hq.sinajs.cn/list="
_SUGGEST_URL = "http://suggest3.sinajs.cn/suggest/type={types}&key={keyword}"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _format_number(val, digits=2):
    """Format a numeric value to string with given decimal places."""
    try:
        return f"{float(val):.{digits}f}"
    except (ValueError, TypeError):
        return "--"


def _calc_change_percent(price, yestclose):
    """Calculate change percentage from current price and yesterday's close."""
    try:
        p, y = float(price), float(yestclose)
        if y == 0:
            return "0.00"
        pct = ((p - y) / y) * 100
        sign = "+" if pct >= 0 else "-"
        return f"{sign}{abs(pct):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def _calc_updown(price, yestclose):
    """Calculate price change amount."""
    try:
        return f"{float(price) - float(yestclose):.2f}"
    except (ValueError, TypeError):
        return "0.00"


# ---------------------------------------------------------------------------
# Response parsers by market type
# ---------------------------------------------------------------------------
def _parse_a_stock(code: str, params: list) -> dict:
    """Parse A-stock data from Sina response fields.

    Fields: name, open, yestclose, price, high, low, [buy1], [sell1],
            volume(8), amount(9), ...date(30), time(31)
    """
    name = params[0] if params else code
    open_ = params[1] if len(params) > 1 else "0"
    yestclose = params[2] if len(params) > 2 else "0"
    price = params[3] if len(params) > 3 else "0"
    high = params[4] if len(params) > 4 else "0"
    low = params[5] if len(params) > 5 else "0"

    # Price might be 0 during pre-market; fall back to buy1 or yestclose
    if float(price) == 0:
        buy1 = params[6] if len(params) > 6 else "0"
        price = buy1 if float(buy1) != 0 else yestclose

    volume = params[8] if len(params) > 8 else "0"
    amount = params[9] if len(params) > 9 else "0"
    date = params[30] if len(params) > 30 else ""
    time_ = params[31] if len(params) > 31 else ""

    return {
        "code": code,
        "name": name,
        "open": _format_number(open_),
        "yestclose": _format_number(yestclose),
        "price": _format_number(price),
        "high": _format_number(high),
        "low": _format_number(low),
        "volume": volume,
        "amount": amount,
        "time": f"{date} {time_}".strip(),
        "type": "a_stock",
        "updown": _calc_updown(price, yestclose),
        "percent": _calc_change_percent(price, yestclose),
    }


def _parse_us_stock(code: str, params: list) -> dict:
    """Parse US stock data from Sina response.

    Fields: 0=name, 1=price, 2=change%, 3=time, 4=change, 5=open, 6=high,
            7=low, 10=volume, 21=pre-market price, 22=pre-market change%,
            26=yestclose
    """
    name = params[0] if params else code
    price = params[1] if len(params) > 1 else "0"
    yestclose = params[26] if len(params) > 26 else "0"
    open_ = params[5] if len(params) > 5 else "0"
    high = params[6] if len(params) > 6 else "0"
    low = params[7] if len(params) > 7 else "0"
    volume = params[10] if len(params) > 10 else "0"
    time_ = params[3] if len(params) > 3 else ""
    pre_price = params[21] if len(params) > 21 else ""
    pre_pct = params[22] if len(params) > 22 else ""

    return {
        "code": code,
        "name": name,
        "open": _format_number(open_),
        "yestclose": _format_number(yestclose),
        "price": _format_number(price),
        "high": _format_number(high),
        "low": _format_number(low),
        "volume": volume,
        "amount": "",
        "time": time_,
        "type": "us_stock",
        "updown": _calc_updown(price, yestclose),
        "percent": _calc_change_percent(price, yestclose),
        "pre_market_price": _format_number(pre_price) if pre_price else "",
        "pre_market_pct": pre_pct,
    }


def _parse_domestic_future(code: str, params: list) -> dict:
    """Parse domestic futures (nf_ prefix).

    Commodity futures:
        0=name, 2=open, 3=high, 4=low, 5=yestclose(usually 0),
        8=price, 10=settlement, 15=volume, 16=open interest
    Stock index futures (IF/IH/IC/IM/T):
        0=open, 1=high, 2=low, 3=price, 4=volume,
        13=yestclose, 14=yest_settlement, 49=name
    """
    is_stock_index = any(
        pat in code for pat in ["nf_IC", "nf_IF", "nf_IH", "nf_IM", "nf_TF", "nf_TS", "nf_TL"]
    ) or re.match(r"nf_T\d+", code)

    if is_stock_index:
        name = params[49].rstrip('"') if len(params) > 49 else code
        open_ = params[0] if len(params) > 0 else "0"
        high = params[1] if len(params) > 1 else "0"
        low = params[2] if len(params) > 2 else "0"
        price = params[3] if len(params) > 3 else "0"
        volume = params[4] if len(params) > 4 else "0"
        yestclose = params[13] if len(params) > 13 else "0"
        yest_settlement = params[14] if len(params) > 14 else "0"
    else:
        name = params[0] if len(params) > 0 else code
        open_ = params[2] if len(params) > 2 else "0"
        high = params[3] if len(params) > 3 else "0"
        low = params[4] if len(params) > 4 else "0"
        price = params[8] if len(params) > 8 else "0"
        yestclose = params[10] if len(params) > 10 else "0"
        yest_settlement = yestclose
        volume = params[15] if len(params) > 15 else "0"

    # Use settlement price as yestclose for change calc (futures convention)
    ref_price = yestclose if float(yestclose) != 0 else yest_settlement

    return {
        "code": code,
        "name": name,
        "open": _format_number(open_),
        "yestclose": _format_number(ref_price),
        "yest_settlement": _format_number(yest_settlement),
        "price": _format_number(price),
        "high": _format_number(high),
        "low": _format_number(low),
        "volume": volume,
        "amount": "",
        "time": "",
        "type": "domestic_future",
        "updown": _calc_updown(price, ref_price),
        "percent": _calc_change_percent(price, ref_price),
    }


def _parse_intl_future(code: str, params: list) -> dict:
    """Parse international futures (hf_ prefix).

    Fields: 0=price, 2=buy1, 3=sell1, 4=high, 5=low,
            6=time, 7=yest_settlement, 8=open, 12=date, 13=name
    """
    price = params[0] if len(params) > 0 else "0"
    # Price anomaly check — fall back to buy1
    buy1 = params[2] if len(params) > 2 else "0"
    sell1 = params[3] if len(params) > 3 else "0"
    if float(price) > float(sell1) or float(price) < float(buy1):
        price = buy1

    name = params[13].rstrip('"') if len(params) > 13 else code
    high = params[4] if len(params) > 4 else "0"
    low = params[5] if len(params) > 5 else "0"
    time_ = params[6] if len(params) > 6 else ""
    yestclose = params[7] if len(params) > 7 else "0"
    open_ = params[8] if len(params) > 8 else "0"
    date = params[12] if len(params) > 12 else ""
    volume = params[14].rstrip('"') if len(params) > 14 else "0"

    return {
        "code": code,
        "name": name,
        "open": _format_number(open_),
        "yestclose": _format_number(yestclose),
        "price": _format_number(price),
        "high": _format_number(high),
        "low": _format_number(low),
        "volume": volume,
        "amount": "",
        "time": f"{date} {time_}".strip(),
        "type": "intl_future",
        "updown": _calc_updown(price, yestclose),
        "percent": _calc_change_percent(price, yestclose),
    }


# ---------------------------------------------------------------------------
# Main API functions
# ---------------------------------------------------------------------------
@retry_with_backoff(source="sina", retries=3, delay_base=1.0)
def sina_get_realtime(codes: list[str]) -> list[dict]:
    """Fetch real-time quotes from Sina Finance.

    Supports code prefixes:
        sh/sz/bj — A-stocks
        usr_      — US stocks
        nf_       — Domestic futures
        hf_       — International futures

    Args:
        codes: List of instrument codes (e.g. ["sh600036", "usr_nvda", "nf_IF0"]).

    Returns:
        List of dicts with standardized fields (code, name, price, etc.).
    """
    if not codes:
        return []

    # Sina uses $ instead of . in codes
    encoded = ",".join(c.replace(".", "$") for c in codes)
    url = f"{_HQ_URL}{encoded}"

    resp = requests.get(
        url,
        headers=random_headers("sina"),
        timeout=10,
    )
    resp.encoding = None  # we decode manually
    text = decode_gb18030(resp.content)

    if "FAILED" in text:
        if len(codes) == 1:
            logger.warning("Sina API rejected code: %s", codes[0])
            return []
        # Retry individually on batch failure
        results = []
        for code in codes:
            results.extend(sina_get_realtime([code]))
        return results

    results = []
    entries = text.strip().split('";\n')

    for entry in entries:
        if not entry.strip():
            continue

        # Parse: var hq_str_sh600036="..."
        match = re.match(r'var hq_str_(\S+)="(.*)"', entry)
        if not match:
            continue

        raw_code = match.group(1).replace("$", ".")
        data_str = match.group(2)

        if not data_str:
            results.append({"code": raw_code, "name": f"{raw_code} no data", "type": "nodata"})
            continue

        params = data_str.split(",")

        # Dispatch to appropriate parser
        if re.match(r"^(sh|sz|bj)", raw_code):
            # Check for all-zero data (unsupported stock)
            if (len(params) > 3 and
                float(params[3]) == 0 and
                float(params[4]) == 0 and
                float(params[5]) == 0 and
                    float(params[2]) == 0):
                results.append({
                    "code": raw_code,
                    "name": f"Unsupported stock {raw_code}",
                    "type": "nodata",
                })
            else:
                results.append(_parse_a_stock(raw_code, params))
        elif raw_code.startswith("usr_"):
            results.append(_parse_us_stock(raw_code, params))
        elif raw_code.startswith("nf_"):
            results.append(_parse_domestic_future(raw_code, params))
        elif raw_code.startswith("hf_"):
            results.append(_parse_intl_future(raw_code, params))
        else:
            results.append({"code": raw_code, "name": f"Unknown type: {raw_code}", "type": "nodata"})

    return results


@retry_with_backoff(source="sina", retries=2, delay_base=1.0)
def sina_search_future(keyword: str) -> list[dict]:
    """Search futures contracts via Sina suggest API.

    Args:
        keyword: Search keyword (e.g. "IF", "原油", "黄金").

    Returns:
        List of dicts with 'code', 'name', 'market' fields.
    """
    if not keyword:
        return []

    url = _SUGGEST_URL.format(types="85,86,88", keyword=keyword)
    resp = requests.get(
        url,
        headers=random_headers("sina"),
        timeout=10,
    )
    text = decode_gb18030(resp.content)

    # Response format: var suggestvalue="...;..."
    content = text[text.find('"') + 1: text.rfind('"')]
    if not content:
        return []

    results = []
    for item in content.split(";"):
        parts = item.split(",")
        if len(parts) < 5:
            continue

        market = parts[1]
        raw_code = parts[3].upper()
        name = parts[4]

        # Prefix based on market
        if market in ("85", "88"):
            code = f"nf_{raw_code}"
        elif market == "86":
            code = f"hf_{raw_code}"
        else:
            code = raw_code

        results.append({"code": code, "name": name, "market": market})

    return results


# ---------------------------------------------------------------------------
# Vendor-compatible wrapper functions for interface.py
# ---------------------------------------------------------------------------
def get_stock_data_sina(symbol: str, start_date: str, end_date: str) -> str:
    """Fetch real-time stock data via Sina (vendor-compatible interface).

    Note: Sina hq.sinajs.cn provides real-time snapshot, not historical ranges.
    Returns the latest available snapshot data.
    """
    from .sohu_history import sohu_get_hist_data

    # Try to get historical data from Sohu for the date range
    code = symbol.lower().replace(".", "")
    # Normalize: remove suffix for A-stocks
    for prefix in ("sh", "sz", "bj"):
        if code.startswith(prefix):
            sohu_code = code[2:]
            try:
                df = sohu_get_hist_data(sohu_code, start_date.replace("-", ""), end_date.replace("-", ""))
                if df is not None and not df.empty:
                    header = f"# Stock data for {symbol} from {start_date} to {end_date} (Sina+Sohu)\n"
                    header += f"# Total records: {len(df)}\n\n"
                    return header + df.to_csv(index=False)
            except Exception as exc:
                logger.debug("Sohu history fallback failed for %s: %s", symbol, exc)

    # Fall back to real-time snapshot
    try:
        results = sina_get_realtime([symbol.lower()])
        if results and results[0].get("type") != "nodata":
            r = results[0]
            lines = [
                f"# Real-time snapshot for {symbol} via Sina Finance",
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
        logger.warning("Sina real-time fetch failed for %s: %s", symbol, exc)

    return f"Error fetching stock data for {symbol} via Sina direct source"


def get_futures_data_sina(symbol: str, start_date: str, end_date: str) -> str:
    """Fetch futures data via Sina (vendor-compatible interface).

    Returns real-time snapshot for the futures contract.
    """
    try:
        results = sina_get_realtime([symbol.lower()])
        if results and results[0].get("type") not in ("nodata", ""):
            r = results[0]
            lines = [
                f"# Futures data for {symbol} via Sina Finance",
                f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                f"Name: {r.get('name', '')}",
                f"Price: {r.get('price', '')}",
                f"Change: {r.get('updown', '')} ({r.get('percent', '')}%)",
                f"Open: {r.get('open', '')}",
                f"High: {r.get('high', '')}",
                f"Low: {r.get('low', '')}",
                f"Settlement: {r.get('yest_settlement', r.get('yestclose', ''))}",
                f"Volume: {r.get('volume', '')}",
                f"Time: {r.get('time', '')}",
            ]
            return "\n".join(lines)
    except Exception as exc:
        logger.warning("Sina futures fetch failed for %s: %s", symbol, exc)

    return f"Error fetching futures data for {symbol} via Sina direct source"
