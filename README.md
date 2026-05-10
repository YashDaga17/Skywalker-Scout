# Skywalker Scout

Autonomous Real Estate Due Diligence Engine for Bengaluru properties.

Skywalker Scout transforms unstructured web data -- RERA filings, Reddit threads, Google Maps reviews, news articles, and forum discussions -- into structured, institutional-grade investment reports. It combines Anakin AI for web intelligence gathering with Google Gemini for data synthesis and audit.

---

## Problem

Evaluating a real estate investment in Bengaluru requires manually checking dozens of sources:

- **RERA portal** for registration and compliance status
- **Consumer forums** for pending legal complaints
- **Reddit and forums** for homebuyer experiences (delays, water issues, maintenance quality)
- **Google Maps reviews** for ground-truth resident feedback
- **Property portals** (99acres, MagicBricks, CommonFloor) for pricing trends
- **News outlets** for builder reputation and legal history

This process takes hours per property and produces inconsistent results. Data is scattered, contradictory, and hard to reconcile -- a builder's website might say "Ready to Move" while Reddit threads report 18-month delays.

## Solution

Skywalker Scout automates the entire due diligence workflow in three stages:

1. **Web Intelligence (Anakin AI)** -- Performs targeted web searches, fetches Google Maps reviews, and runs deep agentic research to gather data from all relevant sources automatically.

2. **AI Synthesis (Google Gemini)** -- Sends all gathered intelligence to Gemini 3.1 Flash Lite, which reconciles conflicting information, identifies red/green flags, and produces a structured Due Diligence Scorecard with risk scoring.

3. **Evidence Ledger** -- Converts raw Anakin output into traceable claims with source type, source reliability, confidence, freshness, and contradiction checks.

4. **Report Dashboard (Streamlit)** -- Presents the results as a single professional due-diligence dossier with risk summary, concerns, positive signals, financial/legal/community sections, and source evidence.

---

## Architecture

Anakin does ALL the data gathering. Gemini only formats the output.

```
User Input (Property Name)
        |
        v
+------------------+
|  Anakin Search    |  POST /v1/search (synchronous)
|  (Web + Infra +   |  Property data, Infrastructure, and Google Maps reviews
|   Reviews)        |  Returns URLs, titles, snippets, dates
+------------------+
        |
        v
+------------------+
|  Anakin Scraper   |  POST /v1/url-scraper/batch (with useBrowser=True)
|  & Crawl API      |  Bypasses bot protections to scrape top 5 URLs.
|  (Anti-Bot)       |  Deep crawls official .gov.in/.nic.in sites.
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
|  Gemini 3.1       |  google-genai SDK (FORMATTER ONLY)
|  Flash Lite       |  Reformats Anakin data into JSON scorecard
|  (Optional)       |  Does NOT generate new research
+------------------+
        |
        v
+------------------+
|  Streamlit UI     |  Plotly risk gauge, sidebar controls, scorecard tabs,
|  (Dashboard)      |  red/green flags, raw data expanders
+------------------+
```


## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Streamlit 1.30+ | Interactive dashboard with dark theme and sidebar |
| Visualizations | Plotly | Interactive gauge charts and data rendering |
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
- **`batch_scrape_urls(urls, use_browser=True)`** -- Scrapes top property URLs using a stealth, anti-bot cloud browser to bypass Cloudflare and security checks.

**Crawl API** (`POST /v1/crawl` -- async with polling)
- **`submit_crawl_job(url, use_browser=True)`** -- Used specifically to deep-crawl official government websites (e.g., RERA Karnataka, BBMP) discovered during the search phase.

**Agentic Search** (`POST /v1/agentic-search` -- async with polling)
- **`submit_agentic_search(prompt)`** -- Starts a 4-stage deep research pipeline.
- **`poll_agentic_search(job_id)`** -- Polls every 10s until research is complete.

All methods return structured dicts with `success`, `error`, and data fields. HTTP failures are caught and returned as error dicts -- the application never crashes from API failures.

### 2. RAG Logic (`rag_logic.py`)

The `gemini_fixer(intelligence)` function:

1. Formats all raw Anakin data into a structured markdown prompt
2. Sends it to Gemini 3.1 Flash Lite with a detailed system prompt defining the Due Diligence Scorecard schema
3. Uses `response_mime_type="application/json"` to ensure structured output
4. Parses and validates the JSON response
5. Computes a composite risk score (0-100) from section scores

The scorecard contains: Financial Viability, Legal/RERA Status, Community Sentiment, Google Reviews, Risk Score, Executive Summary, Red Flags, and Green Flags.

### 3. Evidence Engine (`evidence_engine.py`)

The evidence engine builds an auditable trail from Anakin data before Gemini formats the report:

- Classifies sources as official RERA, government, market portal, owner marketplace, community forum, Google review signal, or unclassified web.
- Gives priority to `rera.karnataka.gov.in`, then Housing.com, NoBroker, Reddit, and Google review snippets.
- Produces evidence items with claim, category, source id, confidence, freshness, and signal.
- Detects simple contradictions, such as positive and negative evidence appearing in the same category.

### 4. Streamlit App (`app.py`)

The UI provides:

- **Sidebar Controls** for entering property names and showing source-priority order.
- **Live Status Updates** showing each pipeline stage in real-time.
- **Plotly Risk Meter** -- Dynamic gauge chart with professional exposure bands.
- **Executive Summary** -- 3-4 sentence investment verdict based on official data.
- **Single Dossier Flow** -- Financial, Legal/RERA, Infrastructure, Community, Reviews, and Evidence sections in one scrollable report.
- **Critical Concerns / Positive Signals** -- Investment risks and supporting positives presented together.
- **Evidence Ledger** -- Source reliability, confidence, and top evidence items.
- **Raw Intelligence** -- Expandable view of all source data from Anakin to maintain full transparency.

---

## API Key Notes

**Anakin API Key**: Obtain from [anakin.io](https://anakin.io). Navigate to your account settings to generate an API access token. The Search API and Agentic Search endpoints require a paid/Pro account.

**Gemini API Key**: Obtain from [Google AI Studio](https://aistudio.google.com/apikey). The `gemini-3.1-flash-lite` model is used for cost-effective, high-throughput structured output generation.

---

## Error Handling

The application is designed for resilience:

- All Anakin API calls use `try/except` blocks with structured error returns
- Exponential backoff on polling prevents hammering the API
- Configurable timeouts (30s for search, 180s for deep research)
- Missing API keys are detected at startup with clear error messages
- Gemini failures raise explicit errors rather than returning stale/mock data

---

## License

MIT
