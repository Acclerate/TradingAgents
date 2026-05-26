"""Agent tools for foreign exchange rate data."""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_forex_data() -> str:
    """Retrieve current foreign exchange rates from Bank of China.

    Returns buy/sell prices for major currencies (USD, EUR, GBP, HKD, JPY, etc.)
    including spot exchange (现汇) and cash (现钞) rates.
    Useful for understanding currency risks in cross-border investments
    and macroeconomic analysis.
    """
    return route_to_vendor("get_forex_data")
