from src.extract import extract_text
from src.models import ExtractedResume
from src.score import score_resume


def _resume(**overrides) -> ExtractedResume:
    base = dict(
        filename="sample.pdf",
        name="Sample Candidate",
        email=None,
        github_url=None,
        github_username=None,
        skills_text="",
        project_text="",
        work_text="",
        full_text="",
    )
    base.update(overrides)
    base["full_text"] = "\n".join(
        part
        for part in (base["skills_text"], base["project_text"], base["work_text"], base["full_text"])
        if part
    )
    return ExtractedResume(**base)


def test_category_caps_hold_on_a_stuffed_resume():
    text = (
        "Python FastAPI async PostgreSQL Redis Docker GCP deployment React Next.js "
        "LangChain LangGraph LlamaIndex RAG embeddings vector search FAISS Chroma Pinecone "
        "tool calling multi-agent agent OpenAI LLM Hugging Face transformers "
        "stateful agent memory evaluation pipeline benchmark backend workflow "
        "pytest architecture caching queues observability concurrency retry"
    )
    card = score_resume(
        _resume(project_text=text, skills_text=text, full_text=text)
    )
    assert card.ai_project_depth <= 40
    assert card.python_backend <= 30
    assert card.cloud_fullstack <= 15
    assert card.github <= 10
    assert card.engineering_depth <= 5
    assert 0 <= card.total() <= 100
    assert card.evidence["ai_project_depth"]
    assert card.evidence["python_backend"]


def test_thin_wrapper_scores_below_a_real_agent_project():
    thin = score_resume(
        _resume(project_text="Built a thin LLM API wrapper chatbot for a class demo.")
    )
    deep = score_resume(
        _resume(
            project_text=(
                "Built a LangGraph RAG pipeline with tool calling, an evaluation pipeline, "
                "and a FastAPI backend."
            )
        )
    )
    assert thin.ai_project_depth < deep.ai_project_depth
    assert thin.ai_project_depth == 6
    assert deep.ai_project_depth <= 40


def test_skills_only_fastapi_scores_below_project_fastapi():
    skills_only = score_resume(
        _resume(
            skills_text="Python FastAPI PostgreSQL",
            project_text="Built a Java notes app for a class.",
        )
    )
    in_project = score_resume(
        _resume(
            skills_text="Git",
            project_text="Built a FastAPI service in Python with PostgreSQL.",
        )
    )
    assert skills_only.python_backend < in_project.python_backend
