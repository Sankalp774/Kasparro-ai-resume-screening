"""Weights, caps, and environment. No secrets live here."""

import os

AI_CAP = 40
PYTHON_CAP = 30
CLOUD_CAP = 15
GITHUB_CAP = 10
ENGINEERING_CAP = 5
TOTAL_CAP = 100

AI_PROJECT_BASE = 16
AI_SKILLS_ONLY = 8
THIN_WRAPPER_PENALTY = 10
TUTORIAL_PENALTY = 8
AI_ADJUSTMENT_MIN = -15
AI_ADJUSTMENT_MAX = 10
MIN_QUOTE_CHARS = 12

GITHUB_RECENT_DAYS = 90
GITHUB_REPO_DAYS = 180

DEFAULT_MODEL = "grok-4.7"
LLM_BASE_URL = "https://api.x.ai/v1"
LLM_TIMEOUT_SECONDS = 30.0

PYTHON_POINTS = {
    "Python": (12, 6),
    "FastAPI": (8, 3),
    "async": (4, 1),
    "PostgreSQL": (4, 1),
    "Redis": (2, 1),
}
CLOUD_POINTS = {
    "GCP": (6, 2),
    "Docker": (5, 2),
    "deployment": (4, 1),
}
REACT_BONUS = 3

AI_DEPTH_POINTS = {
    "retrieval": 6,
    "tool calling": 6,
    "state": 4,
    "orchestration": 6,
    "evaluation": 4,
    "backend logic": 4,
}


def llm_api_key() -> str | None:
    return os.getenv("LLM_API_KEY") or os.getenv("XAI_API_KEY") or None


def llm_model() -> str:
    return os.getenv("LLM_MODEL") or DEFAULT_MODEL


def github_token() -> str | None:
    token = os.getenv("GITHUB_TOKEN")
    return token or None
