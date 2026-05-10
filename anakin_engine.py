"""
anakin_engine.py

Anakin Scraper data engine for Skywalker Scout.
Handles all web intelligence gathering via the AnakinScraper REST API:
  - POST /v1/search           (synchronous AI-powered web search)
  - POST /v1/agentic-search   (async 4-stage research pipeline)
  - GET  /v1/agentic-search/{id}  (poll for research results)

API Docs: https://anakin.io/llms-full.txt
Base URL: https://api.anakin.io/v1
Auth:     X-API-Key header
"""

import os
import time
import logging
import requests
from typing import Optional, Callable
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("anakin_engine")

BASE_URL = "https://api.anakin.io/v1"

# Agentic search recommended polling: 10s, typical completion: 1-5 min
AGENTIC_POLL_INTERVAL = 10
AGENTIC_TIMEOUT = 300  # 5 minutes max


PRIORITY_DOMAINS = {
    "rera.karnataka.gov.in": 100,
    "housing.com": 86,
    "nobroker.in": 82,
    "reddit.com": 74,
    "99acres.com": 58,
    "magicbricks.com": 56,
}


def _merge_search_results(*responses: dict) -> dict:
    """Merge multiple Anakin search responses while preserving order."""
    merged = {
        "success": False,
        "results": [],
        "raw_response": {"merged": []},
        "error": None,
    }
    errors = []
    seen_urls = set()

    for response in responses:
        if not response:
            continue
        merged["raw_response"]["merged"].append(response.get("raw_response"))
        if response.get("success"):
            merged["success"] = True
        elif response.get("error"):
            errors.append(response["error"])

        for result in response.get("results", []):
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged["results"].append(result)

    merged["error"] = "; ".join(errors) if errors and not merged["success"] else None
    return merged


def _domain_from_url(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain
    except Exception:
        return ""


def _domain_priority(url: str) -> int:
    domain = _domain_from_url(url)
    for target, score in PRIORITY_DOMAINS.items():
        if target in domain:
            return score
    if domain.endswith(".gov.in") or domain.endswith(".nic.in"):
        return 90
    return 40


def _is_government_url(url: str) -> bool:
    domain = _domain_from_url(url)
    return (
        "rera.karnataka.gov.in" in domain
        or domain.endswith(".gov.in")
        or domain.endswith(".nic.in")
    )


def _is_scrapable_priority_url(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    if "google.com/maps" in lowered or "maps.google" in lowered:
        return False
    if "reddit.com" in lowered:
        return "/comments/" in lowered or "/r/bangalore/" in lowered or "/r/indiainvestments/" in lowered
    return True


class AnakinClient:
    """
    Client for AnakinScraper REST API.

    All public methods return structured dicts with 'success', 'error',
    and data fields. HTTP failures are caught and surfaced as error
    dicts -- the application never crashes from API failures.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANAKIN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANAKIN_API_KEY not found. "
                "Set it via environment variable or pass it directly."
            )
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        logger.info("AnakinClient initialized.")

    # ------------------------------------------------------------------
    # POST /v1/search  (synchronous)
    # ------------------------------------------------------------------

    def search(self, prompt: str, limit: int = 10) -> dict:
        """
        AI-powered web search. Returns results immediately (no polling).

        Docs: POST /v1/search
        Body: {"prompt": "<query>", "limit": <n>}
        Response: {"id": "...", "results": [{"url", "title", "snippet", "date"}]}

        Returns dict with: success, results (list), raw_response, error
        """
        try:
            logger.info("Search: %s", prompt[:120])
            resp = requests.post(
                f"{BASE_URL}/search",
                json={"prompt": prompt, "limit": limit},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            logger.info("Search returned %d results.", len(results))
            return {
                "success": True,
                "results": results,
                "raw_response": data,
                "error": None,
            }
        except requests.exceptions.Timeout:
            msg = "Search request timed out after 30s."
            logger.warning(msg)
            return {"success": False, "results": [], "raw_response": None, "error": msg}
        except requests.exceptions.HTTPError as exc:
            msg = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            logger.error("Search HTTP error: %s", msg)
            return {"success": False, "results": [], "raw_response": None, "error": msg}
        except requests.exceptions.RequestException as exc:
            logger.error("Search failed: %s", exc)
            return {"success": False, "results": [], "raw_response": None, "error": str(exc)}

    def perform_search(self, prompt: str, limit: int = 10) -> dict:
        """
        Compatibility alias for targeted source searches.

        Older notes and examples refer to perform_search(); internally this
        delegates to the canonical Anakin Search API wrapper.
        """
        return self.search(prompt, limit=limit)

    # ------------------------------------------------------------------
    # Targeted source searches
    # ------------------------------------------------------------------

    def rera_property_search(self, property_name: str) -> dict:
        """Prioritize Karnataka RERA as the legal source of truth."""
        prompt = (
            f'site:rera.karnataka.gov.in "{property_name}" Bangalore '
            f'K-RERA RERA registration project status approval compliance'
        )
        return self.perform_search(prompt, limit=8)

    def market_price_search(self, property_name: str) -> dict:
        """Target Housing.com and NoBroker for pricing, rent, and amenities."""
        housing_prompt = (
            f'site:housing.com "{property_name}" Bangalore price per sqft '
            f'amenities floor plan possession resale rent'
        )
        nobroker_prompt = (
            f'site:nobroker.in "{property_name}" Bangalore owner sale rent '
            f'price amenities maintenance'
        )
        return _merge_search_results(
            self.perform_search(housing_prompt, limit=5),
            self.perform_search(nobroker_prompt, limit=5),
        )

    def reddit_community_search(self, property_name: str) -> dict:
        """
        Search Reddit via Anakin Search, then scrape the thread URLs later.

        This follows the safer flow for Reddit: search with strict subreddit
        operators first, then send the resulting thread pages to the scraper.
        """
        bangalore_prompt = (
            f'site:reddit.com/r/bangalore "{property_name}" '
            f'water OR traffic OR builder OR delay OR maintenance'
        )
        investing_prompt = (
            f'site:reddit.com/r/IndiaInvestments "{property_name}" '
            f'real estate OR investment OR builder OR resale OR delay'
        )
        return _merge_search_results(
            self.perform_search(bangalore_prompt, limit=5),
            self.perform_search(investing_prompt, limit=5),
        )

    # ------------------------------------------------------------------
    # Google Maps Reviews (specialized search query)
    # ------------------------------------------------------------------

    def google_reviews_search(self, property_name: str) -> dict:
        """
        Targeted search for Google Maps reviews of a property/builder.
        Uses the same /v1/search endpoint with a crafted prompt.
        """
        prompt = (
            f'"{property_name}" Bangalore Google Maps reviews ratings '
            f'"star rating" "based on" reviews OR "buyer review" OR "resident review"'
        )
        return self.search(prompt, limit=8)

    # ------------------------------------------------------------------
    # POST /v1/agentic-search  (async -- returns job_id)
    # ------------------------------------------------------------------

    def submit_agentic_search(self, prompt: str) -> dict:
        """
        Start a 4-stage agentic research pipeline.

        Docs: POST /v1/agentic-search
        Body: {"prompt": "<research query>"}
        Response (202): {"job_id": "...", "status": "pending", ...}

        Returns dict with: success, job_id, error
        """
        try:
            logger.info("Submitting agentic search: %s", prompt[:120])
            resp = requests.post(
                f"{BASE_URL}/agentic-search",
                json={"prompt": prompt},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("job_id")
            if not job_id:
                return {
                    "success": False,
                    "job_id": None,
                    "error": f"No job_id returned: {data}",
                }
            logger.info("Agentic search job submitted: %s", job_id)
            return {"success": True, "job_id": job_id, "error": None}
        except requests.exceptions.RequestException as exc:
            logger.error("Agentic search submission failed: %s", exc)
            return {"success": False, "job_id": None, "error": str(exc)}

    # ------------------------------------------------------------------
    # GET /v1/agentic-search/{id}  (poll until completed)
    # ------------------------------------------------------------------

    def poll_agentic_search(
        self,
        job_id: str,
        timeout: int = AGENTIC_TIMEOUT,
        interval: int = AGENTIC_POLL_INTERVAL,
        status_callback: Optional[Callable] = None,
    ) -> dict:
        """
        Poll an agentic search job until completion.

        Docs: GET /v1/agentic-search/{id}
        Statuses: pending -> queued -> processing -> completed | failed

        On completion, response contains:
          generatedJson.summary       -- research summary
          generatedJson.structured_data  -- extracted structured data
          generatedJson.data_schema   -- schema for the structured data

        Returns dict with: success, status, generated_json, error
        """
        start = time.time()
        attempt = 0

        logger.info("Polling agentic search %s (timeout=%ds, interval=%ds)",
                     job_id, timeout, interval)

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                msg = f"Job {job_id} did not complete within {timeout}s."
                logger.warning("Poll timeout: %s", msg)
                return {
                    "success": False,
                    "status": "timeout",
                    "generated_json": None,
                    "error": msg,
                }

            try:
                attempt += 1
                resp = requests.get(
                    f"{BASE_URL}/agentic-search/{job_id}",
                    headers=self.headers,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "unknown")

                logger.info(
                    "  Poll #%d: status=%s (%.0fs elapsed)",
                    attempt, status, elapsed,
                )
                if status_callback:
                    status_callback(
                        f"Research status: {status} ({int(elapsed)}s elapsed)"
                    )

                if status == "completed":
                    generated_json = data.get("generatedJson", {})
                    logger.info("Agentic search completed successfully.")
                    return {
                        "success": True,
                        "status": "completed",
                        "generated_json": generated_json,
                        "raw_response": data,
                        "error": None,
                    }

                if status == "failed":
                    error_msg = data.get("error", "Job failed without details.")
                    logger.error("Agentic search failed: %s", error_msg)
                    return {
                        "success": False,
                        "status": "failed",
                        "generated_json": None,
                        "error": error_msg,
                    }

                # pending / queued / processing -- wait and retry
                time.sleep(interval)

            except requests.exceptions.RequestException as exc:
                logger.warning("Poll #%d network error: %s", attempt, exc)
                time.sleep(interval)

    # ------------------------------------------------------------------
    # POST /v1/url-scraper/batch  (scrape up to 10 URLs)
    # ------------------------------------------------------------------

    def batch_scrape_urls(self, urls: list, country: str = "in", use_browser: bool = True) -> dict:
        """
        Submit up to 10 URLs for batch scraping.
        Uses headless browser (useBrowser=True) to bypass simple bot protections
        and render JS-heavy real estate/government sites.

        Docs: POST /v1/url-scraper/batch
        Body: {"urls": [...], "country": "in", "useBrowser": true}
        Response (202): {"jobId": "...", "status": "pending"}

        Returns dict with: success, job_id, error
        """
        if not urls:
            return {"success": False, "job_id": None, "error": "No URLs provided."}

        # Limit to 10 per API constraint
        urls = urls[:10]

        try:
            logger.info("Batch scraping %d URLs (useBrowser=%s)...", len(urls), use_browser)
            resp = requests.post(
                f"{BASE_URL}/url-scraper/batch",
                json={"urls": urls, "country": country, "useBrowser": use_browser},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("jobId", data.get("job_id"))
            if not job_id:
                return {"success": False, "job_id": None,
                        "error": f"No jobId returned: {data}"}
            logger.info("Batch scrape job submitted: %s", job_id)
            return {"success": True, "job_id": job_id, "error": None}
        except requests.exceptions.RequestException as exc:
            logger.error("Batch scrape submission failed: %s", exc)
            return {"success": False, "job_id": None, "error": str(exc)}

    # ------------------------------------------------------------------
    # GET /v1/url-scraper/{id}  (poll for scrape results)
    # ------------------------------------------------------------------

    def poll_scrape_job(
        self,
        job_id: str,
        timeout: int = 120,
        interval: int = 3,
    ) -> dict:
        """
        Poll a URL scraper job until completion.

        Response contains: markdown, cleanedHtml, generatedJson per URL.
        Returns dict with: success, status, results (list), error
        """
        start = time.time()
        attempt = 0

        logger.info("Polling scrape job %s (timeout=%ds)", job_id, timeout)

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                return {"success": False, "status": "timeout",
                        "results": [], "error": f"Scrape job timed out after {timeout}s."}

            try:
                attempt += 1
                resp = requests.get(
                    f"{BASE_URL}/url-scraper/{job_id}",
                    headers=self.headers,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "unknown")

                logger.info("  Scrape poll #%d: status=%s (%.0fs)", attempt, status, elapsed)

                if status == "completed":
                    # Batch results are in data["results"], single in data directly
                    results = data.get("results", [data])
                    scraped = []
                    for r in results:
                        scraped.append({
                            "url": r.get("url", ""),
                            "markdown": r.get("markdown", ""),
                            "status": r.get("status", "completed"),
                        })
                    logger.info("Scrape completed: %d pages.", len(scraped))
                    return {"success": True, "status": "completed",
                            "results": scraped, "error": None}

                if status == "failed":
                    return {"success": False, "status": "failed",
                            "results": [], "error": data.get("error", "Scrape failed.")}

                time.sleep(interval)

            except requests.exceptions.RequestException as exc:
                logger.warning("Scrape poll #%d error: %s", attempt, exc)
                time.sleep(interval)

    # ------------------------------------------------------------------
    # POST /v1/crawl  (Crawl a specific domain, good for gov sites)
    # ------------------------------------------------------------------

    def submit_crawl_job(self, url: str, max_pages: int = 5, use_browser: bool = True) -> dict:
        """
        Submit a domain for crawling multiple pages.
        """
        try:
            logger.info("Submitting crawl job for %s (max_pages=%d)", url, max_pages)
            resp = requests.post(
                f"{BASE_URL}/crawl",
                json={
                    "url": url,
                    "maxPages": max_pages,
                    "useBrowser": use_browser,
                    "country": "in"
                },
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("jobId")
            if not job_id:
                return {"success": False, "job_id": None, "error": f"No jobId returned: {data}"}
            logger.info("Crawl job submitted: %s", job_id)
            return {"success": True, "job_id": job_id, "error": None}
        except requests.exceptions.RequestException as exc:
            logger.error("Crawl submission failed: %s", exc)
            return {"success": False, "job_id": None, "error": str(exc)}

    def poll_crawl_job(self, job_id: str, timeout: int = 120, interval: int = 5) -> dict:
        """
        Poll a crawl job until completion.
        """
        start = time.time()
        attempt = 0

        logger.info("Polling crawl job %s (timeout=%ds)", job_id, timeout)

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                return {"success": False, "status": "timeout", "results": [], "error": f"Crawl job timed out after {timeout}s."}

            try:
                attempt += 1
                resp = requests.get(
                    f"{BASE_URL}/crawl/{job_id}",
                    headers=self.headers,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "unknown")

                logger.info("  Crawl poll #%d: status=%s (%.0fs)", attempt, status, elapsed)

                if status == "completed":
                    results = data.get("results", [])
                    scraped = []
                    for r in results:
                        if r.get("status") == "completed":
                            scraped.append({
                                "url": r.get("url", ""),
                                "markdown": r.get("markdown", ""),
                                "status": "completed",
                            })
                    logger.info("Crawl completed: %d pages.", len(scraped))
                    return {"success": True, "status": "completed", "results": scraped, "error": None}

                if status == "failed":
                    return {"success": False, "status": "failed", "results": [], "error": data.get("error", "Crawl failed.")}

                time.sleep(interval)

            except requests.exceptions.RequestException as exc:
                logger.warning("Crawl poll #%d error: %s", attempt, exc)
                time.sleep(interval)

    # ------------------------------------------------------------------
    # Full Pipeline Orchestrator
    # ------------------------------------------------------------------

    def run_full_pipeline(
        self,
        property_name: str,
        status_callback: Optional[Callable] = None,
    ) -> dict:
        """
        Run the complete Anakin intelligence-gathering pipeline:
          1. Web search for property/builder info
          2. Web search for infrastructure/development in the area
          3. Google Maps reviews search
          4. Priority source searches (K-RERA, Housing, NoBroker, Reddit)
          5. Submit agentic deep research (async)
          6. Batch scrape top URLs & Crawl official/Gov sites
          7. Poll for all results
          8. Build evidence ledger
        """
        def _update(msg: str):
            logger.info(msg)
            if status_callback:
                status_callback(msg)

        intelligence = {
            "property_name": property_name,
            "web_search": None,
            "infra_search": None,
            "google_reviews": None,
            "rera_search": None,
            "market_search": None,
            "reddit_search": None,
            "scraped_pages": None,
            "crawled_gov_pages": None,
            "agentic_research": None,
            "evidence_ledger": None,
            "errors": [],
        }

        # -- Step 1: Web search -----------------------------------------------
        _update("Step 1/8 -- Anakin Search: property data...")
        search_prompt = (
            f"{property_name} Bangalore real estate RERA registration "
            f"reviews complaints price builder reputation"
        )
        web_result = self.search(search_prompt, limit=10)
        intelligence["web_search"] = web_result
        if not web_result["success"]:
            intelligence["errors"].append(f"Web search: {web_result['error']}")

        # -- Step 2: Infrastructure search ------------------------------------
        _update("Step 2/8 -- Anakin Search: infrastructure & development...")
        infra_prompt = (
            f"infrastructure development road widening metro expansion "
            f"water supply projects near {property_name} Bangalore official news"
        )
        infra_result = self.search(infra_prompt, limit=5)
        intelligence["infra_search"] = infra_result
        if not infra_result["success"]:
            intelligence["errors"].append(f"Infra search: {infra_result['error']}")

        # -- Step 3: Google reviews -------------------------------------------
        _update("Step 3/8 -- Anakin Search: Google Maps review snippets...")
        reviews_result = self.google_reviews_search(property_name)
        intelligence["google_reviews"] = reviews_result
        if not reviews_result["success"]:
            intelligence["errors"].append(f"Google reviews: {reviews_result['error']}")

        # -- Step 4: Priority source searches ---------------------------------
        _update("Step 4/8 -- Priority Search: K-RERA legal registry...")
        rera_result = self.rera_property_search(property_name)
        intelligence["rera_search"] = rera_result
        if not rera_result["success"]:
            intelligence["errors"].append(f"K-RERA search: {rera_result['error']}")

        _update("Step 4/8 -- Priority Search: Housing.com and NoBroker market data...")
        market_result = self.market_price_search(property_name)
        intelligence["market_search"] = market_result
        if not market_result["success"]:
            intelligence["errors"].append(f"Market search: {market_result['error']}")

        _update("Step 4/8 -- Priority Search: Reddit community threads...")
        reddit_result = self.reddit_community_search(property_name)
        intelligence["reddit_search"] = reddit_result
        if not reddit_result["success"]:
            intelligence["errors"].append(f"Reddit search: {reddit_result['error']}")

        # -- Step 5: Submit agentic research ----------------------------------
        _update("Step 5/8 -- Anakin Agentic Search: submitting research...")
        research_prompt = (
            f"Comprehensive due diligence analysis of {property_name} "
            f"real estate project in Bangalore, India. "
            f"Cover: construction delays, legal issues, RERA compliance status, "
            f"water supply problems, homebuyer complaints, builder track record, "
            f"price trends, infrastructure development (roads/metro), and community sentiment. "
            f"Prioritize K-RERA official data, Housing.com, NoBroker, Reddit r/bangalore, "
            f"Reddit r/IndiaInvestments, and Google review snippets when available."
        )
        agentic_job = self.submit_agentic_search(research_prompt)

        # -- Step 6: Scrape & Crawl -------------------------------------------
        scrape_job_id = None
        crawl_job_id = None
        
        top_urls = []
        gov_url = None
        
        # Collect URLs from general and priority searches. Google review snippets
        # are intentionally not scraped directly; the snippets are the signal.
        all_search_results = (
            rera_result.get("results", [])
            + market_result.get("results", [])
            + reddit_result.get("results", [])
            + web_result.get("results", [])
            + infra_result.get("results", [])
        )

        prioritized_results = sorted(
            all_search_results,
            key=lambda item: _domain_priority(item.get("url", "")),
            reverse=True,
        )

        reddit_count = 0
        for r in prioritized_results:
            url = r.get("url", "")
            if not url:
                continue
            
            # Identify government sites (like RERA Karnataka, BBMP, BDA)
            if _is_government_url(url) and not gov_url:
                gov_url = url
                continue

            if not _is_scrapable_priority_url(url) or url in top_urls:
                continue

            if "reddit.com" in url.lower():
                if reddit_count >= 3:
                    continue
                reddit_count += 1

            if len(top_urls) < 8:
                top_urls.append(url)

        if top_urls:
            _update(f"Step 6/8 -- Anakin URL Scraper: scraping {len(top_urls)} priority pages (with anti-bot browser)...")
            scrape_submit = self.batch_scrape_urls(top_urls, use_browser=True)
            if scrape_submit["success"]:
                scrape_job_id = scrape_submit["job_id"]
            else:
                intelligence["errors"].append(f"URL scraper: {scrape_submit['error']}")

        if gov_url:
            _update(f"Step 6/8 -- Anakin Crawl: targeting official/legal site ({gov_url})...")
            crawl_submit = self.submit_crawl_job(gov_url, max_pages=3, use_browser=True)
            if crawl_submit["success"]:
                crawl_job_id = crawl_submit["job_id"]
            else:
                intelligence["errors"].append(f"Crawl API: {crawl_submit['error']}")

        # -- Step 7: Poll for all async results -------------------------------
        
        if scrape_job_id:
            _update("Polling URL Scraper results...")
            scrape_result = self.poll_scrape_job(scrape_job_id)
            intelligence["scraped_pages"] = scrape_result
            if not scrape_result["success"]:
                intelligence["errors"].append(f"URL scraper poll: {scrape_result['error']}")
        else:
            intelligence["scraped_pages"] = {"success": False, "results": [], "error": "Skipped"}

        if crawl_job_id:
            _update("Polling Crawl results (gov site)...")
            crawl_result = self.poll_crawl_job(crawl_job_id)
            intelligence["crawled_gov_pages"] = crawl_result
            if not crawl_result["success"]:
                intelligence["errors"].append(f"Crawl poll: {crawl_result['error']}")
        else:
            intelligence["crawled_gov_pages"] = {"success": False, "results": [], "error": "Skipped"}

        if agentic_job["success"]:
            _update("Step 7/8 -- Waiting for Anakin Agentic Search to complete...")
            # Reduce timeout slightly so user isn't stuck forever, and rely on the other data if it fails
            poll_result = self.poll_agentic_search(
                agentic_job["job_id"],
                timeout=240,
                status_callback=status_callback,
            )
            intelligence["agentic_research"] = poll_result
            if not poll_result["success"]:
                intelligence["errors"].append(f"Agentic research poll: {poll_result['error']}")
        else:
            intelligence["errors"].append(f"Agentic research submit: {agentic_job['error']}")
            intelligence["agentic_research"] = {"success": False, "generated_json": None, "error": agentic_job["error"]}

        # -- Step 8: Evidence ledger -----------------------------------------
        _update("Step 8/8 -- Building evidence ledger and source reliability scores...")
        try:
            from evidence_engine import build_evidence_ledger

            intelligence["evidence_ledger"] = build_evidence_ledger(intelligence)
        except Exception as exc:
            logger.exception("Evidence ledger build failed.")
            intelligence["evidence_ledger"] = {
                "sources": [],
                "items": [],
                "summary": {},
                "contradictions": [],
            }
            intelligence["errors"].append(f"Evidence ledger: {exc}")

        # -- Summary ----------------------------------------------------------
        error_count = len(intelligence["errors"])
        if error_count == 0:
            _update("All Anakin intelligence gathered successfully.")
        else:
            _update(f"Anakin intelligence gathered with {error_count} warning(s).")

        return intelligence
