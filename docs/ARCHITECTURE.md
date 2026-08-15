# Architecture & Design Document

## 1. System Overview

The Airport Investment Intelligence Agent is a conversational AI system that helps investment analysts identify profitable airport modernization opportunities in the United States. It combines deterministic scoring of public aviation data with LLM-driven orchestration and natural language synthesis.

The core investment thesis: **airports where demand exceeds capacity are the best renovation targets**, because expansion directly unlocks revenue — more gates mean more flights, more passengers, and more aeronautical fees.

### How It Works

```
User question (natural language)
    → LLM decides which tools to call
        → Tool: search_airports(region="New England")
        → Tool: score_airports(codes=["BOS","BDL","PVD"])
    → LLM synthesizes tool outputs into an analytical response
    → Response includes data citations, assumptions, and confidence caveats
```

The LLM never computes scores or fabricates data. It **orchestrates deterministic tools** and **explains results** — a deliberate separation that keeps the scoring auditable and the analysis conversational.

---

## 2. Architecture

### System Layers

```
┌────────────────────────────────────────────────────────────────┐
│                  Frontend  (React + Vite + TypeScript)          │
│            Chat UI — markdown rendering, structured data        │
├────────────────────────────────────────────────────────────────┤
│                  API Layer  (FastAPI)                           │
│   POST /chat     GET /airports/:code/stats                     │
│   POST /compare  POST /score       GET /health                 │
├────────────────────────────────────────────────────────────────┤
│               Agent Orchestrator  (LiteLLM)                    │
│   System prompt → tool selection → tool execution              │
│   → result synthesis → assumption injection                    │
├───────────────────────┬────────────────────────────────────────┤
│   Scoring Engine      │         Data Access Layer              │
│   Pure Python         │   pandas on cached BTS CSVs/Parquet    │
│   Deterministic       │   + airport reference data (JSON)      │
│   Configurable        │   + Census MSA population data         │
│   weights             │                                        │
└───────────────────────┴────────────────────────────────────────┘
```

### Request Flow (POST /chat)

1. User sends a message via the chat UI
2. FastAPI receives it, passes it to the agent orchestrator
3. Orchestrator builds the message list: system prompt + conversation history + user message
4. LiteLLM calls the configured LLM with six tool schemas
5. If the LLM requests tool calls, the orchestrator executes them (pure Python, in-memory data) and feeds results back
6. Steps 4-5 repeat up to 6 rounds (multi-step queries may chain tools)
7. The LLM produces a final natural language response synthesizing all tool outputs
8. Response is returned with metadata: tools called, data vintage, assumptions

### Key Design Decision: LLM as Orchestrator, Not Calculator

The LLM's role is strictly limited to three things:
- **Tool selection** — deciding which tools to call based on the user's question
- **Parameter extraction** — mapping natural language ("New England airports") to tool inputs (`region="New England"`)
- **Response synthesis** — explaining tool outputs in context, with citations and caveats

All scoring, ranking, normalization, and data aggregation is done by deterministic Python functions. This means:
- Scores are reproducible — same inputs always produce the same output
- The scoring logic is auditable — no black-box LLM math
- The system works with any LLM provider — swap the model string, behavior stays the same
- Scoring can be tested with standard unit tests (42 tests for the scoring engine alone)

---

## 3. Scoring Methodology: Investment Opportunity Score (IOS)

### The Six Components

| # | Component | Formula | Weight | What It Captures |
|---|---|---|---|---|
| 1 | **Load Factor** | passengers / available_seats | 0.20 | Demand-to-supply ratio. High = market exists but can't grow without infrastructure |
| 2 | **Utilization Rate** | departures_performed / departures_scheduled | 0.20 | Physical constraint. Near 100% = no room for new routes |
| 3 | **Passenger Growth YoY** | (pax_current - pax_prior) / pax_prior | 0.25 | Demand momentum. The strongest investment signal — growing demand at a constrained airport |
| 4 | **Congestion Index** | From delay data or utilization proxy | 0.15 | Operational pain. High delays or near-capacity operations = urgency for investment |
| 5 | **Long-Haul Ratio** | flights >1500mi / total flights | 0.10 | Revenue quality. Long-haul routes generate higher per-passenger revenue |
| 6 | **Unmet Demand Proxy** | MSA population growth - airport capacity growth | 0.10 | Forward-looking potential. Positive gap = regional demand outpacing airport capacity |

### Composite Formula

```
IOS = Σ(weight_i × normalized_i) / Σ(weight_i for available components) × 100
```

Each component is normalized to [0, 1] via min-max normalization across all airports in the active dataset, then weighted and summed. The result is scaled to 0-100.

### Weight Rationale

Passenger growth carries the highest weight (0.25) because it's the strongest forward-looking investment signal — a growing, constrained airport is the ideal target. Load factor and utilization share 0.20 each as the primary constraint indicators. Congestion at 0.15 captures operational urgency. Long-haul ratio and unmet demand carry lower weights (0.10 each) because they're secondary signals — valuable for differentiation but not primary investment drivers.

Weights are configurable via environment variables or per-query overrides, so analysts can adjust the formula for different investment strategies (e.g., emphasizing long-haul for premium terminal projects).

### Normalization

Min-max normalization: `(value - min) / (max - min)`, computed across all airports in the active dataset.

- Values outside [min, max] are clamped to [0, 1]
- When min equals max (uniform data), the normalized value is 0.5 (neutral midpoint)
- Bounds are recomputed for each scoring run, so scores reflect the current dataset
- In "fast" mode (default), bounds are computed over the top ~100 airports by passenger volume. In "deep" mode, all ~125 commercial airports. This means a score of 85 in fast mode is "85th percentile among the top 100" — not necessarily the same as in deep mode

### Missing Data Handling

Not all airports have data for all six components. Small regional airports may lack delay data or MSA population data.

**Approach:** When components are missing, the IOS divides by the actual weight sum of available components (not the full 1.0). An airport with 4/6 components is scored relative to those 4, not penalized for missing data.

**Confidence bands** communicate data completeness:
- **High** — all 6 components available
- **Medium** — 4 or 5 components
- **Low** — fewer than 4 components

The agent explicitly calls out confidence differences when comparing airports.

**Alternatives considered and rejected:**
- *Zero-fill missing components:* Punishes airports for missing data rather than missing performance
- *Exclude airports with incomplete data:* Loses coverage of interesting mid-size targets
- *Impute from peers:* Statistically sounder but hard to audit and explain to analysts

### Congestion Index: Dual-Mode Design

The congestion index supports two data sources:

1. **Delay data (preferred):** When BTS on-time performance data is available — 60% delay frequency (fraction of flights delayed) + 40% normalized delay magnitude (average delay minutes / 60, capped at 1.0). This directly measures operational pain.

2. **Utilization proxy (fallback):** When delay data is unavailable — 60% utilization rate + 40% load factor, scaled by 0.8. The 0.8 dampener prevents overestimating congestion from non-delay data. This captures operational strain without delay-specific information.

The proxy produces conservative scores — genuinely congested airports will score lower than they would with real delay data. When delay data becomes available, scores shift upward automatically with no code changes.

---

## 4. Where AI Is Used (and Where It Isn't)

### The LLM Does:

| Capability | How |
|---|---|
| Understand user intent | Maps "Which New England airports need expansion?" to `search_airports(region="New England")` then `score_airports(codes=[...])` |
| Select tools | Chooses from 6 tools based on the question type |
| Extract parameters | Converts natural language to typed function arguments |
| Chain tool calls | May call search → stats → score in sequence for complex queries |
| Synthesize results | Turns JSON tool outputs into analyst-readable narrative |
| Maintain context | Uses conversation history for follow-up questions |
| Flag uncertainty | Distinguishes data-backed facts from analytical opinions |

### The LLM Does NOT:

| Responsibility | What Does It Instead |
|---|---|
| Compute scores | `scoring/engine.py` — pure Python, deterministic |
| Normalize metrics | `scoring/normalizer.py` — min-max with clamping |
| Calculate KPIs | `scoring/metrics.py` — typed functions with edge case handling |
| Query data | `data/bts.py` — pandas aggregations on cached DataFrames |
| Rank airports | `scoring/engine.py` → `rank_airports()` — sort by IOS descending |
| Store conversations | `agent/conversation.py` — in-memory OrderedDict with LRU |

### The Boundary (Illustrated)

```
     LLM World                           Deterministic World
  ┌──────────────┐                    ┌──────────────────────┐
  │              │   "Call            │                      │
  │  "Which NE   │   score_airports   │  search_airports()   │
  │   airports   │───with codes───►   │  get_airport_stats() │
  │   are best   │   from search"     │  score_airports()    │
  │   targets?"  │                    │  compare_airports()  │
  │              │   ◄── JSON ────    │  get_flight_brkdn()  │
  │  Synthesize  │   results back     │  get_demand_anlys()  │
  │  into prose  │                    │                      │
  └──────────────┘                    └──────────────────────┘
```

This boundary is enforced architecturally: the LLM receives tool schemas (JSON descriptions of what each tool does) and can only interact with data through tool calls. It never has direct access to DataFrames or scoring functions.

---

## 5. LLM Integration: Provider-Agnostic via LiteLLM

### Why LiteLLM

The system uses LiteLLM as its sole LLM abstraction. One `acompletion()` call, one tool schema format. Switch providers via the UI dropdown or `.env` — no code changes.

| Provider | Model String | Cost |
|---|---|---|
| Google Gemini | `gemini/gemini-2.5-flash` | Free tier (default) |
| Anthropic | `anthropic/claude-sonnet-4-20250514` | Pay-per-token |
| OpenAI | `openai/gpt-4o-mini` | Pay-per-token |
| HuggingFace | `huggingface/mistralai/Mistral-7B-Instruct-v0.3` | Free tier |
| Local (Ollama) | `ollama/llama3` | Free (local GPU) |

### Runtime Model Switching

The active model can be changed at runtime without restarting the server. The header bar displays the current model as a dropdown — clicking it shows all preconfigured options plus a custom model input for any LiteLLM-compatible model string. The change takes effect on the next chat message. API keys must be preconfigured in `.env` for the chosen provider; the UI only switches the model identifier, never handling credentials.

### System Prompt Design

The prompt uses a rules-based format (~700 tokens) rather than persona-heavy instructions:
- **Role:** one sentence defining the analyst persona
- **Capabilities:** enumeration of available tools
- **Investment thesis:** domain context for analytical reasoning
- **Metric reference table:** what each KPI measures
- **Eight behavioral rules:** concrete instructions ("Always use tools to get data. Never fabricate numbers.")
- **Output style:** markdown formatting, tables for comparisons, investment takeaways

Combined with tool schemas (~800 tokens), each LLM call has ~1,500 tokens of fixed overhead — well within context windows for multi-turn conversations.

### Agent Loop

The orchestrator runs up to 6 tool-calling rounds per query. Each round:
1. Call the LLM with the current message history
2. If the LLM requests tool calls, execute all of them
3. Feed tool results back as `tool` messages
4. Repeat until the LLM produces a text response (no more tool calls)

The 6-round cap prevents runaway loops while allowing complex multi-step queries (e.g., search → stats → compare → score). A complex query may take 15-30 seconds due to multiple LLM round-trips — acceptable for analytical work.

---

## 6. Data Sources

### Primary: BTS T-100 Domestic Segment Data

| Attribute | Detail |
|---|---|
| **Source** | Bureau of Transportation Statistics (data.bts.gov) |
| **Access** | SODA API with pagination (50K rows/page) |
| **Content** | Passengers, freight, seats, departures performed/scheduled, distance — by carrier, by origin-destination, monthly |
| **Coverage** | All US domestic carriers, all US airports |
| **Freshness** | ~2 months lag from reporting period |
| **Volume** | ~400K-600K rows per year |
| **Local format** | Downloaded as CSV, optionally converted to Parquet for faster reads |

This is the load-bearing dataset. All six KPIs derive from T-100 segment data (except unmet demand, which also uses Census data).

### Secondary: Airport Reference Data

Static JSON bundling 125 US commercial airports with IATA code, name, city, state, coordinates, hub classification (large/medium/small/non-hub), runway count, and estimated annual passengers. Sourced from FAA database and OpenFlights.

Includes a region-to-state mapping (11 US regions) for natural language queries like "New England airports."

### Secondary: Census MSA Population Data

Metropolitan Statistical Area population time series (60 MSAs, 2021-2024) from Census Bureau estimates. Used to compute the Compound Annual Growth Rate (CAGR) for the unmet demand proxy — comparing regional population growth to airport capacity growth.

An airport-to-MSA mapping links each airport to its metropolitan area.

### What We Don't Use (and Why)

| Data Source | Why Not |
|---|---|
| **BTS On-Time Performance** | ~1GB/year, separate download. Congestion uses a utilization proxy instead. Could be added as a data extension. |
| **Real-time flight data (AviationStack)** | 100 free requests/month. Not needed for historical investment analysis. |
| **International traffic data** | Out of scope — US domestic only per exam framing |
| **Construction costs / ROI models** | The agent identifies *where* to invest, not *how much* it costs |
| **Denied boarding / displaced traffic** | Not freely available at the airport level. Approximated via unmet demand proxy. |

---

## 7. Key Tradeoffs

### Data Freshness vs. Availability

**Choice:** All data is pre-downloaded and cached locally. No external API calls at query time.

**Why:** Investment analysis is not time-sensitive to the minute — BTS data already lags ~2 months. Local caching eliminates API rate limits, network failures, and latency as failure modes. The download script (`download_bts.py`) refreshes data when newer months become available.

**Downside:** Data is frozen at download time. An analyst asking about "recent trends" gets data from the last download, not real-time figures. The system communicates this via the data vintage indicator in the UI and in every response.

### LLM vs. Deterministic Logic

**Choice:** The LLM orchestrates; deterministic code computes.

**Why:** Scoring must be reproducible and auditable. An analyst who asks "Why did BOS score 78?" should be able to trace the answer through Python functions, not wonder what the LLM hallucinated. The LLM adds value in understanding intent, selecting tools, and synthesizing results in plain English — tasks where flexibility matters more than precision.

**Downside:** The system can't answer questions that require judgment beyond its six tools. "Is this a good time to invest in airport infrastructure given rising interest rates?" requires economic reasoning the tools don't provide. The LLM can offer opinions but the system prompt instructs it to label these as analytical opinions, not data-backed conclusions.

### Provider Lock-In vs. Simplicity

**Choice:** LiteLLM abstraction with a single `LLM_MODEL` config string. No provider-specific code.

**Why:** The exam evaluates engineering judgment, not API integration. One config change should switch providers. The user's cost constraint (prefer free tiers) makes multi-provider support essential.

**Downside:** LiteLLM adds a layer of indirection. Tool-use behavior varies by provider — some handle complex schemas better than others. Debugging LLM issues requires understanding LiteLLM's provider-specific translations.

### Pre-Computed vs. Live Scoring

**Choice:** Scores are computed on demand, not pre-computed at startup.

**Why:** Analysts may query different years, different airport sets, or custom weights. Pre-computing assumes a fixed analysis context. On-demand scoring supports the conversational pattern where the analyst refines their query iteratively.

**Downside:** Scoring calls compute normalization bounds across all ~100 airports for each request. This adds latency but keeps scores contextually accurate. If performance becomes an issue, bounds can be cached per year.

### Depth vs. Breadth (Fast/Deep Mode)

**Choice:** Default "fast" mode limits scoring to the top ~100 airports by passenger volume. "Deep" mode includes all ~125.

**Why:** 95% of analyst queries focus on large and medium hubs. Fast mode speeds up normalization and reduces noise from small airports with sparse data.

**Downside:** Small-airport investment opportunities are invisible in fast mode. Scores are relative to the active set — an 85 in fast mode means "85th percentile among the top 100," which may differ from deep mode. The mode is switchable at runtime via the header toggle or configurable as the default via `ANALYSIS_MODE` in `.env`.

---

## 8. Assumptions and Limitations

### Assumptions

1. **US domestic only.** International airports and international route data are out of scope. All analysis applies to domestic flights within the United States.

2. **Utilization as congestion proxy.** Without on-time performance data, congestion is approximated from departure utilization and load factor. This conflates "efficiently scheduled" with "congested" — an airport running 95% of scheduled departures might be well-managed, not congested. Real delay data would produce more accurate congestion scores.

3. **Unmet demand approximation.** "Unmet demand" is proxied by the gap between MSA population growth and airport capacity growth. Actual denied boarding, displaced traffic, and competing airport dynamics are not captured. The proxy assumes that regional population growth drives proportional air travel demand.

4. **Static airport metadata.** Airport characteristics (hub classification, runway count) are bundled as static data. Real-world changes (new runways, reclassification) require a data refresh.

5. **Load factor from domestic segments only.** Load factor is computed from BTS T-100 domestic data. Airports with significant international traffic (JFK, MIA, LAX) may show artificially low load factors because international passengers are excluded.

6. **Revenue correlation.** The IOS assumes that high load factor + high utilization + growing demand correlates with renovation profitability. It does not model construction costs, regulatory timelines, land availability, or competitive dynamics.

### Limitations

1. **No financial modeling.** The system identifies *where* to invest, not *how much* or *what returns to expect*. ROI projections, NPV calculations, and cost estimates are out of scope.

2. **Data lag.** BTS data lags ~2 months. Scoring reflects the most recent downloaded period, not current operations.

3. **No real-time data.** The system does not track live flights, current delays, or breaking operational changes.

4. **Conversation state is ephemeral.** Conversations are stored in memory and lost on server restart. There is no persistent storage.

5. **Single-user demo.** No authentication, no multi-tenancy, no concurrent user isolation beyond conversation IDs.

6. **No automated data refresh.** BTS data must be manually re-downloaded when newer months become available.

---

## 9. Project Structure

```
airport-investment-agent/
├── backend/
│   ├── main.py                 # FastAPI app, CORS, startup data loading
│   ├── config.py               # Settings from .env: model, mode, weights
│   ├── agent/
│   │   ├── orchestrator.py     # LiteLLM agent loop (6-round tool calling)
│   │   ├── tools.py            # 6 tool implementations (pure Python)
│   │   ├── tool_schemas.py     # JSON schemas for LLM function calling
│   │   ├── prompts.py          # System prompt (rules-based, ~700 tokens)
│   │   └── conversation.py     # In-memory conversation store (LRU, 100 max)
│   ├── scoring/
│   │   ├── engine.py           # IOS computation, ranking, confidence
│   │   ├── metrics.py          # 6 KPI calculators (load, util, growth, etc.)
│   │   └── normalizer.py       # Min-max normalization across dataset
│   ├── data/
│   │   ├── loader.py           # BTS CSV/Parquet loading with caching
│   │   ├── airports.py         # Airport reference data (125 US airports)
│   │   ├── bts.py              # BTS T-100 query functions
│   │   └── census.py           # MSA population data for demand proxy
│   └── api/
│       ├── routes.py           # 5 FastAPI endpoints
│       └── schemas.py          # Pydantic request/response models
├── frontend/
│   └── src/
│       ├── App.tsx             # Layout with header and chat panel
│       ├── components/
│       │   ├── ChatPanel.tsx   # Message list, input, suggestion buttons
│       │   ├── MessageBubble.tsx # Markdown rendering, tool metadata
│       │   └── DataVintage.tsx # Model and data vintage badges
│       ├── hooks/useChat.ts    # Chat state, API calls, conversation ID
│       └── types/index.ts      # TypeScript interfaces
├── data/
│   ├── reference/              # Static datasets (airports, regions, MSA)
│   └── scripts/download_bts.py # BTS T-100 data download via SODA API
├── tests/                      # 73 unit tests (scoring, data, tools)
├── docs/ARCHITECTURE.md        # This document
└── README.md                   # Setup and run instructions
```

---

## 10. Technology Choices

| Layer | Technology | Why This |
|---|---|---|
| Backend | Python 3.11+, FastAPI | Async API, excellent pandas ecosystem, fast development |
| LLM | LiteLLM | Provider-agnostic tool-use, 140+ providers, single interface |
| Data | pandas, pyarrow | Fast analytical queries on in-memory DataFrames |
| Scoring | Pure Python | Deterministic, auditable, no ML dependencies, fully testable |
| Frontend | React + Vite + TypeScript | Fast dev server, type safety, markdown rendering via react-markdown |
| Validation | Pydantic | Request/response validation, auto-generated API docs |
| Config | python-dotenv | Simple .env-based configuration, no infrastructure |
