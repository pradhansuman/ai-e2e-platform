# Benchmark

A reproducible harness that measures the **ai-e2e-platform** QA pipeline against
six ground-truth applications and publishes nine headline metrics.

## Run

```bash
# from the repo root (with the venv active)
PYTHONPATH=backend .venv/bin/python -m benchmark          # text report
PYTHONPATH=backend .venv/bin/python -m benchmark --markdown   # publishable markdown
PYTHONPATH=backend .venv/bin/python -m benchmark --json       # machine-readable
PYTHONPATH=backend .venv/bin/python -m benchmark --seed 7 --tests 600 --gen-accuracy 0.90
```

## What it measures

| Metric | Definition |
|---|---|
| Requirement coverage | ground-truth requirements covered by generated tests ÷ total |
| Test-generation accuracy | generated tests with a correct, resolvable locator ÷ total |
| Root-cause accuracy | failures correctly classified (`product_defect` vs `automation_defect`) ÷ deterministic failures |
| Self-healing success | heals that recovered the intended element ÷ heal attempts |
| False-healing rate | heals that pointed at the *wrong* element ÷ heal attempts |
| Flaky detection accuracy | flaky tests caught by history scoring ÷ injected flaky tests |
| Human intervention | approval gates triggered ÷ total tests |
| Avg diagnosis time | mean time from failure to classification |
| Cost per test | estimated LLM token cost ÷ tests |

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

Four injected failure classes with known ground-truth labels:

1. **Real defects** — genuine product bugs (assertion mismatch) → expect `product_defect`.
2. **Broken locators** — a selector typo → expect `automation_defect` → self-heal to the right element.
3. **Flaky tests** — alternating pass/fail history → expect flaky detection (not healing).
4. **Requirement changes** — element removed/renamed → stale locator; healing must not silently change intent.

## Mode

This module ships in **deterministic `sim` mode** (seeded, offline). It synthesizes
failure evidence shaped like the executor's output, then calls the **real**
deterministic agents — `heuristic_classify`, `heuristic_heal`,
`detect_flakiness` — so the diagnosis / healing / flakiness numbers reflect the
actual code paths. LLM test generation is simulated with a parameterized accuracy.

A `live` mode (drive the real LangGraph pipeline + browser against the six apps)
is the intended next step once an LLM key with quota is available.

## Structure

| File | Purpose |
|---|---|
| `apps.py` | 6 apps + ground truth (requirements, workflows, elements) |
| `engine.py` | simulation, mutation injection, real-agent measurement, metrics |
| `report.py` | markdown + terminal rendering |
| `__main__.py` | CLI (`--seed`, `--tests`, `--gen-accuracy`, `--json`, `--markdown`) |
