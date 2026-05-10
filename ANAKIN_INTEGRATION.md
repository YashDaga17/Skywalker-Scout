# Anakin Intelligence Integration Guide

Skywalker Scout relies on **Anakin Scraper** as its primary intelligence-gathering engine. This document outlines the Anakin APIs we utilize, how our `AnakinClient` (`anakin_engine.py`) orchestrates these endpoints, and the structure of the data returned.

## Overview

The `AnakinClient` interacts with four core Anakin products:
1. **Search API**: Synchronous web and Google Maps search.
2. **URL Scraper (Batch)**: Asynchronous extraction of full-page markdown (with anti-bot browser).
3. **Crawl API**: Deep extraction of specific domains (used for official `.gov.in` sites).
4. **Agentic Search**: Autonomous 4-stage deep research pipeline.

---

## 1. Search API

Used to rapidly find relevant URLs, news, and Google Maps reviews.

### **Endpoint:** `POST /v1/search`
**Execution:** Synchronous

### **Python Methods:**
- `client.search(prompt: str, limit: int = 10)`
- `client.google_reviews_search(property_name: str)`

**What it does:** Submits an AI-optimized search query. Returns immediate results without polling.

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

Used to fetch the full markdown content of the top URLs discovered in the Search phase.

### **Endpoint:** `POST /v1/url-scraper/batch`
**Execution:** Asynchronous (Submit & Poll)

### **Python Methods:**
- `client.batch_scrape_urls(urls: list, country: str = "in", use_browser: bool = True)`
- `client.poll_scrape_job(job_id: str)`

**What it does:** 
We submit up to 10 URLs. By passing `useBrowser=True`, Anakin spins up a stealth cloud browser (Camoufox) to render JavaScript and bypass Cloudflare/bot protections on heavy real estate sites (e.g., Housing.com, 99acres).

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

**What it does:** Maps and extracts markdown from multiple pages within the same domain to ensure no RERA compliance data is missed.

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

**What it does:** We prompt it to look for construction delays, legal issues, RERA compliance, and builder track records. It takes ~2-4 minutes to complete.

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
3. **Review Search:** Executes `google_reviews_search()`.
4. **Agentic Submission:** Fires off `submit_agentic_search()` asynchronously.
5. **Scrape/Crawl Submission:** Extracts top URLs from steps 1 & 2. 
   - Submits `batch_scrape_urls()` with `useBrowser=True`.
   - If a `.gov.in` site is found, submits `submit_crawl_job()`.
6. **Polling:** Blocks and polls the Scrape, Crawl, and Agentic jobs until all are `completed` (or timed out).

**Final Output:** Returns a massive `intelligence` dictionary containing all the aggregated JSON from the endpoints above. This dictionary is then handed off to Gemini (`rag_logic.py`) to be formatted into the final UI scorecard.
