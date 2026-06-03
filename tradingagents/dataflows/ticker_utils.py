"""A-stock ticker detection and normalization utilities.

A-stocks use 6-digit numeric codes with optional exchange suffixes
consumed by yfinance (.SS / .SZ) or AKShare (plain 6-digit).
"""

import re

# Common Chinese-name aliases used in A-share workflows.
_TICKER_ALIASES = {
    "数据港": "603881",
}

# yfinance uses ``.SS`` for Shanghai while Chinese broker APIs and user
# convention use ``.SH`` — accept both in input, normalize to ``.SS``.
_A_STOCK_PATTERN = re.compile(r"^(\d{6})(\.(SS|SZ|SH))?$", re.IGNORECASE)


def normalize_input_ticker(ticker: str) -> str:
    """Normalize raw ticker input.

    - maps supported Chinese aliases to numeric A-stock code
    - normalizes ``.SH`` suffix to ``.SS`` for compatibility
    - uppercases non-alias symbols
    """
    return normalize_input_ticker_with_display(ticker)[0]


def normalize_input_ticker_with_display(ticker: str) -> tuple[str, str]:
    """Like :func:`normalize_input_ticker` but also returns a display name.

    Returns ``(normalized, display_name)``.  When the raw input is a Chinese
    alias the display name combines code and alias, e.g. ``"603881_数据港"``.
    """
    raw = str(ticker).strip()
    if raw in _TICKER_ALIASES:
        code = _TICKER_ALIASES[raw]
        return code, f"{code}_{raw}"

    # Fast path: already in canonical form (e.g. "603881.SS", "AAPL")
    if raw == raw.upper() and not raw.endswith(".SH"):
        return raw, raw

    normalized = raw.upper()
    if normalized.endswith(".SH") and len(normalized) == 9 and normalized[:6].isdigit():
        normalized = f"{normalized[:6]}.SS"
    return normalized, normalized


def is_a_stock_ticker(ticker: str) -> bool:
    """Return True if *ticker* is a Chinese A-stock code."""
    return bool(_A_STOCK_PATTERN.match(normalize_input_ticker(ticker)))


def should_use_akshare_for_ticker(ticker: str) -> bool:
    """Return True when routing should force A-share data vendor (AKShare)."""
    return is_a_stock_ticker(ticker)


def normalize_a_stock_ticker(ticker: str) -> str:
    """Strip exchange suffix, returning the plain 6-digit code used by AKShare."""
    normalized = normalize_input_ticker(ticker)
    m = _A_STOCK_PATTERN.match(normalized)
    return m.group(1) if m else normalized


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
