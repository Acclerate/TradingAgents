"""A-stock ticker detection and normalization utilities.

A-stocks use 6-digit numeric codes with optional exchange suffixes
consumed by yfinance (.SS / .SZ) or AKShare (plain 6-digit).
"""

import re

_A_STOCK_PATTERN = re.compile(r"^(\d{6})(\.(SS|SZ))?$", re.IGNORECASE)


def is_a_stock_ticker(ticker: str) -> bool:
    """Return True if *ticker* is a Chinese A-stock code."""
    return bool(_A_STOCK_PATTERN.match(str(ticker).strip()))


def normalize_a_stock_ticker(ticker: str) -> str:
    """Strip exchange suffix, returning the plain 6-digit code used by AKShare."""
    m = _A_STOCK_PATTERN.match(str(ticker).strip())
    return m.group(1) if m else str(ticker).strip().upper()


def get_a_stock_exchange(ticker: str) -> str:
    """Return ``"shanghai"`` or ``"shenzhen"``."""
    code = normalize_a_stock_ticker(ticker)
    return "shanghai" if code.startswith("6") else "shenzhen"


def a_stock_market_code(ticker: str) -> str:
    """Return ``"sh"`` or ``"sz"`` (parameter format for EastMoney / AKShare)."""
    return "sh" if normalize_a_stock_ticker(ticker).startswith("6") else "sz"


def a_stock_yfinance_suffix(ticker: str) -> str:
    """Return the yfinance-style suffix (``.SS`` or ``.SZ``)."""
    return ".SS" if normalize_a_stock_ticker(ticker).startswith("6") else ".SZ"
