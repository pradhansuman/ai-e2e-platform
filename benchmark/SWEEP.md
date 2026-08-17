# Benchmark sensitivity sweep

> How the AI-QE Score responds to the two generator-capability priors (assertion quality = fault-detection power, generation accuracy = locator correctness). Fixed seed; deterministic.

## AI-QE Score

| assertion-qty \ gen-acc | 0.80 | 0.86 | 0.92 |
|---|---|---|---|
| 0.70 | 79.0 | 79.4 | 80.3 |
| 0.80 | 79.2 | 78.4 | 82.3 |
| 0.90 | 81.5 | 82.5 | 81.4 |

## Defect detection %

| assertion-qty \ gen-acc | 0.80 | 0.86 | 0.92 |
|---|---|---|---|
| 0.70 | 74.6 | 74.3 | 73.9 |
| 0.80 | 83.7 | 80.9 | 82.4 |
| 0.90 | 90.5 | 87.9 | 88.1 |

## Root-cause accuracy %

| assertion-qty \ gen-acc | 0.80 | 0.86 | 0.92 |
|---|---|---|---|
| 0.70 | 93.0 | 92.4 | 94.3 |
| 0.80 | 92.6 | 90.4 | 92.0 |
| 0.90 | 91.5 | 91.0 | 92.1 |

## Self-healing success %

| assertion-qty \ gen-acc | 0.80 | 0.86 | 0.92 |
|---|---|---|---|
| 0.70 | 59.3 | 56.9 | 56.4 |
| 0.80 | 48.6 | 47.3 | 59.7 |
| 0.90 | 56.2 | 59.0 | 50.0 |

