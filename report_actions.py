"""
report_actions.py

Export, sample, and local-cache helpers for Skywalker Scout reports.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CACHE_DIR = Path(".cache/reports")


def make_report_payload(
    property_name: str,
    scorecard: dict[str, Any] | None,
    intelligence: dict[str, Any],
    *,
    generated_at: str | None = None,
    source: str = "live",
) -> dict[str, Any]:
    """Create the canonical report payload used by session state, cache, and exports."""
    return {
        "property_name": property_name,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "source": source,
        "scorecard": scorecard,
        "intelligence": intelligence,
    }


def slugify_property_name(property_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", property_name.strip().lower()).strip("-")
    return slug or "property-report"


def report_cache_path(property_name: str) -> Path:
    return CACHE_DIR / f"{slugify_property_name(property_name)}.json"


def cache_report(report: dict[str, Any]) -> Path:
    """Persist a report payload locally for quick reloads."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    property_name = str(report.get("property_name") or "property-report")
    path = report_cache_path(property_name)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_cached_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_cached_reports() -> list[dict[str, str]]:
    """Return cached reports newest first for sidebar selection."""
    if not CACHE_DIR.exists():
        return []

    reports = []
    for path in sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = load_cached_report(path)
        except (OSError, json.JSONDecodeError):
            continue
        property_name = str(data.get("property_name") or path.stem)
        generated_at = str(data.get("generated_at") or "")
        label = property_name
        if generated_at:
            label = f"{property_name} ({generated_at[:10]})"
        reports.append({"label": label, "path": str(path)})
    return reports


def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def build_markdown_report(report: dict[str, Any]) -> str:
    """Build a portable Markdown report from a cached/live report payload."""
    property_name = report.get("property_name", "Property")
    generated_at = report.get("generated_at", "")
    scorecard = report.get("scorecard") or {}
    intelligence = report.get("intelligence") or {}
    ledger = intelligence.get("evidence_ledger") or {}
    evidence_summary = ledger.get("summary") or {}

    lines = [
        f"# Skywalker Scout Due Diligence Report",
        "",
        f"**Property:** {property_name}",
        f"**Generated:** {generated_at}",
        f"**Evidence Quality:** {evidence_summary.get('quality_score', 'N/A')}/100",
        "",
    ]

    if not scorecard:
        lines.extend(
            [
                "## Raw Intelligence Report",
                "",
                "Gemini formatting was unavailable for this report. Raw Anakin intelligence and evidence metadata are included in the JSON export.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Executive Summary",
            "",
            str(scorecard.get("executive_summary", "No executive summary available.")),
            "",
            f"**Overall Risk Score:** {scorecard.get('risk_score', 'N/A')}/100",
            "",
        ]
    )

    _append_flags(lines, "Risk Flags", scorecard.get("red_flags", []))
    _append_flags(lines, "Strength Signals", scorecard.get("green_flags", []))

    sections = [
        ("Financial Viability", scorecard.get("financial_viability", {})),
        ("Legal / RERA Status", scorecard.get("legal_rera_status", {})),
        ("Infrastructure Development", scorecard.get("infrastructure_development", {})),
        ("Community Sentiment", scorecard.get("community_sentiment", {})),
        ("Google Review Signal", scorecard.get("google_reviews", {})),
    ]

    for title, section in sections:
        lines.extend([f"## {title}", ""])
        lines.append(f"**Score:** {section.get('score', 'N/A')}/10")
        lines.append("")
        lines.append(str(section.get("summary", "No summary available.")))
        lines.append("")
        points = section.get("key_points") or section.get("highlights") or []
        _append_bullets(lines, points)

    lines.extend(
        [
            "## Evidence Summary",
            "",
            f"- Total sources: {evidence_summary.get('total_sources', 0)}",
            f"- Evidence items: {evidence_summary.get('total_evidence_items', 0)}",
            f"- Official sources: {evidence_summary.get('official_sources', 0)}",
            f"- High-confidence items: {evidence_summary.get('high_confidence_items', 0)}",
            "",
        ]
    )

    top_sources = (ledger.get("sources") or [])[:8]
    if top_sources:
        lines.extend(["## Top Sources", ""])
        for source in top_sources:
            lines.append(
                f"- {source.get('source_type', 'source')} "
                f"({source.get('reliability', 'N/A')}): {source.get('url', '')}"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def sample_report() -> dict[str, Any]:
    """Return a realistic demo report that does not require API access."""
    property_name = "JRC Wildwoods, Sarjapur road"
    scorecard = {
        "financial_viability": {
            "score": 7,
            "summary": "Market sources indicate active buyer and rental interest around Sarjapur Road. Pricing appears competitive but should be benchmarked against live Housing.com and NoBroker listings before purchase.",
            "price_per_sqft": "Insufficient data from sample",
            "price_trend": "stable",
            "rental_yield": "Insufficient data from sample",
            "key_points": [
                "Housing.com and NoBroker are configured as priority market sources.",
                "Live run should validate price per sqft, resale inventory, and rent.",
            ],
        },
        "legal_rera_status": {
            "score": 6,
            "summary": "The live pipeline prioritizes K-RERA records before market or community claims. In demo mode, legal status remains a watch item until an official K-RERA record is retrieved.",
            "rera_number": None,
            "compliance_status": "unknown",
            "pending_cases": None,
            "key_points": ["Official K-RERA lookup is mandatory for a production-grade verdict."],
        },
        "community_sentiment": {
            "score": 6,
            "summary": "Community signal should be interpreted as anecdotal unless corroborated. Reddit is useful for water, traffic, maintenance, and builder-experience patterns.",
            "overall_rating": None,
            "common_praises": ["Location and connectivity can be strong if nearby infrastructure is confirmed."],
            "common_complaints": ["Water, traffic, and maintenance should be explicitly checked in live Reddit threads."],
        },
        "google_reviews": {
            "score": 6,
            "summary": "Google review snippets are useful for directional sentiment but should not be treated as legal or financial evidence.",
            "average_rating": "Insufficient data from sample",
            "total_reviews": None,
            "highlights": ["Live query searches Google-indexed rating snippets."],
            "rating_trend": "unknown",
        },
        "infrastructure_development": {
            "score": 7,
            "summary": "Sarjapur Road has meaningful infrastructure relevance, but commute, water supply, and road widening claims need source-backed validation.",
            "key_projects": ["Road and connectivity improvements should be checked through official or news sources."],
        },
        "location_coordinates": {"latitude": 12.8636, "longitude": 77.7864},
        "risk_score": 48,
        "executive_summary": "This demo report shows the intended output format without spending API calls. A live report should prioritize K-RERA for legal truth, Housing.com and NoBroker for pricing, Reddit for resident experience, and Google snippets for review sentiment.",
        "red_flags": [
            "Official K-RERA status is not confirmed in demo mode.",
            "Water and traffic risks should be validated through live community and infrastructure sources.",
        ],
        "green_flags": [
            "The pipeline is configured to separate official, market, community, and review evidence.",
            "Evidence quality and source reliability are visible in the final dossier.",
        ],
    }

    intelligence = {
        "property_name": property_name,
        "web_search": {"success": True, "results": []},
        "infra_search": {"success": True, "results": []},
        "google_reviews": {"success": True, "results": []},
        "rera_search": {"success": False, "results": [], "error": "Demo mode"},
        "market_search": {"success": False, "results": [], "error": "Demo mode"},
        "reddit_search": {"success": False, "results": [], "error": "Demo mode"},
        "scraped_pages": {"success": False, "results": [], "error": "Demo mode"},
        "crawled_gov_pages": {"success": False, "results": [], "error": "Demo mode"},
        "agentic_research": {"success": False, "generated_json": None, "error": "Demo mode"},
        "evidence_ledger": {
            "sources": [
                {
                    "id": "S001",
                    "url": "https://rera.karnataka.gov.in",
                    "domain": "rera.karnataka.gov.in",
                    "title": "K-RERA",
                    "source_type": "official_rera",
                    "reliability": 0.98,
                    "priority": 100,
                    "rationale": "Official Karnataka RERA registry for legal verification.",
                },
                {
                    "id": "S002",
                    "url": "https://housing.com",
                    "domain": "housing.com",
                    "title": "Housing.com",
                    "source_type": "market_portal",
                    "reliability": 0.82,
                    "priority": 84,
                    "rationale": "Structured market listing source.",
                },
                {
                    "id": "S003",
                    "url": "https://reddit.com/r/bangalore",
                    "domain": "reddit.com",
                    "title": "Reddit r/bangalore",
                    "source_type": "community_forum",
                    "reliability": 0.66,
                    "priority": 70,
                    "rationale": "Anecdotal resident and buyer experience source.",
                },
            ],
            "items": [
                {
                    "id": "E001",
                    "category": "legal_rera",
                    "claim": "K-RERA should be treated as legal source of truth.",
                    "source_id": "S001",
                    "confidence": 0.98,
                    "freshness": "demo",
                    "signal": "neutral",
                    "excerpt": "Demo mode confirms routing logic, not live registration status.",
                }
            ],
            "summary": {
                "total_sources": 3,
                "total_evidence_items": 1,
                "official_sources": 1,
                "high_confidence_items": 1,
                "average_source_reliability": 0.82,
                "coverage_by_category": {"legal_rera": 1},
                "priority_sources_found": ["official_rera", "market_portal", "community_forum"],
                "quality_score": 72,
            },
            "contradictions": [],
        },
        "errors": ["Demo mode: no live Anakin or Gemini calls were made."],
    }

    return make_report_payload(property_name, scorecard, intelligence, source="sample")


def _append_flags(lines: list[str], title: str, items: Any) -> None:
    lines.extend([f"## {title}", ""])
    _append_bullets(lines, items, empty="None identified.")


def _append_bullets(lines: list[str], items: Any, *, empty: str = "No key points available.") -> None:
    if not items:
        lines.extend([f"- {empty}", ""])
        return
    if not isinstance(items, list):
        items = [items]
    for item in items:
        lines.append(f"- {item}")
    lines.append("")
