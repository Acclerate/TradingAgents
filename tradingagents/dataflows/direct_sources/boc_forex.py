"""Bank of China forex exchange rates data source.

Scrapes the official BOC forex page for current exchange rates.

Reference: LeekHub/leek-fund src/explorer/forexService.ts (cheerio → BeautifulSoup)
"""

import logging
from datetime import datetime

import pandas as pd
import requests

from .anti_scraping import random_headers, retry_with_backoff

logger = logging.getLogger(__name__)

_BOC_URL = "https://www.boc.cn/sourcedb/whpj/index.html"


@retry_with_backoff(retries=2, delay_base=2.0)
def get_boc_forex_rates() -> pd.DataFrame:
    """Fetch forex exchange rates from Bank of China.

    Returns:
        DataFrame with columns: name, spot_buy, cash_buy, spot_sell,
        cash_sell, conversion_price, publish_datetime.
    """
    resp = requests.get(_BOC_URL, headers=random_headers("boc"), timeout=15)
    resp.encoding = "utf-8"

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 is required for BOC forex data. Install with: pip install beautifulsoup4")
        return pd.DataFrame()

    soup = BeautifulSoup(resp.text, "html.parser")

    # BOC page has tables; the second table contains forex data
    tables = soup.find_all("table")
    if len(tables) < 2:
        logger.warning("BOC forex page structure changed — no data table found")
        return pd.DataFrame()

    rows = []
    for tr in tables[1].find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue

        name = tds[0].get_text(strip=True)
        if not name:
            continue

        def _parse_float(text):
            try:
                return float(text.strip())
            except (ValueError, AttributeError):
                return None

        rows.append({
            "name": name,
            "spot_buy": _parse_float(tds[1].get_text()),
            "cash_buy": _parse_float(tds[2].get_text()),
            "spot_sell": _parse_float(tds[3].get_text()),
            "cash_sell": _parse_float(tds[4].get_text()),
            "conversion_price": _parse_float(tds[5].get_text()),
            "publish_datetime": tds[6].get_text(strip=True) if len(tds) > 6 else "",
        })

    return pd.DataFrame(rows)


def get_forex_summary() -> str:
    """Get formatted forex summary for agent consumption."""
    df = get_boc_forex_rates()
    if df.empty:
        return "No forex data available from Bank of China"

    # Priority currencies
    priority = ["美元", "欧元", "英镑", "港币", "日元", "韩元", "卢布"]
    df["_sort"] = df["name"].apply(lambda x: priority.index(x) if x in priority else 999)
    df = df.sort_values("_sort").drop(columns=["_sort"])

    lines = [
        f"# 中国银行外汇牌价 (BOC Forex Rates)",
        f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Total currencies: {len(df)}\n",
        "币种 | 现汇买入 | 现钞买入 | 现汇卖出 | 现钞卖出 | 中间价",
        "--- | --- | --- | --- | --- | ---",
    ]

    for _, row in df.iterrows():
        lines.append(
            f"{row['name']} | {row.get('spot_buy', '')} | {row.get('cash_buy', '')} | "
            f"{row.get('spot_sell', '')} | {row.get('cash_sell', '')} | {row.get('conversion_price', '')}"
        )

    return "\n".join(lines)


def get_forex_data_boc() -> str:
    """Vendor-compatible wrapper for BOC forex data."""
    return get_forex_summary()
