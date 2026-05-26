"""AKShare vendor implementation for Chinese A-stock market data.

Provides the same function signatures as the yfinance vendor so it can be
registered in VENDOR_METHODS and selected automatically when an A-stock
ticker is detected.
"""

import logging
import time as _time
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd
import requests

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


def _fetch_hist_sina(code: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    """Fetch OHLCV via Sina Finance (stock_zh_a_daily). 3rd fallback source."""
    import os
    from .config import get_config
    from .utils import safe_ticker_component

    safe_code = safe_ticker_component(code)
    config = get_config()
    cache_file = os.path.join(
        config["data_cache_dir"],
        f"{safe_code}-sina-{start}-{end}.csv",
    )
    os.makedirs(config["data_cache_dir"], exist_ok=True)

    if os.path.exists(cache_file):
        return pd.read_csv(cache_file, encoding="utf-8")

    # AKShare's Sina interface uses different symbol format
    try:
        df = ak.stock_zh_a_daily(
            symbol=code, start_date=start, end_date=end, adjust=adjust
        )
    except Exception:
        return pd.DataFrame()

    if df is not None and not df.empty:
        df.to_csv(cache_file, index=False, encoding="utf-8")
    return df if df is not None else pd.DataFrame()


def _normalize_hist_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names from Tencent / East Money / Sina to standard English."""
    col_map = {
        # Tencent (stock_zh_a_hist_tx)
        "date": "Date", "open": "Open", "close": "Close",
        "high": "High", "low": "Low", "amount": "Volume",
        # Sina (stock_zh_a_daily) — uses same Chinese names as EM
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


def _to_float(val, default=None):
    """Parse numeric value from various formats (with %, commas, etc.).
    Returns *default* (None) when the value is non-numeric, matching
    stock-selector's robust parsing logic."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    try:
        s = str(val).replace("%", "").replace(",", "").strip()
        if s in ("-", "--", "", "nan", "None"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Stock price data (OHLCV)
# ---------------------------------------------------------------------------
def get_stock_data_akshare(
    symbol: str, start_date: str, end_date: str
) -> str:
    """Fetch OHLCV data for an A-stock via AKShare (forward-adjusted).

    Tries Tencent endpoint first (robust), falls back to East Money,
    then Sina AKShare, then Sohu direct source.
    """
    code = normalize_a_stock_ticker(symbol)
    s = start_date.replace("-", "")
    e = end_date.replace("-", "")

    df = None
    errors = []
    for fetcher in (_fetch_hist_tencent, _fetch_hist_eastmoney, _fetch_hist_sina):
        try:
            df = fetcher(code, s, e, adjust="qfq")
            if df is not None and not df.empty:
                break
        except Exception as exc:
            errors.append(f"{fetcher.__name__}: {exc}")
            continue

    if df is None or df.empty:
        # 4th fallback: Sohu direct source
        try:
            from .direct_sources.sohu_history import sohu_get_hist_data
            df = sohu_get_hist_data(code, s, e)
        except Exception as sohu_exc:
            errors.append(f"sohu_direct: {sohu_exc}")

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
        for fetcher in (_fetch_hist_tencent, _fetch_hist_eastmoney, _fetch_hist_sina):
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
# Retry helper — East Money endpoints are flaky under Python's SSL stack
# ---------------------------------------------------------------------------
import time as _time

def _akshare_retry(func, *args, retries=3, delay=2, **kwargs):
    """Call an AKShare function with retries on connection errors."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if attempt < retries - 1:
                logger.debug(
                    "AKShare %s attempt %d/%d failed: %s — retrying in %ds",
                    func.__name__, attempt + 1, retries, exc, delay,
                )
                _time.sleep(delay)
            else:
                raise


# ---------------------------------------------------------------------------
# Fundamentals — multi-source with retry
# ---------------------------------------------------------------------------
def _fundamentals_em(code: str) -> list:
    """Fetch fundamentals from East Money (stock_individual_info_em), then
    fall back to direct HTTP API if AKShare wrapper fails."""
    lines = []

    # Try AKShare wrapper first
    try:
        info_df = _akshare_retry(ak.stock_individual_info_em, symbol=code)
        if info_df is not None and not info_df.empty:
            info_dict = dict(zip(info_df.iloc[:, 0], info_df.iloc[:, 1]))
            fields = [
                ("股票名称", "Name"), ("行业", "Industry"), ("总市值", "Market Cap"),
                ("流通市值", "Float Market Cap"),
                ("市盈率", "PE Ratio (TTM)"), ("市净率", "Price to Book"),
                ("股息率", "Dividend Yield"),
                ("52周最高", "52 Week High"), ("52周最低", "52 Week Low"),
            ]
            for cn, en in fields:
                val = info_dict.get(cn)
                if val is None:
                    for k in info_dict:
                        if cn in str(k) or str(k) in cn:
                            val = info_dict[k]
                            break
                if val is not None:
                    lines.append(f"{en}: {val}")
            if lines:
                return lines
    except Exception as exc:
        logger.debug("AKShare stock_individual_info_em failed: %s", exc)

    # Fallback: direct East Money HTTP API (works when Python SSL causes issues)
    try:
        market = "0" if code.startswith(("0", "3")) else "1"
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": f"{market}.{code}",
            "fields": "f57,f58,f84,f116,f117,f162,f167,f170,f171,f173,f187,f186",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data")
        if not data:
            return lines

        field_map = {
            "f57": ("Stock Code", None),
            "f58": ("Name", None),
            "f84": ("Total Shares", None),
            "f116": ("Market Cap", lambda v: f"{v/1e8:.2f} 亿"),
            "f117": ("Float Market Cap", lambda v: f"{v/1e8:.2f} 亿"),
            "f162": ("PE Ratio (TTM)", lambda v: f"{v/100:.2f}"),
            "f167": ("Price to Book", lambda v: f"{v/100:.2f}"),
            "f170": ("Change %", lambda v: f"{v/100:.2f}%"),
            "f171": ("Volume Ratio", lambda v: f"{v/100:.2f}"),
            "f173": ("Turnover Rate", lambda v: f"{v/100:.2f}%"),
            "f186": ("52 Week High", None),
            "f187": ("52 Week Low", None),
        }
        for key, (label, fmt) in field_map.items():
            val = data.get(key)
            if val is not None:
                display = fmt(val) if fmt else val
                lines.append(f"{label}: {display}")
    except Exception as exc:
        logger.debug("East Money direct HTTP fallback failed for %s: %s", code, exc)

    return lines


def _fundamentals_ths(code: str) -> list:
    """Fetch financial ratios from 同花顺 (stock_financial_abstract_ths).
    Uses partial-match column lookup (same pattern as stock-selector) for
    resilience against renamed/encoded column headers."""
    lines = []
    df = _akshare_retry(ak.stock_financial_abstract_ths, symbol=code, indicator="按年度")
    if df is None or df.empty:
        return lines
    row = df.iloc[0]
    # Each entry: (primary_name, alt_names, english_label)
    field_specs = [
        ("净资产收益率", ["ROE"], "Return on Equity"),
        ("净利润增长", ["净利润同比"], "Net Income Growth"),
        ("营业收入增长", ["营收同比"], "Revenue Growth"),
        ("销售毛利率", ["毛利率"], "Gross Margin"),
        ("销售净利率", ["净利率"], "Net Margin"),
        ("资产负债率", [], "Debt to Asset Ratio"),
    ]
    for primary, alts, en in field_specs:
        for col in df.columns:
            col_str = str(col)
            if primary in col_str or any(a in col_str for a in alts) or (
                primary == "净资产收益率" and "ROE" in col_str.upper()
            ):
                val = _to_float(row[col], default=None)
                if val is not None:
                    lines.append(f"{en}: {val}")
                break
    return lines


def _fundamentals_em_indicator(code: str) -> list:
    """Fetch comprehensive financial indicators from East Money datacenter.
    3rd source — provides EPS, BPS, ROE, YoY growth, cash ratio, etc."""
    lines = []
    try:
        df = _fetch_em_report("RPT_F10_FINANCE_MAINFINADATA", code)
        if df is None or df.empty:
            return lines
        d = df.iloc[0]
        field_map = [
            ("REPORT_DATE", "Report Date", None, lambda v: str(v)[:10]),
            ("EPSJB", "Basic EPS", "CNY", None),
            ("BPS", "Book Value Per Share", "CNY", None),
            ("ROEJQ", "ROE (Diluted)", "%", None),
            ("DJD_TOI_YOY", "Revenue YoY Growth", "%", None),
            ("DJD_DPNP_YOY", "Net Profit YoY Growth", "%", None),
            ("DJD_DEDUCTDPNP_YOY", "Deducted Net Profit YoY", "%", None),
            ("CASH_RATIO", "Cash Ratio", None, None),
            ("LIQUIDATION_RATIO", "Current Ratio", None, None),
            ("NCO_NETPROFIT", "Operating CF / Net Profit", None, None),
            ("OI_YOYRATIO_PK", "Revenue YoY (TTM)", "%", None),
            ("TA_YOYRATIO_PK", "Total Assets YoY", "%", None),
            ("EQUITY_YOYRATIO_PK", "Equity YoY", "%", None),
        ]
        for key, label, unit, fmt in field_map:
            val = d.get(key)
            if val is not None and pd.notna(val):
                display = fmt(val) if fmt else (
                    f"{float(val):.2f}" if isinstance(val, (int, float)) else str(val)
                )
                if unit:
                    display += f" {unit}"
                lines.append(f"{label}: {display}")
    except Exception as exc:
        logger.debug("EM financial indicator API failed for %s: %s", code, exc)
    return lines


def get_fundamentals_akshare(ticker: str, curr_date: str = None) -> str:
    """Company fundamentals for an A-stock via AKShare (multi-source + retry)."""
    code = normalize_a_stock_ticker(ticker)
    lines = []

    # Source 1: East Money company info
    try:
        lines.extend(_fundamentals_em(code))
    except Exception as exc:
        logger.warning("AKShare EM company info failed for %s: %s", code, exc)

    # Source 2: 同花顺 financial ratios
    try:
        lines.extend(_fundamentals_ths(code))
    except Exception as exc:
        logger.warning("AKShare THS financial abstract failed for %s: %s", code, exc)

    # Source 3: AKShare stock_individual_fundamentals_rank (additional metrics)
    if len(lines) < 5:
        try:
            df = _akshare_retry(ak.stock_individual_fundamentals_rank, symbol=code)
            if df is not None and not df.empty:
                row = df.iloc[0]
                for col in df.columns:
                    val = row[col]
                    if pd.notna(val) and col not in ("股票代码", "股票简称", "item"):
                        lines.append(f"{col}: {val}")
        except Exception as exc:
            logger.debug("AKShare fundamentals rank failed for %s: %s", code, exc)

    # Source 4: East Money financial indicator API (comprehensive metrics)
    try:
        em_indicator_lines = _fundamentals_em_indicator(code)
        if em_indicator_lines:
            lines.extend(em_indicator_lines)
    except Exception as exc:
        logger.debug("EM financial indicator failed for %s: %s", code, exc)

    if not lines:
        return f"No fundamentals data found for A-stock '{ticker}'"

    header = f"# Company Fundamentals for {ticker}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + "\n".join(lines)


# ---------------------------------------------------------------------------
# Financial statements — direct East Money datacenter API
# ---------------------------------------------------------------------------
_EM_DATACENTER_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"


def _fetch_em_report(report_name: str, code: str, page_size: int = 4) -> Optional[pd.DataFrame]:
    """Fetch a financial report from East Money datacenter API."""
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageNumber": 1,
        "pageSize": page_size,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
    }
    resp = requests.get(_EM_DATACENTER_URL, params=params, timeout=15)
    resp.raise_for_status()
    j = resp.json()
    if j.get("result") and j["result"].get("data"):
        return pd.DataFrame(j["result"]["data"])
    return None


def _format_amount(val) -> str:
    """Format a monetary value to readable string."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e8:
            return f"{v/1e8:.2f} 亿"
        elif abs(v) >= 1e4:
            return f"{v/1e4:.2f} 万"
        else:
            return f"{v:.2f}"
    except (ValueError, TypeError):
        return str(val)


def _filter_report_by_date(
    df: pd.DataFrame, curr_date: Optional[str]
) -> pd.DataFrame:
    """Keep only report periods on or before curr_date."""
    if not curr_date or df.empty:
        return df
    cutoff = pd.Timestamp(curr_date)
    date_col = None
    for c in df.columns:
        if "REPORT_DATE" in str(c).upper() or "日期" in str(c) or "date" in str(c).lower():
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
        df = _fetch_em_report("RPT_DMSK_FN_BALANCE", code)
        if df is None or df.empty:
            return f"No balance sheet data found for '{ticker}'"
        df = _filter_report_by_date(df, curr_date)

        # Build readable summary from latest report
        d = df.iloc[0]
        lines = [f"# Balance Sheet data for {ticker} ({freq})"]
        lines.append(f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        key_fields = [
            ("REPORT_DATE", "Report Date"),
            ("TOTAL_ASSETS", "Total Assets"),
            ("TOTAL_LIABILITIES", "Total Liabilities"),
            ("TOTAL_EQUITY", "Total Equity"),
            ("TOTAL_PARENT_EQUITY", "Parent Company Equity"),
            ("MONETARYFUNDS", "Cash & Equivalents"),
            ("ACCOUNTS_RECE", "Accounts Receivable"),
            ("INVENTORY", "Inventory"),
            ("FIXED_ASSET", "Fixed Assets"),
            ("GOODWILL", "Goodwill"),
            ("SHORT_LOAN", "Short-term Borrowings"),
            ("LONG_LOAN", "Long-term Borrowings"),
        ]
        for field, label in key_fields:
            if field in d.index:
                val = d[field]
                if pd.notna(val):
                    fmt = _format_amount(val) if field != "REPORT_DATE" else str(val)[:10]
                    lines.append(f"{label}: {fmt}")

        # Include raw CSV for detailed analysis
        lines.append(f"\n## Raw data (latest {len(df)} reports)")
        lines.append(df.to_csv(index=False))
        return "\n".join(lines)
    except Exception as exc:
        return f"Error retrieving balance sheet for {ticker}: {exc}"


def get_cashflow_akshare(
    ticker: str, freq: str = "quarterly", curr_date: str = None
) -> str:
    code = normalize_a_stock_ticker(ticker)
    try:
        df = _fetch_em_report("RPT_DMSK_FN_CASHFLOW", code)
        if df is None or df.empty:
            return f"No cash flow data found for '{ticker}'"
        df = _filter_report_by_date(df, curr_date)

        d = df.iloc[0]
        lines = [f"# Cash Flow data for {ticker} ({freq})"]
        lines.append(f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        key_fields = [
            ("REPORT_DATE", "Report Date"),
            ("NETCASH_OPERATE", "Operating Cash Flow"),
            ("NETCASH_INVEST", "Investing Cash Flow"),
            ("NETCASH_FINANCE", "Financing Cash Flow"),
            ("CCE_ADD", "Net Change in Cash"),
            ("SALES_SERVICES", "Cash from Sales/Services"),
            ("BUY_SERVICES", "Cash Paid for Goods/Services"),
            ("INVEST_PAY", "Cash Paid for Investments"),
        ]
        for field, label in key_fields:
            if field in d.index:
                val = d[field]
                if pd.notna(val):
                    fmt = _format_amount(val) if field != "REPORT_DATE" else str(val)[:10]
                    lines.append(f"{label}: {fmt}")

        lines.append(f"\n## Raw data (latest {len(df)} reports)")
        lines.append(df.to_csv(index=False))
        return "\n".join(lines)
    except Exception as exc:
        return f"Error retrieving cash flow for {ticker}: {exc}"


def get_income_statement_akshare(
    ticker: str, freq: str = "quarterly", curr_date: str = None
) -> str:
    code = normalize_a_stock_ticker(ticker)
    try:
        df = _fetch_em_report("RPT_DMSK_FN_INCOME", code)
        if df is None or df.empty:
            return f"No income statement data found for '{ticker}'"
        df = _filter_report_by_date(df, curr_date)

        d = df.iloc[0]
        lines = [f"# Income Statement data for {ticker} ({freq})"]
        lines.append(f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        key_fields = [
            ("REPORT_DATE", "Report Date"),
            ("TOTAL_OPERATE_INCOME", "Total Revenue"),
            ("OPERATE_INCOME", "Operating Revenue"),
            ("OPERATE_COST", "Operating Cost"),
            ("TOTAL_PROFIT", "Total Profit"),
            ("NETPROFIT", "Net Profit"),
            ("PARENT_NETPROFIT", "Net Profit (Parent)"),
            ("BASIC_EPS", "Basic EPS"),
            ("WEIGHTAVG_ROE", "Weighted Average ROE"),
        ]
        for field, label in key_fields:
            if field in d.index:
                val = d[field]
                if pd.notna(val):
                    fmt = _format_amount(val) if field not in ("REPORT_DATE", "BASIC_EPS", "WEIGHTAVG_ROE") else str(val)
                    lines.append(f"{label}: {fmt}")

        lines.append(f"\n## Raw data (latest {len(df)} reports)")
        lines.append(df.to_csv(index=False))
        return "\n".join(lines)
    except Exception as exc:
        return f"Error retrieving income statement for {ticker}: {exc}"


# ---------------------------------------------------------------------------
# Fund Flow (资金流向) — East Money push2his API
# ---------------------------------------------------------------------------
def get_fund_flow_akshare(ticker: str, look_back_days: int = 10) -> str:
    """Fetch individual stock fund flow (资金流向) data.

    Shows main force (主力) vs retail (散户) net inflows for recent trading
    days — a key short-term indicator used by Chinese market analysts.
    """
    code = normalize_a_stock_ticker(ticker)
    market = "0" if code.startswith(("0", "3")) else "1"

    lines = [f"# Fund Flow (资金流向) for {ticker} (last {look_back_days} trading days)"]
    lines.append(f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        url = "http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            "secid": f"{market}.{code}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": look_back_days,
            "klt": 101,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data")
        if not data or not data.get("klines"):
            return f"No fund flow data available for '{ticker}'"

        # Column headers for the klines data
        col_names = [
            "Date", "Main Net Inflow", "Small Net Inflow", "Medium Net Inflow",
            "Large Net Inflow", "Super Large Net Inflow",
            "Main Net Inflow %", "Small %", "Medium %", "Large %", "Super Large %",
            "Close Price", "Change %",
        ]
        rows = []
        for kline in data["klines"]:
            parts = str(kline).split(",")
            row_dict = {}
            for i, name in enumerate(col_names):
                if i < len(parts):
                    row_dict[name] = parts[i]
            rows.append(row_dict)

        # Format summary
        if rows:
            latest = rows[-1]
            lines.append("## Latest Trading Day Fund Flow")
            for name in ["Date", "Main Net Inflow", "Main Net Inflow %",
                         "Large Net Inflow", "Super Large Net Inflow",
                         "Small Net Inflow", "Medium Net Inflow", "Close Price"]:
                if name in latest:
                    val = latest[name]
                    if "Net Inflow" in name and name not in ("Main Net Inflow %",):
                        try:
                            val = f"{float(val)/1e8:.2f} 亿"
                        except (ValueError, TypeError):
                            pass
                    lines.append(f"  {name}: {val}")

            lines.append(f"\n## Historical Fund Flow ({len(rows)} days)")
            lines.append("Date | Main Net Inflow(亿) | Main % | Close | Change%")
            lines.append("--- | --- | --- | --- | ---")
            for row in rows:
                date = row.get("Date", "")
                main = row.get("Main Net Inflow", "0")
                try:
                    main_display = f"{float(main)/1e8:.2f}"
                except (ValueError, TypeError):
                    main_display = main
                main_pct = row.get("Main Net Inflow %", "")
                close = row.get("Close Price", "")
                change = row.get("Change %", "")
                lines.append(f"{date} | {main_display} | {main_pct} | {close} | {change}")

    except Exception as exc:
        return f"Error retrieving fund flow for {ticker}: {exc}"

    return "\n".join(lines)


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
