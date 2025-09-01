# backend/app/services/report_service.py
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit

PAGE_SIZE = A4
MARGIN = 50

def _new_page(c):
    c.showPage()
    c.setFont("Helvetica-Bold", 14)
    width, height = PAGE_SIZE
    y = height - MARGIN
    c.drawString(MARGIN, y, "VAPT Report")
    c.setFont("Helvetica", 10)
    return y - 24

def _wrap(c, text: str, max_width: float, font="Helvetica", size=10) -> List[str]:
    # Break text into lines that fit into max_width
    return simpleSplit(text or "", font, size, max_width)

def generate_report_pdf(
    dest_path: Path,
    project_id: int,
    tester_id: int,
    summary: str,
    findings: List[Dict[str, str]],
):
    c = canvas.Canvas(str(dest_path), pagesize=PAGE_SIZE)
    width, height = PAGE_SIZE

    # Header
    c.setFont("Helvetica-Bold", 14)
    y = height - MARGIN
    c.drawString(MARGIN, y, "VAPT Report")
    c.setFont("Helvetica", 10)
    y -= 18
    c.drawString(MARGIN, y, f"Project ID: {project_id}")
    y -= 14
    c.drawString(MARGIN, y, f"Tester ID: {tester_id}")
    y -= 14
    c.drawString(MARGIN, y, f"Generated At: {datetime.utcnow().isoformat()}Z")
    y -= 18

    # Summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, y, "Summary")
    y -= 16
    c.setFont("Helvetica", 10)
    for line in _wrap(c, summary, width - 2 * MARGIN):
        if y < MARGIN + 60:
            y = _new_page(c)
        c.drawString(MARGIN, y, line)
        y -= 14

    # Findings section
    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, y, "Findings")
    y -= 12
    c.setFont("Helvetica", 10)

    if not findings:
        if y < MARGIN + 60:
            y = _new_page(c)
        c.drawString(MARGIN, y, "No findings yet.")
    else:
        for idx, f in enumerate(findings, start=1):
            if y < MARGIN + 100:
                y = _new_page(c)

            # Title + Severity
            title = f.get("title", "Untitled")
            sev = f.get("severity", "Unknown")
            c.setFont("Helvetica-Bold", 11)
            c.drawString(MARGIN, y, f"{idx}. {title}")
            c.setFont("Helvetica", 10)
            c.drawString(width - MARGIN - 150, y, f"Severity: {sev}")
            y -= 14

            # Description (wrapped, max ~6 lines to keep report short)
            desc_lines = _wrap(c, f.get("description", ""), width - 2 * MARGIN)
            for line in desc_lines[:6]:
                if y < MARGIN + 60:
                    y = _new_page(c)
                c.drawString(MARGIN + 16, y, line)
                y -= 12
            if len(desc_lines) > 6:
                c.drawString(MARGIN + 16, y, "…")
                y -= 12

            y -= 6  # spacing between findings

    c.save()
    return dest_path
