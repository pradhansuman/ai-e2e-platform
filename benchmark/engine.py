"""Benchmark engine.

Runs a deterministic, seeded simulation of the platform's pipeline against the
six ground-truth applications, but measures the *real* deterministic agents
(``heuristic_classify``, ``heuristic_heal``, ``detect_flakiness``) on the
failures it synthesizes — so the diagnosis / healing / flakiness numbers reflect
the actual code paths, not just random numbers.

Modes:
- ``sim`` (this module): deterministic offline baseline, no LLM / browser needed.
- ``live``: drive the real LangGraph pipeline (needs LLM quota + a browser) —
  the intended next step.

The simulation model is documented inline; every parameter is overridable so
the harness is reproducible and can later be pointed at the live pipeline.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from app.agents.analyzer import heuristic_classify
from app.agents.flakiness import detect_flakiness
from app.agents.healer import heuristic_heal

from . import apps as apps_mod


@dataclass
class Params:
    """Simulation + cost parameters (all reproducible via ``seed``)."""

    total_tests: int = 510
    seed: int = 42

    # Ground-truth generator capability (measured by the benchmark, not set by
    # the platform). P(a generated test has a correct, resolvable locator).
    gen_accuracy: float = 0.86
    # P(a generated test asserts on the behavior a mutation changes, i.e. the
    # test actually *catches* the injected defect). This is the platform's
    # fault-detection power — the mutation score measures caught / injected.
    assertion_quality: float = 0.80
    # Fraction of an app's requirements that end up tested (coverage realism).
    requirement_coverage: float = 0.88

    # Mutation mix lives in the module-level ``MUTATIONS`` registry (see below);
    # weights are applied over correctly-generated tests, with the remainder
    # falling through to ``clean`` (no mutation).

    # Diagnosis noise: fraction of failures whose error text is ambiguous enough
    # that heuristic_classify cannot place them (measures real root-cause accuracy).
    ambiguous_failure_rate: float = 0.08
    # Flaky detection realism: P(a flaky test has a clear alternating history).
    flaky_detectability: float = 0.85
    # Simulated LLM diagnosis latency (seconds) — live mode measures the real value.
    diag_time_range: tuple[float, float] = (1.2, 4.5)
    # Healing path: "heuristic" (deterministic fallback, no LLM) or "llm"
    # (uses ``propose_healing``; requires an LLM key with quota).
    heal_mode: str = "heuristic"
    # Classification path: "heuristic" (deterministic) or "llm"
    # (uses ``analyze_failure_evidence``; requires an LLM key with quota).
    classify_mode: str = "heuristic"

    # Cost model (USD per 1M tokens; cheap mid-tier model).
    cost_input_per_1m: float = 0.30
    cost_output_per_1m: float = 0.60
    gen_input_tokens: int = 2500           # amortized app-model prompt per test
    gen_output_tokens_per_test: int = 400  # per generated test case
    diag_tokens: int = 1200                # per failure analysis
    heal_tokens: int = 900                 # per healing proposal


@dataclass
class BenchResult:
    params: Params
    metrics: dict[str, Any] = field(default_factory=dict)
    counts: dict[str, Any] = field(default_factory=dict)
    per_app: list[dict[str, Any]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Ground-truth DOM + selector helpers
# --------------------------------------------------------------------------- #
def dom_snapshot(elements: dict[str, dict]) -> str:
    """Synthesize an HTML-ish snapshot from ground-truth elements."""
    lines: list[str] = []
    for _sel, el in elements.items():
        role = el.get("role", "input")
        if role == "input":
            lines.append(
                f'<input id="{el["id"]}" name="{el.get("name", "")}" '
                f'type="{el.get("type", "text")}" />'
            )
        elif role == "button":
            lines.append(
                f'<button id="{el["id"]}" name="{el.get("name", "")}">'
                f'{el.get("label", "")}</button>'
            )
        else:
            lines.append(f'<a id="{el["id"]}" href="#">{el.get("label", "")}</a>')
    return "\n".join(lines)


def _break_selector(el: dict, rng: random.Random) -> str:
    """Produce a *healable* typo: a prefix of the element's id (so the token
    still matches the real id, letting ``heuristic_heal`` recover it)."""
    eid = el["id"]
    keep = max(2, len(eid) // 2)
    return "#" + eid[:keep]


def _selector_hits_intent(selected: str | None, el: dict) -> bool:
    """True if the healed selector resolves to the intended element's identity."""
    if not selected:
        return False
    return el["id"] in selected


def _dom_without(elements: dict[str, dict], remove_selector: str) -> str:
    return dom_snapshot({k: v for k, v in elements.items() if k != remove_selector})


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def _generate_for_app(
    app: dict,
    n: int,
    rng: random.Random,
    params: Params,
    testable_reqs: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    workflows = app["workflows"]
    elements = list(app["elements"].keys())
    tests: list[dict[str, Any]] = []
    for i in range(n):
        wf = workflows[i % len(workflows)]
        req = testable_reqs[rng.randrange(len(testable_reqs))]
        locator_correct = rng.random() < params.gen_accuracy
        target = elements[i % len(elements)]
        tests.append(
            {
                "test_id": f"{app['id'].upper()}-{i + 1:03d}",
                "app": app["id"],
                "workflow": wf,
                "requirement_id": req[0],
                "locator_correct": locator_correct,
                "target_selector": target,
                "steps": [
                    {"action": "goto", "target": app["url"]},
                    {"action": "fill", "target": target, "value": "test-value"},
                    {"action": "assert_value", "target": target, "value": "test-value"},
                ],
            }
        )
    return tests


# --------------------------------------------------------------------------- #
# Mutation taxonomy (ground truth)
#
# The full defect-injection corpus from the roadmap (Phase 4). Each entry maps
# an injected mutation to its *correct* classification and a synthesized error
# message shaped like the executor's output. Weights are injection probabilities
# over correctly-generated tests; the remainder is ``clean``.
# --------------------------------------------------------------------------- #
MUTATIONS: dict[str, dict[str, Any]] = {
    # --- product defects: genuine bugs the platform must DETECT (not heal) ---
    "value_change": {
        "classification": "product_defect", "weight": 0.12,
        "error": "expected text `Order Confirmed` but found `Error`",
    },
    "validation_removed": {
        "classification": "product_defect", "weight": 0.07,
        "error": "form accepted invalid email without validation error",
    },
    "api_response_change": {
        "classification": "product_defect", "weight": 0.07,
        "error": "expected field `orderTotal` in API response but was missing",
    },
    "business_rule_change": {
        "classification": "product_defect", "weight": 0.06,
        "error": "expected discount 10% but applied 0%",
    },
    "calculation_change": {
        "classification": "product_defect", "weight": 0.06,
        "error": "expected total 110 but got 100",
    },
    # --- automation defects: the platform must HEAL ---
    "broken_locator": {
        "classification": "automation_defect", "weight": 0.13, "healable": True,
        "error": None,  # generated dynamically from the element id
    },
    "requirement_change": {
        "classification": "automation_defect", "weight": 0.08, "healable": True,
        "error": None,  # generated dynamically from the target selector
    },
    # --- auth / access: security regression ---
    "auth_change": {
        "classification": "authentication", "weight": 0.06,
        "error": "expected 200 OK but got 403 Forbidden",
    },
    # --- timing / flaky: environmental ---
    "timing_issue": {
        "classification": "timing", "weight": 0.09,
        "error": "Timed out after 30000ms waiting for element",
    },
    "flaky": {
        "classification": "flaky", "weight": 0.11,
        "error": "Timed out after 30000ms waiting for element",
    },
}

# Defect mutations scored by the mutation score (fault-detection power).
# ``flaky`` is excluded — it has its own flaky-detection metric.
DEFECT_MUTATIONS = [
    k for k, m in MUTATIONS.items() if m["classification"] != "flaky"
]

HEALABLE_MUTATIONS = {k for k, m in MUTATIONS.items() if m.get("healable")}


# --------------------------------------------------------------------------- #
# Mutation injection
# --------------------------------------------------------------------------- #
def _inject_mutation(rng: random.Random, params: Params) -> str:
    r = rng.random()
    for key, m in MUTATIONS.items():
        r -= m["weight"]
        if r < 0:
            return key
    return "clean"


# --------------------------------------------------------------------------- #
# Execution (synthesized result shaped like the executor's output)
# --------------------------------------------------------------------------- #
def _simulate_execution(
    test: dict, mutation: str, rng: random.Random, params: Params
) -> dict[str, Any]:
    status = "passed"
    error = ""
    broken_locator = None

    if not test["locator_correct"]:
        status, error = "failed", f"waiting for selector `#gen-bad-{test['test_id']}`"
        broken_locator = f"#gen-bad-{test['test_id']}"
    elif mutation == "clean":
        status, error = "passed", ""
    elif mutation == "flaky":
        status = "passed" if rng.random() < 0.5 else "failed"
        if status == "failed":
            error = MUTATIONS["flaky"]["error"]
    elif mutation in MUTATIONS:
        # Fault-detection gate: a generated test only catches the injected
        # defect if it asserts on the mutated behavior. Otherwise it passes
        # despite the defect (a *missed* mutation — no fault-detection power).
        if rng.random() < params.assertion_quality:
            status = "failed"
            if mutation == "broken_locator":
                broken_locator = _break_selector(_el_for(test), rng)
                error = f"waiting for selector `{broken_locator}`"
            elif mutation == "requirement_change":
                broken_locator = test["target_selector"]
                error = f"no element matching `{test['target_selector']}`"
            else:
                error = MUTATIONS[mutation]["error"]

    # Ambiguous error text -> heuristic_classify cannot place it ("unknown").
    if status == "failed" and rng.random() < params.ambiguous_failure_rate:
        error = "An unexpected error occurred during execution"
        broken_locator = None

    return {
        "test_id": test["test_id"],
        "status": status,
        "error": error,
        "duration_ms": rng.randint(400, 9000),
        "steps": [{"target": test["target_selector"], "error": error} if status == "failed" else {}],
        "_mutation": mutation,
        "_broken_locator": broken_locator,
    }


def _el_for(test: dict) -> dict:
    app = next(a for a in apps_mod.APPS if a["id"] == test["app"])
    return app["elements"][test["target_selector"]]


def _simulate_flaky_history(rng: random.Random, detectability: float) -> list[dict[str, Any]]:
    if rng.random() < detectability:
        # clear alternating pattern over a long history -> score ~1.0
        seq = ["passed", "failed"] * 6  # 12 runs, 11 flips
    else:
        # subtle: 5 runs with a single flip -> low score -> missed
        seq = ["passed", "failed", "passed", "passed", "passed"]
    return [{"status": s, "duration_ms": rng.randint(200, 5000)} for s in seq]


# --------------------------------------------------------------------------- #
# Main run
# --------------------------------------------------------------------------- #
def run_benchmark(params: Params | None = None) -> BenchResult:
    params = params or Params()
    rng = random.Random(params.seed)

    c = {
        "generated": 0, "accurate_tests": 0,
        "failures": 0, "deterministic_failures": 0,
        "root_cause_correct": 0,
        "mutations_injected": 0, "mutations_caught": 0,
        "mutation_breakdown": {}, "mutation_caught_breakdown": {},
        "heal_attempts": 0, "heal_success": 0, "false_heals": 0,
        "flaky_injected": 0, "flaky_detected": 0,
        "interventions": 0,
        "diag_ms_total": 0.0, "diag_count": 0,
        "covered_requirements": set(), "total_requirements": 0,
        "tokens_in": 0, "tokens_out": 0,
    }
    per_app: list[dict[str, Any]] = []

    n_per_app = params.total_tests // len(apps_mod.APPS)

    for app in apps_mod.APPS:
        c["total_requirements"] += len(app["requirements"])
        reqs = app["requirements"]
        k = max(1, int(len(reqs) * params.requirement_coverage))
        testable_reqs = rng.sample(reqs, k)

        elements = app["elements"]
        tests = _generate_for_app(app, n_per_app, rng, params, testable_reqs)
        app_pass = app_fail = app_heals = 0

        for test in tests:
            c["generated"] += 1
            c["tokens_in"] += params.gen_input_tokens
            c["tokens_out"] += params.gen_output_tokens_per_test

            if test["locator_correct"]:
                c["accurate_tests"] += 1
            c["covered_requirements"].add((app["id"], test["requirement_id"]))

            mutation = "gen_bad" if not test["locator_correct"] else _inject_mutation(rng, params)
            result = _simulate_execution(test, mutation, rng, params)

            # Count injected defect mutations regardless of whether the test
            # caught them — fault-detection power = caught / injected.
            if mutation in DEFECT_MUTATIONS:
                c["mutations_injected"] += 1
                c["mutation_breakdown"][mutation] = c["mutation_breakdown"].get(mutation, 0) + 1
                if result["status"] == "failed":
                    c["mutations_caught"] += 1
                    c["mutation_caught_breakdown"][mutation] = c["mutation_caught_breakdown"].get(mutation, 0) + 1

            if result["status"] == "failed":
                c["failures"] += 1
                app_fail += 1
            else:
                app_pass += 1

            # Flaky detection (separate path from failure diagnosis).
            if mutation == "flaky":
                c["flaky_injected"] += 1
                det = detect_flakiness(_simulate_flaky_history(rng, params.flaky_detectability))
                if det["classification"] == "flaky":
                    c["flaky_detected"] += 1
                continue

            # Deterministic failure -> diagnosis (REAL heuristic) + time model.
            if result["status"] == "failed":
                c["deterministic_failures"] += 1
                c["tokens_in"] += params.diag_tokens
                c["diag_ms_total"] += rng.uniform(*params.diag_time_range) * 1000
                c["diag_count"] += 1

                rc = _classify(result, params)
                if rc["classification"] == _ground_truth_label(mutation):
                    c["root_cause_correct"] += 1

                # Self-healing for healable automation defects (REAL heuristic).
                if rc["classification"] == "automation_defect" and mutation in HEALABLE_MUTATIONS:
                    c["interventions"] += 1  # approval gate (human approval on by default)
                    c["heal_attempts"] += 1
                    c["tokens_in"] += params.heal_tokens
                    app_heals += 1
                    heal_dom = (
                        _dom_without(elements, test["target_selector"])
                        if mutation == "requirement_change"
                        else dom_snapshot(elements)
                    )
                    if params.heal_mode == "llm":
                        from app.agents.healer import propose_healing
                        suggestion = propose_healing(
                            result["_broken_locator"], heal_dom,
                            "recover the intended element without changing test intent",
                        )
                    else:
                        suggestion = heuristic_heal(result["_broken_locator"], heal_dom)  # REAL
                    selected = suggestion.selected.selector if suggestion.selected else None
                    if _selector_hits_intent(selected, _el_for(test)):
                        c["heal_success"] += 1
                    elif selected:
                        c["false_heals"] += 1

        per_app.append(
            {
                "app": app["id"],
                "name": app["name"],
                "domain": app["domain"],
                "tests": n_per_app,
                "passed": app_pass,
                "failed": app_fail,
                "heals": app_heals,
            }
        )

    # ---- compute the nine headline metrics ----
    total = c["generated"]
    req_cov = len(c["covered_requirements"]) / c["total_requirements"] * 100 if c["total_requirements"] else 0.0
    gen_acc = c["accurate_tests"] / total * 100 if total else 0.0
    rc_acc = c["root_cause_correct"] / c["deterministic_failures"] * 100 if c["deterministic_failures"] else 0.0
    mutation_score = c["mutations_caught"] / c["mutations_injected"] * 100 if c["mutations_injected"] else 0.0
    heal_success = c["heal_success"] / c["heal_attempts"] * 100 if c["heal_attempts"] else 0.0
    false_heal = c["false_heals"] / c["heal_attempts"] * 100 if c["heal_attempts"] else 0.0
    flaky_acc = c["flaky_detected"] / c["flaky_injected"] * 100 if c["flaky_injected"] else 0.0
    intervention = c["interventions"] / total * 100 if total else 0.0
    avg_diag_s = (c["diag_ms_total"] / c["diag_count"]) / 1000.0 if c["diag_count"] else 0.0
    cost = (
        c["tokens_in"] * params.cost_input_per_1m
        + c["tokens_out"] * params.cost_output_per_1m
    ) / 1_000_000.0

    metrics = {
        "requirement_coverage_pct": round(req_cov, 1),
        "test_generation_accuracy_pct": round(gen_acc, 1),
        "root_cause_accuracy_pct": round(rc_acc, 1),
        "defect_detection_pct": round(mutation_score, 1),
        "self_healing_success_pct": round(heal_success, 1),
        "false_healing_rate_pct": round(false_heal, 1),
        "flaky_detection_accuracy_pct": round(flaky_acc, 1),
        "human_intervention_pct": round(intervention, 1),
        "avg_diagnosis_time_sec": round(avg_diag_s, 2),
        "cost_per_test_usd": round(cost / total, 4) if total else 0.0,
    }

    return BenchResult(
        params=params,
        metrics=metrics,
        counts={
            "apps": len(apps_mod.APPS),
            "workflows": apps_mod.total_workflows(),
            "requirements": c["total_requirements"],
            "tests": total,
            "accurate_tests": c["accurate_tests"],
            "failures": c["failures"],
            "root_cause_correct": c["root_cause_correct"],
            "mutations_injected": c["mutations_injected"],
            "mutations_caught": c["mutations_caught"],
            "mutation_breakdown": dict(c["mutation_breakdown"]),
            "mutation_caught_breakdown": dict(c["mutation_caught_breakdown"]),
            "heal_attempts": c["heal_attempts"],
            "heal_success": c["heal_success"],
            "false_heals": c["false_heals"],
            "flaky_injected": c["flaky_injected"],
            "flaky_detected": c["flaky_detected"],
            "interventions": c["interventions"],
            "total_cost_usd": round(cost, 4),
        },
        per_app=per_app,
    )


def _classify(result: dict[str, Any], params: Params) -> dict[str, Any]:
    """Classify a failure via the LLM (live) or the deterministic heuristic."""
    if params.classify_mode == "llm":
        from app.agents.analyzer import analyze_failure_evidence

        try:
            rc = analyze_failure_evidence(result, {"evidence": {}})
            return rc if isinstance(rc, dict) else rc.model_dump()
        except Exception:  # noqa: BLE001 - LLM may be unavailable
            pass
    return heuristic_classify(result, {"evidence": {}})


def _ground_truth_label(mutation: str) -> str:
    """The 'correct' classification the platform is scored against."""
    if mutation == "gen_bad":
        return "automation_defect"
    if mutation in MUTATIONS:
        return MUTATIONS[mutation]["classification"]
    return "unknown"
