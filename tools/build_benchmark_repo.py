"""Build the standalone ai-e2e-benchmark repo from the benchmark ground truth.

Creates the canonical public layout (applications / requirements / workflows /
defects / expected-results / metrics / results) and writes README + LICENSE.
Run:  PYTHONPATH=backend .venv/bin/python tools/build_benchmark_repo.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchmark import apps as apps_mod
from benchmark.engine import MUTATIONS
from benchmark.quality import WEIGHTS, DIMENSION_LABELS

ROOT = Path(__file__).resolve().parents[1]  # ai-e2e-platform/
DEST = ROOT.parent / "ai-e2e-benchmark"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    apps = apps_mod.APPS

    # applications/ — one JSON per app (full ground truth).
    for a in apps:
        _write(DEST / "applications" / f"{a['id']}.json", a)

    # requirements/ — flat, with app reference.
    _write(
        DEST / "requirements" / "requirements.json",
        [
            {"app": a["id"], "requirement_id": rid, "text": text, "category": cat}
            for a in apps
            for rid, text, cat in a["requirements"]
        ],
    )

    # workflows/ — flat user journeys.
    _write(
        DEST / "workflows" / "workflows.json",
        [{"app": a["id"], "workflow": wf} for a in apps for wf in a["workflows"]],
    )

    # defects/ — the mutation corpus.
    _write(DEST / "defects" / "mutations.json", MUTATIONS)

    # expected-results/ — ground-truth DOM + which elements each workflow touches.
    expected = {}
    for a in apps:
        selectors = list(a["elements"].keys())
        workflow_targets = {}
        for i, wf in enumerate(a["workflows"]):
            workflow_targets[wf] = [selectors[i % len(selectors)]]
        expected[a["id"]] = {
            "name": a["name"],
            "expected_elements": a["elements"],
            "workflow_targets": workflow_targets,
        }
    _write(DEST / "expected-results" / "expected-results.json", expected)

    # metrics/ — metric definitions + AI-QE weights + standalone scoring code.
    _write(
        DEST / "metrics" / "metrics.json",
        {
            "metrics": [
                "requirement_coverage_pct",
                "test_generation_accuracy_pct",
                "defect_detection_pct",
                "root_cause_accuracy_pct",
                "self_healing_success_pct",
                "false_healing_rate_pct",
                "flaky_detection_accuracy_pct",
                "human_intervention_pct",
                "avg_diagnosis_time_sec",
                "cost_per_test_usd",
            ],
            "ai_qe_weights": {DIMENSION_LABELS[k]: w for k, w in WEIGHTS.items()},
        },
    )
    shutil.copy(ROOT / "benchmark" / "quality.py", DEST / "metrics" / "ai_qe_score.py")

    # results/ — reference results from this platform.
    results = DEST / "results"
    results.mkdir(exist_ok=True)
    for name in ("REPORT.md", "COMPARISON.md", "SWEEP.md"):
        src = ROOT / "benchmark" / name
        if src.exists():
            shutil.copy(src, results / name)

    shutil.copy(ROOT / "LICENSE", DEST / "LICENSE")

    # README
    (DEST / "README.md").write_text(README, encoding="utf-8")

    print(f"Built {DEST}")
    for p in sorted(DEST.rglob("*")):
        if p.is_file():
            print(" ", p.relative_to(DEST))


README = """# ai-e2e-benchmark

A **public, reproducible benchmark** for AI E2E testing platforms: six real
target applications, a ground-truth requirement/workflow/DOM corpus, an injected
defect (mutation) corpus, and a weighted **AI-QE Score** to compare platforms
on the same yardstick.

This repo is the *data + methodology* companion to
[ai-e2e-platform](https://github.com/pradhansuman/ai-e2e-platform), a
closed-loop autonomous quality-engineering agent. Use this benchmark to measure
**any** E2E testing approach — human-written, scripted Playwright, one-shot LLM,
or a full AI platform — against the same ground truth.

## Structure

```
applications/      six apps, full ground truth (requirements, workflows, DOM)
requirements/      flat ground-truth requirements
workflows/         flat user journeys
defects/           injected mutation (defect) corpus with ground-truth labels
expected-results/  ground-truth DOM + per-workflow assertion targets
metrics/           metric definitions + AI-QE weights + standalone scoring code
results/           reference results from ai-e2e-platform
```

## The AI-QE Score

A single 0-100 number, business-weighted (not a blind average). Dimensions:

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

See `metrics/ai_qe_score.py` for the implementation (0-1 normalization, higher
is better; lower-is-better dimensions are inverted).

## How to benchmark your platform

1. Clone this repo.
2. For each application, generate tests that cover its `requirements` and
   `workflows`, run them, and inject the `defects/mutations.json` corpus.
3. Compute the ten metrics in `metrics/metrics.json`.
4. Feed them into `metrics/ai_qe_score.py` → a single AI-QE Score.

The reference engine that produced `results/` lives in
[ai-e2e-platform/benchmark](https://github.com/pradhansuman/ai-e2e-platform/tree/main/benchmark).

## Reference results (ai-e2e-platform)

- **AI-QE Score: 78.4 / 100** (deterministic baseline, 510 tests)
- Control group: Human 72.1 · Playwright 71.9 · LLM one-shot 69.9 · platform 78.4
- Live LLM heal: **83.3% self-healing success, 0% false-heal** (vs 47% / 53%
  for the deterministic fallback).

See `results/` for the full reports.

## License

MIT — see [LICENSE](LICENSE).
"""


if __name__ == "__main__":
    main()
