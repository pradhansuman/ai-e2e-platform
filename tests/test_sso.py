"""Tests for SSO claim validation."""
import pytest

from app.intelligence.sso import (
    InvalidToken,
    OIDCConfig,
    authenticate,
    identity_from_claims,
    validate_id_token_claims,
)

CONFIG = OIDCConfig(issuer="https://idp.example", audience="my-client")


def _claims(**overrides):
    base = {
        "iss": "https://idp.example",
        "aud": "my-client",
        "sub": "user-123",
        "email": "a@b.c",
        "name": "Alice",
        "iat": 1_700_000_000,
        "exp": 4_000_000_000,
    }
    base.update(overrides)
    return base


def test_valid_claims_authenticate():
    ident = authenticate(_claims(), CONFIG, now=1_700_000_100)
    assert ident == {"user_id": "user-123", "email": "a@b.c", "name": "Alice"}


def test_wrong_issuer_rejected():
    with pytest.raises(InvalidToken):
        validate_id_token_claims(_claims(iss="https://evil.example"), CONFIG)


def test_wrong_audience_rejected():
    with pytest.raises(InvalidToken):
        validate_id_token_claims(_claims(aud="other-client"), CONFIG)


def test_expired_rejected():
    with pytest.raises(InvalidToken):
        validate_id_token_claims(_claims(exp=1_000), CONFIG, now=2_000)


def test_audience_list_accepted():
    validate_id_token_claims(_claims(aud=["my-client", "other"]), CONFIG)


def test_identity_falls_back_to_username():
    claims = _claims()
    del claims["name"]
    claims["preferred_username"] = "alice01"
    assert identity_from_claims(claims)["name"] == "alice01"
