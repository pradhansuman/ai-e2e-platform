> **Measured / estimated / pending.** Human = pending · Playwright = pending · LLM one-shot = estimated · This platform = measured. Pending rows are not fabricated — they show “—” until an independent run fills them in.

| Metric | Human | Playwright | LLM one-shot | This platform |
|---|---|---|---|---|
| Coverage | — | — | 80.0% | 83.3% |
| Test quality | — | — | 85.0% | 87.1% |
| Defect detection | — | — | 75.0% | 80.9% |
| Root-cause accuracy | — | — | 88.0% | 90.4% |
| Self-healing | — | — | 0.0% | 47.3% |
| False-healing | — | — | 0.0% | 52.7% |
| Flaky detection | — | — | 0.0% | 86.7% |
| Human intervention | — | — | 60.0% | 14.5% |
| Avg diagnosis time | — | — | 30s | 3s |
| Cost / test | — | — | $0.008 | $0.001 |
| Test flakiness (rate) | — | — | 22% | 12% |
| Execution time | — | — | seconds (CI) | seconds (CI, autonomous) |
| Human effort | high | high (maintenance) | medium (review + fix) | low (autonomous healing) |
|---|---|---|---|---|
| **AI-QE Score** | — | — | **69.9** | **78.4** |

## Healing modes (reported separately)

> Healing success and false-healing are **never combined** into one number, because the platform's value-add is the LLM heal.

| Healing mode | Measurement | Success | False-healing |
|---|---|---|---|
| Deterministic fallback | measured | 47.3% | 52.7% |
| Mistral LLM | measured | 83.3% | 0.0% |

**Combined policy:** LLM-first with deterministic fallback: when an LLM provider is reachable (Mistral), healing uses the LLM (83.3% success, 0% false-heal); when all providers are exhausted or unreachable, it falls back to the deterministic healer (47.3% success, 52.7% false-heal).
