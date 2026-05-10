"""
evidence_engine.py

Evidence ledger and source reliability scoring for Skywalker Scout.

This module stays deterministic on purpose. Anakin gathers source material,
Gemini formats the report, and this layer records what came from where so the
final due-diligence output is auditable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass
class SourceProfile:
    """Normalized source metadata used by evidence items."""

    id: str
    url: str
    domain: str
    title: str
    source_type: str
    reliability: float
    priority: int
    rationale: str


@dataclass
class EvidenceItem:
    """A traceable claim or excerpt extracted from Anakin intelligence."""

    id: str
    category: str
    claim: str
    source_id: str
    confidence: float
    freshness: str
    signal: str
    excerpt: str


SOURCE_RULES = [
    {
        "match": "rera.karnataka.gov.in",
        "source_type": "official_rera",
        "reliability": 0.98,
        "priority": 100,
        "rationale": "Karnataka RERA is the official legal registry for project registration and compliance.",
    },
    {
        "match": ".gov.in",
        "source_type": "government",
        "reliability": 0.92,
        "priority": 92,
        "rationale": "Government domain. Strong legal and infrastructure signal when content is current.",
    },
    {
        "match": ".nic.in",
        "source_type": "government",
        "reliability": 0.92,
        "priority": 92,
        "rationale": "NIC/government domain. Strong legal and infrastructure signal when content is current.",
    },
    {
        "match": "housing.com",
        "source_type": "market_portal",
        "reliability": 0.82,
        "priority": 84,
        "rationale": "Structured real-estate listing source for competitive pricing and amenities.",
    },
    {
        "match": "nobroker.in",
        "source_type": "owner_marketplace",
        "reliability": 0.78,
        "priority": 80,
        "rationale": "Owner-driven listing source. Useful for market reality and unfiltered property descriptions.",
    },
    {
        "match": "reddit.com",
        "source_type": "community_forum",
        "reliability": 0.66,
        "priority": 70,
        "rationale": "Community discussion source. Useful for lived-experience signals, but anecdotal.",
    },
    {
        "match": "maps.google",
        "source_type": "google_reviews",
        "reliability": 0.72,
        "priority": 72,
        "rationale": "Aggregated review signal. Useful for sentiment, but snippets need corroboration.",
    },
    {
        "match": "google.com",
        "source_type": "google_reviews",
        "reliability": 0.70,
        "priority": 70,
        "rationale": "Google-indexed review or listing signal. Useful for rating snippets.",
    },
    {
        "match": "magicbricks.com",
        "source_type": "market_portal",
        "reliability": 0.72,
        "priority": 62,
        "rationale": "Property portal. Useful market signal, but listing freshness varies.",
    },
    {
        "match": "99acres.com",
        "source_type": "market_portal",
        "reliability": 0.72,
        "priority": 62,
        "rationale": "Property portal. Useful market signal, but listing freshness varies.",
    },
]


CATEGORY_KEYWORDS = {
    "legal_rera": (
        "rera",
        "registration",
        "registered",
        "compliance",
        "case",
        "legal",
        "litigation",
        "approval",
        "occupancy certificate",
        "oc",
    ),
    "financial_market": (
        "price",
        "sq ft",
        "sqft",
        "rent",
        "rental",
        "yield",
        "cost",
        "amenities",
        "sale",
        "resale",
        "market",
    ),
    "community_sentiment": (
        "reddit",
        "complaint",
        "resident",
        "buyer",
        "maintenance",
        "water",
        "traffic",
        "delay",
        "builder",
    ),
    "google_reviews": (
        "google",
        "maps",
        "star",
        "rating",
        "review",
        "reviews",
    ),
    "infrastructure_development": (
        "metro",
        "road",
        "highway",
        "water supply",
        "infrastructure",
        "bbmp",
        "bda",
        "connectivity",
    ),
}


NEGATIVE_SIGNALS = (
    "delay",
    "delayed",
    "complaint",
    "issue",
    "problem",
    "case",
    "litigation",
    "not registered",
    "no rera",
    "water shortage",
    "traffic",
    "poor",
    "bad",
    "fraud",
)

POSITIVE_SIGNALS = (
    "registered",
    "approved",
    "ready to move",
    "completed",
    "good",
    "excellent",
    "positive",
    "near metro",
    "oc received",
    "occupancy certificate",
)


def build_evidence_ledger(intelligence: dict[str, Any]) -> dict[str, Any]:
    """
    Build an auditable evidence ledger from raw Anakin intelligence.

    The returned structure is intentionally JSON-serializable so it can be
    passed to Gemini, shown in Streamlit, or persisted later.
    """
    source_map: dict[str, SourceProfile] = {}
    evidence: list[EvidenceItem] = []

    def source_for(url: str, title: str = "", fallback_type: str = "") -> SourceProfile:
        canonical = _canonical_url(url)
        if canonical in source_map:
            existing = source_map[canonical]
            if title and not existing.title:
                existing.title = title
            return existing

        profile = classify_source(canonical, title, fallback_type)
        profile.id = f"S{len(source_map) + 1:03d}"
        source_map[canonical] = profile
        return profile

    def add_item(
        *,
        category: str,
        claim: str,
        source: SourceProfile,
        excerpt: str,
        freshness: str = "unknown",
    ) -> None:
        normalized_claim = _clean_text(claim)
        normalized_excerpt = _clean_text(excerpt)
        if not normalized_claim and not normalized_excerpt:
            return
        if not normalized_claim:
            normalized_claim = normalized_excerpt[:220]

        confidence = _confidence_for(source, normalized_excerpt, freshness)
        evidence.append(
            EvidenceItem(
                id=f"E{len(evidence) + 1:03d}",
                category=category,
                claim=normalized_claim[:300],
                source_id=source.id,
                confidence=confidence,
                freshness=freshness or "unknown",
                signal=_signal_for(normalized_claim + " " + normalized_excerpt),
                excerpt=normalized_excerpt[:600],
            )
        )

    search_sections = {
        "web_search": ("general", "web_search"),
        "infra_search": ("infrastructure_development", "infrastructure_search"),
        "google_reviews": ("google_reviews", "google_reviews_search"),
        "rera_search": ("legal_rera", "k_rera_search"),
        "market_search": ("financial_market", "market_search"),
        "reddit_search": ("community_sentiment", "reddit_search"),
    }

    for key, (fallback_category, fallback_type) in search_sections.items():
        section = intelligence.get(key) or {}
        for result in section.get("results") or []:
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            date = result.get("date") or "unknown"
            source = source_for(url, title, fallback_type)
            category = _infer_category(
                " ".join([title, snippet, source.source_type]),
                fallback=fallback_category,
            )
            add_item(
                category=category,
                claim=title or snippet,
                source=source,
                excerpt=snippet,
                freshness=date,
            )

    for key, fallback_category, fallback_type in (
        ("scraped_pages", "financial_market", "scraped_page"),
        ("crawled_gov_pages", "legal_rera", "official_crawl"),
    ):
        section = intelligence.get(key) or {}
        for page in section.get("results") or []:
            markdown = page.get("markdown", "")
            url = page.get("url", "")
            title = _title_from_markdown(markdown) or url
            source = source_for(url, title, fallback_type)
            category = _infer_category(
                f"{title} {source.source_type} {markdown[:1200]}",
                fallback=fallback_category,
            )
            excerpt = _best_excerpt(markdown, category)
            add_item(
                category=category,
                claim=f"Full-page evidence from {source.domain or fallback_type}",
                source=source,
                excerpt=excerpt,
            )

    agentic = intelligence.get("agentic_research") or {}
    generated = agentic.get("generated_json")
    if agentic.get("success") and generated:
        summary = generated.get("summary", "") if isinstance(generated, dict) else str(generated)
        if summary:
            source = source_for("anakin://agentic-search", "Anakin Agentic Research", "agentic_research")
            add_item(
                category=_infer_category(summary, fallback="general"),
                claim="Anakin agentic research summary",
                source=source,
                excerpt=summary,
            )

    sources = [asdict(source) for source in sorted(source_map.values(), key=lambda s: (-s.priority, s.id))]
    items = [asdict(item) for item in sorted(evidence, key=lambda e: (-e.confidence, e.id))]

    return {
        "sources": sources,
        "items": items,
        "summary": _build_summary(sources, items),
        "contradictions": _detect_contradictions(items),
    }


def classify_source(url: str, title: str = "", fallback_type: str = "") -> SourceProfile:
    """Classify a URL into a source type and reliability score."""
    domain = _domain_from_url(url)
    haystack = f"{url} {domain} {title}".lower()

    for rule in SOURCE_RULES:
        if rule["match"] in haystack:
            return SourceProfile(
                id="",
                url=url,
                domain=domain,
                title=title,
                source_type=rule["source_type"],
                reliability=rule["reliability"],
                priority=rule["priority"],
                rationale=rule["rationale"],
            )

    if url.startswith("anakin://"):
        return SourceProfile(
            id="",
            url=url,
            domain="anakin",
            title=title,
            source_type=fallback_type or "derived_research",
            reliability=0.62,
            priority=52,
            rationale="Derived Anakin synthesis. Useful context, but primary sources should carry decisions.",
        )

    return SourceProfile(
        id="",
        url=url,
        domain=domain,
        title=title,
        source_type=fallback_type or "unclassified_web",
        reliability=0.58,
        priority=45,
        rationale="Unclassified web source. Needs corroboration from official or priority sources.",
    )


def _build_summary(sources: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for item in items:
        category = item.get("category", "general")
        categories[category] = categories.get(category, 0) + 1

    official_count = sum(
        1
        for source in sources
        if source.get("source_type") in {"official_rera", "government"}
    )
    priority_found = [
        source["source_type"]
        for source in sources
        if source.get("source_type")
        in {"official_rera", "market_portal", "owner_marketplace", "community_forum", "google_reviews"}
    ]
    high_confidence = sum(1 for item in items if item.get("confidence", 0) >= 0.78)
    avg_reliability = (
        round(sum(source.get("reliability", 0) for source in sources) / len(sources), 2)
        if sources
        else 0
    )

    quality_score = min(
        100,
        round(
            (avg_reliability * 45)
            + (min(len(items), 18) / 18 * 25)
            + (min(official_count, 2) / 2 * 20)
            + (min(len(set(priority_found)), 4) / 4 * 10)
        ),
    )

    return {
        "total_sources": len(sources),
        "total_evidence_items": len(items),
        "official_sources": official_count,
        "high_confidence_items": high_confidence,
        "average_source_reliability": avg_reliability,
        "coverage_by_category": categories,
        "priority_sources_found": sorted(set(priority_found)),
        "quality_score": quality_score,
    }


def _detect_contradictions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_category: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in items:
        signal = item.get("signal")
        if signal not in {"positive", "negative"}:
            continue
        category = item.get("category", "general")
        by_category.setdefault(category, {"positive": [], "negative": []})
        by_category[category][signal].append(item)

    contradictions = []
    for category, grouped in by_category.items():
        if grouped["positive"] and grouped["negative"]:
            contradictions.append(
                {
                    "category": category,
                    "summary": "Positive and negative signals both appear in the collected evidence.",
                    "positive_evidence_ids": [item["id"] for item in grouped["positive"][:3]],
                    "negative_evidence_ids": [item["id"] for item in grouped["negative"][:3]],
                }
            )
    return contradictions


def _canonical_url(url: str) -> str:
    if not url:
        return "unknown://source"
    return url.strip()


def _domain_from_url(url: str) -> str:
    if url.startswith("anakin://"):
        return "anakin"
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _clean_text(text: Any) -> str:
    if text is None:
        return ""
    return " ".join(str(text).replace("\n", " ").split())


def _title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _infer_category(text: str, fallback: str = "general") -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return fallback


def _best_excerpt(markdown: str, category: str) -> str:
    if not markdown:
        return ""
    keywords = CATEGORY_KEYWORDS.get(category, ())
    lines = [_clean_text(line) for line in markdown.splitlines()]
    lines = [line for line in lines if line]
    matches = [
        line for line in lines
        if any(keyword in line.lower() for keyword in keywords)
    ]
    selected = matches[:4] if matches else lines[:4]
    return " ".join(selected)[:900]


def _signal_for(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in NEGATIVE_SIGNALS):
        return "negative"
    if any(keyword in lowered for keyword in POSITIVE_SIGNALS):
        return "positive"
    return "neutral"


def _confidence_for(source: SourceProfile, excerpt: str, freshness: str) -> float:
    confidence = source.reliability
    if len(excerpt) > 180:
        confidence += 0.04
    if freshness and freshness != "unknown":
        confidence += 0.03
    return round(max(0.1, min(0.99, confidence)), 2)
