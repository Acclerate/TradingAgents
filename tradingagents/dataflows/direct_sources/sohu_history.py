"""Sohu Finance historical stock data source (A股 backup).

Direct HTTP access to q.stock.sohu.com for forward-adjusted daily OHLCV.
Used as a backup when AKShare's Tencent/EastMoney/Sina endpoints fail.

Reference: LeekHub/leek-fund src/shared/aiStockHistoryData.ts
"""

import logging
import re
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from .anti_scraping import random_headers, retry_with_backoff

logger = logging.getLogger(__name__)

_SOHU_URL = "http://q.stock.sohu.com/hisHq"


@retry_with_backoff(retries=2, delay_base=2.0)
def sohu_get_hist_data(
    code: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Fetch forward-adjusted (前复权) daily OHLCV data from Sohu Finance.

    Args:
        code: 6-digit stock code without prefix (e.g. "000001", "600036").
        start: Start date as YYYYMMDD string.
        end: End date as YYYYMMDD string.

    Returns:
        DataFrame with Date, Open, Close, High, Low, Volume, Turnover columns.
    """
    sohu_code = f"cn_{code}"
    params = {
        "code": sohu_code,
        "start": start,
        "end": end,
        "stat": "1",
        "order": "D",
        "period": "d",
        "callback": "historySearchHandler",
        "rt": "jsonp",
    }

    resp = requests.get(
        _SOHU_URL,
        params=params,
        headers=random_headers("sohu"),
        timeout=15,
    )

    text = resp.text

    # Extract JSON from JSONP: historySearchHandler({...})
    match = re.search(r"historySearchHandler\((.+?)\);?$", text, re.DOTALL)
    if not match:
        logger.debug("Sohu returned non-JSONP response for %s", code)
        return pd.DataFrame()

    import json
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.debug("Sohu JSON parse failed for %s", code)
        return pd.DataFrame()

    hq_list = data.get("hq", [])
    if not hq_list:
        return pd.DataFrame()

    # Sohu format: each entry is [date, open, close, change_pct, change_amt,
    #                             volume, turnover, turnover_rate]
    rows = []
    for entry in hq_list:
        if len(entry) < 7:
            continue
        try:
            rows.append({
                "Date": entry[0],
                "Open": float(entry[1]),
                "Close": float(entry[2]),
                "High": float(entry[6]) if len(entry) > 6 else float(entry[1]),
                "Low": float(entry[7]) if len(entry) > 7 else float(entry[1]),
                "Volume": float(entry[5]),
                "Turnover": float(entry[4]) if len(entry) > 4 else 0,
            })
        except (ValueError, IndexError):
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Sohu returns newest first — reverse to chronological order
    df = df.iloc[::-1].reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"])
    return df
