# AI E2E Platform — Benchmark Report

> Deterministic, seeded baseline (seed `42`). Diagnosis / self-healing / flaky-detection numbers are measured against the **real** deterministic agents; LLM generation is simulated. Re-run with `python -m benchmark`.

## Headline metrics

| Metric | Value |
|---|---|
| Requirement coverage | 83.3% |
| Test-generation accuracy | 87.1% |
| Defect detection (mutation score) | 80.9% |
| Root-cause accuracy | 90.4% |
| Self-healing success | 47.3% |
| False-healing rate | 52.7% |
| Flaky detection accuracy | 86.7% |
| Human intervention | 14.5% |
| Avg diagnosis time | 2.83 sec |
| Cost per test | $0.0013 |
| **AI-QE Score** | **78.4/100** |

## AI-QE Score breakdown

| Dimension | Weight | Score (0-1) | Weighted |
|---|---|---|---|
| Defect Detection | 20% | 0.809 | 0.162 |
| Requirement Coverage | 15% | 0.833 | 0.125 |
| Root Cause Accuracy | 15% | 0.904 | 0.136 |
| Test Quality | 15% | 0.871 | 0.131 |
| Self-Healing | 10% | 0.473 | 0.047 |
| Reliability | 10% | 0.473 | 0.047 |
| Flaky Detection | 5% | 0.867 | 0.043 |
| Human Intervention | 5% | 0.855 | 0.043 |
| Cost Efficiency | 5% | 0.999 | 0.050 |

## Volume

- **6 applications** across 6 domains (e-commerce ×2, banking, forms/widgets, UI patterns, HR/admin)
- **54 workflows** (user journeys)
- **72 ground-truth requirements**
- **510 generated tests** (444 with correct locators)
- **356 failures** → 300 correctly classified, 74 self-healing attempts, 45 flaky tests

## Per-application

| App | Domain | Tests | Passed | Failed | Heals |
|---|---|---|---|---|---|
| Swag Labs | e-commerce | 85 | 27 | 58 | 8 |
| ParaBank | banking | 85 | 29 | 56 | 12 |
| DemoQA | forms / widgets | 85 | 28 | 57 | 10 |
| The Internet | UI patterns | 85 | 26 | 59 | 14 |
| OrangeHRM (demo) | HR / admin | 85 | 20 | 65 | 17 |
| Automation Exercise | e-commerce | 85 | 24 | 61 | 13 |

## Cost

- Total estimated LLM cost: **$0.6444** (blended $0.3/M in, $0.6/M out)
- Cost per test: **$0.0013**

## Mutation corpus

Ten injected mutation classes with known ground-truth labels. The mutation score measures **fault-detection power**: the fraction of injected defects the generated tests actually *catch* (fail on).

| Mutation | Class | Injected | Caught | Detection |
|---|---|---|---|---|
| Api response change | `product_defect` | 29 | 24 | 83% |
| Auth change | `authentication` | 24 | 21 | 88% |
| Broken locator | `automation_defect` | 57 | 47 | 82% |
| Business rule change | `product_defect` | 25 | 18 | 72% |
| Calculation change | `product_defect` | 19 | 13 | 68% |
| Requirement change | `automation_defect` | 40 | 36 | 90% |
| Timing issue | `timing` | 42 | 33 | 79% |
| Validation removed | `product_defect` | 37 | 25 | 68% |
| Value change | `product_defect` | 56 | 49 | 88% |

## Method

Mutations are injected with known ground-truth labels, then the platform is scored on how well it recovers:

1. **Product defects** (value / validation / API response / business rule / calculation change) → must be classified `product_defect` and escalated, never healed.
2. **Automation defects** (broken locator, requirement change) → `automation_defect` → self-heal to the correct element.
3. **Auth change** → `authentication` (security regression, not a locator fix).
4. **Timing issue** → `timing` (wait/race, not a product bug).
5. **Flaky tests** (alternating pass/fail) → detected by history scoring, not healed.
