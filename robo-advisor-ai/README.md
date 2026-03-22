# 📈 RoboAdvisor AI

AI-powered robo-advisor that takes natural language investment goals, researches stocks in real time, and builds an optimized portfolio using Black-Litterman optimization — all orchestrated by a multi-agent LLM system.

Supports portfolio import (CSV/PDF/screenshot), follow-up conversations, live rebalancing, risk decomposition, S&P 500 benchmarking, and exportable investment memos.

![RoboAdvisor AI Screenshot](docs/screenshot.png)

**[Try the Live Demo →](https://robo-advisor-ai-umber.vercel.app/)**

## What It Does

1. **You describe your goals in plain English** — "I have $100K, moderate risk, 5-year horizon, interested in AI"
2. **Three AI agents coordinate behind the scenes:**
   - **Intake Agent** — Parses your input, asks follow-ups if anything's missing
   - **Research Agent** — Selects relevant tickers, fetches live prices, fundamentals, technicals, and news sentiment in parallel
   - **Strategy Agent** — Generates market views via Claude, runs Black-Litterman optimization, computes risk decomposition, benchmarks against S&P 500
3. **You get an optimized portfolio** with allocations, share counts, expected return, Sharpe ratio, risk contribution per position, benchmark comparison, and strategy reasoning
4. **You can ask follow-ups** — "Why is NVDA weighted so high?", "What if NVDA drops 20%?", "Explain the Sharpe ratio"
5. **You can rebalance** — "Add TSLA", "Make it more conservative", "Remove INTC" triggers a full re-research and re-optimization
6. **You can import your existing portfolio** — Upload a brokerage CSV, PDF statement, or screenshot and build on top of your current holdings

## Architecture

```
User Input (natural language or file upload)
        │
        ▼
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ Intake Agent │────▶│Research Agent│────▶│Strategy Agent │
│  (Sonnet)    │     │  (Haiku +   │     │  (Sonnet +    │
│              │     │   yfinance + │     │ Black-Litterman│
│ Parse profile│     │   NewsAPI)   │     │  optimizer)   │
└──────────────┘     └─────────────┘     └──────────────┘
        │                   │                    │
        └───────────────────┴────────────────────┘
                            │
                    ┌───────▼───────┐
                    │   Supabase    │         ┌──────────────┐
                    │  (persistent  │         │Follow-up Agent│
                    │   memory +    │         │ (Q&A + rebal) │
                    │   cache)      │         └──────────────┘
                    └───────────────┘
```

**LLM Orchestration:** LangGraph manages the agent state machine — conditional routing (intake loops if profile is incomplete), shared state passing, sequential execution, and post-strategy follow-up/rebalancing detection.

**Cost Optimization:** Haiku handles ticker selection and sentiment scoring (~$0.001/call). Sonnet handles intake parsing, strategy views, and reasoning where quality matters (~$0.01/call). Total cost per portfolio: ~$0.05-0.10.

**Portfolio Optimization:** Black-Litterman model blends market equilibrium returns (from market cap weights) with Claude-generated "views" (expected returns per asset with confidence levels) to produce optimal portfolio weights. Risk decomposition shows marginal contribution per position.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude (Sonnet 4 + Haiku 4.5) |
| Orchestration | LangGraph |
| Backend | FastAPI + WebSocket |
| Frontend | React + Vite + Tailwind + Recharts |
| Data | yfinance (prices/technicals), NewsAPI (sentiment) |
| Optimization | Black-Litterman (numpy/scipy) |
| Database | Supabase (PostgreSQL) |
| Deployment | Railway (backend) + Vercel (frontend) |

## Features

| Feature | Description |
|---------|-------------|
| Multi-Agent Pipeline | Intake → Research → Strategy with LangGraph conditional routing |
| Black-Litterman Optimization | Institutional-grade portfolio math with LLM-generated views and confidence levels |
| Parallel Research | 8 tickers researched simultaneously via ThreadPoolExecutor (~4s vs ~24s) |
| Live Streaming | WebSocket streams per-ticker status updates: "Researching AAPL...", "Running optimizer..." |
| Follow-up Conversations | Ask "Why NVDA at 48%?" or "Explain the Sharpe ratio" after getting your portfolio |
| Portfolio Rebalancing | "Add TSLA" or "Make it more conservative" triggers full re-research and re-optimization |
| Portfolio Import | Upload brokerage CSV, PDF statement, or screenshot — Claude extracts holdings |
| Risk Decomposition | Marginal risk contribution per position — "NVDA contributes 50% of portfolio risk" |
| S&P 500 Benchmark | Side-by-side comparison: your return, volatility, and Sharpe vs the index |
| Export Investment Memo | Styled HTML report with profile, allocations, risk, benchmark, research, BL parameters |
| Research Cache | Supabase caches research for 1 hour — repeat queries are instant |
| Cost-Optimized Models | Haiku for classification/sentiment, Sonnet for strategy — 10x cheaper without quality loss |
| yfinance Dedup | In-memory .info cache — 1 API call per ticker instead of 4 |
| Persistent Memory | Conversations, profiles, research, and strategies saved to Supabase |

## How Black-Litterman Works Here

Traditional mean-variance optimization (Markowitz) uses only historical returns — garbage in, garbage out. Black-Litterman improves this by:

1. **Starting with market equilibrium** — Reverse-engineer expected returns from market cap weights (what the market "believes")
2. **Adding views** — Claude analyzes fundamentals, technicals, and news sentiment to generate expected return views with confidence levels
3. **Blending** — The math combines market consensus with Claude's views, weighted by confidence, to produce posterior expected returns
4. **Optimizing** — Standard optimization on the blended returns produces portfolio weights that reflect both market wisdom and AI analysis
5. **Risk decomposition** — Marginal risk contribution per position identifies concentrated risk (e.g., "NVDA is 36% of weight but 50% of risk")

The confidence parameter is key: a high-confidence bullish view on NVDA shifts more weight toward it. A low-confidence bearish view on a stock barely moves the needle. This prevents the optimizer from going all-in on any single AI opinion.

## Project Structure

```
robo-advisor-ai/
├── backend/
│   ├── main.py                      # FastAPI server (REST + WebSocket)
│   ├── graph.py                     # LangGraph orchestration + follow-up routing
│   ├── status.py                    # Thread-safe status streaming
│   ├── models.py                    # Pydantic data models
│   ├── agents/
│   │   ├── state.py                 # Shared agent state (phase tracking)
│   │   ├── intake.py                # Profile parsing agent (with rebalance short-circuit)
│   │   ├── research.py              # Ticker selection + parallel research
│   │   ├── strategy.py              # BL optimization + benchmark + risk decomposition
│   │   └── followup.py              # Post-strategy Q&A + rebalance detection
│   ├── tools/
│   │   ├── market_data.py           # yfinance with in-memory cache
│   │   ├── technicals.py            # RSI, MACD, Bollinger Bands
│   │   ├── sentiment.py             # NewsAPI + Claude Haiku sentiment
│   │   ├── research_pipeline.py     # Parallel orchestration + Supabase cache
│   │   ├── portfolio_import.py      # CSV/image/PDF portfolio extraction
│   │   └── export_report.py         # HTML investment memo generator
│   ├── optimizer/
│   │   └── black_litterman.py       # BL implementation + risk contributions
│   └── db/
│       ├── schema.sql               # Supabase table definitions
│       ├── supabase_client.py       # DB connection
│       └── memory.py                # Persistent storage + research cache
├── frontend/
│   └── src/
│       ├── App.jsx                  # Two-panel layout
│       ├── components/
│       │   ├── Chat.jsx             # Chat + portfolio upload button
│       │   ├── Portfolio.jsx        # Dashboard (risk bars, benchmark, export)
│       │   ├── AllocationChart.jsx  # Donut chart
│       │   └── AssetCard.jsx        # Research card
│       └── hooks/
│           └── useWebSocket.js      # Real-time WebSocket connection
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: [Anthropic](https://console.anthropic.com/), [NewsAPI](https://newsapi.org/), [Supabase](https://supabase.com/)

### 1. Clone & Configure

```bash
git clone https://github.com/AAP67/robo-advisor-ai.git
cd robo-advisor-ai
cp .env.example .env
# Edit .env with your API keys
```

### 2. Database Setup

Create a Supabase project, then run `backend/db/schema.sql` in the Supabase SQL Editor.

### 3. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and start investing.

## Built By

**[Karan Rajpal](https://www.linkedin.com/in/krajpal/)** — UC Berkeley Haas MBA '25 · LLM Validation @ Handshake AI (OpenAI/Perplexity) · Former 5th hire at Borderless Capital
