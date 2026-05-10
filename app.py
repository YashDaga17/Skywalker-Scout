"""
app.py

Skywalker Scout -- Autonomous Real Estate Due Diligence Engine.

Primary data engine: Anakin. Gemini is used only to format Anakin's output
into a scorecard. The Streamlit app presents a single professional due
diligence dossier with source reliability and evidence traceability.
"""

from __future__ import annotations

import html
import os
import re
from typing import Any

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from report_actions import (
    build_markdown_report,
    cache_report,
    list_cached_reports,
    load_cached_report,
    make_report_payload,
    report_json,
    sample_report,
    slugify_property_name,
)

try:
    import folium
    from streamlit_folium import st_folium
except Exception:  # pragma: no cover - optional visual dependency
    folium = None
    st_folium = None

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional map dependency
    pd = None

load_dotenv()


st.set_page_config(
    page_title="Skywalker Scout | Real Estate Intelligence",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #090f1d;
    --bg-soft: #0d1628;
    --panel: #111827;
    --panel-soft: #0f172a;
    --panel-raised: #152033;
    --border: #253249;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --faint: #64748b;
    --blue: #60a5fa;
    --blue-soft: rgba(96, 165, 250, 0.12);
    --teal: #2dd4bf;
    --amber: #f59e0b;
    --amber-soft: rgba(245, 158, 11, 0.12);
    --clay: #f97316;
    --clay-soft: rgba(249, 115, 22, 0.12);
    --slate: #cbd5e1;
}

.stApp {
    background:
        radial-gradient(circle at 20% 0%, rgba(37, 99, 235, 0.12), transparent 28rem),
        linear-gradient(180deg, #090f1d 0%, #0b1220 55%, #090f1d 100%);
    color: var(--text);
    font-family: 'Inter', sans-serif;
}

.block-container {
    max-width: 1180px;
    padding-top: 1.4rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #0b1220;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * {
    color: var(--text);
}

.app-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding: 0.6rem 0 1rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.1rem;
}

.brand-title {
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: 0;
    color: var(--text);
    margin: 0;
}

h1 {
    color: var(--text);
}

.brand-subtitle {
    color: var(--muted);
    margin-top: 0.25rem;
    font-size: 0.98rem;
}

.status-pill {
    background: var(--blue-soft);
    border: 1px solid rgba(96, 165, 250, 0.32);
    color: var(--blue);
    border-radius: 999px;
    padding: 0.45rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 700;
    white-space: nowrap;
}

.dossier {
    display: flex;
    flex-direction: column;
    gap: 0.95rem;
}

.report-hero {
    background: linear-gradient(180deg, rgba(21, 32, 51, 0.96) 0%, rgba(15, 23, 42, 0.96) 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem 1.25rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.18);
}

.report-eyebrow {
    color: var(--blue);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.report-title {
    color: var(--text);
    font-size: 1.7rem;
    font-weight: 800;
    line-height: 1.2;
    margin-top: 0.25rem;
}

.report-subtitle {
    color: var(--muted);
    font-size: 0.95rem;
    margin-top: 0.35rem;
}

.section {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.05rem 1.15rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.14);
}

.section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.75rem;
}

.section-kicker {
    color: var(--blue);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}

.section-title {
    font-size: 1.12rem;
    font-weight: 800;
    color: var(--text);
}

.section-summary {
    color: var(--slate);
    font-size: 0.96rem;
    line-height: 1.6;
    margin: 0.4rem 0 0;
}

.score-chip {
    min-width: 72px;
    text-align: center;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.35rem 0.6rem;
    color: var(--slate);
    background: var(--panel-raised);
    font-size: 0.82rem;
    font-weight: 800;
}

.risk-overview {
    display: grid;
    grid-template-columns: minmax(220px, 0.75fr) minmax(0, 1.75fr);
    gap: 1rem;
    align-items: stretch;
}

.risk-score-box {
    background: var(--panel-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
}

.risk-label {
    color: var(--muted);
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.risk-number {
    color: var(--text);
    font-size: 3rem;
    font-weight: 800;
    line-height: 1;
    margin-top: 0.5rem;
}

.risk-caption {
    color: var(--slate);
    font-size: 0.92rem;
    font-weight: 700;
    margin-top: 0.35rem;
}

.risk-track {
    background: #1e293b;
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
    margin-top: 1rem;
}

.risk-fill {
    height: 10px;
    border-radius: 999px;
}

.summary-box {
    background: var(--panel-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    min-height: 100%;
}

.summary-box p {
    color: var(--slate);
    line-height: 1.65;
    margin: 0;
}

.metric-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin-top: 0.85rem;
}

.metric-tile {
    background: var(--panel-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.8rem;
}

.chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
}

.chart-panel {
    background: var(--panel-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem;
    min-height: 320px;
}

.metric-label {
    color: var(--muted);
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.metric-value {
    color: var(--text);
    font-size: 1rem;
    font-weight: 800;
    margin-top: 0.28rem;
    overflow-wrap: anywhere;
}

.signal-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;
}

.signal-panel {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.95rem;
    background: var(--panel-raised);
}

.signal-panel.concern {
    border-color: #fed7aa;
    background: var(--amber-soft);
}

.signal-panel.positive {
    border-color: rgba(96, 165, 250, 0.32);
    background: var(--blue-soft);
}

.signal-title {
    font-weight: 800;
    margin-bottom: 0.55rem;
    color: var(--text);
}

.item-list {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}

.list-item {
    color: var(--slate);
    font-size: 0.92rem;
    line-height: 1.48;
    border-top: 1px solid rgba(148, 163, 184, 0.14);
    padding-top: 0.45rem;
}

.list-item:first-child {
    border-top: none;
    padding-top: 0;
}

.source-list {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
}

.source-row {
    background: var(--panel-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem;
}

.source-title {
    font-weight: 800;
    color: var(--text);
    font-size: 0.9rem;
}

.source-snippet {
    color: var(--slate);
    font-size: 0.84rem;
    line-height: 1.45;
    margin-top: 0.25rem;
}

.source-url {
    color: var(--muted);
    font-size: 0.74rem;
    margin-top: 0.28rem;
    overflow-wrap: anywhere;
}

.evidence-row {
    border-top: 1px solid var(--border);
    padding: 0.75rem 0;
}

.evidence-row:first-child {
    border-top: none;
}

.evidence-meta {
    color: var(--muted);
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.evidence-claim {
    color: var(--text);
    font-weight: 700;
    margin-top: 0.25rem;
}

.evidence-excerpt {
    color: var(--slate);
    font-size: 0.88rem;
    line-height: 1.5;
    margin-top: 0.25rem;
}

.empty-state {
    background: var(--panel);
    border: 1px dashed var(--border);
    border-radius: 8px;
    padding: 1.2rem;
    color: var(--muted);
}

div[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem;
}

.stButton > button,
.stDownloadButton > button {
    background: #2563eb;
    color: white;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    font-weight: 600;
}

.stTextInput input {
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text) !important;
}

.stTextInput input:focus {
    border-color: var(--blue);
    box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.35);
}

.route-list {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.58);
    padding: 0.75rem;
}

.route-item {
    border-top: 1px solid rgba(148, 163, 184, 0.14);
    padding: 0.62rem 0;
}

.route-item:first-child {
    border-top: none;
    padding-top: 0;
}

.route-label {
    color: var(--text);
    font-size: 0.86rem;
    font-weight: 800;
}

.route-detail {
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.35;
    margin-top: 0.15rem;
}

@media (max-width: 900px) {
    .app-header,
    .risk-overview,
    .signal-grid,
    .chart-grid,
    .metric-row {
        grid-template-columns: 1fr;
        display: grid;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value: Any) -> str:
    """HTML-escape display values used in custom markup."""
    if value is None:
        return ""
    return html.escape(str(value))


def risk_label(score: int) -> str:
    if score <= 25:
        return "Low risk"
    if score <= 50:
        return "Moderate risk"
    if score <= 65:
        return "Elevated risk"
    if score <= 80:
        return "High risk"
    return "Critical risk"


def risk_color(score: int) -> str:
    if score <= 25:
        return "#60a5fa"
    if score <= 50:
        return "#2dd4bf"
    if score <= 65:
        return "#f59e0b"
    if score <= 80:
        return "#fb923c"
    return "#f87171"


def risk_explanation(score: int) -> str:
    if score <= 25:
        return "Low exposure. Lower is safer."
    if score <= 50:
        return "Moderate exposure. Lower is safer."
    if score <= 65:
        return "Elevated exposure. Review risk flags carefully."
    if score <= 80:
        return "High exposure. Requires strong source-backed mitigation."
    return "Critical exposure. Avoid unless issues are resolved."


def session_report() -> dict[str, Any] | None:
    report = st.session_state.get("last_report")
    return report if isinstance(report, dict) else None


def store_report(property_name: str, scorecard: dict[str, Any] | None, intelligence: dict[str, Any]) -> None:
    report = make_report_payload(property_name, scorecard, intelligence)
    st.session_state["last_report"] = report
    try:
        cache_report(report)
    except OSError:
        st.warning("Report generated, but local cache write failed.")


def usable_evidence_count(intelligence: dict[str, Any]) -> int:
    """Count evidence that can reasonably support a formatted investment report."""
    ledger_summary = ((intelligence.get("evidence_ledger") or {}).get("summary") or {})
    ledger_count = as_int(ledger_summary.get("total_evidence_items"), fallback=0)
    if ledger_count:
        return ledger_count

    total = 0
    for key in (
        "web_search",
        "infra_search",
        "google_reviews",
        "rera_search",
        "market_search",
        "reddit_search",
    ):
        section = intelligence.get(key) or {}
        total += len(section.get("results") or [])

    for key in ("scraped_pages", "crawled_gov_pages"):
        section = intelligence.get(key) or {}
        total += sum(1 for page in section.get("results") or [] if page.get("markdown"))

    agentic = intelligence.get("agentic_research") or {}
    if agentic.get("success") and agentic.get("generated_json"):
        total += 1

    return total


def annotate_collection_summary(intelligence: dict[str, Any]) -> None:
    warnings = intelligence.get("errors") or []
    evidence_count = usable_evidence_count(intelligence)
    intelligence["collection_summary"] = {
        "usable_evidence_items": evidence_count,
        "warning_count": len(warnings),
        "has_blocking_collection_gap": evidence_count == 0,
    }


def render_sidebar_downloads(report: dict[str, Any] | None) -> None:
    st.markdown("### Exports")
    if not report:
        st.caption("Run or load a report to enable dossier downloads.")
        return

    property_name = str(report.get("property_name") or "property-report")
    filename_slug = slugify_property_name(property_name)
    st.download_button(
        "Download Dossier",
        data=build_markdown_report(report),
        file_name=f"{filename_slug}-due-diligence.md",
        mime="text/markdown",
        type="primary",
        width="stretch",
    )
    st.download_button(
        "Download Raw JSON",
        data=report_json(report),
        file_name=f"{filename_slug}-intelligence.json",
        mime="application/json",
        width="stretch",
    )


def as_int(value: Any, fallback: int = 50) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def as_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def progress_from_message(message: str, current: int) -> int:
    match = re.search(r"Step\s+(\d+)/(\d+)", message)
    if not match:
        return current
    step = int(match.group(1))
    total = max(1, int(match.group(2)))
    return max(current, min(95, round(step / total * 100)))


def scorecard_coordinates(scorecard: dict[str, Any]) -> tuple[float, float]:
    coords = scorecard.get("location_coordinates", {})
    try:
        lat = float(coords.get("latitude")) if coords.get("latitude") is not None else None
        lon = float(coords.get("longitude")) if coords.get("longitude") is not None else None
    except (ValueError, TypeError):
        lat, lon = None, None

    # Demo-safe fallback: Sarjapur Road area.
    if lat is None or lon is None:
        return 12.9239, 77.6844
    return lat, lon


def coerce_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def list_items(items: Any, empty: str = "No data available.") -> str:
    items = [item for item in coerce_list(items) if item not in (None, "")]
    if not items:
        return f"<div class='list-item'>{esc(empty)}</div>"
    return "".join(f"<div class='list-item'>{esc(item)}</div>" for item in items if item)


def metric_tile(label: str, value: Any) -> str:
    return (
        "<div class='metric-tile'>"
        f"<div class='metric-label'>{esc(label)}</div>"
        f"<div class='metric-value'>{esc(value if value not in (None, '') else 'N/A')}</div>"
        "</div>"
    )


def section_header(kicker: str, title: str, score: Any = None) -> str:
    score_html = ""
    if score is not None:
        score_text = f"{score}/10" if isinstance(score, int) else score
        score_html = f"<div class='score-chip'>{esc(score_text)}</div>"
    return (
        "<div class='section-header'>"
        "<div>"
        f"<div class='section-kicker'>{esc(kicker)}</div>"
        f"<div class='section-title'>{esc(title)}</div>"
        "</div>"
        f"{score_html}"
        "</div>"
    )


def render_app_header() -> None:
    st.markdown(
        """
        <div class="app-header">
            <div>
                <div class="brand-title">Skywalker Scout</div>
                <div class="brand-subtitle">Institutional real-estate due diligence for Bengaluru properties.</div>
            </div>
            <div class="status-pill">Anakin-first intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
            Select a Bengaluru property or builder in the sidebar and run an investigation.
            The dossier will prioritize official, market, community, and review sources in that order.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sources(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info("No source results available.")
        return
    rows = []
    for result in results:
        title = esc(result.get("title", "Untitled"))
        snippet = esc(result.get("snippet", ""))
        url = esc(result.get("url", ""))
        date = esc(result.get("date", ""))
        date_text = f" | {date}" if date else ""
        rows.append(
            "<div class='source-row'>"
            f"<div class='source-title'>{title}</div>"
            f"<div class='source-snippet'>{snippet}</div>"
            f"<div class='source-url'>{url}{date_text}</div>"
            "</div>"
        )
    st.markdown("<div class='source-list'>" + "".join(rows) + "</div>", unsafe_allow_html=True)


def render_signal_panels(scorecard: dict[str, Any]) -> None:
    red_flags = coerce_list(scorecard.get("red_flags", []))
    green_flags = coerce_list(scorecard.get("green_flags", []))
    st.markdown(
        "<div class='section'>"
        + section_header("Signals", "Risk Flags and Strength Signals")
        + "</div>",
        unsafe_allow_html=True,
    )
    risk_col, strength_col = st.columns(2)
    with risk_col:
        st.markdown("**Risk Flags**")
        if red_flags:
            for flag in red_flags:
                st.warning(str(flag))
        else:
            st.info("No material risk flags were extracted from the current evidence.")
    with strength_col:
        st.markdown("**Strength Signals**")
        if green_flags:
            for flag in green_flags:
                st.success(str(flag))
        else:
            st.info("No strength signals were extracted from the current evidence.")


def render_risk_and_summary(scorecard: dict[str, Any], property_name: str) -> None:
    risk_score = as_int(scorecard.get("risk_score"), 50)
    summary = scorecard.get("executive_summary", "Analysis pending.")
    color = risk_color(risk_score)
    st.markdown(
        "<div class='section'>"
        + section_header("Executive View", "Investment Risk Summary")
        + "</div>",
        unsafe_allow_html=True,
    )
    score_col, summary_col, map_col = st.columns([0.8, 1.35, 1.0])
    with score_col:
        st.markdown(
            "<div class='risk-overview'>"
            + "<div class='risk-score-box'>"
            + "<div class='risk-label'>Overall risk score</div>"
            + f"<div class='risk-number' style='color:{color};'>{risk_score}/100</div>"
            + f"<div class='risk-caption'>{esc(risk_label(risk_score))}</div>"
            + f"<div class='risk-caption'>{esc(risk_explanation(risk_score))}</div>"
            + "<div class='risk-track'>"
            + f"<div class='risk-fill' style='width:{max(0, min(100, risk_score))}%; background:{color};'></div>"
            + "</div>"
            + "</div>"
            + "</div>",
            unsafe_allow_html=True,
        )
    with summary_col:
        st.markdown(
            "<div class='summary-box'>"
            + f"<p>{esc(summary)}</p>"
            + "</div>",
            unsafe_allow_html=True,
        )
    with map_col:
        st.markdown("**Location Context**")
        render_location_anchor(scorecard, property_name)


def render_metric_strip(scorecard: dict[str, Any], evidence_summary: dict[str, Any]) -> None:
    fin = scorecard.get("financial_viability", {})
    legal = scorecard.get("legal_rera_status", {})
    grev = scorecard.get("google_reviews", {})
    metrics = [
        metric_tile("Price per sqft", fin.get("price_per_sqft", "N/A")),
        metric_tile("RERA status", legal.get("compliance_status", "Unknown")),
        metric_tile("Google rating", grev.get("average_rating", "N/A")),
        metric_tile("Evidence quality", f"{evidence_summary.get('quality_score', 0)}/100"),
    ]
    st.markdown(
        "<div class='section'><div class='metric-row'>"
        + "".join(metrics)
        + "</div></div>",
        unsafe_allow_html=True,
    )


def section_scores(scorecard: dict[str, Any]) -> list[tuple[str, int]]:
    sections = [
        ("Financial", scorecard.get("financial_viability", {})),
        ("Legal/RERA", scorecard.get("legal_rera_status", {})),
        ("Infrastructure", scorecard.get("infrastructure_development", {})),
        ("Community", scorecard.get("community_sentiment", {})),
        ("Reviews", scorecard.get("google_reviews", {})),
    ]
    return [(label, max(0, min(10, as_int(data.get("score"), 5)))) for label, data in sections]


def render_report_charts(scorecard: dict[str, Any], intelligence: dict[str, Any]) -> None:
    scores = section_scores(scorecard)
    labels = [label for label, _score in scores]
    values = [score for _label, score in scores]

    score_fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color="#60a5fa",
            text=[f"{value}/10" for value in values],
            textposition="auto",
            hovertemplate="%{y}: %{x}/10<extra></extra>",
        )
    )
    score_fig.update_layout(
        title="Section Scores",
        xaxis=dict(range=[0, 10], gridcolor="#253249", zerolinecolor="#253249"),
        yaxis=dict(autorange="reversed"),
        height=300,
        margin=dict(l=10, r=10, t=42, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"),
    )

    ledger = intelligence.get("evidence_ledger") or {}
    sources = ledger.get("sources") or []
    source_counts: dict[str, int] = {}
    reliability_totals: dict[str, float] = {}
    for source in sources:
        source_type = str(source.get("source_type", "unknown")).replace("_", " ").title()
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        reliability_totals[source_type] = reliability_totals.get(source_type, 0) + as_float(source.get("reliability"))

    source_labels = list(source_counts.keys()) or ["No sources"]
    source_values = list(source_counts.values()) or [1]
    source_reliability = [
        round((reliability_totals[label] / source_counts[label]) * 100)
        for label in source_counts
    ] or [0]

    source_fig = go.Figure(
        data=[
            go.Bar(
                name="Sources",
                x=source_labels,
                y=source_values,
                marker_color="#2dd4bf",
                yaxis="y",
                hovertemplate="%{x}: %{y} sources<extra></extra>",
            ),
            go.Scatter(
                name="Avg reliability",
                x=source_labels,
                y=source_reliability,
                mode="lines+markers",
                marker=dict(color="#f59e0b", size=8),
                line=dict(color="#f59e0b", width=2),
                yaxis="y2",
                hovertemplate="%{x}: %{y}% reliability<extra></extra>",
            ),
        ]
    )
    source_fig.update_layout(
        title="Source Mix and Reliability",
        height=300,
        margin=dict(l=10, r=10, t=42, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Count", gridcolor="#253249", zerolinecolor="#253249"),
        yaxis2=dict(title="Reliability", overlaying="y", side="right", range=[0, 100], showgrid=False),
    )

    st.markdown(
        "<div class='section'>"
        + section_header("Analytics", "Score and Source Diagnostics")
        + "</div>",
        unsafe_allow_html=True,
    )
    col_score, col_source = st.columns(2)
    with col_score:
        st.plotly_chart(score_fig, width="stretch", config={"displayModeBar": False})
    with col_source:
        st.plotly_chart(source_fig, width="stretch", config={"displayModeBar": False})


def render_analysis_section(
    kicker: str,
    title: str,
    section: dict[str, Any],
    detail_fields: list[tuple[str, str]],
    extra_items: list[Any] | None = None,
) -> None:
    score = section.get("score")
    if isinstance(score, str) and score.isdigit():
        score = int(score)
    summary = section.get("summary", "No summary available.")

    details = []
    for label, key in detail_fields:
        details.append(metric_tile(label, section.get(key, "N/A")))

    key_points = coerce_list(section.get("key_points", []))
    if extra_items:
        key_points = key_points + coerce_list(extra_items)

    html_block = (
        "<div class='section'>"
        + section_header(kicker, title, score)
        + f"<p class='section-summary'>{esc(summary)}</p>"
    )
    if details:
        html_block += "<div class='metric-row'>" + "".join(details) + "</div>"
    if key_points:
        html_block += (
            "<div style='margin-top:0.85rem;' class='item-list'>"
            + list_items(key_points)
            + "</div>"
        )
    html_block += "</div>"
    st.markdown(html_block, unsafe_allow_html=True)


def render_evidence_ledger(intelligence: dict[str, Any]) -> dict[str, Any]:
    ledger = intelligence.get("evidence_ledger") or {}
    summary = ledger.get("summary") or {}
    sources = ledger.get("sources") or []
    items = ledger.get("items") or []
    contradictions = ledger.get("contradictions") or []

    metrics = [
        metric_tile("Sources", summary.get("total_sources", 0)),
        metric_tile("Evidence items", summary.get("total_evidence_items", 0)),
        metric_tile("Official sources", summary.get("official_sources", 0)),
        metric_tile("High-confidence items", summary.get("high_confidence_items", 0)),
    ]

    st.markdown(
        "<div class='section'>"
        + section_header("Audit Trail", "Evidence Ledger and Source Reliability")
        + "<div class='metric-row'>"
        + "".join(metrics)
        + "</div>"
        + "</div>",
        unsafe_allow_html=True,
    )

    if contradictions:
        st.markdown(
            "<div class='section'>"
            + section_header("Evidence Review", "Potential Contradictions")
            + "<div class='item-list'>"
            + list_items([c.get("summary", c) for c in contradictions])
            + "</div></div>",
            unsafe_allow_html=True,
        )

    if sources:
        top_sources = sorted(sources, key=lambda s: s.get("priority", 0), reverse=True)[:8]
        rows = []
        for source in top_sources:
            rows.append(
                "<div class='source-row'>"
                f"<div class='source-title'>{esc(source.get('source_type', 'source'))} "
                f"({esc(source.get('reliability', ''))})</div>"
                f"<div class='source-snippet'>{esc(source.get('rationale', ''))}</div>"
                f"<div class='source-url'>{esc(source.get('url', ''))}</div>"
                "</div>"
            )
        st.markdown(
            "<div class='section'>"
            + section_header("Source Ranking", "Priority Sources Used")
            + "<div class='source-list'>"
            + "".join(rows)
            + "</div></div>",
            unsafe_allow_html=True,
        )

    if items:
        rows = []
        for item in items[:12]:
            rows.append(
                "<div class='evidence-row'>"
                f"<div class='evidence-meta'>{esc(item.get('id'))} | "
                f"{esc(item.get('category'))} | confidence {esc(item.get('confidence'))} | "
                f"{esc(item.get('signal'))}</div>"
                f"<div class='evidence-claim'>{esc(item.get('claim'))}</div>"
                f"<div class='evidence-excerpt'>{esc(item.get('excerpt'))}</div>"
                "</div>"
            )
        st.markdown(
            "<div class='section'>"
            + section_header("Claim Traceability", "Top Evidence Items")
            + "".join(rows)
            + "</div>",
            unsafe_allow_html=True,
        )

    return summary


def render_location_anchor(scorecard: dict[str, Any], property_name: str) -> None:
    lat, lon = scorecard_coordinates(scorecard)
    if pd is not None:
        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=12)
    else:
        st.caption(f"{property_name}: {lat:.4f}, {lon:.4f}")


def render_location(scorecard: dict[str, Any], property_name: str) -> None:
    coords = scorecard.get("location_coordinates", {})
    try:
        lat = float(coords.get("latitude")) if coords.get("latitude") is not None else None
        lon = float(coords.get("longitude")) if coords.get("longitude") is not None else None
    except (ValueError, TypeError):
        lat, lon = None, None
    if lat is None or lon is None:
        return

    st.markdown(
        "<div class='section'>"
        + section_header("Location", "Mapped Property Context")
        + "</div>",
        unsafe_allow_html=True,
    )
    if folium and st_folium:
        map_obj = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            color="#175cd3",
            weight=2,
            fill=True,
            fill_color="#175cd3",
            fill_opacity=0.85,
            popup=property_name,
            tooltip=property_name,
        ).add_to(map_obj)
        st_folium(map_obj, width=None, height=320)
    else:
        st.info(f"Location coordinates found: {lat}, {lon}")


def render_raw_expanders(intelligence: dict[str, Any]) -> None:
    sections = [
        ("K-RERA Official Search", "rera_search"),
        ("Housing.com and NoBroker Market Search", "market_search"),
        ("Reddit Community Search", "reddit_search"),
        ("General Web Search", "web_search"),
        ("Infrastructure Search", "infra_search"),
        ("Google Review Snippets", "google_reviews"),
    ]

    with st.expander("Raw Priority Search Results"):
        for title, key in sections:
            st.markdown(f"#### {title}")
            render_sources((intelligence.get(key) or {}).get("results", []))

    with st.expander("Scraped Priority Pages"):
        scraped = intelligence.get("scraped_pages") or {}
        if scraped.get("success") and scraped.get("results"):
            for page in scraped["results"]:
                st.markdown(f"**{page.get('url', 'Unknown')}**")
                markdown = page.get("markdown", "")
                preview = markdown[:1200] + (f"\n\n... ({len(markdown)} total characters)" if len(markdown) > 1200 else "")
                st.text(preview or "No markdown returned.")
                st.divider()
        else:
            st.info("No scraped page data available.")

    with st.expander("Government Crawl Results"):
        crawled = intelligence.get("crawled_gov_pages") or {}
        if crawled.get("success") and crawled.get("results"):
            for page in crawled["results"]:
                st.markdown(f"**{page.get('url', 'Unknown')}**")
                markdown = page.get("markdown", "")
                st.text(markdown[:1200] or "No markdown returned.")
                st.divider()
        else:
            st.info("No government crawl data available.")

    with st.expander("Anakin Agentic Research"):
        agentic = intelligence.get("agentic_research") or {}
        generated = agentic.get("generated_json")
        if agentic.get("success") and generated:
            if isinstance(generated, dict):
                if generated.get("summary"):
                    st.markdown(generated["summary"])
                if generated.get("structured_data"):
                    st.json(generated["structured_data"])
            else:
                st.markdown(str(generated))
        else:
            st.info(agentic.get("error", "No agentic research available."))

    errors = intelligence.get("errors", [])
    if errors:
        with st.expander("Collection Warnings"):
            for error in errors:
                st.write(error)


def render_raw_only(intelligence: dict[str, Any]) -> None:
    collection_summary = intelligence.get("collection_summary") or {}
    st.markdown(
        "<div class='section'>"
        + section_header("Raw Intelligence", "Gemini Formatting Unavailable")
        + "<p class='section-summary'>Anakin data was collected, but Gemini formatting did not complete. "
        + "The raw source material and evidence ledger are still available below.</p>"
        + "</div>",
        unsafe_allow_html=True,
    )
    if collection_summary.get("has_blocking_collection_gap") or usable_evidence_count(intelligence) == 0:
        st.error(
            "Anakin did not return usable source evidence for this run. "
            "The upstream search or agentic research service may be failing; review Collection Warnings below."
        )
    render_evidence_ledger(intelligence)
    render_raw_expanders(intelligence)


def render_scorecard(property_name: str, scorecard: dict[str, Any], intelligence: dict[str, Any]) -> None:
    evidence_summary = (intelligence.get("evidence_ledger") or {}).get("summary") or {}
    evidence_score = evidence_summary.get("quality_score", 0)

    st.markdown(
        "<div class='report-hero'>"
        "<div class='report-eyebrow'>Due Diligence Dossier</div>"
        f"<div class='report-title'>{esc(property_name)}</div>"
        "<div class='report-subtitle'>"
        "Evidence-first investment review using Anakin source collection, priority domain search, "
        f"and a source quality score of {esc(evidence_score)}/100."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    collection_summary = intelligence.get("collection_summary") or {}
    if collection_summary.get("warning_count"):
        st.warning(
            f"Anakin returned {collection_summary['warning_count']} collection warning(s). "
            "Use the evidence ledger and raw expanders before treating this as final."
        )
    render_risk_and_summary(scorecard, property_name)
    render_metric_strip(scorecard, evidence_summary)
    render_report_charts(scorecard, intelligence)
    render_signal_panels(scorecard)

    render_analysis_section(
        "Financial",
        "Market Price and Investment Viability",
        scorecard.get("financial_viability", {}),
        [
            ("Price per sqft", "price_per_sqft"),
            ("Price trend", "price_trend"),
            ("Rental yield", "rental_yield"),
        ],
    )
    render_analysis_section(
        "Legal",
        "K-RERA and Compliance Status",
        scorecard.get("legal_rera_status", {}),
        [
            ("RERA number", "rera_number"),
            ("Compliance", "compliance_status"),
            ("Pending cases", "pending_cases"),
        ],
    )
    infra = scorecard.get("infrastructure_development", {})
    render_analysis_section(
        "Infrastructure",
        "Connectivity, Water, Roads, and Nearby Projects",
        infra,
        [],
        extra_items=infra.get("key_projects", []),
    )
    community = scorecard.get("community_sentiment", {})
    render_analysis_section(
        "Community",
        "Resident and Buyer Sentiment",
        community,
        [],
        extra_items=(
            coerce_list(community.get("common_praises", []))
            + coerce_list(community.get("common_complaints", []))
        ),
    )
    reviews = scorecard.get("google_reviews", {})
    render_analysis_section(
        "Reviews",
        "Google Review Signal",
        reviews,
        [
            ("Average rating", "average_rating"),
            ("Total reviews", "total_reviews"),
            ("Rating trend", "rating_trend"),
        ],
        extra_items=reviews.get("highlights", []),
    )

    render_evidence_ledger(intelligence)
    render_location(scorecard, property_name)
    render_raw_expanders(intelligence)


def render_results(property_name: str, scorecard: dict[str, Any] | None, intelligence: dict[str, Any]) -> None:
    if scorecard:
        render_scorecard(property_name, scorecard, intelligence)
    else:
        render_raw_only(intelligence)


def run_investigation(property_name: str, has_gemini: bool) -> None:
    """Execute the full pipeline: Anakin gathers data, Gemini formats it."""
    status_events: list[str] = []

    with st.status("Running due-diligence investigation...", expanded=True) as status:
        from anakin_engine import AnakinClient

        progress = st.progress(0)
        latest_status = st.empty()

        def record_status(message: str) -> None:
            status_events.append(message)
            progress.progress(progress_from_message(message, len(status_events) if len(status_events) < 8 else 80))
            latest_status.markdown(f"**Current task:** {esc(message)}")

        try:
            client = AnakinClient()
            intelligence = client.run_full_pipeline(
                property_name,
                status_callback=record_status,
            )
        except Exception as exc:
            st.error(f"Anakin engine error: {exc}")
            status.update(label="Investigation failed.", state="error", expanded=True)
            return

        annotate_collection_summary(intelligence)
        evidence_count = intelligence["collection_summary"]["usable_evidence_items"]
        scorecard = None
        if evidence_count == 0:
            record_status("No usable source evidence returned by Anakin.")
        elif has_gemini:
            record_status("Formatting evidence into scorecard...")
            from rag_logic import format_scorecard

            try:
                scorecard = format_scorecard(intelligence)
            except RuntimeError as exc:
                st.warning(f"Gemini formatting unavailable: {exc}")
                st.write("Showing Anakin evidence and raw intelligence instead.")

        progress.progress(100)
        latest_status.markdown("**Current task:** Report ready.")
        with st.expander("Pipeline event log", expanded=False):
            for event in status_events:
                st.caption(event)
        status.update(label="Investigation complete.", state="complete", expanded=False)

    store_report(property_name, scorecard, intelligence)
    st.rerun()


def main() -> None:
    render_app_header()
    stored_report = session_report()
    stored_property_name = (stored_report or {}).get("property_name") or "JRC Wildwoods, Sarjapur road"
    cached_reports = list_cached_reports()
    cached_lookup = {report["label"]: report["path"] for report in cached_reports}
    selected_cached_label = None
    load_cached = False
    load_sample = False

    with st.sidebar:
        st.markdown("### Investigation")
        property_name_input = st.text_input(
            "Property or Builder Name",
            value=str(stored_property_name),
            placeholder="e.g., JRC Wildwoods Sarjapur",
            help="Enter a Bengaluru project, property, or builder name.",
        )
        col_run, col_clear = st.columns(2)
        with col_run:
            investigate = st.button("Run", type="primary", width="stretch")
        with col_clear:
            clear_report = st.button("Clear", type="secondary", width="stretch")
        st.divider()
        st.markdown("### Report Library")
        if cached_reports:
            selected_cached_label = st.selectbox("Saved Reports", list(cached_lookup.keys()))
            load_cached = st.button("Load Saved Report", width="stretch")
        else:
            st.caption("No saved local reports yet.")
        load_sample = st.button("Load Sample Report", width="stretch")
        st.divider()
        render_sidebar_downloads(stored_report)
        st.divider()
        st.markdown("### Source Routing")
        st.markdown(
            """
            <div class="route-list">
                <div class="route-item">
                    <div class="route-label">Legal Registry</div>
                    <div class="route-detail">K-RERA official project records and compliance status.</div>
                </div>
                <div class="route-item">
                    <div class="route-label">Market Pricing</div>
                    <div class="route-detail">Housing.com and NoBroker pricing, resale, rent, and amenities.</div>
                </div>
                <div class="route-item">
                    <div class="route-label">Community Signal</div>
                    <div class="route-detail">Reddit discussion threads for buyer and resident experience.</div>
                </div>
                <div class="route-item">
                    <div class="route-label">Review Signal</div>
                    <div class="route-detail">Google-indexed rating and review snippets.</div>
                </div>
                <div class="route-item">
                    <div class="route-label">Infrastructure Context</div>
                    <div class="route-detail">Road, metro, water, and local development sources.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    anakin_key = os.getenv("ANAKIN_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not anakin_key:
        st.warning("Missing ANAKIN_API_KEY. Add it to your .env file to run investigations.")
    if not gemini_key:
        st.info("GEMINI_API_KEY is not set. The app will show raw Anakin evidence without formatted scorecards.")

    if clear_report:
        st.session_state.pop("last_report", None)
        st.rerun()

    if load_sample:
        report = sample_report()
        st.session_state["last_report"] = report
        st.rerun()

    if load_cached and selected_cached_label:
        try:
            report = load_cached_report(cached_lookup[selected_cached_label])
        except (OSError, ValueError):
            st.error("Could not load the selected cached report.")
            return
        st.session_state["last_report"] = report
        st.rerun()

    if investigate:
        property_name = property_name_input or ""
        clean_name = property_name.strip()
        if not clean_name:
            st.warning("Enter a property or builder name first.")
            return
        if not anakin_key:
            st.error("Cannot proceed without ANAKIN_API_KEY.")
            return
        run_investigation(clean_name, has_gemini=bool(gemini_key))
    elif stored_report:
        render_results(
            stored_report.get("property_name", "Property"),
            stored_report.get("scorecard"),
            stored_report.get("intelligence", {}),
        )
    else:
        render_empty_state()


if __name__ == "__main__":
    main()
