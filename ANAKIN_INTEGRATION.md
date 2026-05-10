# Anakin Intelligence Integration Guide

Skywalker Scout relies on **Anakin Scraper** as its primary intelligence-gathering engine. This document outlines the Anakin APIs we utilize, how our `AnakinClient` (`anakin_engine.py`) orchestrates these endpoints, how priority sources are selected, and how the final evidence-ready intelligence dictionary is structured.

## Overview

The `AnakinClient` interacts with four core Anakin products:
1. **Search API**: Synchronous web, source-targeted, and Google review snippet search.
2. **URL Scraper (Batch)**: Asynchronous extraction of full-page markdown (with anti-bot browser).
3. **Crawl API**: Deep extraction of specific domains (used for official `.gov.in` sites).
4. **Agentic Search**: Autonomous 4-stage deep research pipeline.

After Anakin completes collection, Skywalker Scout runs a deterministic evidence ledger step in `evidence_engine.py`. This is not another web research engine; it classifies Anakin sources, assigns reliability scores, extracts evidence items, and detects simple contradictions before Gemini formats the final scorecard.

---

## 1. Search API

Used to rapidly find relevant URLs, news, official records, market listings, Reddit discussions, infrastructure context, and Google-indexed review snippets.

### **Endpoint:** `POST /v1/search`
**Execution:** Synchronous

### **Python Methods:**
- `client.search(prompt: str, limit: int = 10)`
- `client.perform_search(prompt: str, limit: int = 10)`
- `client.google_reviews_search(property_name: str)`
- `client.rera_property_search(property_name: str)`
- `client.market_price_search(property_name: str)`
- `client.reddit_community_search(property_name: str)`

**What it does:** Submits an AI-optimized search query. Returns immediate results without polling.

### Source Priority Strategy

The pipeline now runs targeted searches in addition to general web search:

1. **K-RERA**: `site:rera.karnataka.gov.in` for project registration, approval, and compliance status.
2. **Housing.com**: pricing, amenities, possession, resale, and rent signals.
3. **NoBroker.in**: owner-written sale/rent descriptions and unfiltered property reality.
4. **Reddit**: strict subreddit searches for `r/bangalore` and `r/IndiaInvestments`; the top thread URLs are then passed to URL Scraper.
5. **Google Reviews**: search snippets only, using queries such as `"Property Name" Bangalore Google Maps reviews ratings "star rating"`.

Google Maps pages are not scraped directly. The Search API snippets are used because Google often indexes aggregate ratings and helpful review text.

### Search Buckets in `intelligence`

`run_full_pipeline()` stores search results in separate buckets so downstream logic can treat sources differently:

```python
{
    "web_search": {...},       # General property/builder search
    "infra_search": {...},     # Roads, metro, water, development context
    "google_reviews": {...},   # Google review/rating snippets from Search API
    "rera_search": {...},      # K-RERA targeted search
    "market_search": {...},    # Housing.com + NoBroker targeted search
    "reddit_search": {...},    # Reddit subreddit-targeted search
}
```

The evidence ledger later uses these buckets to infer category and reliability.

**Returns:**
```python
{
    "success": True,
    "results": [
        {
            "url": "https://example.com/property",
            "title": "Property Listing",
            "snippet": "Detailed description of the property...",
            "date": "2026-05-01" # (Optional)
        }
    ],
    "raw_response": {...},
    "error": None
}
```

---

## 2. URL Scraper API

Used to fetch the full markdown content of priority URLs discovered in the Search phase.

### **Endpoint:** `POST /v1/url-scraper/batch`
**Execution:** Asynchronous (Submit & Poll)

### **Python Methods:**
- `client.batch_scrape_urls(urls: list, country: str = "in", use_browser: bool = True)`
- `client.poll_scrape_job(job_id: str)`

**What it does:** 
We submit priority URLs from K-RERA/official discovery, Housing.com, NoBroker, Reddit threads, and selected general/infrastructure results. By passing `useBrowser=True`, Anakin spins up a stealth cloud browser (Camoufox) to render JavaScript and bypass Cloudflare/bot protections on heavy real estate sites.

### URL Selection Rules

- Google Maps URLs are not sent to URL Scraper; Search snippets are used instead.
- Reddit is searched first with strict subreddit operators. Up to three discovered thread URLs are sent to the scraper.
- Priority domains are sorted ahead of generic web results.
- The current scraper batch caps selected non-government URLs at eight to control cost and latency.
- K-RERA/`.gov.in`/`.nic.in` URLs are routed to Crawl API where possible.

**Submit Returns:**
```python
{
    "success": True, 
    "job_id": "a0f1bbdf-0d4b-4df2-aad1-36d1cd32e5e0", 
    "error": None
}
```

**Poll Returns (`GET /v1/url-scraper/{job_id}`):**
```python
{
    "success": True,
    "status": "completed",
    "results": [
        {
            "url": "https://housing.com/...",
            "markdown": "# JRC Wildwoods Phase 3\nFull page content...",
            "status": "completed"
        }
    ],
    "error": None
}
```

---

## 3. Crawl API

Used to perform deep, multi-page crawls of a specific domain. In Skywalker Scout, this is triggered specifically when official government sites (`.gov.in` or `.nic.in`) are discovered.

### **Endpoint:** `POST /v1/crawl`
**Execution:** Asynchronous (Submit & Poll)

### **Python Methods:**
- `client.submit_crawl_job(url: str, max_pages: int = 3, use_browser: bool = True)`
- `client.poll_crawl_job(job_id: str)`

**What it does:** Maps and extracts markdown from multiple pages within the same domain to ensure official legal/RERA data is not missed.

The first discovered K-RERA, `.gov.in`, or `.nic.in` URL is treated as the government crawl candidate. K-RERA is the highest priority because it is the legal source of truth for Karnataka project registration and compliance.

**Submit Returns:** Similar to URL scraper (`job_id`).
**Poll Returns:** Similar to URL scraper (Array of URLs and `markdown`).

---

## 4. Agentic Search API

The heavy-lifter. This acts as an autonomous agent that creates its own search queries, browses multiple sites, and synthesizes findings over several minutes.

### **Endpoint:** `POST /v1/agentic-search`
**Execution:** Asynchronous (Long-running Poll)

### **Python Methods:**
- `client.submit_agentic_search(prompt: str)`
- `client.poll_agentic_search(job_id: str)`

**What it does:** We prompt it to look for construction delays, legal issues, RERA compliance, builder track record, pricing, infrastructure, water/traffic complaints, and community sentiment. It takes ~2-4 minutes to complete.

The agentic prompt explicitly tells Anakin to prioritize K-RERA, Housing.com, NoBroker, Reddit `r/bangalore`, Reddit `r/IndiaInvestments`, and Google review snippets when available.

**Submit Returns:**
```python
{
    "success": True, 
    "job_id": "623f8792-c9af-4864-96d6-71fbbe297999", 
    "error": None
}
```

**Poll Returns (`GET /v1/agentic-search/{job_id}`):**
```python
{
    "success": True,
    "status": "completed",
    "generated_json": {
        "summary": "Deep research findings synthesized here...",
        "structured_data": {},
        "data_schema": {}
    },
    "error": None
}
```

---

## Pipeline Orchestrator: `run_full_pipeline`

To tie it all together, `anakin_engine.py` exposes `run_full_pipeline(property_name)`. 

**Execution Flow:**
1. **Search:** Executes `search()` for property data.
2. **Infra Search:** Executes `search()` specifically for roads/metro near the property.
3. **Review Search:** Executes `google_reviews_search()` for Google-indexed rating/review snippets.
4. **Priority Source Search:** Executes targeted K-RERA, Housing.com, NoBroker, and Reddit searches.
5. **Agentic Submission:** Fires off `submit_agentic_search()` asynchronously.
6. **Scrape/Crawl Submission:** Extracts priority URLs from general and targeted searches. 
   - Submits `batch_scrape_urls()` with `useBrowser=True`.
   - Scrapes up to three Reddit thread URLs discovered via Search API.
   - If a K-RERA/`.gov.in`/`.nic.in` site is found, submits `submit_crawl_job()`.
7. **Polling:** Blocks and polls the Scrape, Crawl, and Agentic jobs until all are `completed` (or timed out).
8. **Evidence Ledger:** Builds source reliability scores, evidence claims, confidence, freshness, and contradiction checks.

**Final Output:** Returns an `intelligence` dictionary containing all aggregated endpoint results plus evidence metadata. This dictionary is handed to Gemini (`rag_logic.py`) to be formatted into the final scorecard and to Streamlit (`app.py`) for source/evidence rendering.

```python
{
    "property_name": "JRC Wildwoods, Sarjapur road",
    "web_search": {...},
    "infra_search": {...},
    "google_reviews": {...},
    "rera_search": {...},
    "market_search": {...},
    "reddit_search": {...},
    "scraped_pages": {...},
    "crawled_gov_pages": {...},
    "agentic_research": {...},
    "evidence_ledger": {
        "sources": [...],
        "items": [...],
        "summary": {
            "total_sources": 0,
            "total_evidence_items": 0,
            "official_sources": 0,
            "high_confidence_items": 0,
            "average_source_reliability": 0,
            "coverage_by_category": {},
            "priority_sources_found": [],
            "quality_score": 0
        },
        "contradictions": [...]
    },
    "errors": [...]
}
```

---

## Evidence Ledger Handoff

The evidence ledger is built immediately after Anakin polling completes. It adds audit metadata without creating new claims from outside the collected Anakin data.

### Source Types

| Source Type | Example | Reliability Role |
|-------------|---------|------------------|
| `official_rera` | `rera.karnataka.gov.in` | Highest-confidence legal/compliance evidence |
| `government` | `.gov.in`, `.nic.in` | Strong legal or infrastructure evidence |
| `market_portal` | Housing.com | Structured pricing and amenities signal |
| `owner_marketplace` | NoBroker.in | Owner-written market and reality signal |
| `community_forum` | Reddit | Anecdotal lived-experience signal |
| `google_reviews` | Google-indexed snippets | Rating and review sentiment signal |
| `unclassified_web` | Other websites | Lower-confidence supporting context |

### Evidence Item Shape

```python
{
    "id": "E001",
    "category": "legal_rera",
    "claim": "K-RERA project record found",
    "source_id": "S001",
    "confidence": 0.98,
    "freshness": "2026-05-01",
    "signal": "positive",
    "excerpt": "Relevant source excerpt..."
}
```

### Why This Matters

- Gemini receives source reliability and evidence IDs, making the scorecard more auditable.
- The UI can show source quality, high-confidence item counts, and contradiction warnings.
- The system can distinguish official records from market listings and community anecdotes.

---

## Streamlit Runtime Notes

The Streamlit app uses the Anakin status callback to keep execution progress compact:

- `st.status()` wraps the full investigation.
- `st.progress()` shows approximate pipeline progress.
- The latest task is shown as a single line.
- Full pipeline messages are stored in a collapsed "Pipeline event log" expander.
- The final report is stored in `st.session_state["last_report"]`, so it remains visible after widget-triggered reruns.

This avoids the earlier wall-of-text problem where every Anakin log line appeared directly in the main report area.
