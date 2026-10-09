"""Deterministic 100-point score. The model does not own these numbers."""

import re

from src.config import (
    AI_CAP,
    AI_DEPTH_POINTS,
    AI_PROJECT_BASE,
    AI_SKILLS_ONLY,
    CLOUD_CAP,
    CLOUD_POINTS,
    ENGINEERING_CAP,
    MIN_QUOTE_CHARS,
    PYTHON_CAP,
    PYTHON_POINTS,
    REACT_BONUS,
    THIN_WRAPPER_PENALTY,
    TUTORIAL_PENALTY,
)
from src.eligibility import ai_terms, term_pattern
from src.extract import normalize
from src.models import ExtractedResume, ScoreCard, WitnessJudgment

DEPTH_PATTERNS: dict[str, re.Pattern[str]] = {
    "retrieval": re.compile(
        r"\brag\b|\bembeddings?\b|\bvector\s+(?:search|database|store|db)\b|\bpgvector\b|\bfaiss\b|\bchroma(?:db)?\b|\bpinecone\b",
        re.I,
    ),
    "tool calling": re.compile(r"\btool[-\s]?calling\b|\bfunction\s+calling\b", re.I),
    "state": re.compile(
        r"\bstateful\b|\bagent\s+memory\b|\bcheckpoint\b|\bshort-term\s+memory\b|\blong-term\s+memory\b",
        re.I,
    ),
    "orchestration": re.compile(r"\blang\s*graph\b|\bmulti[-\s]?agents?\b|\borchestrat\w*\b", re.I),
    "evaluation": re.compile(r"\bevaluation\s+pipeline\b|\bevals?\b|\bbenchmark\b", re.I),
    "backend logic": re.compile(r"\bfast\s*api\b|\bbackend\b|\bworkflow\b|\bbusiness\s+logic\b", re.I),
}

ENGINEERING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("testing", re.compile(r"\bpytest\b|\bunit\s+tests?\b|\bintegration\s+tests?\b|\btesting\b|\btest\s+coverage\b", re.I)),
    ("architecture", re.compile(r"\barchitecture\b", re.I)),
    ("caching", re.compile(r"\bcach(?:e|ing)\b", re.I)),
    ("queues", re.compile(r"\bqueues?\b|\bcelery\b|\bkafka\b|\brabbitmq\b", re.I)),
    ("observability", re.compile(r"\bobservability\b|\bprometheus\b|\bgrafana\b|\bmonitoring\b|\btracing\b", re.I)),
    ("concurrency", re.compile(r"\bconcurrency\b|\bconcurrent\b", re.I)),
    ("failure handling", re.compile(r"\bretr(?:y|ies)\b|\bfault\s+toleran\w*\b|\bcircuit\s+breaker\b|\bfailure\s+handling\b", re.I)),
]

TUTORIAL_RE = re.compile(r"\btutorial\b|\bfollowed\s+along\b|\bclone\b", re.I)


def _clamp(value: int, cap: int) -> int:
    return max(0, min(cap, value))


def _project_work(resume: ExtractedResume) -> str:
    return f"{resume.project_text}\n{resume.work_text}".strip()


def _locate(pattern: re.Pattern[str], resume: ExtractedResume) -> str:
    """Where a term earns points. Project text outranks a skills list."""
    project_work = _project_work(resume)
    if project_work and pattern.search(project_work):
        return "project"
    if resume.skills_text and pattern.search(resume.skills_text):
        return "skills"
    if not project_work and not resume.skills_text and pattern.search(resume.full_text):
        return "unsectioned"
    if pattern.search(resume.full_text):
        return "mention"
    return ""


def _score_group(
    resume: ExtractedResume,
    table: dict[str, tuple[int, int]],
) -> tuple[int, list[str]]:
    total = 0
    notes: list[str] = []
    for name, (high, low) in table.items():
        where = _locate(term_pattern(name), resume)
        if where in {"project", "unsectioned"}:
            total += high
            notes.append(f"{name} in project/work (+{high})")
        elif where in {"skills", "mention"}:
            total += low
            notes.append(f"{name} on a skills list (+{low})")
    return total, notes


def _score_ai(resume: ExtractedResume) -> tuple[int, str]:
    project_work = _project_work(resume)
    project_hits = ai_terms(project_work) if project_work else []
    skill_hits = ai_terms(resume.skills_text)
    loose_hits = ai_terms(resume.full_text)

    if project_hits:
        points = AI_PROJECT_BASE
        notes = [f"AI project evidence: {', '.join(project_hits)} (+{AI_PROJECT_BASE})"]
        depth_found = False
        for label, bonus in AI_DEPTH_POINTS.items():
            if DEPTH_PATTERNS[label].search(project_work):
                points += bonus
                depth_found = True
                notes.append(f"{label} (+{bonus})")
        if not depth_found:
            skills_have_depth = any(pattern.search(resume.skills_text) for pattern in DEPTH_PATTERNS.values())
            if skills_have_depth:
                notes.append("depth terms appear in the skills list, so the thin-wrapper penalty was not applied")
            else:
                points -= THIN_WRAPPER_PENALTY
                notes.append(f"thin wrapper or keyword-only project (-{THIN_WRAPPER_PENALTY})")
        if TUTORIAL_RE.search(project_work):
            points -= TUTORIAL_PENALTY
            notes.append(f"tutorial or clone with no ownership (-{TUTORIAL_PENALTY})")
    elif skill_hits or (not project_work and not resume.skills_text and loose_hits):
        hits = skill_hits or loose_hits
        points = AI_SKILLS_ONLY
        notes = [f"AI mentioned outside a project block: {', '.join(hits)} (+{AI_SKILLS_ONLY})"]
    elif loose_hits:
        points = AI_SKILLS_ONLY
        notes = [f"AI mentioned outside a project block: {', '.join(loose_hits)} (+{AI_SKILLS_ONLY})"]
    else:
        points = 0
        notes = ["No AI term in the scored text"]

    points = _clamp(points, AI_CAP)
    return points, "; ".join(notes)


def _score_cloud(resume: ExtractedResume) -> tuple[int, str]:
    points, notes = _score_group(resume, CLOUD_POINTS)
    react = term_pattern("React").search(resume.full_text) or term_pattern("Next.js").search(resume.full_text)
    backendish = any(
        term_pattern(name).search(resume.full_text)
        for name in ("FastAPI", "Docker", "GCP", "deployment", "PostgreSQL")
    )
    if react and backendish:
        points += REACT_BONUS
        notes.append(f"React or Next.js inside a system that also has backend or deploy evidence (+{REACT_BONUS})")
    points = _clamp(points, CLOUD_CAP)
    evidence = "; ".join(notes) if notes else "No cloud, Docker, or deployment evidence"
    return points, evidence


def _score_engineering(resume: ExtractedResume) -> tuple[int, str]:
    project_work = _project_work(resume) or resume.full_text
    notes: list[str] = []
    for label, pattern in ENGINEERING_PATTERNS:
        if pattern.search(project_work):
            notes.append(label)
        if len(notes) == ENGINEERING_CAP:
            break
    points = len(notes)
    if notes:
        return points, "Engineering signals: " + ", ".join(notes)
    return 0, "No testing, architecture, caching, queue, observability, concurrency, or failure-handling evidence"


def _summary(ai: int, python: int, cloud: int, engineering: int) -> str:
    return (
        f"Deterministic read: AI depth {ai}/40, Python backend {python}/30, "
        f"cloud {cloud}/15, engineering {engineering}/5. GitHub is scored separately."
    )


def _lists(ai: int, python: int, cloud: int, engineering: int) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    concerns: list[str] = []
    if ai >= 28:
        strengths.append("Strong AI project evidence in the resume text")
    if python >= 18:
        strengths.append("Python backend evidence in a project or internship")
    if cloud >= 8:
        strengths.append("Cloud or deployment evidence")
    if engineering >= 3:
        strengths.append("Several engineering-depth signals")
    if ai <= 10:
        concerns.append("Limited AI project depth")
    if python < 12:
        concerns.append("Thin Python backend evidence")
    if cloud == 0:
        concerns.append("No cloud or deployment evidence")
    if engineering == 0:
        concerns.append("No testing, architecture, or reliability signals")
    return strengths[:4], concerns[:4]


def score_resume(resume: ExtractedResume) -> ScoreCard:
    ai, ai_evidence = _score_ai(resume)
    python, python_notes = _score_group(resume, PYTHON_POINTS)
    python = _clamp(python, PYTHON_CAP)
    python_evidence = "; ".join(python_notes) if python_notes else "No Python backend evidence"
    cloud, cloud_evidence = _score_cloud(resume)
    engineering, engineering_evidence = _score_engineering(resume)
    strengths, concerns = _lists(ai, python, cloud, engineering)
    return ScoreCard(
        ai_project_depth=ai,
        python_backend=python,
        cloud_fullstack=cloud,
        github=0,
        engineering_depth=engineering,
        evidence={
            "ai_project_depth": ai_evidence,
            "python_backend": python_evidence,
            "cloud_fullstack": cloud_evidence,
            "github": "GitHub not enriched yet",
            "engineering_depth": engineering_evidence,
        },
        strengths=strengths,
        concerns=concerns,
        project_summary=_summary(ai, python, cloud, engineering),
    )


def quote_supported(quote: str, resume_text: str) -> bool:
    normalized_quote = normalize(quote).casefold().strip()
    if len(normalized_quote) < MIN_QUOTE_CHARS:
        return False
    return normalized_quote in normalize(resume_text).casefold()


def apply_witness(card: ScoreCard, judgment: WitnessJudgment, resume_text: str) -> tuple[ScoreCard, str]:
    """Admit a witness adjustment only when its quote is in the resume."""
    if not quote_supported(judgment.evidence_quote, resume_text):
        return card, "ignored"

    updated = card.model_copy(deep=True)
    updated.ai_project_depth = _clamp(
        updated.ai_project_depth + judgment.ai_depth_adjustment,
        AI_CAP,
    )
    quote = " ".join(judgment.evidence_quote.split())
    updated.evidence["ai_project_depth"] = (
        f"{updated.evidence['ai_project_depth']}; witness adjustment "
        f"{judgment.ai_depth_adjustment:+d} supported by: {quote}"
    )
    summary = " ".join(judgment.project_summary.split())
    if summary:
        updated.project_summary = summary[:500]
    if judgment.strengths:
        updated.strengths = [item.strip() for item in judgment.strengths if item.strip()][:4]
    if judgment.concerns:
        updated.concerns = [item.strip() for item in judgment.concerns if item.strip()][:4]
    return updated, "ok"
