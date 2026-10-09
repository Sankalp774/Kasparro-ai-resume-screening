"""Hard eligibility filter. No model calls."""

import re

from src.models import Eligibility, ExtractedResume

PYTHON_REASON = "No evidence of Python stack"
AI_REASON = "No AI/agentic project evidence"

# (canonical name, pattern, kind)
# kind "ai" is the agentic gate. Other kinds are matched skills or score signals.
TERMS: list[tuple[str, re.Pattern[str], str]] = [
    ("Python", re.compile(r"\bpyt\s*hon\b", re.I), "python"),
    ("FastAPI", re.compile(r"\bfast\s*api\b", re.I), "backend"),
    ("async", re.compile(r"\basync(?:io)?\b", re.I), "backend"),
    ("PostgreSQL", re.compile(r"\bpostgres(?:ql)?\b|\bpostgre\s*sql\b", re.I), "backend"),
    ("Redis", re.compile(r"\bredis\b", re.I), "backend"),
    ("Docker", re.compile(r"\bdocker\b", re.I), "cloud"),
    ("GCP", re.compile(r"\bgcp\b|\bgoogle\s+cloud\b", re.I), "cloud"),
    ("deployment", re.compile(r"\bdeploy(?:ed|ment|ing)?\b|\bcloud\s+run\b|\bgke\b", re.I), "cloud"),
    ("React", re.compile(r"\breact(?:\.js|js)?\b", re.I), "frontend"),
    ("Next.js", re.compile(r"\bnext\.js\b|\bnextjs\b", re.I), "frontend"),
    ("LangChain", re.compile(r"\blang\s*chain\b", re.I), "ai"),
    ("LangGraph", re.compile(r"\blang\s*graph\b", re.I), "ai"),
    ("LlamaIndex", re.compile(r"\bllama\s*index\b", re.I), "ai"),
    ("Google ADK", re.compile(r"\bgoogle\s+adk\b|\bagent\s+development\s+kit\b", re.I), "ai"),
    ("RAG", re.compile(r"\brag\b", re.I), "ai"),
    ("embeddings", re.compile(r"\bembeddings?\b", re.I), "ai"),
    ("vector search", re.compile(r"\bvector\s+(?:search|database|store|db)\b|\bpgvector\b", re.I), "ai"),
    ("FAISS", re.compile(r"\bfaiss\b", re.I), "ai"),
    ("Chroma", re.compile(r"\bchroma(?:db)?\b", re.I), "ai"),
    ("Pinecone", re.compile(r"\bpinecone\b", re.I), "ai"),
    ("tool calling", re.compile(r"\btool[-\s]?calling\b|\bfunction\s+calling\b", re.I), "ai"),
    ("multi-agent", re.compile(r"\bmulti[-\s]?agents?\b", re.I), "ai"),
    ("agent", re.compile(r"\bagents?\b", re.I), "ai"),
    ("OpenAI", re.compile(r"\bopen\s*ai\b", re.I), "ai"),
    ("Gen AI", re.compile(r"\bgen\s*ai\b", re.I), "ai"),
    ("LLM", re.compile(r"\bllms?\b", re.I), "ai"),
    ("Hugging Face", re.compile(r"\bhugging\s*face\b", re.I), "ai"),
    ("transformers", re.compile(r"\btransformers?\b", re.I), "ai"),
    ("Java", re.compile(r"\bjava\b", re.I), "extra"),
    ("JavaScript", re.compile(r"\bjava\s*script\b|\bnode\.js\b|\bnodejs\b", re.I), "extra"),
    ("Spring Boot", re.compile(r"\bspring\s*boot\b", re.I), "extra"),
]

_BY_NAME = {name: pattern for name, pattern, _kind in TERMS}


def term_pattern(name: str) -> re.Pattern[str]:
    return _BY_NAME[name]


def matched_names(text: str, kind: str | None = None) -> list[str]:
    found: list[str] = []
    for name, pattern, term_kind in TERMS:
        if kind is not None and term_kind != kind:
            continue
        if pattern.search(text):
            found.append(name)
    return found


def has_python(text: str) -> bool:
    return bool(_BY_NAME["Python"].search(text))


def ai_terms(text: str) -> list[str]:
    return matched_names(text, kind="ai")


def assess(resume: ExtractedResume) -> Eligibility:
    text = resume.full_text
    skills = matched_names(text)
    # "deployment" is a scoring signal, not a skill name we show.
    visible = [name for name in skills if name != "deployment"]
    reasons: list[str] = []
    if not has_python(text):
        reasons.append(PYTHON_REASON)
    if not ai_terms(text):
        reasons.append(AI_REASON)
    return Eligibility(
        eligible=not reasons,
        rejection_reasons=reasons,
        matched_skills=visible,
    )
