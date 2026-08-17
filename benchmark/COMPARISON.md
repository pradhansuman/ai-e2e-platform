# Control-Group Baseline

> **Measured vs estimated.** The "This platform" row is measured by the benchmark engine (real deterministic agents). Human / Playwright / LLM rows are parameterized estimates (directional priors, not measured ground truth). AI-QE Score uses business weights (defect detection 20%, coverage/root-cause/test-quality 15% each, self-healing/reliability 10% each, flaky-detection/intervention/cost 5% each).

| Metric | Human | Playwright | LLM one-shot | This platform |
|---|---|---|---|---|
| Coverage | 94.0% | 90.0% | 80.0% | 83.3% |
| Test quality | 96.0% | 95.0% | 85.0% | 87.5% |
| Defect detection | 92.0% | 88.0% | 75.0% | 90.6% |
| Root-cause accuracy | 95.0% | 92.0% | 88.0% | 91.5% |
| Self-healing | 0.0% | 0.0% | 0.0% | 41.3% |
| False-healing | 0.0% | 0.0% | 0.0% | 58.7% |
| Flaky detection | 0.0% | 0.0% | 0.0% | 80.0% |
| Human intervention | 100.0% | 90.0% | 60.0% | 20.4% |
| Avg diagnosis time | 1,200s | 300s | 30s | 3s |
| Cost / test | $4.500 | $1.200 | $0.008 | $0.001 |
| Test flakiness (rate) | 8% | 15% | 22% | 12% |
| Execution time | hours (manual triage) | minutes (CI) | seconds (CI) | seconds (CI, autonomous) |
| Human effort | high | high (maintenance) | medium (review + fix) | low (autonomous healing) |
|---|---|---|---|---|
| **AI-QE Score** | **72.1** | **71.9** | **69.9** | **78.7** |
