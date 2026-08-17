# AI-Powered E2E Testing Platform

An autonomous, AI-driven end-to-end testing platform built on **LangChain +
LangGraph + LangSmith + Python + Playwright + FastAPI + PostgreSQL + Vector DB
+ Docker + GitHub Actions**.

Give it a URL (or a spec), and it discovers the application, models it,
generates and prioritizes a test suite, executes the tests in a real browser,
classifies any failures, attempts controlled self-healing (with human
approval), retests, and reports — with a deterministic fallback for every AI
step so it keeps working even when the LLM is rate-limited or down.

[![CI](https://github.com/pradhansuman/ai-e2e-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/pradhansuman/ai-e2e-platform/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Table of contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Choosing an LLM provider](#choosing-an-llm-provider)
- [Running the tests](#running-the-tests)
- [Security](#security)
- [Deployment (Docker)](#deployment-docker)
- [Database migrations](#database-migrations)
- [Modification guide](#modification-guide)
- [Status](#status)
- [License](#license)

---

## What it does

- **Application discovery** — crawls the app and builds an *Application
  Knowledge Model* (pages, forms, inputs, buttons, workflows, auth, risk
  areas).
- **Requirements analysis** — turns user stories into testable business rules
  and flags missing/ambiguous/contradictory requirements.
- **Application understanding** — distills the app model into three parallel
  artifacts: testable **requirements**, **risks**, and **user journeys**.
- **AI test generation** — writes a comprehensive suite (happy paths,
  negative, boundary, validation, auth, security, regression, …).
- **Test intelligence** — measures coverage against risks/journeys and flags
  uncovered areas and weak tests.
- **Risk-based prioritization** — scores tests P0–P3.
- **Browser execution** — drives Chromium/Firefox/WebKit via Playwright through
  an **allow-listed** set of actions (the LLM can never inject arbitrary JS).
- **Evidence capture** — screenshots, console/network logs, traces, videos.
- **Failure intelligence** — classifies every failure into a 10-category
  taxonomy (`product_defect`, `automation_defect`, `environment`, `test_data`,
  `timing`, `network`, `dependency`, `authentication`, `configuration`,
  `flaky`, `unknown`) with confidence + evidence + a recommended fix.
- **Self-healing** — repairs broken locators and gates every change behind
  **human approval**.
- **Retry + flakiness detection** — retry budgets and pass/fail-sequence
  tracking.
- **Persistence + reporting** — durable run/results/failure history (SQLite in
  dev, PostgreSQL in prod) and a dashboard.
- **REST API + RBAC** — FastAPI with JWT roles (`admin` / `engineer` /
  `viewer`).
- **Async worker queue** — non-blocking `POST /runs`; poll `GET /runs/{id}`.
- **Observability** — optional LangSmith tracing + an evaluation harness.
- **Learn/improve loop** — persists healed selectors, failure patterns, and
  pass/fail outcomes so every run improves the next.

## How it works

The pipeline follows this flowchart:

```
APPLICATION → UNDERSTANDING → APPLICATION MODEL
            → [ Requirements | Risks | User Journeys ]
            → TEST DESIGN → TEST INTELLIGENCE → RISK-BASED SELECT
            → PLAYWRIGHT → EXECUTE → EVIDENCE
            → AI DIAGNOSIS ── PRODUCT BUG ──→ REPORT
                         └─ TEST BUG ──→ HEAL → RETEST
            → VALIDATE → LANGSMITH → LEARN/IMPROVE → NEXT RUN
```

Implemented as a **15-node LangGraph state machine** (implementation node names
in parentheses):

```
ingest (APPLICATION)
  → discover (UNDERSTANDING → APPLICATION MODEL)
  → analyze_requirements (Requirements | Risks | User Journeys)
  → generate_tests (TEST DESIGN)
  → test_intelligence (TEST INTELLIGENCE)
  → prioritize (RISK-BASED SELECT)
  → execute (PLAYWRIGHT → EXECUTE) → observe (EVIDENCE)
        │
        └─(failed)─→ analyze_failure (AI DIAGNOSIS)
                       ├─ product_defect ──→ report
                       └─ automation_defect ──→ diagnose → repair (HEAL)
                                                 → [human approval] → retest → execute (loop)
        └─(passed)─→ validate
                       → report → learn (LANGSMITH + LEARN/IMPROVE) → END
```

Every AI step has a **deterministic fallback**, so the platform never hard-fails
on a free-tier LLM:

| Step | LLM path | Fallback |
|---|---|---|
| Discovery | `discover_application_model` | raw crawl data |
| Understanding | `understand_application` | `fallback_understand` |
| Test generation | `generate_tests` | `fallback_generate_tests` (smoke/form/action) |
| Coverage | `analyze_test_coverage` | `fallback_coverage` |
| Failure analysis | `analyze_failure_evidence` | `heuristic_classify` |
| Self-healing | `propose_healing` | `heuristic_heal` |

## Repository layout

```
ai-e2e-platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # pydantic-settings (all secrets)
│   │   ├── db.py                # async SQLAlchemy engine/session
│   │   ├── security.py          # masking, RBAC, prompt-injection guard, audit
│   │   ├── schemas.py           # Pydantic structured-output contracts
│   │   ├── llm.py               # model factory + LangSmith + multi-provider failover
│   │   ├── cli.py               # `python -m app.cli run`
│   │   ├── api/                 # FastAPI routes (runs, apps, dashboard)
│   │   ├── agents/              # discovery, understanding, requirements,
│   │   │                        #   generator, intelligence, prioritizer,
│   │   │                        #   analyzer, healer, flakiness
│   │   ├── graph/               # LangGraph state + nodes + workflow
│   │   ├── executor/            # Playwright executor + allow-listed actions
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── services/            # persistence, worker queue, vector store
│   │   └── evaluation/          # AI quality scoring + LangSmith eval
│   ├── alembic/                 # database migrations
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                    # dashboard (HTML/CSS/JS, no build step)
├── database/schema.sql          # reference Postgres schema
├── prompts/                     # versioned prompt templates
├── tests/                       # pytest unit tests
├── docker/backend.Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml     # lint → unit → e2e smoke → LangSmith eval
└── docs/architecture.md
```

## Requirements

- **Python 3.12+** (3.12–3.13 recommended; 3.14 is too new for some wheels)
- Playwright browsers (installed in a step below)
- Optional: Docker (for Postgres + the containerised stack)
- An LLM API key (any of OpenAI / Anthropic / OpenRouter / Google Gemini /
  Groq — free tiers work)

## Installation

### Option A — Local (recommended for development)

```bash
# 1. Clone
git clone https://github.com/pradhansuman/ai-e2e-platform.git
cd ai-e2e-platform

# 2. Create a virtualenv
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Install a browser
python -m playwright install chromium      # Linux: add --with-deps

# 5. Configure
cp .env.example .env                 # then edit .env (see "Configuration")

# 6. Run the API
cd backend
uvicorn app.main:app --reload --port 8000
```

Open the interactive docs at http://localhost:8000/docs and the dashboard at
`frontend/index.html`.

### Option B — Docker

```bash
cp .env.example .env                 # add your LLM key
docker compose up --build
# API:        http://localhost:8000/docs
```

## Quick start

### Run a test run (CLI)

```bash
cd backend
python -m app.cli run --objective "smoke test" --url https://example.com
```

Limit and prioritise:

```bash
python -m app.cli run --objective "checkout flow" \
  --url https://example.com --priority P0 --limit 5
```

### Watch it in a visible browser (headed + slow motion)

```bash
BROWSER_HEADLESS=false BROWSER_SLOW_MO=700 \
  python -m app.cli run --objective "smoke" --url https://example.com
```

### Run a test run (REST API)

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"objective":"smoke test","application":{"url":"https://example.com","source":"url"}}'
# → {"run_id": "...", "status": "queued"}

curl http://localhost:8000/api/v1/runs/<run_id>
# → {"status": "running" | "passed" | "failed", ...}
```

`POST /runs` is non-blocking; the run is drained by a background worker.

### Mint an API token (when auth is enabled)

```bash
python -m app.cli token --role engineer
# pass as: Authorization: Bearer <token>
```

## Configuration

All settings are env-driven (`.env`, see `.env.example`). The important ones:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `auto` | `auto` / `openai` / `openrouter` / `anthropic` / `google` / `groq` |
| `LLM_MODEL` | `gpt-4o` | model used when provider is `openai` |
| `OPENAI_API_KEY` | — | OpenAI key |
| `ANTHROPIC_API_KEY` | — | Anthropic key |
| `OPENROUTER_API_KEY` | — | OpenRouter key (free models available) |
| `OPENROUTER_MODEL` | `google/gemma-4-26b-a4b-it:free` | primary OpenRouter model |
| `OPENROUTER_FALLBACK_MODELS` | `qwen/…,meta-llama/…` | extra OpenRouter `:free` models to fail over to |
| `GEMINI_API_KEY` | — | Google Gemini key |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model |
| `GROQ_API_KEY` | — | Groq key (fast free llama models) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model |
| `LANGSMITH_API_KEY` | — | LangSmith tracing (optional) |
| `LANGSMITH_TRACING` | `true` | enable tracing |
| `DATABASE_URL` | Postgres URL | dev tip: `sqlite+aiosqlite:///./e2e.db` |
| `BROWSER_HEADLESS` | `true` | `false` = visible browser |
| `BROWSER_SLOW_MO` | `0` | ms delay between actions (watchable runs) |
| `BROWSER_TYPE` | `chromium` | `chromium` / `firefox` / `webkit` |
| `MAX_RETRIES` / `MAX_HEAL_RETRIES` | `3` / `2` | loop-safety bounds |
| `HUMAN_APPROVAL_REQUIRED` | `true` | gate self-healing behind approval |
| `WORKER_CONCURRENCY` | `1` | background workers draining the run queue |
| `SECRET_KEY` | dev default | **≥32 bytes** for production JWT signing |
| `ALLOW_UNAUTHENTICATED` | `true` | `false` enforces JWT RBAC |

## Choosing an LLM provider

The platform **automatically fails over** across every provider you configure.
When one returns `429` (quota exhausted), it is marked exhausted and the next
provider is tried — so the LLM-powered path keeps working as long as *any*
configured provider still has quota. Just add the keys you have; no provider
switching is required.

**Free tiers (no payment required):**

```bash
# Google Gemini (free tier ~20 req/day)
GEMINI_API_KEY=***

# Groq (fast llama models; generous free tier)
GROQ_API_KEY=***

# OpenRouter (many free models; ~50 free req/day)
OPENROUTER_API_KEY=***
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free
OPENROUTER_FALLBACK_MODELS=qwen/qwen-2.5-72b-instruct:free,meta-llama/llama-3.3-70b-instruct:free
```

With `LLM_PROVIDER=auto` (default) the failover order is
**Gemini → Groq → OpenRouter**. Pin a single provider with
`LLM_PROVIDER=google|groq|openrouter|openai|anthropic` instead.

**Paid:** add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` — paid providers are
tried last.

> Free models are rate-limited and occasionally return malformed JSON. The
> structured-output layer + deterministic fallbacks absorb that, and the
> multi-provider failover keeps the LLM path alive far longer than any single
> free tier. When every provider is exhausted, runs degrade to deterministic
> fallbacks (still functional).

## Running the tests

```bash
# from the repo root (conftest.py puts backend/ on sys.path)
python -m pytest tests -q
```

CI runs the same suite on every push (Python 3.12, ubuntu-latest).

## Security

- **Allow-listed browser verbs only** — the LLM cannot run arbitrary
  JavaScript or shell.
- **Prompt-injection guard** — untrusted page content is sanitised before it
  reaches the LLM.
- **Secret/PII masking** — sensitive fields are masked in logs and stored data.
- **JWT RBAC** — `admin` / `engineer` / `viewer` roles; enforced when
  `ALLOW_UNAUTHENTICATED=false`.
- **Human-approval gate** — self-healing mutations are blocked pending approval
  (`HUMAN_APPROVAL_REQUIRED=true`).

## Deployment (Docker)

`docker compose up --build` starts the API + Postgres + Qdrant. See
`docker-compose.yml` and `docker/backend.Dockerfile`.

## Database migrations

Migrations live in `backend/alembic/`. In dev the schema is created
automatically; in production the server runs `alembic upgrade head` on
startup.

```bash
cd backend
alembic upgrade head          # apply
alembic revision --autogenerate -m "message"   # create a new migration
```

## Modification guide

| To change… | Edit… |
|---|---|
| LLM model / temperature | `backend/app/config.py` or `.env` |
| LLM failover providers | `backend/app/llm.py` (`get_llm_candidates`) + `.env` keys |
| Prompt wording / behavior | `prompts/*.md` + the matching `ChatPromptTemplate` in `backend/app/agents/*.py` |
| Allowed browser actions | `backend/app/executor/actions.py` |
| Priority scoring weights | `backend/app/agents/prioritizer.py` |
| Failure taxonomy | `backend/app/schemas.py` |
| RBAC roles per tool | `backend/app/security.py` |
| DB schema | `backend/app/models/orm.py` + Alembic migration |
| Dashboard | `frontend/index.html` + `frontend/app.js` |
| CI stages / secrets | `.github/workflows/ci.yml` |

## Status

Verified end-to-end: discovery → generation → execution → failure
classification → self-healing → re-execution (live against saucedemo.com,
demoqa.com, and a local app; **70 unit tests passing**, CI green).

- A deliberately failing assertion was classified `product_defect`.
- A broken locator was classified `automation_defect`, healed to a stable
  selector, and re-run to green.
- JWT RBAC, durable persistence, the async worker queue, and Alembic
  migrations are all implemented.

## License

[MIT](LICENSE)
