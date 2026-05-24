"""Sentiment analyst — multi-source sentiment analysis for a target ticker.

Previously named ``social_media_analyst``. Renamed and redesigned because
the old version had a prompt that demanded social-media analysis but the
only tool available was Yahoo Finance news — which led LLMs to fabricate
Reddit/X/StockTwits content under prompt pressure (verified live).

The redesigned agent pre-fetches three complementary data sources before
the LLM is invoked and injects them into the prompt as structured blocks:

  1. News headlines     — Yahoo Finance (institutional framing)
  2. StockTwits messages — retail-trader posts indexed by cashtag, with
                           user-labeled Bullish/Bearish sentiment tags
  3. Reddit posts        — r/wallstreetbets, r/stocks, r/investing

The agent does not use tool-calling; the data is in the prompt from
turn 0. The LLM produces the sentiment report in a single invocation.

See: https://github.com/TauricResearch/TradingAgents/issues/557
"""

from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.reddit import fetch_reddit_posts
from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
from tradingagents.dataflows.ticker_utils import is_a_stock_ticker


def _seven_days_back(trade_date: str) -> str:
    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")


def create_sentiment_analyst(llm):
    """Create a sentiment analyst node for the trading graph.

    Pre-fetches news + StockTwits + Reddit data, injects them into the
    prompt as structured blocks, and produces a sentiment report in a
    single LLM call.
    """

    def sentiment_analyst_node(state):
        ticker = state["company_of_interest"]
        end_date = state["trade_date"]
        start_date = _seven_days_back(end_date)
        instrument_context = build_instrument_context(ticker)

        # Pre-fetch data sources. A-stocks use Chinese platforms; others use
        # the default US-centric sources. Each fetcher degrades gracefully.
        news_block = get_news.func(ticker, start_date, end_date)

        if is_a_stock_ticker(ticker):
            from tradingagents.dataflows.eastmoney_guba import fetch_eastmoney_guba
            from tradingagents.dataflows.xueqiu import fetch_xueqiu_posts
            social_block_1 = fetch_eastmoney_guba(ticker, limit=30)
            social_block_2 = fetch_xueqiu_posts(ticker, limit=30)
        else:
            social_block_1 = fetch_stocktwits_messages(ticker, limit=30)
            social_block_2 = fetch_reddit_posts(ticker)

        system_message = _build_system_message(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            news_block=news_block,
            social_block_1=social_block_1,
            social_block_2=social_block_2,
            is_a_stock=is_a_stock_ticker(ticker),
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    "\n{system_message}\n"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=end_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        # No bind_tools — the data is already in the prompt; a single LLM
        # call produces the report directly.
        chain = prompt | llm
        result = chain.invoke(state["messages"])

        return {
            "messages": [result],
            "sentiment_report": result.content,
        }

    return sentiment_analyst_node


def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    news_block: str,
    social_block_1: str,
    social_block_2: str,
    is_a_stock: bool = False,
) -> str:
    """Assemble the sentiment-analyst system message with structured data blocks."""
    if is_a_stock:
        source_1_name = "东方财富股吧 (EastMoney Guba)"
        source_1_desc = "Chinese retail investor discussions. Community sentiment from one of the largest Chinese stock forums."
        source_2_name = "雪球 (Xueqiu / Snowball)"
        source_2_desc = "Chinese investment social platform. Mix of retail and semi-professional investor analysis."
    else:
        source_1_name = "StockTwits"
        source_1_desc = "Retail-trader social platform indexed by cashtag. Each message carries a user-labeled sentiment tag (Bullish / Bearish / no-label) plus the message body."
        source_2_name = "Reddit (r/wallstreetbets, r/stocks, r/investing)"
        source_2_desc = "Community discussion. Engagement signal via upvote score and comment count."

    return f"""You are a financial market sentiment analyst. Your task is to produce a comprehensive sentiment report for {ticker} covering the period from {start_date} to {end_date}, drawing on three complementary data sources that have already been collected for you.

## Data sources (pre-fetched, in this prompt)

### News headlines — past 7 days
Institutional framing. Fact-driven, slower-moving signal.

<start_of_news>
{news_block}
<end_of_news>

### {source_1_name}
{source_1_desc}

<start_of_social_1>
{social_block_1}
<end_of_social_1>

### {source_2_name}
{source_2_desc}

<start_of_social_2>
{social_block_2}
<end_of_social_2>

## How to analyze this data (best practices)

1. **Read the overall sentiment ratio as a leading retail-sentiment signal.** A heavily one-sided split may indicate over-extension and contrarian risk; balanced opinions suggest uncertainty. Sample size matters — base rates on the actual data count, not percentages alone.

2. **Look for cross-source divergences.** If news framing is bearish but social sentiment is overwhelmingly bullish, that mismatch is itself a signal — it can mean retail is leaning into a thesis the news flow hasn't caught up to (or vice versa, that retail is chasing while institutions are cautious).

3. **Weight social posts by engagement and credibility.** Detailed analysis with evidence is more valuable than brief emotional reactions.

4. **Distinguish opinion from event.** A news headline is an event; a social post expressing a view is opinion. Both are inputs but should be weighted differently in your conclusions.

5. **Identify recurring narrative themes.** What topic keeps coming up across sources? That's the dominant narrative driving current sentiment.

6. **Be honest about data limits.** If sources returned limited data or "<unavailable>" placeholders, the sentiment read is less robust — flag this caveat explicitly.

7. **Identify catalysts and risks** that emerge across sources — news of upcoming earnings, product launches, competitive threats, macro headlines, etc.

8. **Past sentiment is not predictive.** Frame your conclusions as signal for the trader to weigh alongside fundamentals and technicals, not as a price call.

## Output

Produce a sentiment report covering, in order:

1. **Overall sentiment direction** — Bullish / Bearish / Neutral / Mixed — with a brief confidence note based on data quality and sample size.
2. **Source-by-source breakdown** — what each of news / {source_1_name} / {source_2_name} is telling you, with specific evidence.
3. **Divergences, alignments, and key narratives** across sources.
4. **Catalysts and risks** surfaced by the data.
5. **Markdown table** at the end summarizing key sentiment signals, their direction, source, and supporting evidence.

{get_language_instruction()}"""


# ---------------------------------------------------------------------------
# Backwards-compatibility shim
# ---------------------------------------------------------------------------
def create_social_media_analyst(llm):
    """Deprecated alias for :func:`create_sentiment_analyst`.

    Kept so existing code that imports ``create_social_media_analyst``
    continues to work.

    .. deprecated::
        Import :func:`create_sentiment_analyst` directly instead.
    """
    import warnings
    warnings.warn(
        "create_social_media_analyst is deprecated and will be removed in a "
        "future version. Use create_sentiment_analyst instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_sentiment_analyst(llm)
