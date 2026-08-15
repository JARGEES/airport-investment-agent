# Airport Investment Intelligence Agent

An AI-powered conversational agent that helps analysts identify profitable airport modernization investment opportunities in the US. It combines public BTS aviation data with deterministic scoring logic and LLM-driven reasoning.

## Prerequisites

- **Python 3.11+** — backend and data processing
- **Node.js 18+** — frontend dev server
- **API key** for at least one LLM provider (Google Gemini has a generous free tier)

## Setup

### 1. Clone and enter the project

```bash
cd airport-investment-agent
```

### 2. Python environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Configuration

```bash
cp .env.example .env
```

Edit `.env` and set your LLM model and API key:

```ini
# Google Gemini (free tier, recommended for getting started)
LLM_MODEL=gemini/gemini-2.5-flash
GEMINI_API_KEY=your-key-here

# Or Anthropic Claude
# LLM_MODEL=anthropic/claude-sonnet-4-20250514
# ANTHROPIC_API_KEY=your-key-here

# Or OpenAI
# LLM_MODEL=openai/gpt-4o-mini
# OPENAI_API_KEY=your-key-here
```

### 5. Download BTS data

```bash
python data/scripts/download_bts.py
```

This downloads T-100 domestic segment data from the Bureau of Transportation Statistics via the SODA API. It fetches up to 3 years of data and saves to `data/raw/`. First run may take a few minutes depending on API speed.

## Running

Start the backend and frontend in separate terminals:

**Terminal 1 — Backend:**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

## Example Queries

Try these questions to see the agent's capabilities:

1. **"Which airports in New England are strong candidates for terminal expansion?"**
   The agent searches for New England airports, scores them using the Investment Opportunity Score, and explains which ones show the strongest combination of demand growth and capacity constraints.

2. **"Compare LA and Santa Ana airport congestion levels."**
   Side-by-side comparison of LAX and SNA on congestion and related metrics, with rankings showing which airport is more constrained.

3. **"What is the percentage of long haul flights out of Anchorage airport?"**
   Flight distance breakdown for ANC — short, medium, and long-haul percentages with top carriers and destinations.

4. **"What is the unmet flight demand in SFO airport and why?"**
   Demand analysis for SFO — capacity trend over available years, MSA population growth vs airport capacity growth, and a qualitative assessment of the demand gap.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Main conversational endpoint (LLM-powered) |
| `/airports/{iata_code}/stats` | GET | Direct KPI access for one airport |
| `/airports/compare` | POST | Compare multiple airports on metrics |
| `/airports/score` | POST | Score and rank airports (IOS) |
| `/health` | GET | Status, active model, data vintage |
| `/settings` | PATCH | Change model or analysis mode at runtime |

## Configuration Options

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `gemini/gemini-2.5-flash` | LiteLLM model string |
| `ANALYSIS_MODE` | `fast` | `fast` (top ~100 airports) or `deep` (all ~125) |
| `BTS_DATA_YEARS` | `3` | Years of BTS data to download (1-3) |
| `WEIGHT_LOAD_FACTOR` | `0.20` | IOS weight override |
| `WEIGHT_UTILIZATION` | `0.20` | IOS weight override |
| `WEIGHT_PAX_GROWTH` | `0.25` | IOS weight override |
| `WEIGHT_CONGESTION` | `0.15` | IOS weight override |
| `WEIGHT_LONG_HAUL_RATIO` | `0.10` | IOS weight override |
| `WEIGHT_UNMET_DEMAND` | `0.10` | IOS weight override |

## Runtime Controls

The header bar includes interactive controls that take effect immediately without restarting:

- **Model selector** — dropdown to switch between preconfigured LLM providers (Gemini, Anthropic, OpenAI, HuggingFace, Ollama) or enter a custom LiteLLM model string. API keys must be set in `.env` for the chosen provider.
- **Analysis mode** — toggle between Fast (top ~100 airports, faster scoring) and Deep (all airports, comprehensive).
- **Data vintage** — shows the loaded BTS data period and record count.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design document covering scoring methodology, AI/deterministic boundary, data sources, tradeoffs, and assumptions.

## Tests

```bash
python -m pytest tests/ -v
```

73 unit tests covering the scoring engine, data layer, and tool implementations.
