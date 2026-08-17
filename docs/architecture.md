# Architecture

This document describes the design of the AI-Powered E2E Testing Platform.

## 1. The pipeline

```
Application (URL / repo / spec / requirements)
        │
        ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│     INGEST    │ → │    DISCOVER   │ → │   ANALYZE     │
│ URL/Repo/Spec │   │ Pages/APIs    │   │ Requirements  │
└───────────────┘   └───────────────┘   └───────────────┘
                                                 │
                                                 ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   PRIORITIZE  │ ← │  GENERATE     │   │  TEST DESIGN  │
│  Risk-based   │   │  AI test gen  │   │ (structured)  │
└───────┬───────┘   └───────────────┘   └───────────────┘
        │
        ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    EXECUTE    │ → │    OBSERVE    │ → │ ANALYZE FAIL  │
│   Playwright  │   │ Logs/DOM/Shot │   │  Pass/Fail    │
└───────┬───────┘   └───────────────┘   └───────┬───────┘
        │                                        │
        │                              ┌─────────┴─────────┐
        │                              │                   │
        │                           FAILED              PASSED
        │                              │                   │
        │                        ┌─────▼─────┐       ┌─────▼─────┐
        │                        │ DIAGNOSE  │       │  VALIDATE │
        │                        │ root cause│       │ evidence  │
        │                        └─────┬─────┘       └─────┬─────┘
        │                              │                   │
        │                     ┌────────▼────────┐          │
        │                     │  REPAIR (heal)  │          │
        │                     │  + human gate   │          │
        │                     └────────┬────────┘          │
        │                              │                   │
        └──────────────────────────────┴────► RETEST       │
                                             │             │
                                             ▼             ▼
                                          ┌─────────────────┐
                                          │     REPORT      │
                                          └─────────────────┘
```

## 2. LangGraph state machine

`backend/app/graph/state.py` defines `TestState` (a TypedDict) that carries all
data between nodes. `backend/app/graph/workflow.py` assembles a `StateGraph`
with the nodes and conditional edges shown above.

**Loop safety** is enforced by two counters in state:
- `retry_count` (capped by `MAX_RETRIES`) — bounds retest loops.
- `heal_count` (capped by `MAX_HEAL_RETRIES`) — bounds self-healing attempts.

Conditional edges route on `PASS / FAIL / RETRY / HUMAN_APPROVAL / BLOCKED`
exactly as the spec requires.

**Human approval** is modeled as a state flag: when a healing suggestion is
produced and `HUMAN_APPROVAL_REQUIRED=true`, the graph ends with
`status="awaiting_approval"`. The persisted state is resumed via
`build_approval_workflow()` (entry node `approve`) after a human sets
`approval_decision`. This is the LangGraph idiom for external interrupts.

## 3. Validated tool-call boundary

The LLM never drives the browser directly. The chain is:

```
LLM → Structured TestPlan (Pydantic TestCase) → Validated tool call → Playwright → Evidence
```

`backend/app/executor/actions.py` is the **only** allow-list of browser verbs
(`goto`, `click`, `fill`, `assert_text`, …). Anything else is rejected by the
executor, so a model cannot emit arbitrary JavaScript or shell commands.

## 4. AI evaluation

Executing successfully does **not** mean the AI was correct. The platform
computes a seven-dimension quality score
(`backend/app/evaluation/__init__.py`):

- test quality, requirement coverage, risk coverage, execution accuracy,
  failure-diagnosis accuracy, self-healing accuracy, hallucination rate.

LangSmith datasets (section 13) measure the same dimensions across runs so the
AI system's own regressions are tracked.

## 5. Security boundaries

- Secrets are centralized in `config.py`; never hard-coded.
- `security.mask_secrets` / `redact_for_llm` strip PII/secrets before any LLM call.
- `sanitize_untrusted_content` quarantines prompt-injection patterns found in
  application content (application content is always treated as **data**).
- `TOOL_PERMISSIONS` enforces RBAC on tool execution (viewer/engineer/admin).
- `audit_event` logs all mutating operations.

## 6. Data model

`database/schema.sql` and `backend/app/models/orm.py` define 15 entities:
applications, pages, apis, requirements, test_cases, test_runs, test_results,
failures, healing_events, flakiness_records, test_evaluations, ai_traces,
audit_logs — with relationships and indexes for the dashboard and history tools.
