# Assignment spec — AI Resume Screening & Ranking System

Time box: 2–3 hours. Language: Python. Interface: CLI is enough; FastAPI is optional. Input: about 50 resumes. Output: ranked candidates plus reasons.

## Goal

Ingest a folder of resumes, hard-filter for Python + AI/agentic evidence, score eligible candidates on engineering and AI project depth, enrich with public GitHub activity, and return a ranked shortlist.

## Pipeline

1. Ingest every resume in the input directory.
2. Extract text and useful fields: name, email, skills, projects, GitHub URL when present.
3. Apply hard eligibility filters before ranking.
4. Score only eligible candidates.
5. Check public GitHub activity when a profile URL exists.
6. Return every candidate with eligibility, evidence, score breakdown, and final rank.

## Input

```text
project/
  resumes/
    candidate_01.pdf
    candidate_02.pdf
  src/
  README.md
  requirements.txt or pyproject.toml
```

- PDF support is required. DOCX/TXT is a bonus.
- Layouts and section names will differ. Do not assume a template.
- A malformed or unreadable resume must not crash the batch.

## Hard eligibility (rule-based, not LLM)

Eligible only if both are true:

- **Python evidence:** Python appears as a real skill, project technology, internship/work technology, or implementation language. A JavaScript / Java / React-only profile is rejected.
- **AI / agentic evidence:** at least one meaningful AI / LLM / RAG / agentic project, framework, or implementation. Examples: LangChain, LangGraph, Google ADK, LlamaIndex, RAG pipelines, embeddings / vector search, tool-calling agents, multi-agent workflows, evaluation pipelines, or an equivalent custom implementation.

Do not reject someone only because they also list JavaScript, Java, React, or Next.js.

Suggested reject shape:

```json
{
  "candidate": "Candidate Name",
  "eligible": false,
  "rejection_reasons": ["No evidence of Python stack", "No AI/agentic project evidence"],
  "matched_skills": ["Java", "React", "Spring Boot"]
}
```

## Score — 100 points

Deterministic, LLM, or hybrid. Must be explainable and include resume evidence.

| Category | Weight | Reward |
| --- | --- | --- |
| AI / Agentic / RAG project depth | 40 | Agents, RAG, tools, retrieval, state, orchestration, evaluation, real business logic |
| Python and backend engineering | 30 | Python, FastAPI, async, PostgreSQL, Redis. Projects and internships over keyword lists |
| Cloud / deployment / full stack | 15 | GCP, Docker, deployment. React/Next.js only as part of an end-to-end system |
| GitHub activity | 10 | Recent public engineering activity and maintained/relevant repos. Missing or private GitHub must not fail screening |
| Engineering depth signals | 5 | Testing, architecture, caching, queues, observability, concurrency, failure handling |

Penalties:

- Deduct 5–15 when an “AI project” is only a thin LLM/API wrapper with no workflow, data processing, retrieval, state, backend logic, evaluation, or product logic.
- Deduct for tutorial-style projects with no implementation detail or ownership.
- Do not give full points because a framework name is in the skills section. Prefer evidence of how it was used.
- Strong Python with no meaningful AI project must not rank near the top, even if it barely passes eligibility.

## GitHub enrichment

- Extract username or profile URL from the resume.
- Use the public GitHub API or equivalent public data.
- Signals: recent public events/commits, recently updated repos, number of maintained public repos, Python/AI-relevant repos.
- Cap at 10 points. Suggested split: 0–5 recent activity + 0–5 maintained/relevant repos.
- API failure, rate limit, private profile, or missing profile: continue and record the failure.
- Token from an environment variable only. Never hard-code credentials.
- Cache within the run. Do not repeat the same network call.

## LLM usage

Encouraged for semantic extraction or project-quality judgment. Must stay predictable and testable.

- Structured output (Pydantic or JSON schema).
- Keep hard eligibility outside the LLM where possible.
- Model must return evidence or short reasons for important score decisions.
- Provider-specific code behind a small adapter.
- API keys from environment variables.
- One failed model call for one resume must not fail the batch.

## Required output

JSON preferred.

```json
[
  {
    "rank": 1,
    "candidate_name": "Asha Rao",
    "eligible": true,
    "total_score": 86,
    "score_breakdown": {
      "ai_project_depth": 35,
      "python_backend": 27,
      "cloud_fullstack": 12,
      "github": 8,
      "engineering_depth": 4
    },
    "matched_skills": ["Python", "FastAPI", "PostgreSQL", "LangGraph", "Docker", "GCP"],
    "project_summary": "Built a stateful agentic workflow with retrieval and tool calling.",
    "github_summary": "Recently active; multiple maintained Python repositories.",
    "strengths": ["Strong agentic project", "Async FastAPI backend"],
    "concerns": ["Limited Redis evidence"]
  }
]
```

Minimum:

- Eligible candidates ranked highest score first.
- Rejected candidates with explicit rejection reasons.
- Matched skills and a short evidence-backed project summary.
- Score breakdown for every eligible candidate.
- GitHub enrichment status/summary when a profile exists.
- Batch summary: total resumes, successfully parsed, eligible, rejected, failed/unreadable.

## How to run

```bash
python main.py --input ./resumes --output ./output/results.json
```

Optional API: `POST /screen`, `GET /results`. Do not build a frontend.

## Engineering expectations

- Modules, not one file.
- Handle malformed resumes, missing fields, duplicate files, GitHub failures, and LLM failures.
- Bound concurrency if async is used.
- Config (model name, thresholds, weights, API keys) separate from business logic.
- At least a few tests, especially eligibility and scoring.
- Explainability over clever math.

## Deliverables

- Source in a git repo or ZIP.
- README with setup and run instructions.
- `requirements.txt` or `pyproject.toml`.
- `.env.example` with variable names, no secrets.
- Generated `results.json` for the provided resume set.
- README section **Design Decisions**: filtering, scoring, LLM usage, GitHub scoring.
- README section **If I Had More Time**: next 2–4 improvements.

## Bonus only after the core works

DOCX parsing, FastAPI, bounded async, caching, small HTML/terminal report, synthetic-resume tests.

## Scope guardrails

No frontend, auth, database, deployment, or vector DB. They care that an ambiguous requirement became a reliable pipeline another engineer can run and review.
