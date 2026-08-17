# Benchmark

A reproducible harness that measures the **ai-e2e-platform** QA pipeline against
six ground-truth applications and publishes nine headline metrics.

## Run

```bash
# from the repo root (with the venv active)
PYTHONPATH=backend .venv/bin/python -m benchmark          # text report
PYTHONPATH=backend .venv/bin/python -m benchmark --markdown   # publishable markdown
PYTHONPATH=backend .venv/bin/python -m benchmark --json       # machine-readable
PYTHONPATH=backend .venv/bin/python -m benchmark --compare    # control group (Human/Playwright/LLM/platform)
PYTHONPATH=backend .venv/bin/python -m benchmark --compare --markdown
PYTHONPATH=backend .venv/bin/python -m benchmark --sweep        # sensitivity sweep of the AI-QE score
PYTHONPATH=backend .venv/bin/python -m benchmark --seed 7 --tests 600 --gen-accuracy 0.90 --assertion-quality 0.85 --heal heuristic
```

## What it measures

| Metric | Definition |
|---|---|
| Requirement coverage | ground-truth requirements covered by generated tests ÷ total |
| Test-generation accuracy | generated tests with a correct, resolvable locator ÷ total |
| Defect detection (mutation score) | injected mutations the generated tests *caught* ÷ total mutations (fault-detection power) |
| Root-cause accuracy | failures correctly classified (`product_defect` vs `automation_defect`) ÷ deterministic failures |
| Self-healing success | heals that recovered the intended element ÷ heal attempts |
| False-healing rate | heals that pointed at the *wrong* element ÷ heal attempts |
| Flaky detection accuracy | flaky tests caught by history scoring ÷ injected flaky tests |
| Human intervention | approval gates triggered ÷ total tests |
| Avg diagnosis time | mean time from failure to classification |
| Cost per test | estimated LLM token cost ÷ tests |

## AI-QE Score

A single 0-100 composite of the metrics, business-weighted (not a blind average)
in `quality.py`:

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

This is the single number tracked over time as the platform evolves.

## Control group (baseline)

`--compare` runs the four approaches side by side on the **same** benchmark:

| Approach | Row source |
|---|---|
| Human-written automation | parameterized estimate |
| Standard Playwright | parameterized estimate |
| LLM-generated Playwright (one-shot) | parameterized estimate |
| AI E2E Platform | **measured** (real deterministic agents) |

Human / Playwright / LLM rows are **estimates** (directional priors, not measured
ground truth) — see `approaches.py`. The platform row is measured. The rigorous
next step is to *measure* all four with real suites.

## Target applications (ground truth)

Six real, widely-used test apps across six domains, with hand-written
requirements, workflows, and DOM elements (see `apps.py`):

| App | Domain |
|---|---|
| Swag Labs | e-commerce |
| ParaBank | banking |
| DemoQA | forms / widgets |
| The Internet | UI patterns |
| OrangeHRM (demo) | HR / admin |
| Automation Exercise | e-commerce |

## Mutation model

Ten injected mutation classes with known ground-truth labels (see
`engine.py::MUTATIONS` and the exported `data/defects.json`):

**Product defects — must be detected (`product_defect`), never healed:**
1. Value change (`expected text X but found Y`)
2. Validation removed
3. API response change
4. Business-rule change
5. Calculation change

**Automation defects — must be self-healed (`automation_defect`):**
6. Broken locator (selector typo)
7. Requirement change (element removed/renamed)

**Other:**
8. Auth change → `authentication` (security regression)
9. Timing issue → `timing`
10. Flaky test → detected by history scoring, not healed

The **defect-detection (mutation) score** = injected defects the generated tests
*caught* (failed on) ÷ total injected defects — the platform's **fault-detection
power**: whether its tests actually detect the mutation at all, not whether a
failure was later diagnosed. Diagnosis accuracy is measured separately as
root-cause accuracy.

## Mode

This module ships in **deterministic `sim` mode** (seeded, offline). It synthesizes
failure evidence shaped like the executor's output, then calls the **real**
deterministic agents — `heuristic_classify`, `heuristic_heal`,
`detect_flakiness` — so the diagnosis / healing / flakiness numbers reflect the
actual code paths. LLM test generation is simulated with a parameterized accuracy.

Healing path is selectable via `heal_mode`:
- `heuristic` (default) — deterministic fallback, no LLM needed.
- `llm` — uses `propose_healing` (requires an LLM key with quota). This is the
  path to measure the *true* self-healing score once quota is available.

A `live` mode (drive the real LangGraph pipeline + browser against the six apps)
is the intended next step once an LLM key with quota is available.

## Structure

| File | Purpose |
|---|---|
| `apps.py` | 6 apps + ground truth (requirements, workflows, elements) |
| `engine.py` | simulation, mutation injection, real-agent measurement, metrics |
| `quality.py` | weighted AI-QE Score |
| `approaches.py` | control-group baseline (Human / Playwright / LLM / platform) |
| `report.py` | markdown + terminal rendering |
| `__main__.py` | CLI (`--seed`, `--tests`, `--gen-accuracy`, `--assertion-quality`, `--requirement-coverage`, `--heal`, `--json`, `--markdown`, `--compare`, `--sweep`) |
| `sweep.py` | sensitivity sweep of the AI-QE score over generator priors |
| `export_data.py` | dump ground truth to the canonical public layout (`data/*.json`) |
| `data/` | exported ground truth: applications, requirements, workflows, defects, metrics |

## Public benchmark repo (planned)

For reproducibility and credibility, the benchmark is intended to be published as
its own repo with this layout (see `docs/roadmap.md` Phase 10):

```
ai-e2e-benchmark/
├── applications/        # ecommerce/ banking/ hr/ booking/ crm/ saas/
├── defects/             # injected mutation corpus + ground truth
├── requirements/        # ground-truth requirements per app
├── workflows/           # user journeys per app
├── expected-results/    # expected outcomes per workflow
└── metrics/             # score definitions + historical results
```
