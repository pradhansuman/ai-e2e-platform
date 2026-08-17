"""Tests for JWT authentication + RBAC enforcement."""
from app import config
from app.security import Principal, Role, can_execute, create_token, decode_token


def test_token_roundtrip():
    token = create_token("alice", "engineer", 60)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"
    assert payload["role"] == "engineer"


def test_tampered_token_rejected():
    token = create_token("alice", "engineer", 60)
    assert decode_token(token + "x") is None


def test_wrong_secret_rejected():
    token = create_token("alice", "engineer", 60)
    assert decode_token(token, secret="w" * 32) is None


def test_expired_token_rejected():
    token = create_token("alice", "engineer", expires_minutes=-1)
    assert decode_token(token) is None


def test_rbac_enforced_when_auth_required():
    original = config.settings.allow_unauthenticated
    config.settings.allow_unauthenticated = False
    try:
        viewer = Principal("v", Role.VIEWER)
        engineer = Principal("e", Role.ENGINEER)
        admin = Principal("a", Role.ADMIN)
        assert not can_execute(viewer, "execute_playwright_test")
        assert can_execute(engineer, "execute_playwright_test")
        assert can_execute(viewer, "inspect_page")
        assert can_execute(admin, "create_test_case")
    finally:
        config.settings.allow_unauthenticated = original
