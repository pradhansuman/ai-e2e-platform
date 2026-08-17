# AI E2E Platform — Benchmark Report

> Deterministic, seeded baseline (seed `42`). Diagnosis / self-healing / flaky-detection numbers are measured against the **real** deterministic agents; LLM generation is simulated. Re-run with `python -m benchmark`.

## Headline metrics

| Metric | Value |
|---|---|
| Requirement coverage | 83.3% |
| Test-generation accuracy | 87.5% |
| Defect detection (mutation score) | 90.6% |
| Root-cause accuracy | 91.5% |
| Self-healing success | 41.3% |
| False-healing rate | 58.7% |
| Flaky detection accuracy | 80.0% |
| Human intervention | 20.4% |
| Avg diagnosis time | 2.81 sec |
| Cost per test | 0.0012$ |
| **AI-QE Score** | **78.7/100** |

## AI-QE Score breakdown

| Dimension | Weight | Score (0-1) | Weighted |
|---|---|---|---|
| Defect Detection | 20% | 0.906 | 0.181 |
| Requirement Coverage | 15% | 0.833 | 0.125 |
| Root Cause Accuracy | 15% | 0.915 | 0.137 |
| Test Quality | 15% | 0.875 | 0.131 |
| Self-Healing | 10% | 0.413 | 0.041 |
| Reliability | 10% | 0.413 | 0.041 |
| Flaky Detection | 5% | 0.800 | 0.040 |
| Human Intervention | 5% | 0.796 | 0.040 |
| Cost Efficiency | 5% | 0.999 | 0.050 |

## Volume

- **6 applications** across 6 domains (e-commerce ×2, banking, forms/widgets, UI patterns, HR/admin)
- **54 workflows** (user journeys)
- **72 ground-truth requirements**
- **510 generated tests** (446 with correct locators)
- **248 failures** → 205 correctly classified, 104 self-healing attempts, 65 flaky tests

## Per-application

| App | Domain | Tests | Passed | Failed | Heals |
|---|---|---|---|---|---|
| Swag Labs | e-commerce | 85 | 40 | 45 | 17 |
| ParaBank | banking | 85 | 51 | 34 | 19 |
| DemoQA | forms / widgets | 85 | 43 | 42 | 19 |
| The Internet | UI patterns | 85 | 50 | 35 | 11 |
| OrangeHRM (demo) | HR / admin | 85 | 38 | 47 | 20 |
| Automation Exercise | e-commerce | 85 | 40 | 45 | 18 |

## Cost

- Total estimated LLM cost: **$0.6136** (blended $0.3/M in, $0.6/M out)
- Cost per test: **$0.0012**

## Method

Four mutation classes are injected with known ground-truth labels, then the platform is scored on how well it recovers:

1. **Real defects** (product bugs) → must be classified `product_defect`, not healed.
2. **Broken locators** (typo'd selector) → `automation_defect` → self-heal to the correct element.
3. **Flaky tests** (alternating pass/fail) → detected by history scoring, not healed.
4. **Requirement changes** (element removed/renamed) → stale locator; heal must not silently change intent.
