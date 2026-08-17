"""Tests for Phase 8-9: cost controls, usage limits, integrations, secrets, scheduler."""
import pytest

from app.intelligence.continuous_qe import ContinuousQEEngine
from app.intelligence.cost_controls import (
    Budget,
    BudgetExceeded,
    CostController,
    ModelPricing,
    ModelRouter,
)
from app.intelligence.integrations import GitHubClient, JiraClient, SlackNotifier
from app.intelligence.quality_graph import QualityGraph
from app.intelligence.scheduler import ContinuousRunner
from app.intelligence.secrets import SecretsStore
from app.intelligence.usage_limits import Limits, QuotaExceeded, UsageLimiter


# --------------------------------------------------------------------------- #
# Cost controls
# --------------------------------------------------------------------------- #
def _models():
    return [
        ModelPricing("cheap", 0.10, 0.20, tier="basic"),
        ModelPricing("std", 0.30, 0.60, tier="standard"),
        ModelPricing("pro", 3.0, 15.0, tier="premium"),
    ]


def test_model_router_picks_cheapest_matching_tier():
    r = ModelRouter(_models())
    assert r.route("basic").name == "cheap"
    assert r.route("premium").name == "pro"
    assert r.route("standard").name == "std"


def test_cost_controller_enforces_budget():
    cc = CostController(_models(), Budget(limit_usd=0.001), require_tier="premium")
    # premium model: 1k in + 1k out = (1000*3 + 1000*15)/1e6 = 0.018 > 0.001
    assert cc.record(1000, 1000) is None  # no model fits the budget
    assert cc.usage.calls == 0


def test_cost_controller_records_within_budget():
    cc = CostController(_models(), Budget(limit_usd=10.0))
    model = cc.record(1000, 1000)  # cheap: (0.1+0.2)/1e6 * 1000 = 0.0003
    assert model is not None and model.name == "cheap"
    assert cc.usage.calls == 1
    assert cc.summary()["remaining_usd"] < 10.0


def test_budget_exceeded_raises():
    b = Budget(limit_usd=1.0, spent_usd=0.9)
    with pytest.raises(BudgetExceeded):
        b.record(0.5)


# --------------------------------------------------------------------------- #
# Usage limits
# --------------------------------------------------------------------------- #
def test_usage_limiter_quota():
    ul = UsageLimiter(Limits(runs_per_day=3))
    assert ul.try_consume("org1", "runs_per_day") is True
    assert ul.try_consume("org1", "runs_per_day") is True
    assert ul.try_consume("org1", "runs_per_day") is True
    assert ul.try_consume("org1", "runs_per_day") is False  # exceeded
    assert ul.usage("org1") == {"runs_per_day": 3}


def test_usage_limiter_consume_raises():
    ul = UsageLimiter(Limits(healing_per_run=1))
    ul.consume("org1", "healing_per_run")
    with pytest.raises(QuotaExceeded):
        ul.consume("org1", "healing_per_run")


# --------------------------------------------------------------------------- #
# Secrets
# --------------------------------------------------------------------------- #
def test_secrets_redaction():
    s = SecretsStore()
    s.set("org1", "api_key", "sk-1234secret")
    assert s.mask("sk-1234secret") == "****"
    text = "Authorization: Bearer sk-1234secret in the log"
    assert "sk-1234secret" not in s.redact(text)
    assert "****" in s.redact(text)


def test_secrets_scoped_by_tenant():
    s = SecretsStore()
    s.set("org1", "k", "v1")
    s.set("org2", "k", "v2")
    assert s.get("org1", "k") == "v1"
    assert s.get("org2", "k") == "v2"
    assert s.list_keys("org1") == ["k"]


# --------------------------------------------------------------------------- #
# Integrations (formatting is pure + testable)
# --------------------------------------------------------------------------- #
def test_slack_format():
    n = SlackNotifier("https://hooks.example/x")
    p = n.format("Run failed", "3 tests", level="error")
    assert p["attachments"][0]["color"] == "#ff0000"
    assert p["attachments"][0]["title"] == "Run failed"


def test_jira_format_issue():
    j = JiraClient("https://j.example", "a@b.c", "tok", "QA")
    p = j.format_issue("Bug", "details")
    assert p["fields"]["project"] == {"key": "QA"}
    assert p["fields"]["issuetype"] == {"name": "Bug"}


def test_github_format_issue_with_labels():
    g = GitHubClient("tok", "owner/repo")
    p = g.format_issue("T", "B", labels=["flaky"])
    assert p["title"] == "T"
    assert p["labels"] == ["flaky"]


def test_integrations_transport_is_injectable():
    calls = []

    def rec(url, payload, headers):
        calls.append((url, payload))
        return {"ok": True}

    n = SlackNotifier("https://hooks.example/x", transport=rec)
    n.notify("hi", "body")
    assert calls and calls[0][0] == "https://hooks.example/x"


# --------------------------------------------------------------------------- #
# Scheduler (Phase 8 loop)
# --------------------------------------------------------------------------- #
def _engine():
    g = QualityGraph()
    for nid, typ in (
        ("api:orders", "api"),
        ("test:checkout", "test"),
        ("journey:buy", "user_journey"),
    ):
        g.add_node(nid, typ)
    g.add_dependency("test:checkout", "api:orders", "covers")
    g.add_dependency("journey:buy", "api:orders", "flows_through")
    return ContinuousQEEngine(g)


def test_continuous_runner_run_once():
    executed = []
    runner = ContinuousRunner(_engine(), on_execute=lambda t: executed.append(t) or {"status": "passed"})
    record = runner.run_once(changed_components=["api:orders"])
    assert "test:checkout" in record["plan"]["selected_tests"]
    assert "test:checkout" in executed


def test_continuous_runner_run_forever_bounded():
    runner = ContinuousRunner(_engine())
    ticks = runner.run_forever(interval_seconds=0, max_iterations=2, changed_components=["api:orders"])
    assert ticks == 2
    assert len(runner.results) == 2
