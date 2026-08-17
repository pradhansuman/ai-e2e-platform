# AI-Powered E2E Testing Platform

An autonomous, AI-driven end-to-end testing platform built on **LangChain +
LangGraph + LangSmith + Python + Playwright + FastAPI + PostgreSQL + Vector DB
+ Docker + GitHub Actions**.

It is a real engineering platform — not a chatbot that emits Playwright code.
It discovers an application, models it, generates and prioritizes tests,
executes them through a validated tool-call boundary, diagnoses failures,
attempts controlled self-healing (with human approval), retests, and evaluates
its own output quality.

---

## Pipeline (Definition of Done)

```
Give URL → Discover → Understand → Model → Generate → Prioritize → Execute →
Capture Evidence → Detect Failure → Diagnose → Controlled Healing → Retest →
Validate → Report → Trace & Evaluate
```

---

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
│   │   ├── llm.py               # model factory + LangSmith bootstrap
│   │   ├── cli.py               # `python -m app.cli run`
│   │   ├── api/                 # FastAPI routes (runs, apps, dashboard)
│   │   ├── agents/              # discovery, requirements, generator,
│   │   │                        #   prioritizer, analyzer, healer, flakiness
│   │   ├── graph/               # LangGraph state + nodes + workflow
│   │   ├── tools/               # reusable LangChain tools
│   │   ├── executor/            # Playwright executor + allow-listed actions
│   │   ├── models/              # SQLAlchemy ORM (15 entities)
│   │   ├── services/            # storage + vector-store facade
│   │   └── evaluation/          # AI quality scoring + LangSmith eval
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

---

## Quickstart

### Option A — Docker (recommended)

```bash
cp .env.example .env          # add your OPENAI_API_KEY / LANGSMITH_API_KEY
docker compose up --build
# API:        http://localhost:8000/docs
# Dashboard:  open frontend/index.html (or serve it) — points at /api/v1
```

### Option B — Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python -m playwright install --with-deps chromium
cp .env.example .env
cd backend && uvicorn app.main:app --reload --port 8000
```

### Run a test run

```bash
# REST
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"objective":"smoke test","application":{"url":"https://example.com","source":"url"}}'

# CLI
cd backend && python -m app.cli run --objective "smoke" --url https://example.com
```

### Run the unit tests

```bash
cd backend && pytest ../../tests -q
```

---

## Configuration

All settings are env-driven (see `.env.example`). The important ones:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `auto` / `openai` / `openrouter` / `anthropic` |
| `OPENROUTER_API_KEY` | OpenRouter key (works with free-tier models) |
| `OPENROUTER_MODEL` | default free model, e.g. `google/gemma-4-31b-it:free` |
| `OPENAI_API_KEY` | OpenAI access (used when provider resolves to `openai`) |
| `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | tracing + evaluation |
| `DATABASE_URL` | Postgres (asyncpg) |
| `VECTOR_STORE_URL` | Qdrant endpoint |
| `HUMAN_APPROVAL_REQUIRED` | gate self-healing behind approval |
| `MAX_RETRIES` / `MAX_HEAL_RETRIES` | loop-safety bounds |
| `ALLOW_UNAUTHENTICATED` | dev mode (disable RBAC); set `false` in prod |

### Using a free OpenRouter key

Set in `.env`:

```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

Any OpenAI-compatible free model works. **For the platform's structured
(function-calling) outputs, use `google/gemma-4-31b-it:free`** — verified
here. `nvidia/nemotron-3-super-120b-a12b:free` handles plain chat but not
reliably tool calling. If a model id errors with "unavailable for free", the
paid slug usually drops the `:free` suffix.

---

## Modification guide

| To change… | Edit… |
|---|---|
| LLM model / temperature | `backend/app/config.py` (`llm_model`) or `.env` |
| Prompt wording / behavior | `prompts/*.md` + the matching `ChatPromptTemplate` in `backend/app/agents/*.py` |
| Allowed browser actions | `backend/app/executor/actions.py` (add to `ACTIONS`) |
| Priority scoring weights | `backend/app/agents/prioritizer.py` (`DEFAULT_WEIGHTS`) |
| Failure taxonomy | `backend/app/schemas.py` (`RootCause.classification`) |
| RBAC roles per tool | `backend/app/security.py` (`TOOL_PERMISSIONS`) |
| DB schema | `backend/app/models/orm.py` + `database/schema.sql` (+ Alembic migration) |
| Dashboard tiles | `frontend/index.html` + `frontend/app.js` |
| CI stages / secrets | `.github/workflows/ci.yml` |

---

## Quality coverage

- **Correctness**: structured outputs (Pydantic) with validation; deterministic
  prioritization; allow-listed browser verbs.
- **Safety**: prompt-injection guard, secret/PII masking, RBAC, audit logging,
  credential isolation, human-approval gate for mutations.
- **Observability**: LangSmith tracing across agents/LLM/tools/graph nodes;
  token + latency capture; `ai_traces` table.
- **Testability**: pure routing/prioritization/flakiness functions with unit
  tests; graph nodes are isolated and independently testable.
- **Reliability**: retry/heal budgets, graceful degradation (LLM/DB/browser
  failures are caught and logged, never crash the run).
- **UX states**: dashboard handles loading, empty (no failures), and
  offline/error states; responsive mobile/desktop layout.

## Status (verified)

The full pipeline has been run **live** against `https://www.saucedemo.com`:

- Discovery (crawl) → 3 deterministic fallback tests → prioritization →
  Playwright execution → **all passed** (pass rate 1.0).
- A deliberately failing test was detected, classified `product_defect`, and
  the root cause reported.
- A broken locator was detected → classified `automation_defect` → healed to a
  stable selector → re-executed → **passed** (self-healing loop closed).

Every AI step has a deterministic fallback, so the platform keeps working even
when the (free-tier) LLM is rate-limited or returns malformed output:

| Step | LLM path | Fallback |
|---|---|---|
| Discovery | `discover_application_model` | raw crawl data |
| Test generation | `generate_tests` | `fallback_generate_tests` (smoke/form/action) |
| Failure analysis | `analyze_failure_evidence` | `heuristic_classify` |
| Self-healing | `propose_healing` | `heuristic_heal` |

JWT RBAC, durable persistence, a background worker queue (non-blocking
`POST /runs`; status via `GET /runs/{id}`), and Alembic migrations are all
implemented (SQLite for dev, PostgreSQL in production). Mint API tokens with
`python -m app.cli token --role engineer` and pass them as
`Authorization: Bearer <token>`; set `ALLOW_UNAUTHENTICATED=false` + a
`SECRET_KEY` (>=32 bytes) to enforce auth.
