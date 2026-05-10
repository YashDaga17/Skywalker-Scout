"""
app.py

Skywalker Scout -- Autonomous Real Estate Due Diligence Engine.
Streamlit UI with dark theme, glassmorphism cards, and SVG risk gauge.

Primary data engine: Anakin (Search API, Agentic Search, URL Scraper).
Gemini is used only to format Anakin's output into a scorecard.
"""

import os
import json
import math
import math
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
from streamlit_lottie import st_lottie
from streamlit_extras.metric_cards import style_metric_cards
import folium
from streamlit_folium import st_folium
# from pdf_export import generate_pdf_report
from dotenv import load_dotenv

load_dotenv()

# -- Page Config ---------------------------------------------------------------
st.set_page_config(
    page_title="Skywalker Scout | Real Estate Intelligence",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -- Custom CSS ----------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');

.stApp {
    background: linear-gradient(165deg, #0a0a1a 0%, #0e1525 40%, #111827 100%);
    font-family: 'Inter', sans-serif;
}
.block-container { max-width: 1200px; padding-top: 2rem; }

.scout-header {
    text-align: center;
    padding: 2rem 0 1rem;
}
.scout-title {
    font-family: 'Outfit', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00d2ff, #7b2ff7, #ff6b6b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
    letter-spacing: -1px;
}
.scout-subtitle {
    color: #8b95a5;
    font-size: 1.1rem;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.glass-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.8rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.glass-card:hover {
    border-color: rgba(0,210,255,0.2);
    box-shadow: 0 8px 32px rgba(0,210,255,0.08);
}

.risk-score-value {
    font-family: 'Outfit', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    margin-top: -1rem;
}
.risk-label {
    color: #8b95a5;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.score-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
}
.score-high { background: rgba(16,185,129,0.15); color: #34d399; }
.score-mid { background: rgba(251,191,36,0.15); color: #fbbf24; }
.score-low { background: rgba(239,68,68,0.15); color: #ef4444; }

.flag-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    color: #c9d1d9;
    font-size: 0.92rem;
}
.flag-item:last-child { border-bottom: none; }

.source-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    transition: all 0.2s ease;
}
.source-card:hover {
    background: rgba(255,255,255,0.06);
    border-color: rgba(0,210,255,0.15);
}
.source-title {
    color: #58a6ff;
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 4px;
}
.source-snippet {
    color: #8b949e;
    font-size: 0.82rem;
    line-height: 1.4;
}
.source-url {
    color: #484f58;
    font-size: 0.72rem;
    margin-top: 4px;
    word-break: break-all;
}

.summary-card {
    background: linear-gradient(135deg, rgba(0,210,255,0.08), rgba(123,47,247,0.08));
    border: 1px solid rgba(0,210,255,0.15);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    color: #e6edf3;
    font-size: 1.05rem;
    line-height: 1.7;
    margin: 1rem 0;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #8b95a5;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,210,255,0.1) !important;
    color: #00d2ff !important;
}

@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 20px rgba(0,210,255,0.1); }
    50% { box-shadow: 0 0 40px rgba(0,210,255,0.2); }
}
.pulse-glow { animation: pulse-glow 3s ease-in-out infinite; }

.stTextInput > div > div > input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #e6edf3 !important;
    font-size: 1.1rem !important;
    padding: 0.8rem 1.2rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0,210,255,0.4) !important;
    box-shadow: 0 0 20px rgba(0,210,255,0.1) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #00d2ff, #7b2ff7) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.7rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0,210,255,0.3) !important;
}

[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1rem;
}
</style>
""", unsafe_allow_html=True)


# -- Helper Functions ----------------------------------------------------------

def get_risk_color(score):
    if score <= 25:
        return "#10b981"
    elif score <= 50:
        return "#34d399"
    elif score <= 65:
        return "#fbbf24"
    elif score <= 80:
        return "#f59e0b"
    else:
        return "#ef4444"


def get_risk_label(score):
    if score <= 25:
        return "LOW RISK"
    elif score <= 50:
        return "MODERATE"
    elif score <= 65:
        return "ELEVATED"
    elif score <= 80:
        return "HIGH RISK"
    else:
        return "CRITICAL"


def get_score_badge(score):
    if score >= 7:
        cls = "score-high"
    elif score >= 5:
        cls = "score-mid"
    else:
        cls = "score-low"
    return f'<span class="score-badge {cls}">{score}/10</span>'


def render_section(section, label):
    score = section.get("score", "N/A")
    summary = section.get("summary", "No data available.")
    key_points = section.get("key_points", [])

    badge = get_score_badge(score) if isinstance(score, int) else f"<span>{score}</span>"
    st.markdown(f"""
    <div class="glass-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
            <span style="font-size:1.1rem;font-weight:600;color:#e6edf3;">{label}</span>
            {badge}
        </div>
        <p style="color:#c9d1d9;line-height:1.6;margin-bottom:1rem;">{summary}</p>
    </div>
    """, unsafe_allow_html=True)

    if key_points:
        for pt in key_points:
            st.markdown(f"<div class='flag-item'>-- {pt}</div>", unsafe_allow_html=True)


def render_flags(flags, flag_type="red"):
    marker = "[!]" if flag_type == "red" else "[+]"
    for flag in flags:
        st.markdown(f"<div class='flag-item'>{marker} {flag}</div>", unsafe_allow_html=True)


def render_sources(results):
    for r in results:
        title = r.get("title", "Untitled")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        date = r.get("date", "")
        date_str = f" | {date}" if date else ""
        st.markdown(f"""
        <div class="source-card">
            <div class="source-title">{title}</div>
            <div class="source-snippet">{snippet}</div>
            <div class="source-url">{url}{date_str}</div>
        </div>
        """, unsafe_allow_html=True)


# -- Helpers -------------------------------------------------------------------

@st.cache_data
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# -- Main App -----------------------------------------------------------------

def main():
    st.markdown("""
    <div class="scout-header">
        <div class="scout-title">Skywalker Scout</div>
        <div class="scout-subtitle">Autonomous Real Estate Due Diligence Engine</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Use sidebar for inputs to create a cleaner main dashboard
    with st.sidebar:
        st.markdown("<h2 style='color:#00d2ff;'>Configuration</h2>", unsafe_allow_html=True)
        property_name = st.text_input(
            "Property or Builder Name",
            placeholder="e.g., Prestige Lakeside...",
            help="Enter the name of the project and location"
        )
        investigate = st.button("Investigate", width="stretch")
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; color:#8b95a5;'>Using Anakin API for intelligent agentic search, web scraping, and government site crawling.</div>", unsafe_allow_html=True)

    # Validate API keys
    anakin_key = os.getenv("ANAKIN_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not anakin_key:
        st.markdown("""
        <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
             border-radius:10px;padding:0.8rem 1.2rem;margin:0.5rem 0;color:#ef4444;font-size:0.85rem;">
            <strong>Missing ANAKIN_API_KEY</strong> -- This is required. Anakin is the primary data engine.
            Add it to your <code>.env</code> file.
        </div>
        """, unsafe_allow_html=True)

    if not gemini_key:
        st.markdown("""
        <div style="background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);
             border-radius:10px;padding:0.8rem 1.2rem;margin:0.5rem 0;color:#fbbf24;font-size:0.85rem;">
            <strong>GEMINI_API_KEY not set</strong> -- Gemini is used to format Anakin's results
            into a structured scorecard. Without it, raw Anakin data will be shown.
        </div>
        """, unsafe_allow_html=True)

    if investigate and property_name.strip():
        if not anakin_key:
            st.error("Cannot proceed without ANAKIN_API_KEY.")
            return
        run_investigation(property_name.strip(), has_gemini=bool(gemini_key))


def run_investigation(property_name, has_gemini):
    """Execute the full pipeline: Anakin gathers data, Gemini formats it."""

    with st.status("Skywalker Scout is investigating...", expanded=True) as status:
        
        # Lottie Animation
        lottie_search = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_tijmpky4.json")
        if lottie_search:
            st_lottie(lottie_search, height=150, key="search_anim")

        # Step 1: Anakin gathers ALL data
        from anakin_engine import AnakinClient

        try:
            client = AnakinClient()
            intelligence = client.run_full_pipeline(
                property_name,
                status_callback=lambda msg: st.write(msg),
            )
        except Exception as exc:
            st.error(f"Anakin engine error: {exc}")
            status.update(label="Investigation failed.", state="error")
            return

        # Step 2: Format with Gemini (optional -- Anakin data is primary)
        scorecard = None
        if has_gemini:
            st.write("Formatting results with Gemini...")
            from rag_logic import format_scorecard
            try:
                scorecard = format_scorecard(intelligence)
            except RuntimeError as exc:
                st.write(f"Gemini formatting unavailable: {exc}")
                st.write("Showing raw Anakin data instead.")

        st.write("Report generated.")
        status.update(label="Investigation complete.", state="complete")

    render_results(property_name, scorecard, intelligence)


def render_results(property_name, scorecard, intelligence):
    """Render the due diligence report."""

    st.markdown(f"""
    <div style="text-align:center;margin:1.5rem 0 0.5rem;">
        <span style="font-family:'Outfit';font-size:1.8rem;font-weight:700;color:#e6edf3;">
            Due Diligence Report
        </span><br/>
        <span style="color:#8b95a5;font-size:1rem;">{property_name} -- Bengaluru</span>
    </div>
    """, unsafe_allow_html=True)

    if scorecard:
        _render_scorecard(property_name, scorecard, intelligence)
    else:
        _render_raw_only(intelligence)


def _render_scorecard(property_name, scorecard, intelligence):
    """Render Gemini-formatted scorecard view."""

    # Risk Meter + Executive Summary
    col_risk, col_summary = st.columns([1, 2])

    with col_risk:
        risk_score = scorecard.get("risk_score", 50)
        
        # Plotly Gauge Chart for Risk Score
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk_score,
            title={'text': "Risk Score", 'font': {'color': '#8b95a5', 'size': 20}},
            number={'font': {'color': get_risk_color(risk_score), 'size': 50}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "rgba(255,255,255,0.5)"},
                'bar': {'color': get_risk_color(risk_score)},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "rgba(255,255,255,0.1)",
                'steps': [
                    {'range': [0, 25], 'color': "rgba(16,185,129,0.1)"},
                    {'range': [25, 50], 'color': "rgba(52,211,153,0.1)"},
                    {'range': [50, 65], 'color': "rgba(251,191,36,0.1)"},
                    {'range': [65, 80], 'color': "rgba(245,158,11,0.1)"},
                    {'range': [80, 100], 'color': "rgba(239,68,68,0.1)"}],
            }
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=250,
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, width="stretch")

    with col_summary:
        exec_summary = scorecard.get("executive_summary", "Analysis pending.")
        st.markdown(f'<div class="summary-card">{exec_summary}</div>',
                    unsafe_allow_html=True)

        fin = scorecard.get("financial_viability", {})
        legal = scorecard.get("legal_rera_status", {})
        grev = scorecard.get("google_reviews", {})

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Price/sqft", fin.get("price_per_sqft", "N/A"),
                       fin.get("price_trend", ""))
        with m2:
            st.metric("RERA Status", legal.get("compliance_status", "Unknown"),
                       f"{legal.get('pending_cases', 0)} cases")
        with m3:
            st.metric("Google Rating", grev.get("average_rating", "N/A"),
                       grev.get("rating_trend", ""))
                       
        style_metric_cards(background_color="#1e2329", border_left_color="#00d2ff")

    st.divider()

    # -- Location & PDF Export ------------------------------------------------
    c_map, c_export = st.columns([3, 1])
    with c_map:
        coords = scorecard.get("location_coordinates", {})
        try:
            lat = float(coords.get("latitude")) if coords.get("latitude") is not None else None
            lon = float(coords.get("longitude")) if coords.get("longitude") is not None else None
        except (ValueError, TypeError):
            lat, lon = None, None
            
        if lat and lon:
            st.markdown("### Location")
            try:
                m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB dark_matter")
                folium.Marker([lat, lon], popup=property_name, tooltip=property_name).add_to(m)
                st_folium(m, width=800, height=300)
            except Exception as e:
                st.error(f"Could not render map: {e}")
            
    with c_export:
        st.markdown("### Export")
        st.info("PDF Export is temporarily disabled for maintenance.")
        # pdf_bytes = generate_pdf_report(property_name, scorecard)
        # if pdf_bytes:
        #     st.download_button(
        #         label="Download PDF Report",
        #         data=pdf_bytes,
        #         file_name=f"{property_name.replace(' ', '_')}_Due_Diligence.pdf",
        #         mime="application/pdf",
        #         type="primary"
        #     )
            
    st.divider()

    # Scorecard Tabs
    tabs = st.tabs(["Financial", "Legal / RERA", "Infrastructure", "Community", "Google Reviews"])

    with tabs[0]:
        render_section(scorecard.get("financial_viability", {}), "Financial Viability")

    with tabs[1]:
        render_section(scorecard.get("legal_rera_status", {}), "Legal & RERA Status")

    with tabs[2]:
        render_section(scorecard.get("infrastructure_development", {}), "Infrastructure & Development")
        key_projects = scorecard.get("infrastructure_development", {}).get("key_projects", [])
        if key_projects:
            st.markdown("**Key Projects Nearby**")
            for proj in key_projects:
                st.markdown(f"<div class='flag-item'>[+] {proj}</div>", unsafe_allow_html=True)

    with tabs[3]:
        section = scorecard.get("community_sentiment", {})
        render_section(section, "Community Sentiment")
        praises = section.get("common_praises", [])
        complaints = section.get("common_complaints", [])
        if praises or complaints:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Praises**")
                for p in praises:
                    st.markdown(f"<div class='flag-item'>[+] {p}</div>",
                                unsafe_allow_html=True)
            with c2:
                st.markdown("**Complaints**")
                for c in complaints:
                    st.markdown(f"<div class='flag-item'>[!] {c}</div>",
                                unsafe_allow_html=True)

    with tabs[4]:
        grev = scorecard.get("google_reviews", {})
        render_section(grev, "Google Maps Reviews")
        highlights = grev.get("highlights", [])
        if highlights:
            for h in highlights:
                st.markdown(f"<div class='flag-item'>-- {h}</div>",
                            unsafe_allow_html=True)
        total = grev.get("total_reviews")
        trend = grev.get("rating_trend", "unknown")
        if total:
            st.markdown(
                f"<div style='color:#8b95a5;font-size:0.85rem;margin-top:0.5rem;'>"
                f"Based on {total} Google Maps reviews | Trend: {trend}</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # Red & Green Flags
    col_red, col_green = st.columns(2)

    with col_red:
        st.markdown("""
        <div class="glass-card" style="border-color:rgba(239,68,68,0.2);">
            <div style="font-size:1.1rem;font-weight:600;color:#ef4444;margin-bottom:0.8rem;">
                Red Flags
            </div>
        """, unsafe_allow_html=True)
        red_flags = scorecard.get("red_flags", [])
        if red_flags:
            render_flags(red_flags, "red")
        else:
            st.markdown("<div style='color:#8b95a5;'>No red flags identified.</div>",
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_green:
        st.markdown("""
        <div class="glass-card" style="border-color:rgba(16,185,129,0.2);">
            <div style="font-size:1.1rem;font-weight:600;color:#10b981;margin-bottom:0.8rem;">
                Green Flags
            </div>
        """, unsafe_allow_html=True)
        green_flags = scorecard.get("green_flags", [])
        if green_flags:
            render_flags(green_flags, "green")
        else:
            st.markdown("<div style='color:#8b95a5;'>No green flags identified.</div>",
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Raw data expanders
    _render_raw_expanders(intelligence)


def _render_raw_only(intelligence):
    """Render raw Anakin data when Gemini is unavailable."""
    st.markdown("""
    <div class="glass-card">
        <div style="font-size:1.1rem;font-weight:600;color:#00d2ff;margin-bottom:0.8rem;">
            Raw Anakin Intelligence
        </div>
        <p style="color:#8b95a5;">
            Gemini formatting is unavailable. Showing raw Anakin data below.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Show agentic research summary if available
    ar = intelligence.get("agentic_research", {})
    if ar.get("success") and ar.get("generated_json"):
        gj = ar["generated_json"]
        summary = gj.get("summary", "") if isinstance(gj, dict) else str(gj)
        if summary:
            st.markdown(f'<div class="summary-card">{summary}</div>',
                        unsafe_allow_html=True)

    _render_raw_expanders(intelligence)


def _render_raw_expanders(intelligence):
    """Render expandable raw Anakin data sections."""

    with st.expander("Anakin Web Search Results"):
        ws = intelligence.get("web_search", {})
        if ws.get("results"):
            render_sources(ws["results"])
        else:
            st.info("No web search results available.")

    with st.expander("Anakin Google Reviews Search"):
        gr = intelligence.get("google_reviews", {})
        if gr.get("results"):
            render_sources(gr["results"])
        else:
            st.info("No Google review data available.")

    with st.expander("Anakin URL Scraper -- Full Page Content"):
        sp = intelligence.get("scraped_pages", {})
        if sp.get("success") and sp.get("results"):
            for page in sp["results"]:
                url = page.get("url", "Unknown")
                status = page.get("status", "unknown")
                markdown = page.get("markdown", "")
                st.markdown(f"**{url}** ({status})")
                if markdown:
                    # Show first 1000 chars of each page
                    preview = markdown[:1000]
                    if len(markdown) > 1000:
                        preview += f"\n\n... ({len(markdown)} total characters)"
                    st.text(preview)
                st.divider()
        else:
            st.info("No scraped page data available.")


    with st.expander("Anakin Agentic Research"):
        ar = intelligence.get("agentic_research", {})
        if ar.get("success") and ar.get("generated_json"):
            gj = ar["generated_json"]
            if isinstance(gj, dict):
                summary = gj.get("summary", "")
                if summary:
                    st.markdown(summary)
                structured = gj.get("structured_data")
                if structured:
                    st.subheader("Structured Data")
                    st.json(structured)
            else:
                st.markdown(str(gj))
        else:
            error = ar.get("error", "No data available.") if ar else "Not executed."
            st.info(f"Agentic research: {error}")

    errors = intelligence.get("errors", [])
    if errors:
        with st.expander("Data Collection Warnings"):
            for e in errors:
                st.write(f"WARNING: {e}")

    # Raw scorecard JSON if available
    with st.expander("Raw JSON"):
        st.json({
            k: v for k, v in intelligence.items()
            if k not in ("_raw_gemini_response",)
        })


if __name__ == "__main__":
    main()
