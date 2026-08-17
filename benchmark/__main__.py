"""Benchmark CLI entry point.

Usage:
    python -m benchmark                    # deterministic baseline, text report
    python -m benchmark --markdown         # print markdown report (publishable)
    python -m benchmark --json             # machine-readable metrics
    python -m benchmark --compare          # control group: Human / Playwright / LLM / platform
    python -m benchmark --compare --markdown
    python -m benchmark --seed 7 --tests 600
"""
from __future__ import annotations

import argparse
import json

from .approaches import (
    build_comparison,
    render_comparison_markdown,
    render_comparison_text,
)
from .engine import Params, run_benchmark
from .report import render_markdown, render_text


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m benchmark")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tests", type=int, default=510)
    parser.add_argument("--gen-accuracy", type=float, default=0.86)
    parser.add_argument("--assertion-quality", type=float, default=0.80)
    parser.add_argument("--requirement-coverage", type=float, default=0.88)
    parser.add_argument("--heal", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--classify", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--markdown", action="store_true", help="print publishable markdown")
    parser.add_argument("--json", action="store_true", help="print metrics as JSON")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="control-group baseline: Human / Playwright / LLM / this platform",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="sensitivity sweep of the AI-QE score over generator priors",
    )
    args = parser.parse_args()

    if args.sweep:
        from .sweep import render_markdown as sweep_md, render_text as sweep_text, run_sweep
        rows = run_sweep(seed=args.seed)
        print(sweep_md(rows) if args.markdown else sweep_text(rows))
        return

    params = Params(
        seed=args.seed,
        total_tests=args.tests,
        gen_accuracy=args.gen_accuracy,
        assertion_quality=args.assertion_quality,
        requirement_coverage=args.requirement_coverage,
        heal_mode=args.heal,
        classify_mode=args.classify,
    )
    result = run_benchmark(params)

    if args.compare:
        rows = build_comparison(result.metrics)
        if args.markdown:
            print(render_comparison_markdown(rows))
        else:
            print(render_comparison_text(rows))
        return

    if args.json:
        print(json.dumps(result.metrics, indent=2))
    elif args.markdown:
        print(render_markdown(result))
    else:
        print(render_text(result))


if __name__ == "__main__":
    main()
