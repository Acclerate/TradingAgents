from typing import Annotated

# Import from vendor-specific modules
from .y_finance import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_fundamentals as get_yfinance_fundamentals,
    get_balance_sheet as get_yfinance_balance_sheet,
    get_cashflow as get_yfinance_cashflow,
    get_income_statement as get_yfinance_income_statement,
    get_insider_transactions as get_yfinance_insider_transactions,
)
from .yfinance_news import get_news_yfinance, get_global_news_yfinance
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_fundamentals as get_alpha_vantage_fundamentals,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
    get_news as get_alpha_vantage_news,
    get_global_news as get_alpha_vantage_global_news,
)
from .alpha_vantage_common import AlphaVantageRateLimitError
from .akshare_data import (
    get_stock_data_akshare,
    get_indicators_akshare,
    get_fundamentals_akshare,
    get_balance_sheet_akshare,
    get_cashflow_akshare,
    get_income_statement_akshare,
    get_insider_transactions_akshare,
    get_fund_flow_akshare,
)
from .akshare_news import get_news_akshare, get_global_news_akshare
from .ticker_utils import is_a_stock_ticker

# Direct source imports (backup vendors bypassing AKShare/yfinance)
from .direct_sources.sina_stock import get_stock_data_sina, get_futures_data_sina
from .direct_sources.tencent_hk import get_hk_stock_data_tencent
from .direct_sources.eastmoney_sector import get_sector_capital_flow
from .direct_sources.boc_forex import get_forex_data_boc

# Configuration and routing logic
from .config import get_config

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News and insider data",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ]
    },
    "fund_flow": {
        "description": "Capital flow / fund flow data",
        "tools": [
            "get_fund_flow"
        ]
    },
    "hk_stock_data": {
        "description": "Hong Kong stock price data",
        "tools": [
            "get_hk_stock_data"
        ]
    },
    "futures_data": {
        "description": "Futures price data (domestic and international)",
        "tools": [
            "get_futures_data"
        ]
    },
    "forex_data": {
        "description": "Foreign exchange rates",
        "tools": [
            "get_forex_data"
        ]
    },
    "sector_flow": {
        "description": "Sector-level capital flow (industry/concept/region)",
        "tools": [
            "get_sector_flow"
        ]
    }
}

VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
    "akshare",
    "sina_direct",
    "tencent_direct",
    "eastmoney_direct",
    "boc_direct",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
        "akshare": get_stock_data_akshare,
        "sina_direct": get_stock_data_sina,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
        "akshare": get_indicators_akshare,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "yfinance": get_yfinance_fundamentals,
        "akshare": get_fundamentals_akshare,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
        "akshare": get_balance_sheet_akshare,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
        "akshare": get_cashflow_akshare,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
        "akshare": get_income_statement_akshare,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
        "akshare": get_news_akshare,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
        "akshare": get_global_news_akshare,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
        "akshare": get_insider_transactions_akshare,
    },
    # Fund flow (资金流向) — A-stock capital flow data
    "get_fund_flow": {
        "akshare": get_fund_flow_akshare,
    },
    # HK stock data — Tencent Finance direct
    "get_hk_stock_data": {
        "tencent_direct": get_hk_stock_data_tencent,
    },
    # Futures data — Sina Finance direct
    "get_futures_data": {
        "sina_direct": get_futures_data_sina,
    },
    # Forex data — Bank of China
    "get_forex_data": {
        "boc_direct": get_forex_data_boc,
    },
    # Sector capital flow — East Money direct
    "get_sector_flow": {
        "eastmoney_direct": get_sector_capital_flow,
    },
}

# Methods whose first positional argument is a ticker symbol
_TICKER_ARG_METHODS = frozenset({
    "get_stock_data", "get_indicators", "get_fundamentals",
    "get_balance_sheet", "get_cashflow", "get_income_statement",
    "get_news", "get_insider_transactions", "get_fund_flow",
    "get_hk_stock_data", "get_futures_data",
})


def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")


def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")


def _extract_ticker(method: str, args, kwargs) -> str:
    """Extract the ticker argument from a method call."""
    if args:
        return str(args[0])
    return str(kwargs.get("symbol") or kwargs.get("ticker", ""))


def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support.

    A-stock tickers are automatically routed to the "akshare" vendor regardless
    of the configured data vendor, ensuring Chinese market data is fetched from
    the correct source.
    """
    category = get_category_for_method(method)

    # Auto-detect A-stock tickers and force akshare vendor
    if method in _TICKER_ARG_METHODS:
        ticker = _extract_ticker(method, args, kwargs)
        if is_a_stock_ticker(ticker):
            vendor_config = "akshare"
        else:
            vendor_config = get_vendor(category, method)
    else:
        vendor_config = get_vendor(category, method)

    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Build fallback chain: primary vendors first, then remaining available vendors
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except AlphaVantageRateLimitError:
            continue  # Only rate limits trigger fallback

    raise RuntimeError(f"No available vendor for '{method}'")
