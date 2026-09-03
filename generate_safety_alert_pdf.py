"""
generate_safety_alert_pdf.py
----------------------------
Generates the 1-page professional Safety Alert PDF: Week7_Safety_Alert_YvonneWochuna.pdf
Based on findings from the HSE Safety Dashboard (Depot B Slip/Trip incidents).

Requirements:
    pip install reportlab
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_FILENAME = "Week7_Safety_Alert_YvonneWochuna.pdf"


def build_pdf(filename: str = OUTPUT_FILENAME):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []

    # Color Palette
    PRIMARY_RED = HexColor("#b91c1c")   # Urgent banner red
    DARK_TEXT = HexColor("#1e293b")     # Slate 800
    MUTED_TEXT = HexColor("#64748b")    # Slate 500
    LIGHT_BG = HexColor("#fef2f2")      # Subtle red highlight background
    ACCENT_LINE = HexColor("#e2e8f0")   # Border grey

    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    banner_badge_style = ParagraphStyle(
        "BannerBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=HexColor("#ffffff"),
    )

    banner_title_style = ParagraphStyle(
        "BannerTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=HexColor("#ffffff"),
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=MUTED_TEXT,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=PRIMARY_RED,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT,
    )

    bullet_style = ParagraphStyle(
        "BulletPoint",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=5,
    )

    contact_style = ParagraphStyle(
        "ContactStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT,
    )

    footer_style = ParagraphStyle(
        "FooterNote",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=MUTED_TEXT,
    )

    # 1. Header Banner Box
    header_content = [
        [Paragraph("🚨 <b>SAFETY ALERT &bull; IMMEDIATE ACTION REQUIRED</b>", banner_badge_style)],
        [Spacer(1, 4)],
        [Paragraph("Slips Are Sending People to First Aid at Depot B", banner_title_style)],
    ]
    header_table = Table(header_content, colWidths=[540])
    header_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_RED),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 2. Metadata Strip
    meta_p = Paragraph(
        "<b>To:</b> All Depot B Personnel & Shift Supervisors &nbsp;|&nbsp; "
        "<b>Date:</b> Week 7 Operations &nbsp;|&nbsp; "
        "<b>From:</b> Yvonne Wochuna, HSE Department",
        meta_style,
    )
    story.append(meta_p)
    story.append(Spacer(1, 10))

    # 3. Context & What's Happening
    story.append(Paragraph("What's Happening", heading_style))
    story.append(
        Paragraph(
            "Recent review of the HSE Safety Dashboard reveals that <b>Depot B has recorded 33 slip and trip incidents</b> "
            "— more than any other facility in our network and nearly double the next highest site. "
            "Alarmingly, <b>82% of these incidents occurred during the Night Shift</b>, concentrated around the transfer walkway. "
            "Ten of these occurrences were classified as high-potential serious injury events (Potential SIFs). "
            "Nobody has suffered a life-altering disability yet, and our goal is to keep it that way.",
            body_style,
        )
    )
    story.append(Spacer(1, 9))

    # 4. Why This Matters To You (Empathetic Tone)
    story.append(Paragraph("Why This Matters to You", heading_style))
    story.append(
        Paragraph(
            "If you work night operations at Depot B, you walk through this corridor every single shift under varying lighting "
            "and ambient moisture conditions. <b>This is not about blame or policing how you walk</b> — it is about identifying "
            "an environmental hazard that is catching team members off guard. We would rather listen, fix the physical root causes, "
            "and eliminate the risk today than conduct a serious injury investigation tomorrow.",
            body_style,
        )
    )
    story.append(Spacer(1, 9))

    # 5. Specific Action Steps
    story.append(Paragraph("What We Need You to Do — Starting Today", heading_style))
    bullets = [
        "&bull; <b>Slow down through the transfer walkway</b>, particularly during the first and last hours of the shift when fatigue peaks.",
        "&bull; <b>Wear your company-issued slip-resistant footwear</b> on every shift — no personal trainers or worn-out treads.",
        "&bull; <b>Report wet, oily, or poorly lit areas immediately</b> to your supervisor so facilities can deploy absorbent mats and lighting crews.",
        "&bull; <b>Keep three points of contact on stairs and handrails</b> near the walkway ramps.",
        "&bull; <b>Speak up in your pre-shift huddle:</b> If you had a near-slip or spotted moisture pooling, raise it immediately without fear of reprimand.",
    ]
    for b in bullets:
        story.append(Paragraph(b, bullet_style))
    story.append(Spacer(1, 9))

    # 6. Contact Information Box
    story.append(Paragraph("Questions, Feedback, or Hazards to Report?", heading_style))
    contact_box = [
        [
            Paragraph(
                "Your safety is our top priority. If you encounter any hazard or have questions, contact HSE immediately:<br/>"
                "<b>Yvonne Wochuna</b>, HSE Specialist &bull; <b>Email:</b> wochunayvonne@gmail.com &bull; <b>Depot B Safety Desk:</b> Ext. 4402",
                contact_style,
            )
        ]
    ]
    contact_table = Table(contact_box, colWidths=[540])
    contact_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, PRIMARY_RED),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(contact_table)
    story.append(Spacer(1, 10))

    # 7. Data Citation Footer
    story.append(
        Paragraph(
            "Source: Week 7 HSE Safety Dashboard (app_safety_dashboard.py), safety_incidents.csv (Depot B Night Shift analysis).",
            footer_style,
        )
    )

    doc.build(story)
    print(f"Successfully created {filename} (strictly 1 page).")


if __name__ == "__main__":
    build_pdf()

