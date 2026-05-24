"""Capture final results for 003031 analysis."""
import os, time, json
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "siliconflow"
config["deep_think_llm"] = "deepseek-ai/DeepSeek-V4-Flash"
config["quick_think_llm"] = "deepseek-ai/DeepSeek-V4-Flash"
config["backend_url"] = "https://api.siliconflow.cn"
config["max_debate_rounds"] = 1
config["max_risk_discuss_rounds"] = 1
config["output_language"] = "Chinese"

ticker = "003031"
date = "2026-05-24"
analysts = ["market"]

graph = TradingAgentsGraph(analysts, config=config, debug=True)
init_state = graph.propagator.create_initial_state(ticker, date, asset_type="stock")
args = graph.propagator.get_graph_args()

print(f"Running analysis for {ticker} on {date}...", flush=True)
start = time.time()

final_state = None
for chunk in graph.graph.stream(init_state, **args):
    for node_name, node_state in chunk.items():
        final_state = node_state

elapsed = time.time() - start
print(f"Analysis completed in {elapsed:.0f}s", flush=True)

if final_state and isinstance(final_state, dict):
    # Save all reports
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
    os.makedirs(out_dir, exist_ok=True)

    reports = {
        "market_report": "市场分析师报告",
        "final_trade_decision": "最终交易决策",
        "investment_plan": "投资计划",
        "trader_investment_plan": "交易员投资计划",
    }
    for key, label in reports.items():
        val = final_state.get(key, "")
        if val and isinstance(val, str) and val.strip():
            path = os.path.join(out_dir, f"{key}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(val)
            print(f"Saved {label} -> {path} ({len(val)} chars)", flush=True)

    # Print final decision
    decision = final_state.get("final_trade_decision", "")
    if decision:
        print(f"\n{'='*60}", flush=True)
        print(f"最终交易决策 ({len(decision)} chars):", flush=True)
        print(f"{'='*60}", flush=True)
        print(decision[:2000], flush=True)
    else:
        print("No final_trade_decision found. Dumping state keys:", flush=True)
        for k, v in final_state.items():
            if isinstance(v, str) and v.strip():
                print(f"  {k}: {v[:100]}...", flush=True)
