from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news,
    get_fund_flow,
)


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Applied to every agent whose output reaches the saved report —
    analysts, researchers, debaters, research manager, trader, and
    portfolio manager — so a non-English run produces a fully localized
    report rather than a mix of languages.
    """
    from tradingagents.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def build_instrument_context(ticker: str, asset_type: str = "stock") -> str:
    """Describe the exact instrument so agents preserve exchange-qualified tickers."""
    from tradingagents.dataflows.ticker_utils import is_a_stock_ticker, normalize_a_stock_ticker

    instrument_label = "asset" if asset_type == "crypto" else "instrument"
    extra_hint = ""

    if asset_type == "crypto":
        extra_hint = " Treat it as a crypto asset rather than a company, and do not assume company fundamentals are available."
    elif is_a_stock_ticker(ticker):
        code = normalize_a_stock_ticker(ticker)
        price_limit = "20%" if code.startswith(("30", "688")) else "10%"
        board = "创业板 (ChiNext)" if code.startswith("30") else "科创板 (STAR)" if code.startswith("688") else "主板 (Main Board)"
        extra_hint = (
            f" This is a Chinese A-stock on the {board}. Key market rules:\n"
            f" - T+1 settlement: shares bought today cannot be sold until the next trading day.\n"
            f" - Price limit: {price_limit} daily price movement limit.\n"
            f" - Lot size: minimum trade unit is 100 shares.\n"
            f" - Currency: CNY (Chinese Yuan).\n"
            f" - Trading hours: 09:30-11:30 and 13:00-15:00 Beijing time (UTC+8), Monday-Friday.\n"
            f"Use this exact ticker in every tool call."
        )

    return (
        f"The {instrument_label} to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`, `.SS`, `.SZ`, `-USD`)."
        + extra_hint
    )

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
