"""Agent tools for sector capital flow analysis."""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_sector_flow(
    sector_type: Annotated[str, "板块类型: industry(行业板块), concept(概念板块), region(区域板块)"] = "industry",
) -> str:
    """Retrieve sector-level capital flow data from East Money.

    Shows top 10 sectors by net capital inflow and outflow, useful for
    understanding which sectors institutional money is flowing into or out of.
    A key indicator for sector rotation analysis and thematic investing.
    """
    return route_to_vendor("get_sector_flow", sector_type)
