"""AKShare vendor implementation for Chinese A-stock market data.

Provides the same function signatures as the yfinance vendor so it can be
registered in VENDOR_METHODS and selected automatically when an A-stock
ticker is detected.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd

from .ticker_utils import (
    a_stock_market_code,
    get_a_stock_exchange,
    normalize_a_stock_ticker,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# A-stock OHLCV fetch — try Tencent first (robust), fall back to East Money
# ---------------------------------------------------------------------------
def _fetch_hist_tencent(code: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    """Fetch OHLCV via Tencent (stock_zh_a_hist_tx). Returns raw AKShare DataFrame."""
    market = "sz" if get_a_stock_exchange(code) == "shenzhen" else "sh"
    return ak.stock_zh_a_hist_tx(
        symbol=f"{market}{code}",
        start_date=start, end_date=end, adjust=adjust,
    )


def _fetch_hist_eastmoney(code: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    """Fetch OHLCV via East Money (stock_zh_a_hist). May fail with SSL issues."""
    return ak.stock_zh_a_hist(
        symbol=code, period="daily",
        start_date=start, end_date=end, adjust=adjust,
    )


def _normalize_hist_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names from either Tencent or East Money to standard English."""
    col_map = {
        # Tencent (stock_zh_a_hist_tx)
        "date": "Date", "open": "Open", "close": "Close",
        "high": "High", "low": "Low", "amount": "Volume",
        # East Money (stock_zh_a_hist)
        **_HIST_COL_MAP,
    }
    return df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

# ---------------------------------------------------------------------------
# Column name mappings (AKShare Chinese → English standard)
# ---------------------------------------------------------------------------
_HIST_COL_MAP = {
    "日期": "Date",
    "开盘": "Open",
    "最高": "High",
    "最低": "Low",
    "收盘": "Close",
    "成交量": "Volume",
    "成交额": "Turnover",
    "振幅": "Amplitude",
    "涨跌幅": "ChangePct",
    "涨跌额": "ChangeAmount",
    "换手率": "TurnoverRate",
}


def _to_float(val, default=0.0):
    try:
        f = float(val)
        return f if pd.notna(f) else default
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Stock price data (OHLCV)
# ---------------------------------------------------------------------------
def get_stock_data_akshare(
    symbol: str, start_date: str, end_date: str
) -> str:
    """Fetch OHLCV data for an A-stock via AKShare (forward-adjusted).

    Tries Tencent endpoint first (robust), falls back to East Money.
    """
    code = normalize_a_stock_ticker(symbol)
    s = start_date.replace("-", "")
    e = end_date.replace("-", "")

    df = None
    errors = []
    for fetcher in (_fetch_hist_tencent, _fetch_hist_eastmoney):
        try:
            df = fetcher(code, s, e, adjust="qfq")
            if df is not None and not df.empty:
                break
        except Exception as exc:
            errors.append(f"{fetcher.__name__}: {exc}")
            continue

    if df is None or df.empty:
        err_detail = "; ".join(errors) if errors else "empty result"
        return f"Error fetching stock data for {symbol} via AKShare: {err_detail}"

    df = _normalize_hist_columns(df)
    keep = ["Date", "Open", "High", "Low", "Close", "Volume"]
    df = df[[c for c in keep if c in df.columns]]

    for c in ["Open", "High", "Low", "Close"]:
        if c in df.columns:
            df[c] = df[c].round(2)

    header = f"# Stock data for {symbol} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(df)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + df.to_csv(index=False)


# ---------------------------------------------------------------------------
# Load OHLCV for indicator calculation (cached)
# ---------------------------------------------------------------------------
def load_ohlcv_akshare(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch OHLCV via AKShare, cached per symbol, filtered to *curr_date*."""
    import os
    from .config import get_config
    from .utils import safe_ticker_component
    from .stockstats_utils import _clean_dataframe

    code = normalize_a_stock_ticker(symbol)
    safe_code = safe_ticker_component(code)

    config = get_config()
    curr_date_dt = pd.to_datetime(curr_date)

    today = pd.Timestamp.today()
    start = today - pd.DateOffset(years=5)

    os.makedirs(config["data_cache_dir"], exist_ok=True)
    cache_file = os.path.join(
        config["data_cache_dir"],
        f"{safe_code}-AKShare-data-{start.strftime('%Y-%m-%d')}-{today.strftime('%Y-%m-%d')}.csv",
    )

    if os.path.exists(cache_file):
        data = pd.read_csv(cache_file, on_bad_lines="skip", encoding="utf-8")
    else:
        df = None
        for fetcher in (_fetch_hist_tencent, _fetch_hist_eastmoney):
            try:
                df = fetcher(code, start.strftime("%Y%m%d"), today.strftime("%Y%m%d"), adjust="qfq")
                if df is not None and not df.empty:
                    break
            except Exception:
                continue
        if df is None or df.empty:
            logger.warning("AKShare OHLCV fetch failed for %s: all sources exhausted", code)
            return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        df = _normalize_hist_columns(df)
        keep = ["Date", "Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in keep if c in df.columns]]
        df.to_csv(cache_file, index=False, encoding="utf-8")
        data = df

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]
    return data


# ---------------------------------------------------------------------------
# Technical indicators — delegates to stockstats with AKShare data loader
# ---------------------------------------------------------------------------
def get_indicators_akshare(
    symbol: str, indicator: str, curr_date: str, look_back_days: int
) -> str:
    """Compute technical indicators for an A-stock using stockstats + AKShare data."""
    from dateutil.relativedelta import relativedelta
    from stockstats import wrap

    data = load_ohlcv_akshare(symbol, curr_date)
    if data.empty:
        return f"No OHLCV data available for {symbol} to compute {indicator}"

    df = wrap(data)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    try:
        df[indicator]  # trigger stockstats calculation
    except Exception as exc:
        return f"Indicator '{indicator}' calculation failed: {exc}"

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - relativedelta(days=look_back_days)

    lines = []
    dt = curr_date_dt
    while dt >= before:
        ds = dt.strftime("%Y-%m-%d")
        matching = df[df["Date"] == ds]
        if not matching.empty:
            val = matching[indicator].values[0]
            lines.append(f"{ds}: {val}")
        else:
            lines.append(f"{ds}: N/A: Not a trading day (weekend or holiday)")
        dt -= timedelta(days=1)

    # Re-use the description map from yfinance
    from .y_finance import get_stock_stats_indicators_window

    best_ind_params = get_stock_stats_indicators_window.__code__.co_consts
    # Get descriptions from the original function's local dict
    ind_desc = _get_indicator_descriptions().get(
        indicator, "No description available."
    )

    result = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + ind_desc
    )
    return result


def _get_indicator_descriptions() -> dict:
    """Indicator descriptions (shared with yfinance vendor)."""
    return {
        "close_50_sma": "50 SMA: A medium-term trend indicator.",
        "close_200_sma": "200 SMA: A long-term trend benchmark.",
        "close_10_ema": "10 EMA: A responsive short-term average.",
        "macd": "MACD: Computes momentum via differences of EMAs.",
        "macds": "MACD Signal: An EMA smoothing of the MACD line.",
        "macdh": "MACD Histogram: Shows the gap between MACD line and its signal.",
        "rsi": "RSI: Measures momentum to flag overbought/oversold conditions.",
        "boll": "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands.",
        "boll_ub": "Bollinger Upper Band: Typically 2 std dev above the middle line.",
        "boll_lb": "Bollinger Lower Band: Typically 2 std dev below the middle line.",
        "atr": "ATR: Averages true range to measure volatility.",
        "vwma": "VWMA: A moving average weighted by volume.",
        "mfi": "MFI: Money Flow Index, momentum indicator using price and volume.",
    }


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------
def get_fundamentals_akshare(ticker: str, curr_date: str = None) -> str:
    """Company fundamentals for an A-stock via AKShare."""
    code = normalize_a_stock_ticker(ticker)
    lines = []

    # --- Company info ---
    try:
        info_df = ak.stock_individual_info_em(symbol=code)
        if info_df is not None and not info_df.empty:
            info_dict = dict(zip(info_df.iloc[:, 0], info_df.iloc[:, 1]))
            fields = [
                ("股票名称", "Name"), ("行业", "Industry"), ("总市值", "Market Cap"),
                ("流通市值", "Float Market Cap"), ("市盈率(动)", "PE Ratio (TTM)"),
                ("市净率", "Price to Book"), ("股息率", "Dividend Yield"),
                ("52周最高", "52 Week High"), ("52周最低", "52 Week Low"),
            ]
            for cn, en in fields:
                val = info_dict.get(cn)
                if val is not None:
                    lines.append(f"{en}: {val}")
    except Exception as exc:
        logger.warning("AKShare company info failed for %s: %s", code, exc)

    # --- Financial abstract (THS) ---
    try:
        df = ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
        if df is not None and not df.empty:
            row = df.iloc[0]
            cn_map = {
                "净资产收益率": "Return on Equity",
                "净利润增长": "Net Income Growth",
                "营业收入增长": "Revenue Growth",
                "销售毛利率": "Gross Margin",
                "销售净利率": "Net Margin",
                "资产负债率": "Debt to Asset Ratio",
            }
            for cn, en in cn_map.items():
                for col in df.columns:
                    if cn in str(col):
                        val = _to_float(row[col], default=None)
                        if val is not None:
                            lines.append(f"{en}: {val}")
                        break
    except Exception as exc:
        logger.warning("AKShare financial abstract failed for %s: %s", code, exc)

    if not lines:
        return f"No fundamentals data found for A-stock '{ticker}'"

    header = f"# Company Fundamentals for {ticker}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + "\n".join(lines)


# ---------------------------------------------------------------------------
# Financial statements
# ---------------------------------------------------------------------------
def _filter_report_by_date(
    df: pd.DataFrame, curr_date: Optional[str]
) -> pd.DataFrame:
    """Keep only report periods on or before curr_date."""
    if not curr_date or df.empty:
        return df
    cutoff = pd.Timestamp(curr_date)
    date_col = None
    for c in df.columns:
        if "日期" in str(c) or "date" in str(c).lower():
            date_col = c
            break
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df[df[date_col] <= cutoff]
    return df


def get_balance_sheet_akshare(
    ticker: str, freq: str = "quarterly", curr_date: str = None
) -> str:
    code = normalize_a_stock_ticker(ticker)
    try:
        df = ak.stock_balance_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return f"No balance sheet data found for '{ticker}'"
        df = _filter_report_by_date(df, curr_date)
        header = f"# Balance Sheet data for {ticker} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + df.to_csv(index=False)
    except Exception as exc:
        return f"Error retrieving balance sheet for {ticker}: {exc}"


def get_cashflow_akshare(
    ticker: str, freq: str = "quarterly", curr_date: str = None
) -> str:
    code = normalize_a_stock_ticker(ticker)
    try:
        df = ak.stock_cash_flow_statement_by_report_em(symbol=code)
        if df is None or df.empty:
            return f"No cash flow data found for '{ticker}'"
        df = _filter_report_by_date(df, curr_date)
        header = f"# Cash Flow data for {ticker} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + df.to_csv(index=False)
    except Exception as exc:
        return f"Error retrieving cash flow for {ticker}: {exc}"


def get_income_statement_akshare(
    ticker: str, freq: str = "quarterly", curr_date: str = None
) -> str:
    code = normalize_a_stock_ticker(ticker)
    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return f"No income statement data found for '{ticker}'"
        df = _filter_report_by_date(df, curr_date)
        header = f"# Income Statement data for {ticker} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + df.to_csv(index=False)
    except Exception as exc:
        return f"Error retrieving income statement for {ticker}: {exc}"


# ---------------------------------------------------------------------------
# Insider transactions → 龙虎榜 (Dragon & Tiger List)
# ---------------------------------------------------------------------------
def get_insider_transactions_akshare(ticker: str) -> str:
    """A-stocks use 龙虎榜 as the closest equivalent to insider transaction data."""
    code = normalize_a_stock_ticker(ticker)
    try:
        end = datetime.now()
        start = end - timedelta(days=30)
        df = ak.stock_lhb_detail_em(
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return (
                f"No 龙虎榜 (Dragon & Tiger List) data found for '{ticker}' in the last 30 days. "
                f"A-stocks do not have US-style insider transaction reporting."
            )
        # Filter to this stock
        stock_df = df[df["代码"] == code]
        if stock_df.empty:
            return (
                f"No 龙虎榜 (Dragon & Tiger List) entries for '{ticker}' in the last 30 days. "
                f"This stock may not have appeared on the Dragon & Tiger List recently."
            )
        header = f"# 龙虎榜 (Dragon & Tiger List) data for {ticker} (last 30 days)\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + stock_df.to_csv(index=False)
    except Exception as exc:
        return f"Error retrieving 龙虎榜 data for {ticker}: {exc}"
