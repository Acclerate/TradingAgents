"""Agent tools for Hong Kong stock data."""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_hk_stock_data(
    symbol: Annotated[str, "港股代码，如 00700(腾讯控股), 09988(阿里巴巴), 03690(美团), 01810(小米), 或指数如 HSI(恒生指数)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Retrieve Hong Kong stock real-time and historical price data.

    Data sourced from Tencent Finance. Provides forward-adjusted daily OHLCV
    data for the specified date range, falling back to real-time snapshot
    when historical data is unavailable.

    HK market rules:
    - Trading hours: 09:30-12:00 and 13:00-16:00 HKT (UTC+8), Mon-Fri
    - No price limit (unlike A-stocks' 10%/20% limits)
    - Currency: HKD
    - T+0 settlement (can buy and sell same day)
    """
    return route_to_vendor("get_hk_stock_data", symbol, start_date, end_date)
