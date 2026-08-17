# Roadmap — Autonomous Quality Engineering Platform

> Positioning: an **AI Quality Engineering Agent** that understands application
> risk, designs tests, executes them, diagnoses failures, safely heals
> automation, and continuously evaluates its own testing intelligence.
>
> The differentiator is **not** LangChain/LangGraph/Playwright — those are
> implementation details. The differentiator is **closed-loop autonomous quality
> engineering with measurable AI reliability.**

## Phases

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Build the platform (discovery → generation → execution → diagnosis → healing → learning) | ✅ |
| 2 | Benchmark 6 apps / 500+ tests / 4 mutation classes / 9 metrics | ✅ (deterministic baseline) |
| 3 | Control-group baseline: Human / Playwright / LLM / platform + AI-QE Score | ✅ standard evaluator (`benchmark-result.json` contract) + AI-QE Score; platform & LLM heal **measured**, LLM one-shot **estimated**, Human/Playwright **pending** (not fabricated) |
| 4 | Mutation-testing benchmark (fault-detection power = AI E2E Mutation Score) | ✅ full 10-class corpus + mutation score |
| 5 | Change-aware regression intelligence (git → affected tests → risk → minimal set) | ✅ `app/intelligence/change_analysis.py` |
| 6 | Application knowledge graph (requirement ↔ API ↔ component ↔ journey ↔ test ↔ defect ↔ incident) | ✅ `app/intelligence/quality_graph.py` |
| 7 | Production → test intelligence (logs/traffic → risk → generate) | ✅ `app/intelligence/production_intelligence.py` |
| 8 | Continuous autonomous QE loop (observe → risk → select → execute → diagnose → heal → learn) | ✅ decision layer (`continuous_qe.py`) + runnable scheduler (`scheduler.py`) |
| 9 | Enterprise platform (multi-tenancy, RBAC, SSO, audit, limits, integrations) | ✅ architecture + adapters (`enterprise.py`, `sso.py`, `cost_controls.py`, `usage_limits.py`, `integrations.py`, `secrets.py`); live integration ⏳ pending env credentials |
| 10 | Public benchmark + research (reproducible `ai-e2e-benchmark` repo) | ✅ published at github.com/pradhansuman/ai-e2e-benchmark |
| 11 | Product / SaaS | ✅ positioning + GTM in `docs/product.md` (go-to-market is not code) |

## The critical next move

Rigor is now achieved by **separating measured / estimated / pending** — never
fabricating a control-group number:

1. **Standard evaluator** — `benchmark/contract.py` (platform repo) and
   `benchmark/` (ai-e2e-benchmark) validate + score any `benchmark-result.json`,
   so the scoring engine is agnostic to who generated the tests.
2. **Independent Playwright baseline** — separate repo
   `ai-e2e-playwright-baseline` (real Playwright, no AI). **Pending run.**
3. **Human study protocol** — `ai-e2e-benchmark/baselines/human/PROTOCOL.md`.
   **Pending recruitment** of 3–5 testers.
4. **Healing reported separately** — deterministic fallback (47.3% success /
   52.7% false-heal) vs. Mistral LLM (83.3% success / 0% false-heal), never
   combined.
5. **Confidence intervals** — `python -m benchmark --repeat N` reports mean ±
   stdev per metric (deterministic engine has residual seed variance).
6. **Enterprise = deployment validation** — adapters are implemented and unit
   tested; live SSO/Jira/GitHub/Slack/CI-CD/K8s are validated separately,
   pending environment credentials — not "missing functionality".

## AI-QE Score (the single number to track)

A weighted composite of the benchmark's metrics (see `benchmark/quality.py`):

| Dimension | Weight |
|---|---|
| Defect Detection (mutation score) | 20% |
| Requirement Coverage | 15% |
| Root Cause Accuracy | 15% |
| Test Quality | 15% |
| Self-Healing | 10% |
| Reliability (1 − false-healing) | 10% |
| Flaky Detection | 5% |
| Human Intervention (autonomy) | 5% |
| Cost Efficiency | 5% |

This is the number tracked over time as the platform evolves — not 20 unrelated
metrics.
