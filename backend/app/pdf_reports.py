from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_pressing_pdf(analysis: dict) -> bytes:
    """Generate a downloadable PDF from existing pressing analysis."""

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Tactical_XI Pressing Analysis",
        author="Tactical_XI",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#16324F"),
        spaceAfter=14,
    )

    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#16324F"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = styles["BodyText"]

    story = []

    metadata = analysis.get("match_metadata") or {}
    match_name = analysis.get("match", "Match analysis")
    match_id = analysis.get("match_id", "Unknown")

    story.append(Paragraph("Tactical_XI", title_style))
    story.append(
        Paragraph("Football Pressing Intelligence Report", styles["Heading2"])
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Match Information", section_style))

    match_rows = [
        ["Match", str(match_name)],
        ["Match ID", str(match_id)],
        ["Competition", str(metadata.get("competition") or "Not available")],
        ["Season", str(metadata.get("season") or "Not available")],
        ["Date", str(metadata.get("date") or "Not available")],
        [
            "Score",
            (
                f"{metadata.get('home_score')} - {metadata.get('away_score')}"
                if metadata.get("home_score") is not None
                and metadata.get("away_score") is not None
                else "Not available"
            ),
        ],
        [
            "Data source",
            str(metadata.get("data_source") or "StatsBomb Open Data"),
        ],
    ]

    match_table = Table(
        match_rows,
        colWidths=[4 * cm, 12 * cm],
    )

    match_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF0F6")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#16324F")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2DE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(match_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Analysis Summary", section_style))

    # Include scalar metrics already calculated by the analytics module.
    excluded_keys = {
        "match",
        "match_id",
        "match_metadata",
        "candidate_sequences",
    }

    metric_rows = [["Metric", "Value"]]

    for key, value in analysis.items():
        if key in excluded_keys:
            continue

        if isinstance(value, (str, int, float, bool)) or value is None:
            label = str(key).replace("_", " ").title()
            metric_rows.append([
                label,
                "Not available" if value is None else str(value),
            ])

    if len(metric_rows) == 1:
        metric_rows.append([
            "Summary",
            "No scalar analysis metrics were returned.",
        ])

    metrics_table = Table(
        metric_rows,
        colWidths=[8 * cm, 8 * cm],
        repeatRows=1,
    )

    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2DE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F5F8FB"),
        ]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(metrics_table)

    sequences = analysis.get("candidate_sequences", [])

    story.append(Paragraph("Candidate Pressing Sequences", section_style))
    story.append(Paragraph(
        f"Total candidate sequences: {len(sequences)}",
        body_style,
    ))
    story.append(Spacer(1, 6))

    if sequences:
        sequence_rows = [["#", "Sequence details"]]

        for index, sequence in enumerate(sequences, start=1):
            # Store a readable representation without assuming a schema.
            details = str(sequence)

            if len(details) > 500:
                details = details[:497] + "..."

            sequence_rows.append([
                str(index),
                Paragraph(
                    details.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                    body_style,
                ),
            ])

        sequence_table = Table(
            sequence_rows,
            colWidths=[1.2 * cm, 14.8 * cm],
            repeatRows=1,
        )

        sequence_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2DE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(sequence_table)
    else:
        story.append(Paragraph(
            "No candidate sequences were returned for this match.",
            body_style,
        ))

    story.append(Spacer(1, 18))

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph(
        f"Generated by Tactical_XI on {generated_at}.",
        styles["Italic"],
    ))

    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "Interpretation note: a pressure followed by a same-team ball "
        "recovery within five seconds is a candidate sequence, not proof "
        "that the pressure caused the recovery.",
        body_style,
    ))

    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes