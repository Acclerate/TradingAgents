"""Test: 003031 market analyst, write output to local file."""
import os, sys, time
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

LOG_PATH = os.path.join(os.path.dirname(__file__), "test_run.log")
LOG = open(LOG_PATH, "w", encoding="utf-8")

def log(msg):
    t = time.time() - START
    line = f"[{t:.0f}s] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()

START = time.time()

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

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

log(f"Starting {ticker} on {date}")

graph = TradingAgentsGraph(analysts, config=config, debug=True)
init_state = graph.propagator.create_initial_state(ticker, date, asset_type="stock")
args = graph.propagator.get_graph_args()

log("Graph ready, streaming...")

final_state = None
node_count = 0
try:
    for chunk in graph.graph.stream(init_state, **args):
        for node_name, node_state in chunk.items():
            node_count += 1
            if isinstance(node_state, dict) and "messages" in node_state:
                msgs = node_state["messages"]
                if msgs:
                    last = msgs[-1]
                    content = getattr(last, "content", "")
                    tc = getattr(last, "tool_calls", None)
                    if tc:
                        tools = [t["name"] for t in tc if isinstance(t, dict)]
                        log(f"{node_name}: tool_calls={tools}")
                    elif content and str(content).strip():
                        log(f"{node_name}: {str(content)[:150].replace(chr(10), ' ')}")
            final_state = node_state
except Exception as e:
    log(f"ERROR: {e}")
    import traceback
    LOG.write(traceback.format_exc())
    LOG.flush()

elapsed = time.time() - START
log(f"Done in {elapsed:.1f}s ({node_count} nodes)")

if final_state and isinstance(final_state, dict):
    msgs = final_state.get("messages", [])
    if msgs:
        last_msg = msgs[-1].content if hasattr(msgs[-1], "content") else str(msgs[-1])
        log(f"Final output ({len(last_msg)} chars):\n{last_msg[:1000]}")

LOG.close()
