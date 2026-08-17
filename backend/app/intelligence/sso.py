"""SSO scaffold (Phase 9): OIDC ID-token claim validation + identity mapping.

Validates the *claims* of an OIDC ID token (issuer, audience, expiry, not-before)
and maps them to a platform identity. Signature verification against the IdP's
JWKS is the caller's responsibility (requires a JWT library + the IdP's keys);
this module owns the claim-semantics layer, which is fully unit-testable.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


class InvalidToken(Exception):
    pass


@dataclass
class OIDCConfig:
    issuer: str
    audience: str  # client_id
    leeway_seconds: int = 30


def validate_id_token_claims(
    claims: dict[str, Any],
    config: OIDCConfig,
    *,
    now: int | None = None,
) -> None:
    """Raise ``InvalidToken`` if the claims fail OIDC validation."""
    now = int(now if now is not None else time.time())
    if claims.get("iss") != config.issuer:
        raise InvalidToken(f"issuer mismatch: {claims.get('iss')!r}")
    aud = claims.get("aud")
    # aud may be a string or a list of strings.
    auds = aud if isinstance(aud, list) else [aud]
    if config.audience not in auds:
        raise InvalidToken(f"audience {config.audience!r} not in {auds!r}")
    if claims.get("exp", 0) <= now - config.leeway_seconds:
        raise InvalidToken("token expired")
    if claims.get("iat", 0) > now + config.leeway_seconds:
        raise InvalidToken("token issued in the future")


def identity_from_claims(claims: dict[str, Any]) -> dict[str, str]:
    """Map OIDC claims to a platform identity (user_id, email, name)."""
    return {
        "user_id": str(claims.get("sub", "")),
        "email": claims.get("email", "") or "",
        "name": claims.get("name", "") or claims.get("preferred_username", "") or "",
    }


def authenticate(
    claims: dict[str, Any], config: OIDCConfig, *, now: int | None = None
) -> dict[str, str]:
    """Validate claims and return the platform identity, or raise."""
    validate_id_token_claims(claims, config, now=now)
    return identity_from_claims(claims)
