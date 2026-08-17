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
| 3 | Control-group baseline: Human / Playwright / LLM / platform + AI-QE Score | ✅ (estimates for A–C, measured platform; LLM path measured via Mistral) |
| 4 | Mutation-testing benchmark (fault-detection power = AI E2E Mutation Score) | ✅ full 10-class corpus + mutation score |
| 5 | Change-aware regression intelligence (git → affected tests → risk → minimal set) | ✅ `app/intelligence/change_analysis.py` |
| 6 | Application knowledge graph (requirement ↔ API ↔ component ↔ journey ↔ test ↔ defect ↔ incident) | ✅ `app/intelligence/quality_graph.py` |
| 7 | Production → test intelligence (logs/traffic → risk → generate) | ✅ `app/intelligence/production_intelligence.py` |
| 8 | Continuous autonomous QE loop (observe → risk → select → execute → diagnose → heal → learn) | 🔶 decision layer done (`continuous_qe.py`); execution delegates to the LangGraph pipeline |
| 9 | Enterprise platform (multi-tenancy, RBAC, SSO, audit, limits, integrations) | 🔶 RBAC + tenancy + audit scaffold (`enterprise.py`); SSO/integrations pending |
| 10 | Public benchmark + research (reproducible `ai-e2e-benchmark` repo) | ✅ published at github.com/pradhansuman/ai-e2e-benchmark |
| 11 | Product / SaaS | ⬜ go-to-market (not code) |

## The critical next move

**Do not jump to Phase 5.** Make Phase 2 + Phase 3 rigorous first:

1. **Replace estimates with measurements** — the Human/Playwright/LLM rows are
   currently parameterized priors. Rigor means running *actual* human-written,
   Playwright, and one-shot-LLM suites against the same six apps and mutations.
2. **Wire the LLM path** — the benchmark's self-healing/false-healing numbers
   currently reflect the *deterministic fallback* heal (58.7% false-heal). The
   LLM heal must be measured to get the true self-healing score.
3. **Expand the mutation corpus** — from 4 mutation classes to the full set
   (value change, validation removal, locator break, API response change,
   auth change, business-rule change, calculation change, timing issue).
4. **Publish the benchmark repo** — restructure into the public
   `ai-e2e-benchmark/` layout (applications / defects / requirements /
   workflows / expected-results / metrics) so results are reproducible.

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
