"""Rank eligible candidates and write the batch JSON."""

import json
from pathlib import Path

from src.eligibility import AI_REASON, PYTHON_REASON

_BACKEND_SKILLS = ("FastAPI", "PostgreSQL", "Redis")
_AI_SKILLS = {
    "LangChain",
    "LangGraph",
    "LlamaIndex",
    "Google ADK",
    "RAG",
    "embeddings",
    "vector search",
    "FAISS",
    "Chroma",
    "Pinecone",
    "tool calling",
    "multi-agent",
    "agent",
    "OpenAI",
    "Gen AI",
    "LLM",
    "Hugging Face",
    "transformers",
}


def _english_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _has(row: dict, reason: str) -> bool:
    return reason in (row.get("rejection_reasons") or [])


def _person(row: dict, **extra: object) -> dict:
    item = {
        "filename": row.get("filename"),
        "candidate_name": row.get("candidate_name"),
    }
    item.update(extra)
    return item


def build_reasoning(rows: list[dict]) -> dict:
    """Group the batch into sections a person can scan."""
    rejected = [row for row in rows if row.get("status") == "parsed" and not row.get("eligible")]
    eligible = [row for row in rows if row.get("eligible")]
    failed = [row for row in rows if row.get("status") == "failed"]

    both = [row for row in rejected if _has(row, PYTHON_REASON) and _has(row, AI_REASON)]
    ai_only = [row for row in rejected if _has(row, AI_REASON) and not _has(row, PYTHON_REASON)]
    python_only = [row for row in rejected if _has(row, PYTHON_REASON) and not _has(row, AI_REASON)]

    ranking: dict = {"top_score": None, "tied_for_first": [], "note": ""}
    if eligible:
        top_score = eligible[0].get("total_score")
        tied = [row for row in eligible if row.get("total_score") == top_score]
        names = [row.get("candidate_name") or row["filename"] for row in tied]
        if len(tied) > 1:
            note = f"{_english_list(names)} are tied at {top_score}."
        else:
            note = f"{names[0]} ranks first with {top_score}."
        ranking = {"top_score": top_score, "tied_for_first": names, "note": note}

    if eligible and all(row.get("llm_status") == "skipped" for row in eligible):
        llm_note = "No model key was set. Every eligible row is llm_status: skipped."
    elif eligible:
        counts: dict[str, int] = {}
        for row in eligible:
            status = row.get("llm_status") or "unknown"
            counts[status] = counts.get(status, 0) + 1
        detail = ", ".join(f"{count} {status}" for status, count in sorted(counts.items()))
        llm_note = f"Eligible resumes: {detail}."
    else:
        llm_note = "No eligible resumes, so the model was not called."

    checked = [row for row in eligible if row.get("github_status") in {"ok", "failed"}]
    scored = sum(1 for row in checked if row.get("github_status") == "ok")
    failed_github = sum(1 for row in checked if row.get("github_status") == "failed")
    github = {
        "checked": len(checked),
        "scored": scored,
        "failed": failed_github,
        "note": (
            f"Checked {len(checked)} profiles. {scored} returned a score. "
            f"{failed_github} {'failure' if failed_github == 1 else 'failures'} recorded as 0."
        ),
    }

    return {
        "rejected": {
            "neither_python_nor_ai": [
                _person(row, reason="No Python and no AI project") for row in both
            ],
            "python_without_ai_project": [
                _person(
                    row,
                    reason="No AI project",
                    noted_skills=[
                        skill for skill in _BACKEND_SKILLS if skill in (row.get("matched_skills") or [])
                    ],
                )
                for row in ai_only
            ],
            "ai_without_python": [
                _person(
                    row,
                    reason="No Python",
                    skills_kept=[
                        skill for skill in (row.get("matched_skills") or []) if skill in _AI_SKILLS
                    ],
                )
                for row in python_only
            ],
        },
        "ranking": ranking,
        "witnesses": {"llm": llm_note, "github": github},
        "failed_files": [_person(row, error=row.get("error")) for row in failed],
        "reliability": (
            "A witness failure on one resume keeps that person's deterministic score. "
            "A corrupt PDF is recorded as failed without stopping the batch."
        ),
    }


def _person_line(row: dict, extra: list[str] | None = None) -> str:
    name = row.get("candidate_name") or "—"
    suffix = f"   {', '.join(extra)}" if extra else ""
    return f"  {row.get('filename', ''):<22}{name:<28}{suffix}"


def render_report(report: dict) -> str:
    """Short text report: counts, one line per reject, then the ranking table."""
    lines: list[str] = ["AI Resume Screening", "===================", ""]
    summary = report["batch_summary"]
    reasoning = report["reasoning"]

    lines.extend(["Batch", "-----"])
    for key in ("total", "parsed", "eligible", "rejected", "failed"):
        lines.append(f"  {key:<12}{summary[key]}")
    lines.append("")

    lines.extend(["Rejected", "--------"])
    rejected = reasoning["rejected"]
    groups = [
        ("Neither Python nor an AI project", rejected["neither_python_nor_ai"], None),
        ("Python, no AI project", rejected["python_without_ai_project"], "noted_skills"),
        ("AI project, no Python", rejected["ai_without_python"], "skills_kept"),
    ]
    for title, people, extra_key in groups:
        lines.append("")
        lines.append(title)
        if not people:
            lines.append("  None")
            continue
        for person in people:
            extra = person.get(extra_key) if extra_key else None
            lines.append(_person_line(person, extra or None))
    lines.append("")

    lines.extend(["Ranking", "-------", ""])
    lines.append(f"  {'Rank':<6}{'Score':<8}{'Name':<32}File")
    lines.append(f"  {'----':<6}{'-----':<8}{'----':<32}----")
    eligible = [row for row in report["candidates"] if row.get("eligible")]
    for row in eligible:
        name = row.get("candidate_name") or "—"
        lines.append(
            f"  {str(row.get('rank')):<6}{str(row.get('total_score')):<8}{name:<32}{row.get('filename')}"
        )
    lines.append("")
    if reasoning["ranking"]["note"]:
        lines.append(f"  {reasoning['ranking']['note']}")
        lines.append("")

    github = reasoning["witnesses"]["github"]
    lines.extend(["Witnesses", "---------", ""])
    lines.append(f"  Model     {reasoning['witnesses']['llm']}")
    lines.append(
        f"  GitHub    Checked {github['checked']}. "
        f"Scored {github['scored']}. Failed {github['failed']}."
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def finalize(rows: list[dict]) -> dict:
    eligible = [row for row in rows if row.get("eligible")]
    rejected = [row for row in rows if row.get("status") == "parsed" and not row.get("eligible")]
    failed = [row for row in rows if row.get("status") == "failed"]
    duplicates = [row for row in rows if row.get("status") == "duplicate"]

    eligible.sort(key=lambda row: (-(row.get("total_score") or 0), (row.get("candidate_name") or "").casefold()))
    for index, row in enumerate(eligible, start=1):
        row["rank"] = index
    rejected.sort(key=lambda row: (row.get("candidate_name") or row.get("filename") or "").casefold())
    failed.sort(key=lambda row: row.get("filename") or "")
    duplicates.sort(key=lambda row: row.get("filename") or "")

    ordered = eligible + rejected + failed + duplicates
    return {
        "batch_summary": {
            "total": len(eligible) + len(rejected) + len(failed),
            "parsed": len(eligible) + len(rejected),
            "eligible": len(eligible),
            "rejected": len(rejected),
            "failed": len(failed),
        },
        "reasoning": build_reasoning(ordered),
        "candidates": ordered,
    }


def write_results(report: dict, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    text_path = path.with_suffix(".txt")
    text_path.write_text(render_report(report), encoding="utf-8")
