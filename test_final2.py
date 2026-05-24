import os, time
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
os.makedirs(OUT, exist_ok=True)

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

start = time.time()
graph = TradingAgentsGraph(["market"], config=config, debug=True)
init_state = graph.propagator.create_initial_state("003031", "2026-05-24", asset_type="stock")
args = graph.propagator.get_graph_args()

final_state = None
for chunk in graph.graph.stream(init_state, **args):
    for node_name, node_state in chunk.items():
        final_state = node_state

elapsed = time.time() - start

with open(os.path.join(OUT, "elapsed.txt"), "w") as f:
    f.write(f"{elapsed}s\n")

if final_state and isinstance(final_state, dict):
    for key, val in final_state.items():
        if isinstance(val, str) and val.strip():
            with open(os.path.join(OUT, f"{key}.md"), "w", encoding="utf-8") as f:
                f.write(val)
        elif isinstance(val, dict):
            import json
            with open(os.path.join(OUT, f"{key}.json"), "w", encoding="utf-8") as f:
                json.dump(val, f, ensure_ascii=False, indent=2)
else:
    with open(os.path.join(OUT, "error.txt"), "w") as f:
        f.write(f"No final_state. Type: {type(final_state)}\n")
