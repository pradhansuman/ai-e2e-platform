"""Tests for the Understanding agent (Requirements | Risks | User Journeys)."""
from app.agents.understanding import fallback_understand


def test_fallback_extracts_risks_from_model():
    model = {
        "risk_areas": [
            {"area": "Payments", "description": "card handling", "severity": "critical"},
        ],
        "business_workflows": [],
        "pages": [],
    }
    u = fallback_understand(model)
    assert u.risks[0].area == "Payments"
    assert u.risks[0].severity == "critical"
    assert u.risks[0].risk_id == "RISK-01"


def test_fallback_extracts_user_journeys():
    model = {
        "risk_areas": [],
        "business_workflows": [
            {"name": "Checkout", "steps": ["add to cart", "pay"], "entry_point": "/cart"},
        ],
        "pages": [],
    }
    u = fallback_understand(model)
    assert u.user_journeys[0].name == "Checkout"
    assert u.user_journeys[0].steps == ["add to cart", "pay"]
    assert u.user_journeys[0].entry_point == "/cart"


def test_fallback_derives_requirements_from_forms():
    model = {
        "risk_areas": [],
        "business_workflows": [],
        "pages": [{"forms": [{"name": "login"}]}],
    }
    u = fallback_understand(model)
    assert any("login" in r for r in u.requirements)


def test_fallback_empty_model_is_safe():
    u = fallback_understand({})
    assert u.requirements == []
    assert u.risks == []
    assert u.user_journeys == []
