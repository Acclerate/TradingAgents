<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="./assets/wechat.png" target="_blank"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-TauricResearch-brightgreen?logo=wechat&logoColor=white"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
  <br>
  <a href="https://github.com/TauricResearch/" target="_blank"><img alt="Community" src="https://img.shields.io/badge/Join_GitHub_Community-TauricResearch-14C290?logo=discourse"/></a>
</div>

<div align="center">
  <!-- Keep these links. Translations will automatically update with the README. -->
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=de">Deutsch</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=es">Español</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=fr">français</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ja">日本語</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ko">한국어</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=pt">Português</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ru">Русский</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=zh">中文</a>
</div>

---

# TradingAgents：多智能体LLM金融交易框架

## 最新动态
- [2026-05] **TradingAgents v0.2.5** 发布，新增基于实证的情绪分析师、GPT-5.5等模型覆盖、Qwen/GLM/MiniMax双区域支持、`TRADINGAGENTS_*` 环境变量配置及API密钥自动检测、远程Ollama支持、非美股Alpha基准测试，以及股票代码路径遍历安全加固。完整列表请参阅 [CHANGELOG.md](CHANGELOG.md)。
- [2026-04] **TradingAgents v0.2.4** 发布，新增结构化输出智能体（研究经理、交易员、投资组合经理）、LangGraph检查点恢复、持久化决策日志、DeepSeek/Qwen/GLM/Azure提供商支持、Docker部署，以及Windows UTF-8编码修复。
- [2026-03] **TradingAgents v0.2.3** 发布，新增多语言支持、GPT-5.4系列模型、统一模型目录、回测日期保真度，以及代理支持。
- [2026-03] **TradingAgents v0.2.2** 发布，新增GPT-5.4/Gemini 3.1/Claude 4.6模型覆盖、五级评级标准、OpenAI Responses API、Anthropic努力控制，以及跨平台稳定性改进。
- [2026-02] **TradingAgents v0.2.0** 发布，新增多提供商LLM支持（GPT-5.x、Gemini 3.x、Claude 4.x、Grok 4.x）及改进的系统架构。
- [2026-01] **Trading-R1** [技术报告](https://arxiv.org/abs/2509.11420) 发布，[终端版本](https://github.com/TauricResearch/Trading-R1) 即将推出。

<div align="center">
<a href="https://www.star-history.com/#TauricResearch/TradingAgents&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date" />
   <img alt="TradingAgents Star History" src="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date" style="width: 80%; height: auto;" />
 </picture>
</a>
</div>

> 🎉 **TradingAgents** 正式发布！我们收到了大量关于这项工作的咨询，感谢社区的热情支持。
>
> 因此我们决定完全开源该框架。期待与你一起构建有影响力的项目！

<div align="center">

🚀 [TradingAgents框架](#tradingagents-框架) | ⚡ [安装与CLI](#安装与cli) | 🎬 [演示](https://www.youtube.com/watch?v=90gr5lwjIho) | 📦 [包使用](#tradingagents-包) | 🤝 [贡献](#贡献) | 📄 [引用](#引用)

</div>

## TradingAgents 框架

TradingAgents是一个多智能体交易框架，模拟真实世界交易公司的运作模式。通过部署由LLM驱动的专业智能体——包括基本面分析师、情绪专家、技术分析师、交易员和风险管理团队——平台协作评估市场条件并做出交易决策。此外，这些智能体通过动态讨论来确定最优策略。

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> TradingAgents框架专为研究目的设计。交易表现可能受多种因素影响，包括选择的骨干语言模型、模型温度、交易周期、数据质量以及其他非确定性因素。[不构成财务、投资或交易建议。](https://tauric.ai/disclaimer/)

我们的框架将复杂的交易任务分解为专门的角色，确保系统实现稳健、可扩展的市场分析和决策方法。

### 分析师团队
- **基本面分析师**：评估公司财务和绩效指标，识别内在价值和潜在风险。
- **情绪分析师**：聚合新闻标题、StockTwits和Reddit讨论，形成单一情绪读数，以衡量短期市场情绪。
- **新闻分析师**：监控全球新闻和宏观经济指标，解读事件对市场条件的影响。
- **技术分析师**：利用技术指标（如MACD和RSI）检测交易模式并预测价格走势。

<p align="center">
  <img src="assets/analyst.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

### 研究员团队
- 由看涨和看跌研究员组成，批判性评估分析师团队提供的洞察。通过结构化辩论，平衡潜在收益与固有风险。

<p align="center">
  <img src="assets/researcher.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### 交易员智能体
- 整合分析师和研究员的报告，做出明智的交易决策。基于全面的市场洞察，确定交易时机和规模。

<p align="center">
  <img src="assets/trader.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### 风险管理与投资组合经理
- 通过评估市场波动性、流动性及其他风险因素，持续评估投资组合风险。风险管理团队评估并调整交易策略，向投资组合经理提供评估报告以供最终决策。
- 投资组合经理批准/拒绝交易提案。如果批准，订单将发送至模拟交易所执行。

<p align="center">
  <img src="assets/risk.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

## 安装与CLI

### 安装

克隆TradingAgents：
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

使用你喜欢的环境管理器创建虚拟环境：
```bash
conda create -n tradingagents python=3.13
conda activate tradingagents
```

安装包及其依赖：
```bash
pip install .
```

### Docker

或者使用Docker运行：
```bash
cp .env.example .env  # 添加你的API密钥
docker compose run --rm tradingagents
```

使用Ollama运行本地模型：
```bash
docker compose --profile ollama run --rm tradingagents-ollama
```

### 所需API

TradingAgents支持多个LLM提供商。设置你选择的提供商的API密钥：

```bash
export OPENAI_API_KEY=...          # OpenAI (GPT)
export GOOGLE_API_KEY=...          # Google (Gemini)
export ANTHROPIC_API_KEY=...       # Anthropic (Claude)
export XAI_API_KEY=...             # xAI (Grok)
export DEEPSEEK_API_KEY=...        # DeepSeek
export DASHSCOPE_API_KEY=...       # Qwen — 国际版 (dashscope-intl.aliyuncs.com)
export DASHSCOPE_CN_API_KEY=...    # Qwen — 中国版 (dashscope.aliyuncs.com)
export ZHIPU_API_KEY=...           # GLM via Z.AI (国际版)
export ZHIPU_CN_API_KEY=...        # GLM via BigModel (中国版, open.bigmodel.cn)
export MINIMAX_API_KEY=...         # MiniMax — 全球版 (api.minimax.io, M2.x, 204K ctx)
export MINIMAX_CN_API_KEY=...      # MiniMax — 中国版 (api.minimaxi.com, M2.x, 204K ctx)
export OPENROUTER_API_KEY=...      # OpenRouter
export ALPHA_VANTAGE_API_KEY=...   # Alpha Vantage
```

对于企业提供商（如Azure OpenAI、AWS Bedrock），将 `.env.enterprise.example` 复制为 `.env.enterprise` 并填入你的凭据。

对于本地模型，使用 `llm_provider: "ollama"` 配置Ollama。默认端点为 `http://localhost:11434/v1`；设置 `OLLAMA_BASE_URL` 指向远程 `ollama-serve`。使用 `ollama pull <name>` 拉取模型，在CLI中选择"自定义模型ID"来使用未列出的模型。

或者，将 `.env.example` 复制为 `.env` 并填入你的密钥：
```bash
cp .env.example .env
```

### CLI使用

启动交互式CLI：
```bash
tradingagents          # 已安装的命令
python -m cli.main     # 替代方案：直接从源码运行
```
你将看到一个界面，可以选择所需的股票代码、分析日期、LLM提供商、研究深度等。

<p align="center">
  <img src="assets/cli/cli_init.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

加载结果时将显示一个界面，让你跟踪智能体的运行进度。

<p align="center">
  <img src="assets/cli/cli_news.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

<p align="center">
  <img src="assets/cli/cli_transaction.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

## TradingAgents 包

### 实现细节

我们使用LangGraph构建TradingAgents，确保灵活性和模块化。该框架支持多个LLM提供商：OpenAI、Google、Anthropic、xAI、DeepSeek、Qwen（阿里DashScope，国际和中国端点）、GLM（智谱）、MiniMax（全球+中国）、OpenRouter、用于本地模型的Ollama，以及用于企业的Azure OpenAI。

### Python使用

要在代码中使用TradingAgents，你可以导入 `tradingagents` 模块并初始化 `TradingAgentsGraph()` 对象。`.propagate()` 函数将返回决策。你可以运行 `main.py`，这里有一个简单示例：

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# 前向传播
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

你也可以调整默认配置来设置自己的LLM选择、辩论轮数等。

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"        # openai, google, anthropic, xai, deepseek, qwen, qwen-cn, glm, glm-cn, minimax, minimax-cn, openrouter, ollama, azure
config["deep_think_llm"] = "gpt-5.4"     # 复杂推理模型
config["quick_think_llm"] = "gpt-5.4-mini" # 快速任务模型
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

所有配置选项请参阅 `tradingagents/default_config.py`。

## 持久化与恢复

TradingAgents在运行之间持久化两种状态。

### 决策日志

决策日志始终开启。每次完成的运行都会将其决策追加到 `~/.tradingagents/memory/trading_memory.md`。在下一次对同一股票代码的运行中，TradingAgents会获取已实现的收益率（原始和相对于SPY的Alpha），生成一段反思，并将最近的同股票代码决策以及近期的跨股票代码经验注入投资组合经理的提示中，这样每次分析都能继承之前的成功经验和失败教训。

使用 `TRADINGAGENTS_MEMORY_LOG_PATH` 覆盖路径。

### 检查点恢复

检查点恢复通过 `--checkpoint` 可选启用。启用后，LangGraph在每个节点后保存状态，这样崩溃或中断的运行可以从最后成功的步骤恢复，而不是重新开始。在恢复运行中，你将在日志中看到 `Resuming from step N for <TICKER> on <date>`；在新运行中将看到 `Starting fresh`。检查点在成功完成后自动清除。

每个股票代码的SQLite数据库位于 `~/.tradingagents/cache/checkpoints/<TICKER>.db`（使用 `TRADINGAGENTS_CACHE_DIR` 覆盖基础路径）。使用 `--clear-checkpoints` 在运行前重置所有检查点。

```bash
tradingagents analyze --checkpoint           # 本次运行启用
tradingagents analyze --clear-checkpoints    # 运行前重置
```

```python
config = DEFAULT_CONFIG.copy()
config["checkpoint_enabled"] = True
ta = TradingAgentsGraph(config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
```

## 贡献

我们欢迎社区的贡献！无论是修复bug、改进文档还是建议新功能，你的参与都能帮助项目变得更好。如果你对这个研究方向感兴趣，请考虑加入我们的开源金融AI研究社区 [Tauric Research](https://tauric.ai/)。

过去的贡献（包括代码、设计反馈和bug报告）在 [`CHANGELOG.md`](CHANGELOG.md) 中按版本记录。

## 引用

如果你觉得 *TradingAgents* 对你有帮助，请引用我们的工作 :)

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```
