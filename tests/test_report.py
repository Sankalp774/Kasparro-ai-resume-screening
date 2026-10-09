from src.eligibility import AI_REASON, PYTHON_REASON
from src.report import finalize, render_report


def test_reasoning_explains_rejects_ties_and_witnesses():
    rows = [
        {
            "filename": "candidate_01.pdf",
            "candidate_name": "Kartikay Sinha",
            "eligible": False,
            "status": "parsed",
            "rejection_reasons": [PYTHON_REASON, AI_REASON],
            "matched_skills": ["React"],
            "llm_status": "not_called",
            "github_status": "not_scored",
        },
        {
            "filename": "candidate_42.pdf",
            "candidate_name": "ANJALI PATIL",
            "eligible": False,
            "status": "parsed",
            "rejection_reasons": [PYTHON_REASON, AI_REASON],
            "matched_skills": ["Java"],
            "llm_status": "not_called",
            "github_status": "missing",
        },
        {
            "filename": "candidate_03.pdf",
            "candidate_name": "Agam Jain",
            "eligible": False,
            "status": "parsed",
            "rejection_reasons": [AI_REASON],
            "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            "llm_status": "not_called",
            "github_status": "missing",
        },
        {
            "filename": "candidate_11.pdf",
            "candidate_name": "MD AZIZUL ISLAM",
            "eligible": False,
            "status": "parsed",
            "rejection_reasons": [PYTHON_REASON],
            "matched_skills": ["RAG", "embeddings", "JavaScript"],
            "llm_status": "not_called",
            "github_status": "not_scored",
        },
        {
            "filename": "a.pdf",
            "candidate_name": "Arunima Saha",
            "eligible": True,
            "status": "parsed",
            "total_score": 80,
            "llm_status": "skipped",
            "github_status": "missing",
            "rejection_reasons": [],
        },
        {
            "filename": "b.pdf",
            "candidate_name": "Prajwal A S",
            "eligible": True,
            "status": "parsed",
            "total_score": 80,
            "llm_status": "skipped",
            "github_status": "ok",
            "rejection_reasons": [],
        },
        {
            "filename": "c.pdf",
            "candidate_name": "Yash Maini",
            "eligible": True,
            "status": "parsed",
            "total_score": 80,
            "llm_status": "skipped",
            "github_status": "failed",
            "rejection_reasons": [],
        },
    ]

    report = finalize(rows)
    reasoning = report["reasoning"]
    neither = {person["filename"] for person in reasoning["rejected"]["neither_python_nor_ai"]}
    assert {"candidate_01.pdf", "candidate_42.pdf"} <= neither

    agam = next(
        person
        for person in reasoning["rejected"]["python_without_ai_project"]
        if person["filename"] == "candidate_03.pdf"
    )
    assert agam["noted_skills"] == ["FastAPI", "PostgreSQL", "Redis"]
    assert agam["reason"] == "No AI project"

    islam = next(
        person
        for person in reasoning["rejected"]["ai_without_python"]
        if person["filename"] == "candidate_11.pdf"
    )
    assert islam["skills_kept"] == ["RAG", "embeddings"]

    assert reasoning["ranking"]["top_score"] == 80
    assert reasoning["ranking"]["tied_for_first"] == ["Arunima Saha", "Prajwal A S", "Yash Maini"]
    assert "skipped" in reasoning["witnesses"]["llm"]
    assert reasoning["witnesses"]["github"] == {
        "checked": 2,
        "scored": 1,
        "failed": 1,
        "note": "Checked 2 profiles. 1 returned a score. 1 failure recorded as 0.",
    }

    rendered = render_report(report)
    assert "\n\nRejected\n" in rendered
    assert "\n\nRanking\n" in rendered
    assert "Eligible resumes" not in rendered
    assert "candidate_01.pdf" in rendered and "Kartikay Sinha" in rendered
    assert "FastAPI, PostgreSQL, Redis" in rendered
    assert "RAG, embeddings" in rendered
