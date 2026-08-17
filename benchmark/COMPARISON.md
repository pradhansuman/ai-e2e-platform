# Control-Group Baseline

> **Measured vs estimated.** The "This platform" row is measured by the benchmark engine (real deterministic agents). Human / Playwright / LLM rows are parameterized estimates (directional priors, not measured ground truth). AI-QE Score uses business weights (defect detection 20%, coverage/root-cause/test-quality 15% each, self-healing/reliability 10% each, flaky-detection/intervention/cost 5% each).

| Metric | Human | Playwright | LLM one-shot | This platform |
|---|---|---|---|---|
| Coverage | 94.0% | 90.0% | 80.0% | 83.3% |
| Test quality | 96.0% | 95.0% | 85.0% | 87.1% |
| Defect detection | 92.0% | 88.0% | 75.0% | 80.9% |
| Root-cause accuracy | 95.0% | 92.0% | 88.0% | 90.4% |
| Self-healing | 0.0% | 0.0% | 0.0% | 47.3% |
| False-healing | 0.0% | 0.0% | 0.0% | 52.7% |
| Flaky detection | 0.0% | 0.0% | 0.0% | 86.7% |
| Human intervention | 100.0% | 90.0% | 60.0% | 14.5% |
| Avg diagnosis time | 1,200s | 300s | 30s | 3s |
| Cost / test | $4.500 | $1.200 | $0.008 | $0.001 |
| Test flakiness (rate) | 8% | 15% | 22% | 12% |
| Execution time | hours (manual triage) | minutes (CI) | seconds (CI) | seconds (CI, autonomous) |
| Human effort | high | high (maintenance) | medium (review + fix) | low (autonomous healing) |
|---|---|---|---|---|
| **AI-QE Score** | **72.1** | **71.9** | **69.9** | **78.4** |
