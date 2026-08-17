"""Benchmark harness for the ai-e2e-platform.

Measures the platform's QA pipeline (generation → risk selection → execution →
diagnosis → self-healing → flaky detection) against six ground-truth target
applications, with injected mutations, and publishes nine headline metrics.

Run:
    python -m benchmark              # deterministic (seeded) baseline
    python -m benchmark --seed 7     # another reproducible draw
    python -m benchmark --json       # machine-readable output
"""
from .engine import Params, run_benchmark
from .report import render_markdown, render_text

__all__ = ["Params", "run_benchmark", "render_markdown", "render_text"]
