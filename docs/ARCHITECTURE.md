# Design & Architecture

## Overview

This is a tool-use AI agent for airport investment analysis. The core idea: the LLM doesn't compute anything — it decides which Python tools to call and then explains the results in plain English. All the scoring and data logic is deterministic and testable.

I built this with AI assistance for implementation speed, but the architecture and scoring design are my own decisions. The separation between LLM orchestration and deterministic scoring was the first thing I locked in — it directly addresses the exam requirement for deterministic logic while keeping the conversational interface flexible.

```
User question → LLM picks tools → tools query data + compute scores → LLM explains results
```

## How the System Fits Together

```
┌──────────────────────────────────────────────────────────┐
│              Frontend (React + Vite + TypeScript)         │
│          Chat UI, model selector, mode toggle             │
├──────────────────────────────────────────────────────────┤
│              API Layer (FastAPI)                          │
│   /chat   /stats   /compare   /score   /health           │
├──────────────────────────────────────────────────────────┤
│           Agent Orchestrator (LiteLLM)                   │
│   Picks tools → executes them → feeds results to LLM    │
├─────────────────────┬────────────────────────────────────┤
│  Scoring Engine     │       Data Layer                   │
│  Pure Python,       │  pandas DataFrames in memory,      │
│  deterministic      │  loaded from BTS CSV/Parquet       │
└─────────────────────┴────────────────────────────────────┘
```

The request flow for a chat message:

1. User sends a question through the React frontend
2. FastAPI passes it to the orchestrator
3. Orchestrator sends the question + 6 tool schemas to the LLM via LiteLLM
4. LLM decides which tools to call (e.g., `search_airports` then `score_airports`)
5. Orchestrator executes those tools — they're just Python functions querying pandas DataFrames
6. Results go back to the LLM, which writes a natural language response with citations
7. This can loop up to 6 times for multi-step queries

I used LiteLLM to keep it provider-agnostic. You can swap the model from the UI dropdown (Gemini, Claude, GPT, HuggingFace, Ollama) without touching code. API keys stay in `.env`.

---

## Scoring Methodology

### Investment Opportunity Score (IOS)

The investment thesis: airports where demand exceeds capacity are the best renovation targets, because expansion directly unlocks revenue.

I defined six KPIs that capture different aspects of this:

| Component | Formula | Weight | Why |
|---|---|---|---|
| Passenger Growth YoY | (current - prior) / prior | 0.25 | Strongest signal — growing demand at a constrained airport is the ideal target |
| Load Factor | passengers / seats | 0.20 | How full the planes are — high means demand exists |
| Utilization Rate | departures performed / scheduled | 0.20 | How close to physical capacity |
| Congestion Index | delay data or utilization proxy | 0.15 | Operational pain = urgency for investment |
| Long-Haul Ratio | flights >1500mi / total | 0.10 | Revenue quality — long-haul = higher per-passenger revenue |
| Unmet Demand | MSA pop growth - capacity growth | 0.10 | Forward-looking — is the region outgrowing the airport? |

The composite score:

```
IOS = Σ(weight × normalized_value) / Σ(weights of available components) × 100
```

Each KPI is normalized to [0,1] using min-max across all airports in the dataset, then weighted and summed. I gave passenger growth the highest weight because it's forward-looking — load factor tells you it's full *now*, growth tells you it's getting *fuller*.

Weights are configurable via env vars or per-query overrides, so an analyst can emphasize different factors for different investment strategies.

### Handling Missing Data

Not every airport has all 6 KPIs (small airports often lack delay data or MSA population data). Rather than penalizing them with zeros or excluding them entirely, I rescale by the actual weight sum. So an airport with 4/6 KPIs gets a valid 0-100 score based on those 4. A confidence tag (high/medium/low) tells the analyst how complete the data was.

### The Congestion Proxy

This was the trickiest design decision. The BTS on-time performance dataset has real delay data but it's ~1GB/year — too much for a 24-hour project. So I built a dual-mode congestion index:
- If delay data is available: 60% delay frequency + 40% delay magnitude
- Fallback: 60% utilization + 40% load factor, dampened by 0.8

The 0.8 dampener is important — without it, an airport running at 95% utilization looks "congested" even if it's just well-managed. The proxy is conservative on purpose; real delay data would give higher scores for genuinely congested airports.

If I had more time, I'd add the on-time performance dataset to get real congestion numbers.

---

## Where AI Is Used (and Where It Isn't)

This is the key architectural boundary:

**The LLM does:** understand what the user is asking, pick which tools to call, extract parameters from natural language ("New England" → `region="New England"`), and write analyst-readable explanations of the results.

**The LLM does NOT:** compute scores, run formulas, query data, or rank airports. All of that is pure Python with unit tests.

This matters because:
- Scores are reproducible — same inputs, same output, every time
- The logic is auditable — you can read `scoring/engine.py` and see exactly how the IOS is calculated
- It works with any LLM — swap providers and the scores don't change, only the explanation style does
- I can test it — 73 unit tests cover the scoring engine, data layer, and tools

The LLM interacts with data exclusively through 6 tool schemas (JSON descriptions). It can't see the DataFrames or call functions directly. The system prompt enforces rules like "always use tools, never fabricate numbers, cite the data period."

---

## Key Tradeoffs

**Pre-downloaded data vs. live API calls.** I chose to pre-download BTS data and query it in memory. BTS data is historical (lags ~2 months), doesn't change once published, and downloading on-demand would add 30-60s latency per chat message. The tradeoff: data is frozen at download time, so the UI always shows the data vintage so analysts know what period they're looking at.

**LLM as orchestrator vs. LLM as calculator.** The LLM only orchestrates — it can't compute. This makes scores deterministic and testable, but means the system can't answer open-ended questions that fall outside its 6 tools. The prompt tells the LLM to flag when it's giving an opinion vs. a data-backed answer.

**Provider-agnostic via LiteLLM.** One abstraction layer, swap the model string to change providers. The cost: LiteLLM is a heavy dependency and adds debugging indirection. The benefit: the reviewer can use whatever LLM they have an API key for.

**Fast/Deep analysis mode.** Fast mode (default) scores the top ~100 airports by passenger volume. Deep mode includes all ~125. Fast mode covers 95% of analyst queries and scores faster. The tradeoff: scores are relative to the active set, so an 85 in fast mode isn't the same as an 85 in deep mode.

---

## Limitations & What I'd Improve

- **Congestion is approximate** — utilization proxy instead of real delay data. Adding the on-time performance dataset would fix this.
- **No streaming responses** — multi-tool queries can take 15-30s with just a loading spinner. SSE streaming would improve the UX significantly.
- **Conversations aren't persisted** — in-memory only, lost on server restart. SQLite would be the obvious fix.
- **No international data** — US domestic only, per the exam scope.
- **The scoring doesn't model costs** — it identifies *where* to invest, not *how much it costs* or *what the ROI would be*.

---

## Data Sources

- **BTS T-100 Domestic Segment** (primary) — passengers, seats, departures, freight, distance by carrier/route/month. Downloaded via the SODA API at data.bts.gov. This is where all the KPIs come from.
- **Airport reference data** — 125 US commercial airports with metadata (hub size, runways, coordinates). Bundled as static JSON.
- **Census MSA population** — metropolitan area population trends for the unmet demand proxy. Bundled as static CSV.
