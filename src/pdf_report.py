"""Turn a finished results JSON file into a detailed PDF. Does not screen resumes."""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_CATEGORIES = (
    ("ai_project_depth", "AI / agentic / RAG", "40"),
    ("python_backend", "Python / backend", "30"),
    ("cloud_fullstack", "Cloud / full stack", "15"),
    ("github", "GitHub", "10"),
    ("engineering_depth", "Engineering depth", "5"),
)


def load_report(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _esc(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="Section", parent=base["Heading1"], spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1f2933")))
    base.add(ParagraphStyle(name="Person", parent=base["Heading2"], spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#243b53")))
    base.add(ParagraphStyle(name="Small", parent=base["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#334e68")))
    base.add(ParagraphStyle(name="Cell", parent=base["BodyText"], fontSize=8.5, leading=11))
    base.add(ParagraphStyle(name="CellBold", parent=base["BodyText"], fontSize=8.5, leading=11, fontName="Helvetica-Bold"))
    return base


def _p(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_esc(text), style)


def _table(rows: list[list[Paragraph]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9aa5b1")),
    ]))
    return table


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#627d98"))
    canvas.drawString(0.7 * inch, letter[1] - 0.45 * inch, "AI Resume Screening  |  Detailed report")
    canvas.drawRightString(letter[0] - 0.7 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _batch_section(report: dict, styles: dict) -> list:
    summary = report.get("batch_summary") or {}
    cell = styles["Cell"]
    head = styles["CellBold"]
    labels = ("total", "parsed", "eligible", "rejected", "failed")
    rows = [[_p(label, head) for label in labels]]
    rows.append([_p(summary.get(label, ""), cell) for label in labels])
    story = [
        Paragraph("Batch", styles["Section"]),
        _table(rows, [1.3 * inch] * 5),
        Spacer(1, 8),
    ]
    witnesses = (report.get("reasoning") or {}).get("witnesses") or {}
    if witnesses.get("llm"):
        story.append(_p(f"Model: {witnesses['llm']}", styles["Small"]))
    github = witnesses.get("github") or {}
    if github:
        story.append(_p(
            f"GitHub: checked {github.get('checked', 0)}, scored {github.get('scored', 0)}, failed {github.get('failed', 0)}.",
            styles["Small"],
        ))
    note = ((report.get("reasoning") or {}).get("ranking") or {}).get("note")
    if note:
        story.append(Spacer(1, 4))
        story.append(_p(note, styles["BodyText"]))
    return story


def _rejected_section(report: dict, styles: dict) -> list:
    rejected = ((report.get("reasoning") or {}).get("rejected") or {})
    groups = (
        ("Neither Python nor an AI project", "neither_python_nor_ai", None),
        ("Python, no AI project", "python_without_ai_project", "noted_skills"),
        ("AI project, no Python", "ai_without_python", "skills_kept"),
    )
    cell = styles["Cell"]
    head = styles["CellBold"]
    story = [Paragraph("Rejected", styles["Section"])]
    for title, key, extra_key in groups:
        people = rejected.get(key) or []
        story.append(_p(title, styles["Person"]))
        header = [_p("File", head), _p("Name", head), _p("Notes", head)]
        body = [header]
        if not people:
            body.append([_p("-", cell), _p("None", cell), _p("", cell)])
        for person in people:
            extra = ", ".join(person.get(extra_key) or []) if extra_key else ""
            body.append([
                _p(person.get("filename"), cell),
                _p(person.get("candidate_name") or "-", cell),
                _p(extra, cell),
            ])
        story.append(_table(body, [1.7 * inch, 2.2 * inch, 3.1 * inch]))
        story.append(Spacer(1, 8))
    return story


def _ranking_section(report: dict, styles: dict) -> list:
    cell = styles["Cell"]
    head = styles["CellBold"]
    rows = [[_p(label, head) for label in ("Rank", "Score", "Name", "File")]]
    for row in report.get("candidates") or []:
        if not row.get("eligible"):
            continue
        rows.append([
            _p(row.get("rank"), cell),
            _p(row.get("total_score"), cell),
            _p(row.get("candidate_name") or "-", cell),
            _p(row.get("filename"), cell),
        ])
    return [
        Paragraph("Ranking", styles["Section"]),
        _table(rows, [0.7 * inch, 0.7 * inch, 3.1 * inch, 2.5 * inch]),
    ]


def _score_table(row: dict, styles: dict) -> Table:
    cell = styles["Cell"]
    head = styles["CellBold"]
    breakdown = row.get("score_breakdown") or {}
    evidence = row.get("score_evidence") or {}
    rows = [[_p("Category", head), _p("Points", head), _p("Cap", head), _p("Evidence", head)]]
    for key, label, cap in _CATEGORIES:
        rows.append([
            _p(label, cell),
            _p(breakdown.get(key, ""), cell),
            _p(cap, cell),
            _p(evidence.get(key) or "", cell),
        ])
    rows.append([
        _p("Total", head),
        _p(row.get("total_score"), head),
        _p("100", head),
        _p("", cell),
    ])
    return _table(rows, [1.5 * inch, 0.7 * inch, 0.5 * inch, 4.3 * inch])


def _person_section(row: dict, styles: dict) -> list:
    name = row.get("candidate_name") or "Name not found"
    story = [
        Paragraph(f"{row.get('rank')}. {_esc(name)}", styles["Person"]),
        _p(f"{row.get('filename')}    {row.get('email') or ''}", styles["Small"]),
        Spacer(1, 4),
        _score_table(row, styles),
        Spacer(1, 6),
    ]
    skills = row.get("matched_skills") or []
    if skills:
        story.append(_p("Skills: " + ", ".join(skills), styles["BodyText"]))
    if row.get("project_summary"):
        story.append(Spacer(1, 3))
        story.append(_p("Summary: " + row["project_summary"], styles["BodyText"]))
    if row.get("strengths"):
        story.append(_p("Strengths: " + "; ".join(row["strengths"]), styles["Small"]))
    if row.get("concerns"):
        story.append(_p("Concerns: " + "; ".join(row["concerns"]), styles["Small"]))
    story.append(_p(
        f"Model: {row.get('llm_status') or '-'}  {row.get('llm_note') or ''}",
        styles["Small"],
    ))
    story.append(_p(
        f"GitHub: {row.get('github_status') or '-'}  {row.get('github_summary') or ''}",
        styles["Small"],
    ))
    return story


def build_story(report: dict) -> list:
    styles = _styles()
    story = [
        Paragraph("Detailed screening report", styles["Title"]),
        _p("Built from the saved results JSON. This file does not rescore the resumes.", styles["Small"]),
        Spacer(1, 8),
    ]
    story.extend(_batch_section(report, styles))
    story.extend(_rejected_section(report, styles))
    story.extend(_ranking_section(report, styles))
    story.append(PageBreak())
    story.append(Paragraph("Eligible resumes", styles["Section"]))
    eligible = [row for row in report.get("candidates") or [] if row.get("eligible")]
    for row in eligible:
        story.extend(_person_section(row, styles))
    if not eligible:
        story.append(_p("No eligible resumes.", styles["BodyText"]))
    return story


def write_detailed_pdf(report: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.65 * inch,
        title="Detailed screening report",
    )
    document.build(build_story(report), onFirstPage=_header_footer, onLaterPages=_header_footer)
