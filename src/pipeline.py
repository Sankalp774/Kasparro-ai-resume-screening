"""Run one resume, then the batch. A witness failure stays on that row."""

import logging
from collections.abc import Callable

from src.config import github_token, llm_api_key
from src.eligibility import assess
from src.extract import extract_text
from src.github_enrich import GitHubEnricher
from src.ingest import ingest_folder
from src.llm import judge_resume
from src.models import ExtractedResume, GitHubResult, IngestedFile, ScoreCard, WitnessJudgment
from src.score import apply_witness, score_resume

logger = logging.getLogger("screener")

Judge = Callable[[ExtractedResume], WitnessJudgment]


def _blank_row(filename: str, status: str, error: str | None) -> dict:
    return {
        "rank": None,
        "filename": filename,
        "candidate_name": None,
        "email": None,
        "eligible": False,
        "status": status,
        "total_score": None,
        "score_breakdown": None,
        "score_evidence": None,
        "matched_skills": [],
        "project_summary": None,
        "github_summary": None,
        "github_status": None,
        "llm_status": None,
        "llm_note": None,
        "strengths": [],
        "concerns": [],
        "rejection_reasons": [],
        "error": error,
    }


def _row_from_unparsed(document: IngestedFile) -> dict:
    row = _blank_row(document.filename, document.status, document.error)
    if document.status == "duplicate":
        row["project_summary"] = document.error
    return row


def _apply_github(card: ScoreCard, result: GitHubResult) -> None:
    card.github = result.points
    card.evidence["github"] = result.summary


def _screen_one(
    resume: ExtractedResume,
    judge: Judge | None,
    github: GitHubEnricher,
) -> dict:
    decision = assess(resume)
    row = _blank_row(resume.filename, "parsed", None)
    row["candidate_name"] = resume.name
    row["email"] = resume.email
    row["matched_skills"] = decision.matched_skills
    row["eligible"] = decision.eligible
    row["rejection_reasons"] = decision.rejection_reasons

    if not decision.eligible:
        row["project_summary"] = (
            "Hard filter rejected this resume. "
            + "; ".join(decision.rejection_reasons)
        )
        if resume.github_username:
            row["github_status"] = "not_scored"
            row["github_summary"] = (
                f"Profile github.com/{resume.github_username} was not enriched "
                "because the candidate failed the hard filter."
            )
        else:
            row["github_status"] = "missing"
            row["github_summary"] = "No GitHub profile on resume"
        row["llm_status"] = "not_called"
        row["llm_note"] = "The model is not called after a failed hard filter."
        return row

    card = score_resume(resume)
    llm_status = "skipped"
    llm_note = "No LLM_API_KEY or XAI_API_KEY set. Deterministic score kept."
    if judge is not None:
        try:
            judgment = judge(resume)
            card, llm_status = apply_witness(card, judgment, resume.full_text)
            if llm_status == "ok":
                llm_note = "Witness quote found in the resume. AI depth adjusted inside the cap."
            else:
                llm_note = "Witness quote was not in the resume. Adjustment ignored."
        except Exception as exc:
            llm_status = "failed"
            llm_note = f"{type(exc).__name__}: {exc}"
            logger.warning("Witness failed for %s: %s", resume.filename, llm_note)

    try:
        github_result = github.enrich(resume.github_username)
    except Exception as exc:
        github_result = GitHubResult(
            points=0,
            status="failed",
            summary=f"GitHub enrichment failed ({type(exc).__name__}). Score left at 0.",
        )
        logger.warning("GitHub failed for %s: %s", resume.filename, exc)
    _apply_github(card, github_result)

    row["total_score"] = card.total()
    row["score_breakdown"] = card.breakdown()
    row["score_evidence"] = card.evidence
    row["project_summary"] = card.project_summary
    row["github_summary"] = github_result.summary
    row["github_status"] = github_result.status
    row["llm_status"] = llm_status
    row["llm_note"] = llm_note[:300]
    row["strengths"] = card.strengths
    row["concerns"] = card.concerns
    return row


def screen_extracted(
    resumes: list[ExtractedResume],
    *,
    judge: Judge | None = None,
    github: GitHubEnricher | None = None,
) -> list[dict]:
    enricher = github or GitHubEnricher(token=github_token())
    active_judge = judge
    if active_judge is None and llm_api_key():
        active_judge = lambda resume: judge_resume(resume.full_text)
    return [_screen_one(resume, active_judge, enricher) for resume in resumes]


def screen_batch(
    input_dir: str,
    *,
    judge: Judge | None = None,
    github: GitHubEnricher | None = None,
) -> list[dict]:
    rows: list[dict] = []
    parsed: list[ExtractedResume] = []
    for document in ingest_folder(input_dir):
        if document.status != "parsed":
            rows.append(_row_from_unparsed(document))
            continue
        parsed.append(extract_text(document.text, document.filename))
    rows.extend(screen_extracted(parsed, judge=judge, github=github))
    return rows
