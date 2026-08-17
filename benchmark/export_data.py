"""Export the benchmark's ground-truth data to the canonical public layout.

Dumps the applications, requirements, workflows, defect (mutation) corpus, and
metric definitions as JSON under ``benchmark/data/`` so the benchmark is
portable and reproducible outside this repository — the seed of the public
``ai-e2e-benchmark`` repo (see docs/roadmap.md, Phase 10).

Run:  PYTHONPATH=backend python -m benchmark.export_data
"""
from __future__ import annotations

import json
from pathlib import Path

from . import apps as apps_mod
from .engine import MUTATIONS
from .quality import WEIGHTS, DIMENSION_LABELS

DATA_DIR = Path(__file__).parent / "data"


def _write(name: str, payload) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    )


def main() -> None:
    # Applications: full ground truth (id, name, domain, url, requirements,
    # workflows, elements).
    _write("applications.json", apps_mod.APPS)

    # Requirements: flattened with an app reference for downstream tooling.
    requirements = [
        {"app": a["id"], "requirement_id": rid, "text": text, "category": cat}
        for a in apps_mod.APPS
        for rid, text, cat in a["requirements"]
    ]
    _write("requirements.json", requirements)

    # Workflows: flattened user journeys.
    workflows = [
        {"app": a["id"], "workflow": wf}
        for a in apps_mod.APPS
        for wf in a["workflows"]
    ]
    _write("workflows.json", workflows)

    # Defect corpus: the injected mutation taxonomy with ground-truth labels.
    _write("defects.json", MUTATIONS)

    # Metric definitions + AI-QE weights.
    metrics = {
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
        "ai_qe_weights": {
            DIMENSION_LABELS[k]: w for k, w in WEIGHTS.items()
        },
    }
    _write("metrics.json", metrics)

    print(f"Exported benchmark data to {DATA_DIR}:")
    for p in sorted(DATA_DIR.glob("*.json")):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
