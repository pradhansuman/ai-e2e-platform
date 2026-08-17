# AI E2E Platform — Benchmark Report

> Deterministic, seeded baseline (seed `42`). Diagnosis / self-healing / flaky-detection numbers are measured against the **real** deterministic agents; LLM generation is simulated. Re-run with `python -m benchmark`.

## Headline metrics

| Metric | Value |
|---|---|
| Requirement coverage | 83.3% |
| Test-generation accuracy | 86.9% |
| Defect detection (mutation score) | 92.3% |
| Root-cause accuracy | 92.1% |
| Self-healing success | 60.0% |
| False-healing rate | 40.0% |
| Flaky detection accuracy | 84.0% |
| Human intervention | 15.7% |
| Avg diagnosis time | 2.86 sec |
| Cost per test | $0.0013 |
| **AI-QE Score** | **83.2/100** |

## AI-QE Score breakdown

| Dimension | Weight | Score (0-1) | Weighted |
|---|---|---|---|
| Defect Detection | 20% | 0.923 | 0.185 |
| Requirement Coverage | 15% | 0.833 | 0.125 |
| Root Cause Accuracy | 15% | 0.921 | 0.138 |
| Test Quality | 15% | 0.869 | 0.130 |
| Self-Healing | 10% | 0.600 | 0.060 |
| Reliability | 10% | 0.600 | 0.060 |
| Flaky Detection | 5% | 0.840 | 0.042 |
| Human Intervention | 5% | 0.843 | 0.042 |
| Cost Efficiency | 5% | 0.999 | 0.050 |

## Volume

- **6 applications** across 6 domains (e-commerce ×2, banking, forms/widgets, UI patterns, HR/admin)
- **54 workflows** (user journeys)
- **72 ground-truth requirements**
- **510 generated tests** (443 with correct locators)
- **419 failures** → 359 correctly classified, 80 self-healing attempts, 50 flaky tests

## Per-application

| App | Domain | Tests | Passed | Failed | Heals |
|---|---|---|---|---|---|
| Swag Labs | e-commerce | 85 | 15 | 70 | 15 |
| ParaBank | banking | 85 | 15 | 70 | 16 |
| DemoQA | forms / widgets | 85 | 13 | 72 | 13 |
| The Internet | UI patterns | 85 | 15 | 70 | 12 |
| OrangeHRM (demo) | HR / admin | 85 | 10 | 75 | 11 |
| Automation Exercise | e-commerce | 85 | 23 | 62 | 13 |

## Cost

- Total estimated LLM cost: **$0.6669** (blended $0.3/M in, $0.6/M out)
- Cost per test: **$0.0013**

## Mutation corpus

Ten injected mutation classes with known ground-truth labels; the platform is scored on whether it both catches **and** correctly diagnoses each one.

| Mutation | Class | Injected | Detected | Accuracy |
|---|---|---|---|---|
| Api response change | `product_defect` | 26 | 23 | 88% |
| Auth change | `authentication` | 19 | 17 | 89% |
| Broken locator | `automation_defect` | 59 | 53 | 90% |
| Business rule change | `product_defect` | 32 | 29 | 91% |
| Calculation change | `product_defect` | 23 | 22 | 96% |
| Requirement change | `automation_defect` | 28 | 27 | 96% |
| Timing issue | `timing` | 46 | 43 | 93% |
| Validation removed | `product_defect` | 33 | 31 | 94% |
| Value change | `product_defect` | 57 | 53 | 93% |

## Method

Mutations are injected with known ground-truth labels, then the platform is scored on how well it recovers:

1. **Product defects** (value / validation / API response / business rule / calculation change) → must be classified `product_defect` and escalated, never healed.
2. **Automation defects** (broken locator, requirement change) → `automation_defect` → self-heal to the correct element.
3. **Auth change** → `authentication` (security regression, not a locator fix).
4. **Timing issue** → `timing` (wait/race, not a product bug).
5. **Flaky tests** (alternating pass/fail) → detected by history scoring, not healed.
