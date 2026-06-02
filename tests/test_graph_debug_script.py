"""Debug: trace exactly where the graph stream stalls."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import os, time, sys
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

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
config["analyst_concurrency_limit"] = 1

ticker = "003031"
date = "2026-05-24"
analysts = ["market"]

print(f"[{time.time():.0f}] Creating graph...", flush=True)
graph = TradingAgentsGraph(analysts, config=config, debug=True)

print(f"[{time.time():.0f}] Creating initial state...", flush=True)
init_state = graph.propagator.create_initial_state(ticker, date, asset_type="stock")

print(f"[{time.time():.0f}] Getting graph args...", flush=True)
args = graph.propagator.get_graph_args()

print(f"[{time.time():.0f}] About to stream. State keys: {list(init_state.keys())}", flush=True)
print(f"[{time.time():.0f}] Graph nodes: {list(graph.graph.nodes.keys())}", flush=True)

# Try invoking just the first node directly
first_node = list(graph.graph.nodes.keys())[0]
print(f"[{time.time():.0f}] First node: {first_node}", flush=True)

print(f"[{time.time():.0f}] Starting stream...", flush=True)
node_count = 0
try:
    for chunk in graph.graph.stream(init_state, **args):
        for node_name, node_state in chunk.items():
            node_count += 1
            elapsed = time.time()
            if isinstance(node_state, dict) and "messages" in node_state:
                msgs = node_state["messages"]
                n_msgs = len(msgs)
                last = msgs[-1] if msgs else None
                tc = getattr(last, "tool_calls", None) if last else None
                if tc:
                    tools = [t["name"] for t in tc if isinstance(t, dict)]
                    print(f"[{elapsed:.0f}] #{node_count} {node_name}: tool_calls={tools}", flush=True)
                elif last and getattr(last, "content", ""):
                    c = str(last.content)[:100].replace(chr(10), " ")
                    print(f"[{elapsed:.0f}] #{node_count} {node_name}: {c}", flush=True)
                else:
                    print(f"[{elapsed:.0f}] #{node_count} {node_name}: {n_msgs} msgs", flush=True)
            else:
                keys = list(node_state.keys()) if isinstance(node_state, dict) else str(type(node_state))
                print(f"[{elapsed:.0f}] #{node_count} {node_name}: state_keys={keys}", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback; traceback.print_exc()

print(f"[{time.time():.0f}] Stream done ({node_count} chunks)", flush=True)
