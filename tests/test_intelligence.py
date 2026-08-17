"""Tests for the intelligence layer (Phases 5-9)."""
import pytest

from app.intelligence.change_analysis import (
    analyze_change,
    map_changed_files,
    regression_plan,
)
from app.intelligence.continuous_qe import ContinuousQEEngine
from app.intelligence.enterprise import (
    AccessControl,
    ROLE_PERMISSIONS,
    role_can,
)
from app.intelligence.production_intelligence import (
    detect_test_gaps,
    production_risk_report,
)
from app.intelligence.quality_graph import QualityGraph


def _graph() -> QualityGraph:
    """A small but representative quality graph."""
    g = QualityGraph()
    for nid, typ in (
        ("req:checkout", "requirement"),
        ("req:login", "requirement"),
        ("api:orders", "api"),
        ("api:payments", "api"),
        ("ui:cart", "ui_component"),
        ("ui:checkout-form", "ui_component"),
        ("journey:buy", "user_journey"),
        ("journey:login", "user_journey"),
        ("test:cart-add", "test"),
        ("test:checkout", "test"),
        ("test:login", "test"),
    ):
        g.add_node(nid, typ)
    # requirements -> components
    g.add_dependency("req:checkout", "ui:checkout-form", "specifies")
    g.add_dependency("req:login", "ui:cart", "specifies")
    # components -> apis
    g.add_dependency("ui:checkout-form", "api:payments", "calls")
    g.add_dependency("ui:cart", "api:orders", "calls")
    # tests -> what they cover
    g.add_dependency("test:checkout", "ui:checkout-form", "covers")
    g.add_dependency("test:cart-add", "ui:cart", "covers")
    g.add_dependency("test:login", "ui:cart", "covers")
    g.add_dependency("test:checkout", "req:checkout", "verifies")
    g.add_dependency("test:login", "req:login", "verifies")
    # journeys -> components they flow through
    g.add_dependency("journey:buy", "ui:checkout-form", "flows_through")
    g.add_dependency("journey:buy", "ui:cart", "flows_through")
    g.add_dependency("journey:login", "ui:cart", "flows_through")
    # tests -> journeys
    g.add_dependency("test:checkout", "journey:buy", "covers")
    return g


# --------------------------------------------------------------------------- #
# Phase 6 — knowledge graph
# --------------------------------------------------------------------------- #
def test_impact_of_is_transitive():
    g = _graph()
    # changing api:payments breaks the checkout form, the checkout test,
    # the checkout requirement, and the buy journey.
    impact = g.impact_of("api:payments")
    assert {"ui:checkout-form", "test:checkout", "req:checkout", "journey:buy"} <= impact


def test_affected_queries():
    g = _graph()
    # api:orders → ui:cart → (tests cart-add/login, journeys login/buy, req:login);
    # journey:buy → test:checkout, so checkout is transitively affected too.
    assert g.affected_tests("api:orders") == {"test:cart-add", "test:login", "test:checkout"}
    assert g.affected_requirements("api:orders") == {"req:login"}
    assert g.affected_requirements("api:payments") == {"req:checkout"}
    assert g.affected_journeys("api:payments") == {"journey:buy"}


def test_explain_impact_shape():
    g = _graph()
    expl = g.explain_impact("api:orders")
    assert set(expl) == {"node", "requirements", "tests", "user_journeys"}
    assert "test:cart-add" in expl["tests"]


def test_unknown_node_type_rejected():
    g = QualityGraph()
    with pytest.raises(ValueError):
        g.add_node("x", "not-a-type")


def test_dependency_on_unknown_node_rejected():
    g = QualityGraph()
    g.add_node("a", "api")
    with pytest.raises(KeyError):
        g.add_dependency("a", "missing", "calls")


# --------------------------------------------------------------------------- #
# Phase 5 — change-aware regression
# --------------------------------------------------------------------------- #
def test_map_changed_files():
    rules = [
        {"prefix": "src/api/orders", "component": "api:orders"},
        {"prefix": "src/ui/checkout", "component": "ui:checkout-form"},
    ]
    got = map_changed_files(
        ["src/api/orders/service.py", "src/ui/checkout/form.tsx", "README.md"],
        rules,
    )
    assert got == {"api:orders", "ui:checkout-form"}


def test_analyze_change_risk_ranking():
    g = _graph()
    analysis = analyze_change(g, ["api:orders"])
    assert set(analysis["affected_tests"]) == {"test:cart-add", "test:login", "test:checkout"}
    assert {r["test"] for r in analysis["risk_ranked_tests"]} == set(
        analysis["affected_tests"]
    )


def test_regression_plan_selects_minimal_set():
    g = _graph()
    rules = [{"prefix": "src/api/orders", "component": "api:orders"}]
    plan = regression_plan(g, ["src/api/orders/x.py"], rules, max_tests=1)
    assert plan["changed_components"] == ["api:orders"]
    assert len(plan["selected_tests"]) == 1
    assert plan["selected_tests"][0] in {"test:cart-add", "test:login"}


# --------------------------------------------------------------------------- #
# Phase 7 — production intelligence
# --------------------------------------------------------------------------- #
def test_detect_test_gaps_ranks_by_traffic():
    g = _graph()
    # journey:login has no test directly covering the journey node
    gaps = detect_test_gaps(g, {"journey:buy": 500, "journey:login": 9000})
    # login has high traffic and no covering test -> top risk
    top = gaps[0]
    assert top["journey"] == "journey:login"
    assert top["covering_tests"] == []


def test_production_risk_report_suggests_tests():
    g = _graph()
    report = production_risk_report(g, {"journey:login": 9000}, top_n=2)
    assert report["suggested_tests"]
    assert report["suggested_tests"][0]["journey"] == "journey:login"


# --------------------------------------------------------------------------- #
# Phase 8 — continuous QE loop
# --------------------------------------------------------------------------- #
def test_continuous_qe_loop_plan():
    g = _graph()
    engine = ContinuousQEEngine(g)
    plan = engine.iterate(
        changed_components=["api:payments"],
        journey_traffic={"journey:login": 9000},
    )
    assert plan["stage"] == "planned"
    assert "test:checkout" in plan["selected_tests"]
    assert engine.history  # one tick recorded


# --------------------------------------------------------------------------- #
# Phase 9 — enterprise scaffold
# --------------------------------------------------------------------------- #
def test_rbac_roles():
    assert role_can("owner", "org.billing")
    assert role_can("admin", "org.manage")
    assert not role_can("admin", "org.billing")
    assert role_can("member", "test.run")
    assert not role_can("viewer", "test.heal")
    assert not role_can("unknown", "test.run")


def test_access_control_authorize_and_audit():
    ac = AccessControl()
    ac.create_org("org1", "Acme")
    ac.create_project("proj1", "org1", "Checkout")
    ac.add_member("org1", "alice", "admin")
    ac.add_member("org1", "bob", "viewer")

    assert ac.authorize("alice", "org1", "test.heal") is True
    assert ac.authorize("bob", "org1", "test.heal") is False
    assert len(ac.audit_for("bob")) == 1
    assert ac.usage_summary("org1")["members"] == 2
    assert ac.usage_summary("org1")["projects"] == 1


def test_access_control_rejects_unknown_org_and_role():
    ac = AccessControl()
    with pytest.raises(ValueError):
        ac.add_member("org1", "alice", "superuser")  # unknown role, org not checked first
    ac.create_org("org1", "Acme")
    with pytest.raises(KeyError):
        ac.add_member("org2", "alice", "admin")  # unknown org
