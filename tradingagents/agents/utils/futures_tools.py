"""Agent tools for futures data analysis."""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_futures_data(
    symbol: Annotated[str, "期货合约代码，如 nf_IF0(沪深300主力), nf_IH0(上证50主力), nf_IC0(中证500主力), hf_OIL(WTI原油), hf_XAU(伦敦金), hf_CHA50CFD(富时中国A50)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Retrieve futures real-time and historical price data.

    Supports domestic futures (nf_ prefix) and international futures (hf_ prefix).
    Domestic futures include stock index futures (IF, IH, IC, IM), treasury bonds,
    and commodities. International futures include WTI oil, gold, silver, etc.

    Note: Futures use settlement price (结算价) as the reference for change%,
    which differs from stocks that use previous close.
    """
    return route_to_vendor("get_futures_data", symbol, start_date, end_date)
