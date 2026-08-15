# Airport Investment Intelligence Agent

An AI-powered conversational agent that helps analysts identify profitable airport modernization investment opportunities in the US. It combines public BTS aviation data with deterministic scoring logic and LLM-driven reasoning.

## Quick Start

You need **Python 3.11+**, **Node.js 18+**, and a free **Google Gemini API key** (or any other LLM provider key).

### 1. Setup

```bash
git clone <repo-url>
cd airport-investment-agent

# Python
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure

```bash
cp .env.example .env
```

Open `.env` and add your API key. The easiest option is Google Gemini (free tier):

```ini
LLM_MODEL=gemini/gemini-2.5-flash
GEMINI_API_KEY=your-key-here
```

To get a free Gemini key: go to https://aistudio.google.com/apikey and click "Create API Key".

Other providers work too — just set the matching `LLM_MODEL` and API key:
```ini
# OpenAI
LLM_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=your-key

# Anthropic
LLM_MODEL=anthropic/claude-sonnet-4-20250514
ANTHROPIC_API_KEY=your-key
```

### 3. Download data

```bash
python data/scripts/download_bts.py
```

This downloads aviation data from the Bureau of Transportation Statistics (BTS) public API. Takes 2-5 minutes depending on connection speed. The data is saved to `data/raw/` and `data/processed/`.

If the BTS API is slow or down, the script will still work with partial data — it downloads the most recent years first and falls back gracefully.

### 4. Run

Open **two terminals** from the project root:

**Terminal 1 — Backend (port 8000):**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend (port 5173):**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser. Both servers need to be running — the frontend proxies API calls to the backend.

## Example Queries

These are the four example questions from the exam. Try them to see the agent in action:

1. **"Which airports in New England are strong candidates for terminal expansion?"**
2. **"Compare LA and Santa Ana airport congestion levels."**
3. **"What is the percentage of long haul flights out of Anchorage airport?"**
4. **"What is the unmet flight demand in SFO airport and why?"**

## UI Controls

The header bar has controls that take effect immediately without restarting:

- **Model selector** — dropdown to switch LLM providers or enter a custom model string
- **Fast/Deep toggle** — Fast scores the top ~100 airports; Deep includes all ~125
- **Data vintage** — shows the loaded BTS data period and record count

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Conversational endpoint (LLM-powered) |
| `/airports/{code}/stats` | GET | KPIs for one airport |
| `/airports/compare` | POST | Compare airports on metrics |
| `/airports/score` | POST | Score and rank airports (IOS) |
| `/health` | GET | Status, model, data vintage |
| `/settings` | PATCH | Change model or analysis mode |

## Tests

```bash
python -m pytest tests/ -v
```

73 unit tests covering the scoring engine, data layer, and tool implementations.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design document covering scoring methodology, key tradeoffs, and where/how AI is used.
