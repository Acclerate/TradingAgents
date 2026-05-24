"""Minimal test: just call the LLM with a simple market analyst prompt."""
import os, time
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from tradingagents.llm_clients.factory import create_llm_client

print("Creating SiliconFlow client...", flush=True)
client = create_llm_client(
    provider="siliconflow",
    model="deepseek-ai/DeepSeek-V4-Flash",
    base_url="https://api.siliconflow.cn",
)
llm = client.get_llm()

print("Calling LLM with long prompt...", flush=True)
start = time.time()
resp = llm.invoke([
    ("system", "You are a stock market analyst. Analyze the stock 003031 (中瓷电子). Be concise."),
    ("human", "Provide a brief market analysis for 003031."),
])
elapsed = time.time() - start
print(f"LLM responded in {elapsed:.1f}s", flush=True)
print(f"Response: {resp[:500]}", flush=True)
