from src.extract import extract_text
from src.github_enrich import GitHubEnricher
from src.models import WitnessJudgment
from src.pipeline import screen_extracted
from src.report import finalize
from src.score import apply_witness, score_resume

STRONG = (
    "Skills\nPython FastAPI\n"
    "Projects\nBuilt a LangGraph retrieval pipeline with tool calling and a FastAPI backend."
)


def _judgment(**overrides) -> WitnessJudgment:
    payload = dict(
        ai_depth_adjustment=10,
        thin_wrapper=False,
        project_summary="Built a retrieval pipeline.",
        strengths=["Real retrieval workflow"],
        concerns=[],
        evidence_quote="not in the resume at all",
        suggested_name="Suggested Name",
        suggested_email="suggested@example.com",
        suggested_skills=["SuggestedSkill"],
    )
    payload.update(overrides)
    return WitnessJudgment(**payload)


def test_quote_missing_from_resume_does_not_change_ai_depth():
    resume = extract_text(STRONG, "good.pdf")
    card = score_resume(resume)
    updated, status = apply_witness(card, _judgment(), resume.full_text)
    assert status == "ignored"
    assert updated.ai_project_depth == card.ai_project_depth
    assert updated.project_summary == card.project_summary


def test_quote_in_resume_adjusts_ai_depth_inside_the_cap():
    resume = extract_text(STRONG, "good.pdf")
    card = score_resume(resume)
    quote = "LangGraph retrieval pipeline with tool calling"
    updated, status = apply_witness(
        card,
        _judgment(evidence_quote=quote, ai_depth_adjustment=10),
        resume.full_text,
    )
    assert status == "ok"
    assert updated.ai_project_depth == min(40, card.ai_project_depth + 10)
    assert updated.ai_project_depth <= 40
    assert updated.project_summary == "Built a retrieval pipeline."


def test_failed_witness_keeps_the_deterministic_score_and_the_batch():
    good = extract_text(STRONG, "good.pdf")
    bad = extract_text(STRONG, "bad.pdf")

    def judge(resume):
        if resume.filename == "bad.pdf":
            raise TimeoutError("timeout")
        return _judgment(evidence_quote="LangGraph retrieval pipeline with tool calling")

    rows = screen_extracted(
        [good, bad],
        judge=judge,
        github=GitHubEnricher(getter=lambda url: []),
    )
    report = finalize(rows)
    by_name = {row["filename"]: row for row in report["candidates"]}

    assert by_name["bad.pdf"]["llm_status"] == "failed"
    assert by_name["bad.pdf"]["eligible"] is True
    assert by_name["bad.pdf"]["total_score"] == score_resume(bad).total()
    assert by_name["bad.pdf"]["candidate_name"] != "Suggested Name"
    assert by_name["good.pdf"]["llm_status"] == "ok"
    assert len(report["candidates"]) == 2
    assert report["batch_summary"]["eligible"] == 2
