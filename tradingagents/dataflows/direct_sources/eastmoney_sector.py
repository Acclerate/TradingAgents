"""East Money sector capital flow data source.

Direct HTTP access to data.eastmoney.com for industry, concept, and
regional capital flow data.

Reference: LeekHub/leek-fund src/service/eastmoney.ts
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from .anti_scraping import random_headers, retry_with_backoff

logger = logging.getLogger(__name__)

_BASE_URL = "https://data.eastmoney.com/dataapi/bkzj/getbkzj"

# Sector type codes
_SECTOR_TYPES = {
    "region": "m%3A90%2Bt%3A1",
    "industry": "m%3A90%2Bt%3A2",
    "concept": "m%3A90%2Bt%3A3",
}

# Common sectors to exclude from concept list (too generic)
_EXCLUDE_GN = [
    "深成", "昨日涨停", "沪股通", "MSCI中国", "央国企改革",
    "标准普尔", "创业板综", "富时罗素", "深股通", "融资融券",
    "S300", "沪深",
]


def _convert_to_yi(num) -> float:
    """Convert a numeric value to 亿元 (hundred millions)."""
    try:
        return round(float(num) / 1e8, 2)
    except (ValueError, TypeError):
        return 0.0


@retry_with_backoff(source="eastmoney", retries=3, delay_base=2.0)
def _fetch_sector_data(sector_type: str) -> dict:
    """Fetch raw sector capital flow data from East Money.

    Args:
        sector_type: One of 'region', 'industry', 'concept'.

    Returns:
        Raw JSON response data.
    """
    code = _SECTOR_TYPES.get(sector_type)
    if not code:
        raise ValueError(f"Invalid sector_type: {sector_type}. Use: {list(_SECTOR_TYPES.keys())}")

    url = f"{_BASE_URL}?key=f174&code={code}"
    resp = requests.get(url, headers=random_headers("eastmoney"), timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_region_capital_flow() -> pd.DataFrame:
    """Fetch regional capital flow data (区域资金流).

    Returns:
        DataFrame with columns: name, net_inflow_yi, ...
    """
    return _to_dataframe(_fetch_sector_data("region"))


def get_industry_capital_flow() -> pd.DataFrame:
    """Fetch industry capital flow data (行业资金流).

    Returns:
        DataFrame sorted by net inflow.
    """
    return _to_dataframe(_fetch_sector_data("industry"), exclude=_EXCLUDE_GN)


def get_concept_capital_flow() -> pd.DataFrame:
    """Fetch concept capital flow data (概念资金流).

    Returns:
        DataFrame sorted by net inflow, excluding generic concepts.
    """
    return _to_dataframe(_fetch_sector_data("concept"), exclude=_EXCLUDE_GN)


def _to_dataframe(raw_data: dict, exclude: list = None) -> pd.DataFrame:
    """Convert raw East Money response to DataFrame."""
    diff = raw_data.get("data", {}).get("diff", [])
    if not diff:
        return pd.DataFrame()

    rows = []
    for item in diff:
        name = item.get("f14", "")
        if exclude and any(ex in name for ex in exclude):
            continue
        net_inflow = item.get("f174", 0)
        rows.append({
            "name": name,
            "net_inflow": net_inflow,
            "net_inflow_yi": _convert_to_yi(net_inflow),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("net_inflow", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Aggregate formatted output (vendor-compatible)
# ---------------------------------------------------------------------------
def get_sector_capital_flow(sector_type: str = "industry") -> str:
    """Get formatted sector capital flow data.

    Args:
        sector_type: 'industry' (行业), 'concept' (概念), or 'region' (区域).

    Returns:
        Formatted text suitable for agent consumption.
    """
    type_names = {"industry": "行业", "concept": "概念", "region": "区域"}
    type_name = type_names.get(sector_type, sector_type)

    try:
        df = _to_dataframe(_fetch_sector_data(sector_type), exclude=_EXCLUDE_GN if sector_type == "concept" else None)
        if df.empty:
            return f"No {type_name} capital flow data available"

        # Top 10 inflows and outflows
        top_in = df.head(10)
        top_out = df.tail(10).iloc[::-1]

        lines = [
            f"# {type_name}板块资金流向 (Sector Capital Flow)",
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"## Top 10 净流入 ({type_name})",
            "板块名称 | 主力净流入(亿)",
            "--- | ---",
        ]
        for _, row in top_in.iterrows():
            lines.append(f"{row['name']} | {row['net_inflow_yi']}")

        lines.extend([
            f"\n## Top 10 净流出 ({type_name})",
            "板块名称 | 主力净流出(亿)",
            "--- | ---",
        ])
        for _, row in top_out.iterrows():
            lines.append(f"{row['name']} | {row['net_inflow_yi']}")

        return "\n".join(lines)

    except Exception as exc:
        return f"Error fetching {type_name} capital flow: {exc}"
