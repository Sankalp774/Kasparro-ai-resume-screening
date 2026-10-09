from src.eligibility import AI_REASON, PYTHON_REASON, assess
from src.extract import extract_text


def _decision(text: str):
    return assess(extract_text(text, "sample.pdf"))


def test_python_langgraph_project_is_eligible():
    decision = _decision("Skills\nPython\nProjects\nBuilt a LangGraph agent for support tickets.")
    assert decision.eligible
    assert decision.rejection_reasons == []
    assert "Python" in decision.matched_skills
    assert "LangGraph" in decision.matched_skills


def test_javascript_and_react_only_is_rejected_for_both_reasons():
    text = (
        "Skills\nJavaScript React\n"
        "Projects\nLeveraged AI-assisted development to build a React dashboard."
    )
    decision = _decision(text)
    assert not decision.eligible
    assert decision.rejection_reasons == [PYTHON_REASON, AI_REASON]


def test_python_backend_without_ai_is_rejected_for_ai_only():
    text = (
        "Skills\nPython FastAPI PostgreSQL Redis\n"
        "Projects\nBuilt a FastAPI service with PostgreSQL and Redis."
    )
    decision = _decision(text)
    assert not decision.eligible
    assert decision.rejection_reasons == [AI_REASON]
    assert "FastAPI" in decision.matched_skills


def test_pythonic_does_not_count_as_python():
    decision = _decision("I write pythonic Java and React code for web apps.")
    assert not decision.eligible
    assert PYTHON_REASON in decision.rejection_reasons
    assert "Python" not in decision.matched_skills


def test_rag_hidden_inside_other_words_does_not_count():
    text = (
        "Python developer from Kharagpur. Improved test coverage and storage. "
        "Leveraged an average result and a drag gesture."
    )
    decision = _decision(text)
    assert not decision.eligible
    assert decision.rejection_reasons == [AI_REASON]
    assert "RAG" not in decision.matched_skills


def test_rag_without_python_keeps_the_ai_skills_and_rejects_python():
    text = (
        "Projects\nEngineered an AI-powered RAG platform using React, "
        "PostgreSQL, and pgvector for retrieval."
    )
    decision = _decision(text)
    assert not decision.eligible
    assert decision.rejection_reasons == [PYTHON_REASON]
    assert "RAG" in decision.matched_skills
    assert "vector search" in decision.matched_skills
