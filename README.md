# Skywalker Scout

Autonomous Real Estate Due Diligence Engine for Bengaluru properties.

Skywalker Scout transforms unstructured web data -- K-RERA filings, market listings, Reddit threads, Google review snippets, news articles, and forum discussions -- into structured, institutional-grade investment dossiers. It combines Anakin AI for web intelligence gathering, a deterministic evidence ledger for auditability, and Google Gemini for strict JSON formatting.

---

## Problem

Evaluating a real estate investment in Bengaluru requires manually checking dozens of sources:

- **RERA portal** for registration and compliance status
- **Consumer forums** for pending legal complaints
- **Reddit and forums** for homebuyer experiences (delays, water issues, maintenance quality)
- **Google-indexed review snippets** for rating and resident feedback signals
- **Property portals** (99acres, MagicBricks, CommonFloor) for pricing trends
- **News outlets** for builder reputation and legal history

This process takes hours per property and produces inconsistent results. Data is scattered, contradictory, and hard to reconcile -- a builder's website might say "Ready to Move" while Reddit threads report 18-month delays.

## Solution

Skywalker Scout automates the entire due diligence workflow in four stages:

1. **Web Intelligence (Anakin AI)** -- Performs targeted web searches, gathers Google-indexed review snippets, scrapes priority property and Reddit pages, crawls official sites, and runs deep agentic research.

2. **Evidence Ledger** -- Converts raw Anakin output into traceable evidence items with source type, reliability, confidence, freshness, signal, and contradiction checks.

3. **AI Synthesis (Google Gemini)** -- Sends the gathered intelligence and evidence ledger to Gemini 3.1 Flash Lite, which formats the data into a strict Due Diligence Scorecard JSON without adding new research.

4. **Report Dashboard (Streamlit)** -- Presents the results as a single professional due-diligence dossier with risk summary, concerns, positive signals, financial/legal/community sections, and source evidence.

---

## Current Capabilities

- **Priority source routing**: K-RERA first, then Housing.com and NoBroker, Reddit community threads, Google review snippets, and infrastructure/general web search.
- **Evidence-first reporting**: every important source is classified and scored for reliability before Gemini formats the report.
- **Contradiction detection**: flags categories where positive and negative evidence both appear.
- **Financial viability signals**: captures pricing, rent, resale, amenities, and market-source evidence where available.
- **Legal/RERA review**: prioritizes official `rera.karnataka.gov.in` and other `.gov.in` / `.nic.in` domains.
- **Community intelligence**: searches Reddit with strict subreddit operators and scrapes discovered thread URLs instead of scraping Reddit homepages.
- **Review intelligence**: uses Anakin Search snippets for Google ratings/reviews rather than scraping Google Maps directly.
- **Professional dossier UI**: dark institutional theme, compact pipeline status, persisted last report, risk/strength sections, analytics charts, evidence ledger, and raw source expanders.

---

## Architecture

Anakin does ALL data gathering. Gemini only formats the output. The evidence engine adds deterministic audit metadata before Gemini receives the final formatting prompt.

```
User Input (Property Name)
        |
        v
+------------------+
|  Anakin Search    |  POST /v1/search (synchronous)
|  Priority Queries |  K-RERA, Housing.com, NoBroker, Reddit,
|                   |  Google review snippets, infrastructure
+------------------+
        |
        v
+------------------+
|  Anakin Scraper   |  POST /v1/url-scraper/batch (with useBrowser=True)
|  & Crawl API      |  Scrapes priority market/community URLs.
|  (Anti-Bot)       |  Crawls K-RERA/.gov.in/.nic.in where found.
+------------------+
        |
        v
+------------------+
|  Anakin Agentic   |  POST /v1/agentic-search (async)
|  Search           |  4-stage deep research pipeline
|  (Deep Research)  |  Returns summary + structured_data
+------------------+
        |
        v
+------------------+
|  Evidence Ledger  |  Deterministic source classification,
|  & Reliability    |  reliability, confidence, freshness,
|  Engine           |  signal, contradiction checks
+------------------+
        |
        v
+------------------+
|  Gemini 3.1       |  google-genai SDK (FORMATTER ONLY)
|  Flash Lite       |  Reformats evidence into JSON scorecard
|  (Optional)       |  Does NOT generate new research
+------------------+
        |
        v
+------------------+
|  Streamlit UI     |  Dark professional dossier, compact status,
|  (Dashboard)      |  analytics charts, persisted report, raw data
+------------------+
```


## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Streamlit 1.30+ | Professional dark dossier UI, sidebar controls, status/progress, expanders |
| Visualizations | Plotly | Section score chart and source mix/reliability diagnostics |
| Data Engine | Anakin Scraper API | Search API, URL Scraper (Anti-Bot), Crawl API, Agentic Search |
| Evidence Engine | Python | Source classification, reliability scoring, evidence ledger, contradiction checks |
| Formatter | Google Gemini 3.1 | Reformats Anakin data into structured JSON scorecard |
| HTTP Client | requests | Anakin API communication |
| Config | python-dotenv | Environment variable management |

## Project Structure

```
Skywalker-Scout/
    app.py              # Streamlit UI and main entry point
    anakin_engine.py     # Anakin AI client (search, reviews, deep research, polling)
    evidence_engine.py   # Evidence ledger, source reliability, contradiction checks
    rag_logic.py         # Gemini synthesis layer (scorecard generation)
    requirements.txt     # Python dependencies
    .env.example         # API key template
    .env                 # Your API keys (gitignored)
    .gitignore           # Git ignore rules
    .streamlit/
        config.toml      # Streamlit dark theme configuration
```

## Source Routing

The pipeline uses explicit source priorities instead of treating all search results equally:

| Priority | Source | Purpose |
|----------|--------|---------|
| 1 | `rera.karnataka.gov.in` | Official project registration, approval, and compliance status |
| 2 | Housing.com | Structured pricing, amenities, possession, rent, resale, and market context |
| 3 | NoBroker.in | Owner-written sale/rent descriptions and practical property details |
| 4 | Reddit `r/bangalore`, `r/IndiaInvestments` | Community complaints, buyer sentiment, water/traffic/builder issues |
| 5 | Google-indexed snippets | Aggregate rating and helpful review text without scraping Google Maps directly |
| 6 | General web/infrastructure sources | Roads, metro, water, local development, builder/news context |

## Setup

### Prerequisites

- Python 3.10+
- An [Anakin AI](https://anakin.io) API key
- A [Google Gemini](https://aistudio.google.com/apikey) API key

### Installation

```bash
# Clone the repository
git clone https://github.com/YashDaga17/Skywalker-Scout.git
cd Skywalker-Scout

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```
ANAKIN_API_KEY=your_anakin_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Running

```bash
source venv/bin/activate
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## How It Works

### 1. Anakin Engine (`anakin_engine.py`)

The `AnakinClient` class provides comprehensive intelligence gathering:

**Search API** (`POST /v1/search` -- synchronous)
- **`search(prompt, limit)`** -- AI-powered web search for property and infrastructure data.
- **`perform_search(prompt, limit)`** -- Alias for targeted source searches.
- **`google_reviews_search(property_name)`** -- Specialized search for Google Maps ratings.
- **`rera_property_search(property_name)`** -- Prioritizes K-RERA official records.
- **`market_price_search(property_name)`** -- Prioritizes Housing.com and NoBroker for pricing, rent, resale, and amenities.
- **`reddit_community_search(property_name)`** -- Searches Reddit threads through strict subreddit operators before scraping thread URLs.

**URL Scraper** (`POST /v1/url-scraper/batch` -- async with polling)
- **`batch_scrape_urls(urls, use_browser=True)`** -- Scrapes priority market, community, property, and infrastructure URLs using a stealth, anti-bot cloud browser.

**Crawl API** (`POST /v1/crawl` -- async with polling)
- **`submit_crawl_job(url, use_browser=True)`** -- Used specifically to deep-crawl official K-RERA, `.gov.in`, and `.nic.in` websites discovered during the search phase.

**Agentic Search** (`POST /v1/agentic-search` -- async with polling)
- **`submit_agentic_search(prompt)`** -- Starts a 4-stage deep research pipeline.
- **`poll_agentic_search(job_id)`** -- Polls every 10s until research is complete.

All methods return structured dicts with `success`, `error`, and data fields. HTTP failures are caught and returned as error dicts -- the application never crashes from API failures.

### 2. RAG Logic (`rag_logic.py`)

The `format_scorecard(intelligence)` function:

1. Formats raw Anakin data, priority search results, scraped pages, crawled government pages, agentic research, and the evidence ledger into a structured prompt.
2. Sends the prompt to Gemini 3.1 Flash Lite with strict formatter-only instructions.
3. Uses `response_mime_type="application/json"` to ensure structured output.
4. Parses and validates the JSON response.
5. Computes a composite risk score (0-100) from section scores when needed.

The scorecard contains: Financial Viability, Legal/RERA Status, Community Sentiment, Google Reviews, Risk Score, Executive Summary, Red Flags, and Green Flags.

### 3. Evidence Engine (`evidence_engine.py`)

The evidence engine builds an auditable trail from Anakin data before Gemini formats the report:

- Classifies sources as official RERA, government, market portal, owner marketplace, community forum, Google review signal, or unclassified web.
- Gives priority to `rera.karnataka.gov.in`, then Housing.com, NoBroker, Reddit, and Google review snippets.
- Produces evidence items with claim, category, source id, confidence, freshness, and signal.
- Detects simple contradictions, such as positive and negative evidence appearing in the same category.
- Computes a report evidence quality score from source reliability, source coverage, official-source count, and evidence volume.

The ledger is included in the Gemini prompt and also rendered in the Streamlit dossier so users can audit the report.

### 4. Streamlit App (`app.py`)

The UI provides:

- **Professional dark theme** configured in `.streamlit/config.toml` and reinforced with app-level CSS.
- **Sidebar Controls** with Run/Clear actions and a source-routing panel.
- **Compact Pipeline Status** using `st.status`, `st.progress`, and a collapsed event log so Anakin logs do not overwhelm the main page.
- **Persisted Last Report** using `st.session_state["last_report"]`, so completed results remain visible after Streamlit reruns.
- **Executive Summary** with overall exposure score and risk bar.
- **Plotly Analytics** including section score diagnostics and source mix/reliability diagnostics.
- **Single Dossier Flow** -- Financial, Legal/RERA, Infrastructure, Community, Reviews, and Evidence sections in one scrollable report.
- **Risk Flags / Strength Signals** -- Investment risks and supporting positives presented together.
- **Evidence Ledger** -- Source reliability, confidence, and top evidence items.
- **Raw Intelligence** -- Expandable view of all source data from Anakin to maintain full transparency.

### UI Design Notes

- The interface intentionally avoids authentication/login flows and avoids decorative landing-page content.
- The main report is built as an operational dashboard/dossier, not a marketing page.
- The theme uses a restrained dark slate palette with blue/teal/amber accents for a professional investment-analysis feel.
- Google Maps markers use `folium.CircleMarker` to avoid broken Leaflet marker PNG requests.

---

## API Key Notes

**Anakin API Key**: Obtain from [anakin.io](https://anakin.io). Navigate to your account settings to generate an API access token. The Search API and Agentic Search endpoints require a paid/Pro account.

**Gemini API Key**: Obtain from [Google AI Studio](https://aistudio.google.com/apikey). The `gemini-3.1-flash-lite` model is used for cost-effective, high-throughput structured output generation.

---

## Error Handling

The application is designed for resilience:

- All Anakin API calls use `try/except` blocks with structured error returns
- Exponential backoff on polling prevents hammering the API
- Configurable timeouts: 30s for synchronous search, 120s for scrape/crawl polling, and up to 240-300s for agentic research
- Missing API keys are detected at startup with clear error messages
- Gemini failures raise explicit errors rather than returning stale/mock data
- Streamlit reruns preserve the last completed report in session state
- Pipeline logs are captured in a compact status container rather than printed as a wall of text

---

## Recent Improvements

- Added `evidence_engine.py` for deterministic source classification, reliability scoring, evidence items, and contradiction detection.
- Added targeted Anakin source methods for K-RERA, Housing.com, NoBroker, Reddit, and Google review snippets.
- Reworked the Streamlit UI into a persisted dark professional dossier.
- Added compact `st.status` execution tracking with progress and collapsed event logs.
- Added Plotly section score and source reliability charts.
- Fixed report disappearance after Streamlit reruns by storing the last report in `st.session_state`.
- Replaced default Leaflet markers with `folium.CircleMarker` to avoid missing marker icon requests.

---

## License

MIT
