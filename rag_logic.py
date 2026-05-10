"""
rag_logic.py

Gemini formatting layer for Skywalker Scout.

Anakin does ALL the data gathering and research.
Gemini's only job is to take Anakin's raw output and
reformat it into a clean, structured JSON scorecard.

Uses the google-genai SDK with gemini-3.1-flash-lite.
"""

import os
import json
import re
import logging
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag_logic")


# ---------------------------------------------------------------------------
# Gemini Client
# ---------------------------------------------------------------------------

def _get_gemini_client():
    """
    Initialize and return a google-genai Client.
    Requires the GEMINI_API_KEY environment variable.
    """
    try:
        from google import genai
    except ImportError:
        logger.error(
            "google-genai SDK not installed. Run: pip install google-genai"
        )
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not set.")
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        logger.error("Failed to initialize Gemini client: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-3.1-flash-lite"

# Gemini is ONLY used to reformat Anakin's output. It does NOT generate
# new research or make claims beyond what Anakin provides.
SYSTEM_PROMPT = """You are a data formatter for a real estate due diligence tool focused on Bengaluru properties.

You will receive raw intelligence data that was gathered by Anakin (a web search and research engine).
Your ONLY job is to organize and format this data into a clean JSON scorecard.

Rules:
1. Use ONLY the data provided. Do not invent or hallucinate information.
2. If Anakin's data is insufficient for a section, say "Insufficient data from search" and score 5 (neutral).
3. Reconcile conflicting information by noting both sources.
4. Keep all summaries factual and traceable to the provided data.
5. Prefer official K-RERA/government evidence over portals, portals over forums, and forums/reviews as sentiment signals.
6. Treat the evidence ledger as the audit trail. High-reliability evidence should carry more weight than low-reliability snippets.

Return ONLY a valid JSON object with these exact keys:
{
  "financial_viability": {
    "score": <1-10>,
    "summary": "<2-3 sentences based on Anakin data>",
    "price_per_sqft": "<from Anakin data or null>",
    "price_trend": "<up/down/stable/unknown>",
    "rental_yield": "<from Anakin data or null>",
    "key_points": ["<point from data>"]
  },
  "legal_rera_status": {
    "score": <1-10>,
    "summary": "<2-3 sentences based on Anakin data>",
    "rera_number": "<from Anakin data or null>",
    "compliance_status": "<compliant/issues/unknown>",
    "pending_cases": <number or null>,
    "key_points": ["<point from data>"]
  },
  "community_sentiment": {
    "score": <1-10>,
    "summary": "<2-3 sentences based on Anakin data>",
    "overall_rating": "<from Anakin data or null>",
    "common_praises": ["<from data>"],
    "common_complaints": ["<from data>"]
  },
  "google_reviews": {
    "score": <1-10>,
    "summary": "<2-3 sentences based on Anakin data>",
    "average_rating": "<from Anakin data or null>",
    "total_reviews": <number or null>,
    "highlights": ["<from data>"],
    "rating_trend": "<improving/declining/stable/unknown>"
  },
  "infrastructure_development": {
    "score": <1-10>,
    "summary": "<2-3 sentences based on Anakin data about roads, metro, water supply, etc.>",
    "key_projects": ["<nearby infra projects>"]
  },
  "location_coordinates": {
    "latitude": <float from Anakin data or null>,
    "longitude": <float from Anakin data or null>
  },
  "risk_score": <0-100, where 0=very safe and 100=extremely risky>,
  "executive_summary": "<3-4 sentence verdict based strictly on Anakin data. Mention any official government/RERA data if found.>",
  "red_flags": ["<concern from data>"],
  "green_flags": ["<positive from data>"]
}"""


# ---------------------------------------------------------------------------
# Format Anakin Intelligence for Gemini
# ---------------------------------------------------------------------------

def _format_intelligence(intelligence: dict) -> str:
    """
    Format raw Anakin intelligence into a readable text block
    for Gemini to reformat into a scorecard.
    """
    parts = [f"# Property: {intelligence.get('property_name', 'Unknown')}\n"]

    def append_search_section(key: str, heading: str):
        section = intelligence.get(key, {})
        if section.get("success") and section.get("results"):
            parts.append(f"## {heading}")
            for r in section["results"]:
                parts.append(f"- **{r.get('title', 'N/A')}**")
                parts.append(f"  URL: {r.get('url', 'N/A')}")
                if r.get("date"):
                    parts.append(f"  Date: {r.get('date')}")
                parts.append(f"  {r.get('snippet', 'No snippet')}\n")

    # Web search results (from Anakin /v1/search)
    append_search_section("web_search", "Anakin Web Search Results")

    # Priority legal source
    append_search_section("rera_search", "Priority Source: K-RERA Official Search")

    # Priority market sources
    append_search_section("market_search", "Priority Sources: Housing.com and NoBroker Market Search")

    # Google reviews (from Anakin /v1/search with targeted query)
    append_search_section("google_reviews", "Anakin Google Maps Reviews Search Snippets")

    # Reddit search results. Thread pages are scraped separately when available.
    append_search_section("reddit_search", "Priority Source: Reddit Community Search")

    # Infra search
    append_search_section("infra_search", "Anakin Infrastructure Search Results")

    # Scraped pages (from Anakin /v1/url-scraper/batch -- full page content)
    sp = intelligence.get("scraped_pages", {})
    if sp.get("success") and sp.get("results"):
        parts.append("## Anakin URL Scraper -- Full Page Content (Anti-Bot Browser Enabled)")
        for page in sp["results"]:
            if page.get("status") == "completed" and page.get("markdown"):
                parts.append(f"### Source: {page.get('url', 'Unknown')}")
                # Truncate to avoid token limits
                content = page["markdown"][:3000]
                parts.append(content + "\n")

    # Crawled Gov pages (from Anakin /v1/crawl)
    cp = intelligence.get("crawled_gov_pages", {})
    if cp.get("success") and cp.get("results"):
        parts.append("## Anakin Crawled Government Pages (Official Data)")
        for page in cp["results"]:
            if page.get("status") == "completed" and page.get("markdown"):
                parts.append(f"### Source: {page.get('url', 'Unknown')}")
                content = page["markdown"][:3000]
                parts.append(content + "\n")

    # Agentic research (from Anakin /v1/agentic-search)
    ar = intelligence.get("agentic_research", {})
    if ar.get("success") and ar.get("generated_json"):
        gj = ar["generated_json"]
        parts.append("## Anakin Agentic Research Report")
        if isinstance(gj, dict):
            summary = gj.get("summary", "")
            if summary:
                parts.append(f"### Research Summary\n{summary}\n")
            structured = gj.get("structured_data")
            if structured:
                parts.append("### Structured Data")
                parts.append(json.dumps(structured, indent=2))
        else:
            parts.append(str(gj))

    # Evidence ledger: deterministic audit trail and source reliability scores.
    ledger = intelligence.get("evidence_ledger") or {}
    summary = ledger.get("summary") or {}
    items = ledger.get("items") or []
    contradictions = ledger.get("contradictions") or []
    if summary or items:
        parts.append("## Evidence Ledger and Source Reliability")
        if summary:
            parts.append(json.dumps(summary, indent=2))
        for item in items[:18]:
            parts.append(
                "- "
                f"[{item.get('id')}] {item.get('category')} | "
                f"confidence={item.get('confidence')} | "
                f"source={item.get('source_id')} | "
                f"signal={item.get('signal')}: {item.get('claim')}"
            )
            if item.get("excerpt"):
                parts.append(f"  Excerpt: {item.get('excerpt')[:350]}")
        if contradictions:
            parts.append("### Potential Contradictions")
            parts.append(json.dumps(contradictions[:5], indent=2))

    # Data collection warnings
    errors = intelligence.get("errors", [])
    if errors:
        parts.append("\n## Data Collection Warnings")
        for e in errors:
            parts.append(f"- WARNING: {e}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# JSON Parsing
# ---------------------------------------------------------------------------

def parse_scorecard(text: str) -> Optional[dict]:
    """Extract JSON scorecard from Gemini's response."""
    # Fenced code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Raw JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Embedded JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse JSON from Gemini response.")
    return None


# ---------------------------------------------------------------------------
# Risk Score Computation
# ---------------------------------------------------------------------------

def compute_risk_score(scorecard: dict) -> int:
    """Derive 0-100 risk score from section scores if not provided."""
    if "risk_score" in scorecard:
        return max(0, min(100, int(scorecard["risk_score"])))

    scores = []
    for key in ("financial_viability", "legal_rera_status",
                "community_sentiment", "google_reviews", "infrastructure_development"):
        section = scorecard.get(key, {})
        if isinstance(section, dict) and "score" in section:
            try:
                scores.append(int(section["score"]))
            except (ValueError, TypeError):
                pass

    if scores:
        avg = sum(scores) / len(scores)
        return max(0, min(100, int((10 - avg) * 10)))

    return 50


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def format_scorecard(intelligence: dict) -> dict:
    """
    Take Anakin's raw intelligence and use Gemini to format it
    into a structured Due Diligence Scorecard.

    Anakin does the research. Gemini only formats.

    Raises RuntimeError if Gemini is unavailable or fails.
    """
    client = _get_gemini_client()
    formatted = _format_intelligence(intelligence)

    if client is None:
        raise RuntimeError(
            "Gemini client could not be initialized. "
            "Ensure GEMINI_API_KEY is set and google-genai is installed."
        )

    try:
        from google.genai import types

        logger.info(
            "Sending Anakin intelligence to Gemini (%s) for formatting...",
            MODEL_NAME,
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=(
                "Format the following Anakin intelligence data into "
                "a Due Diligence Scorecard JSON:\n\n" + formatted
            ),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        response_text = response.text
        if response_text is None:
            logger.error("Gemini response.text is None. Full response: %s", response)
            response_text = ""

        logger.info("Gemini formatting complete (%d chars).", len(response_text))

        scorecard = parse_scorecard(response_text)
        if scorecard:
            scorecard["risk_score"] = compute_risk_score(scorecard)
            scorecard["_raw_gemini_response"] = response_text
            return scorecard

        raise RuntimeError(
            "Gemini returned a response but it could not be parsed as JSON. "
            f"Raw (first 500 chars): {str(response_text)[:500]}"
        )

    except Exception as exc:
        logger.error("Gemini formatting failed: %s", exc)
        raise RuntimeError(f"Gemini formatting failed: {exc}") from exc
