import json

from pypdf import PdfReader

from src.pdf_report import write_detailed_pdf


def test_pdf_reads_json_and_leaves_the_source_unchanged(tmp_path):
    report = {
        "batch_summary": {"total": 2, "parsed": 2, "eligible": 1, "rejected": 1, "failed": 0},
        "reasoning": {
            "rejected": {
                "neither_python_nor_ai": [],
                "python_without_ai_project": [
                    {
                        "filename": "candidate_03.pdf",
                        "candidate_name": "Agam Jain",
                        "reason": "No AI project",
                        "noted_skills": ["FastAPI", "PostgreSQL", "Redis"],
                    }
                ],
                "ai_without_python": [],
            },
            "ranking": {"top_score": 80, "tied_for_first": ["Ada Lovelace"], "note": "Ada Lovelace ranks first with 80."},
            "witnesses": {
                "llm": "No model key was set. Every eligible row is llm_status: skipped.",
                "github": {"checked": 1, "scored": 1, "failed": 0},
            },
        },
        "candidates": [
            {
                "rank": 1,
                "filename": "strong.pdf",
                "candidate_name": "Ada Lovelace",
                "email": "ada@example.com",
                "eligible": True,
                "total_score": 80,
                "score_breakdown": {
                    "ai_project_depth": 40,
                    "python_backend": 24,
                    "cloud_fullstack": 6,
                    "github": 6,
                    "engineering_depth": 4,
                },
                "score_evidence": {
                    "ai_project_depth": "LangGraph RAG project with tool calling",
                    "python_backend": "FastAPI in project/work",
                    "cloud_fullstack": "Docker in project/work",
                    "github": "2 relevant public repos",
                    "engineering_depth": "pytest",
                },
                "matched_skills": ["Python", "LangGraph", "RAG"],
                "project_summary": "Built a retrieval pipeline.",
                "strengths": ["Strong AI project evidence"],
                "concerns": [],
                "llm_status": "skipped",
                "llm_note": "No key.",
                "github_status": "ok",
                "github_summary": "2 relevant public repos",
            }
        ],
    }
    source = tmp_path / "results.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    original = source.read_bytes()
    destination = tmp_path / "detailed.pdf"

    write_detailed_pdf(json.loads(source.read_text(encoding="utf-8")), destination)

    assert source.read_bytes() == original
    reader = PdfReader(str(destination))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Ada Lovelace" in text
    assert "80" in text
    assert "LangGraph RAG project with tool calling" in text
    assert "Agam Jain" in text
    assert "FastAPI, PostgreSQL, Redis" in text
    assert len(reader.pages) >= 2
