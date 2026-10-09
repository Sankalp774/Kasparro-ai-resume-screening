# Build plan for Grok — resume screening pipeline

Read `01-company-context.md` and `02-assignment-spec.md` first. Implement only this plan. Do not add a frontend.

## Design rule

LLM as witness, code as judge. See `01-company-context.md`.

- Eligibility is pure code. The model cannot flip `eligible`.
- Scores start from deterministic rules. The model may only adjust AI depth inside the 40 cap, and only with a quoted evidence span. If the quote is not in the resume text, ignore the adjustment.
- One injected failure (timeout, invalid JSON, empty output, 429) must leave that candidate scored and the rest of the batch intact.
- Test this with a fake adapter that raises on a chosen filename.

```bash
python main.py --input ./resumes --output ./output/results.json
```

writes valid JSON for a mixed folder: good PDFs, one corrupt file, one JS-only resume, one Python-without-AI resume, one strong Python+RAG resume. The corrupt file is listed under failed, not as a crash.

## Layout

```text
src/
  config.py          # weights, thresholds, model name, env
  models.py          # Pydantic schemas
  ingest.py          # PDF text; optional DOCX/TXT
  extract.py         # name, email, skills, projects, github url
  eligibility.py     # hard filter, no LLM
  score.py           # 100-point breakdown + penalties
  llm.py             # one adapter, structured output, per-resume failure
  github_enrich.py   # public API, in-run cache, token from env
  pipeline.py        # orchestrate one resume and the batch
  report.py          # rank, rejected, batch summary, write JSON
main.py              # CLI
tests/
  test_eligibility.py
  test_score.py
requirements.txt
.env.example
README.md
output/results.json
```

## Phase 1 — Skeleton

- CLI flags `--input` and `--output`.
- Walk the folder, skip non-files, write an empty result list plus batch counts.
- `.env.example`: `LLM_API_KEY`, `LLM_MODEL`, `GITHUB_TOKEN` (optional).

## Phase 2 — Ingest

- PDF via `pypdf` or `pdfplumber`.
- Catch parse errors per file. Record `status: failed` and the filename.
- Optional: DOCX via `python-docx`, plain TXT.
- Dedupe by normalized filename or file hash.

## Phase 3 — Extract

Regex/heuristics first:

- Email
- GitHub URL → username
- Name from the first non-empty lines if no label
- Skill-like tokens and project blocks

Missing fields stay null. Do not crash.

## Phase 4 — Hard filter

Eligible only if both:

- Python evidence in skills, projects, or work (word-boundary `python`, not a substring accident).
- AI evidence: langchain, langgraph, llamaindex, google adk, rag, embedding, vector, faiss, chroma, pinecone, tool calling, agent, multi-agent, openai, llm, huggingface, transformers, or a clear custom AI implementation phrase.

Return `eligible`, `rejection_reasons`, `matched_skills`.

Tests:

- Python + LangGraph project → eligible
- Java + React only → reject, both reasons if AI also missing
- Python skills, no AI project → reject for AI only
- “python” inside an unrelated word must not count

## Phase 5 — Score

Only eligible candidates. Caps:

- ai_project_depth ≤ 40
- python_backend ≤ 30
- cloud_fullstack ≤ 15
- github ≤ 10 (filled in Phase 7, else 0)
- engineering_depth ≤ 5

Rules:

- Project/work evidence outranks a skills-list mention.
- Thin wrapper or tutorial with no ownership: subtract 5–15 from AI depth, floor at 0.
- Always attach a short evidence string per category.
- `total_score` is the sum after penalties, clamped 0–100.

Tests: weight caps, penalty lowers AI depth, keyword-only FastAPI scores below project evidence.

## Phase 6 — LLM adapter

- Single function: resume text in, structured project-quality judgment out.
- Use it to refine AI depth and the project summary, not to override eligibility.
- On timeout, bad JSON, or missing key: log the failure on that candidate and keep the deterministic score.
- No provider SDK calls outside `llm.py`.

## Phase 7 — GitHub

- If no URL: `github_summary = "No GitHub profile on resume"`, score 0.
- Else GET public user repos and recent events. Cache by username.
- 0–5 recent activity (push/commit in last 90 days), 0–5 if public repos look Python/AI and were updated recently.
- On 403/404/timeout: record enrichment failure, score 0, continue.

## Phase 8 — Output and README

Rank eligible by `total_score` desc, then name. Rejected and failed stay in the file with reasons.

Batch summary fields: `total`, `parsed`, `eligible`, `rejected`, `failed`.

README must include setup, the run command, **Design Decisions**, and **If I Had More Time** (2–4 items: DOCX, bounded async, result cache, FastAPI).

## Do not build

Frontend, auth, database, deployment, vector DB, custom scoring math beyond the table above.
