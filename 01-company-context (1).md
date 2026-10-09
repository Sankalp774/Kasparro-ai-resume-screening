# Hiring context for the SDE Intern assignment

Use this file as company context when building the resume screener. Do not invent a company name, product, or stack beyond what is written here.

## What is known

The issuer is unnamed in the assignment document (`SDE Intern Coding Assignment — AI Resume Screening & Ranking System`).

They are hiring an **SDE Intern with an AI background**. The role they are screening *for* is an internship that needs:

- Strong Python fundamentals
- Practical exposure to AI / agentic systems
- Backend engineering, not UI polish

They describe the work as “our minimum Python/AI requirements,” so this screener is for their own intern pipeline, not a generic job board.

## Core philosophy (from their job description, not the assignment PDF)

Repeated emphasis: **LLM as witness, code as judge.**

- The LLM may read a resume and testify: extracted fields, project summary, evidence quotes, quality opinion.
- Python code makes the binding decision: eligibility, score caps, penalties, rank, and what happens when the witness fails.
- A model answer must not override a failed hard filter. A missing or broken model call must not change eligibility.
- They may deliberately introduce an AI failure (timeout, bad JSON, empty completion, rate limit, one poisoned resume). The batch must continue. That resume keeps its deterministic result and records the witness failure.
- GitHub enrichment is the same pattern: the API is a witness, the scorer is the judge, and a 403/404 does not fail the run.

This is the interesting part of the assignment. They are testing whether the pipeline treats the model as evidence, not as the authority.

Engineering judgment over presentation.

- A simple, correct, explainable backend beats an over-engineered app.
- Hard filters must reject irrelevant but well-written resumes.
- Scores must be evidence-backed and explainable to another engineer.
- One bad resume, one GitHub failure, or one LLM failure must not kill the batch.
- They will read the README sections **Design Decisions** and **If I Had More Time**.

## Stack signals in the brief (their world, not a required product stack)

Reward these when they appear on a candidate resume. Do not require all of them.

- Python, FastAPI, async, PostgreSQL, Redis
- LangChain, LangGraph, Google ADK, LlamaIndex
- RAG, embeddings, vector search, tool-calling agents, multi-agent workflows, evaluation pipelines
- GCP, Docker, deployment
- React / Next.js only as supporting full-stack signal inside an end-to-end system
- Testing, architecture, caching, queues, observability, concurrency, failure handling

Java, JavaScript, React, and Next.js are acceptable extras. They are not enough alone.

## Evaluation of *your* submission (separate from the 100-point resume score)

| Area | Weight |
| --- | --- |
| Ingestion + hard filtering correctness | 25% |
| Ranking and project-quality logic | 25% |
| AI / LLM implementation | 15% |
| Code quality and architecture | 15% |
| GitHub enrichment | 10% |
| Reliability and tests | 5% |
| README and usability | 5% |

## Explicit non-goals

No frontend, auth, database, deployment, or vector database. No visual design. 2–3 hour time box. Hand off something another engineer can run.

## Not this company

Career OS is the candidate’s own project name. It is not the hiring company, and no product spec for Career OS is in this packet. Do not blend Career OS into the screener unless the user later provides that spec.
