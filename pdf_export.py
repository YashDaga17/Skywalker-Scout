from fpdf import FPDF
import json
import logging

logger = logging.getLogger("pdf_export")

def sanitize(text) -> str:
    if not isinstance(text, str):
        text = str(text)
    # Replace common unicode chars that Helvetica doesn't support
    text = text.replace("₹", "Rs. ").replace("—", "-").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Replace any other unsupported characters with a '?' to prevent crashing
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_report(property_name: str, scorecard: dict) -> bytes:
    """Generate a PDF report from the scorecard and return as bytes."""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font("helvetica", "B", 24)
        pdf.cell(0, 15, sanitize("Skywalker Scout: Due Diligence Report"), new_x="LMARGIN", new_y="NEXT", align="C")
        
        pdf.set_font("helvetica", "I", 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, sanitize(f"Property: {property_name}"), new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        # Risk Score & Executive Summary
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "B", 16)
        risk_score = scorecard.get("risk_score", "N/A")
        pdf.cell(0, 10, sanitize(f"Overall Risk Score: {risk_score} / 100"), new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("helvetica", "", 12)
        exec_summary = scorecard.get("executive_summary", "No summary available.")
        pdf.multi_cell(0, 8, sanitize(f"Executive Summary: {exec_summary}"))
        pdf.ln(10)
        
        # Sections
        sections = [
            ("Financial Viability", scorecard.get("financial_viability", {})),
            ("Legal & RERA Status", scorecard.get("legal_rera_status", {})),
            ("Infrastructure & Development", scorecard.get("infrastructure_development", {})),
            ("Community Sentiment", scorecard.get("community_sentiment", {})),
            ("Google Maps Reviews", scorecard.get("google_reviews", {}))
        ]
        
        for title, data in sections:
            if not data: continue
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 10, sanitize(title), new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("helvetica", "", 12)
            pdf.set_text_color(0, 0, 0)
            score = data.get("score", "N/A")
            summary = data.get("summary", "")
            
            pdf.multi_cell(0, 8, sanitize(f"Score: {score}/10"))
            pdf.multi_cell(0, 8, sanitize(f"Summary: {summary}"))
            pdf.ln(5)

        # Red Flags
        red_flags = scorecard.get("red_flags", [])
        if red_flags:
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, "Red Flags", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 12)
            pdf.set_text_color(0, 0, 0)
            for flag in red_flags:
                pdf.multi_cell(0, 8, sanitize(f"- {flag}"))
            pdf.ln(5)

        # Green Flags
        green_flags = scorecard.get("green_flags", [])
        if green_flags:
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(0, 150, 0)
            pdf.cell(0, 10, "Green Flags", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 12)
            pdf.set_text_color(0, 0, 0)
            for flag in green_flags:
                pdf.multi_cell(0, 8, sanitize(f"- {flag}"))
            pdf.ln(5)
            
        return bytes(pdf.output())
    except Exception as exc:
        logger.error(f"Failed to generate PDF: {exc}")
        return b""
