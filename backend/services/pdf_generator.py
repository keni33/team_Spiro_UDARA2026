"""PDF Report Generator — creates downloadable inspection reports using ReportLab."""
import json
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT


RISK_COLOURS = {
    "safe":      colors.HexColor("#16a34a"),
    "monitor":   colors.HexColor("#d97706"),
    "high_risk": colors.HexColor("#dc2626"),
    "critical":  colors.HexColor("#7f1d1d"),
}


def generate_pdf(submission, output_path: str):
    """Generate a PDF inspection report for a completed submission."""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm
    )
    styles  = getSampleStyleSheet()
    story   = []
    project = submission.project

    # Header
    header_style = ParagraphStyle("header", parent=styles["Title"],
        fontSize=20, spaceAfter=4, textColor=colors.HexColor("#1e3a5f"))
    story.append(Paragraph("StructGuard AI", header_style))
    story.append(Paragraph("Construction Safety Inspection Report", styles["Normal"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 0.4*cm))

    # Risk badge
    risk = submission.risk_level or "monitor"
    risk_col = RISK_COLOURS.get(risk, colors.grey)
    risk_label = risk.replace("_", " ").upper()
    risk_data = [[f"RISK LEVEL: {risk_label}   |   SCORE: {submission.risk_score:.0f}/100"]]
    risk_table = Table(risk_data, colWidths=["100%"])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), risk_col),
        ("TEXTCOLOR",  (0,0), (-1,-1), colors.white),
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 13),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[risk_col]),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 0.5*cm))

    # Project details table
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12,
                         textColor=colors.HexColor("#1e3a5f"), spaceAfter=6)
    story.append(Paragraph("Project Details", h2))
    details = [
        ["Project Name", project.name],
        ["StructGuard ID", project.sgid],
        ["Address", project.address],
        ["State / LGA", f"{project.state} / {project.lga or 'N/A'}"],
        ["Building Type", (project.building_type or "").title()],
        ["Permit Reference", project.permit_ref or "Not provided"],
        ["Submission Date", submission.submitted_at.strftime("%d %B %Y, %H:%M") if submission.submitted_at else "N/A"],
        ["Submitted By", submission.submitted_by.name if submission.submitted_by else "N/A"],
    ]
    t = Table(details, colWidths=[5*cm, 12*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("BACKGROUND",   (0,0), (0,-1), colors.HexColor("#f1f5f9")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # AI Summary
    story.append(Paragraph("AI Analysis Summary", h2))
    story.append(Paragraph(submission.ai_summary or "No summary available.", styles["Normal"]))
    story.append(Spacer(1, 0.4*cm))

    # Violations
    violations = json.loads(submission.violations) if submission.violations else []
    if violations:
        story.append(Paragraph("Safety Violations Detected", h2))
        for i, v in enumerate(violations, 1):
            vp = ParagraphStyle("viol", parent=styles["Normal"],
                leftIndent=15, spaceBefore=3,
                textColor=colors.HexColor("#dc2626"))
            story.append(Paragraph(f"{i}. {v}", vp))
        story.append(Spacer(1, 0.4*cm))

    # Recommendations
    recs = json.loads(submission.recommendations) if submission.recommendations else []
    if recs:
        story.append(Paragraph("Recommendations", h2))
        for i, r in enumerate(recs, 1):
            rp = ParagraphStyle("rec", parent=styles["Normal"],
                leftIndent=15, spaceBefore=3,
                textColor=colors.HexColor("#15803d"))
            story.append(Paragraph(f"{i}. {r}", rp))
        story.append(Spacer(1, 0.4*cm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 0.2*cm))
    footer_style = ParagraphStyle("footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    story.append(Paragraph(
        f"Generated by StructGuard AI — {datetime.now(timezone.utc).strftime('%d %B %Y')} | "
        "LASBCA Compliance Platform | Team Spiro — UDARA Bootcamp 2025",
        footer_style
    ))

    doc.build(story)
