"""The only module that talks to a model provider."""

from openai import OpenAI

from src.config import LLM_BASE_URL, LLM_TIMEOUT_SECONDS, llm_api_key, llm_model
from src.models import WitnessJudgment

SYSTEM_PROMPT = """You are a witness for a resume screener, not the judge.
Read the resume and fill the schema. Do not decide whether the candidate is eligible.
Rules:
- evidence_quote must be copied from the resume, at least 12 characters. If you cannot find a span, use an empty string.
- ai_depth_adjustment is an integer from -15 to 10. Positive only when the quote shows a real RAG, agent, tool-calling, or evaluation workflow. Negative when the quote shows a thin API wrapper or a tutorial.
- project_summary is one sentence about the strongest project in the resume.
- suggested_name, suggested_email, and suggested_skills are notes. Use empty strings or an empty list when unsure.
- thin_wrapper is true when the AI work is only a wrapper around an API with no retrieval, tools, state, orchestration, or evaluation.
"""


class WitnessError(Exception):
    """The witness failed. The caller keeps the deterministic score."""


def judge_resume(text: str, *, client: OpenAI | None = None) -> WitnessJudgment:
    key = llm_api_key()
    if client is None and not key:
        raise WitnessError("missing API key")

    model_client = client or OpenAI(
        api_key=key,
        base_url=LLM_BASE_URL,
        timeout=LLM_TIMEOUT_SECONDS,
    )
    try:
        completion = model_client.beta.chat.completions.parse(
            model=llm_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (text or "")[:15000]},
            ],
            response_format=WitnessJudgment,
        )
    except Exception as exc:
        raise WitnessError(f"{type(exc).__name__}: {exc}") from exc

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise WitnessError("empty completion")
    return parsed
