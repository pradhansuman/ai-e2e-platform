"""Security utilities: secrets, masking, prompt-injection guard, RBAC, audit.

Design goals (per spec section 17):
- Never expose credentials to the LLM unnecessarily.
- Mask PII and secrets before any data reaches a model.
- Guard against prompt injection arriving via application content.
- Enforce role-based access on tool execution.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from .config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Data masking
# --------------------------------------------------------------------------- #

_MASK_RE = re.compile(
    r"(?i)\b("
    + "|".join(settings.pii_fields)
    + r")\b\s*[:=]\s*([^\s,;]+(?:\s+[^\s,;]+)?)"
)


def mask_secrets(text: str) -> str:
    """Replace ``key=value`` / ``key: value`` occurrences of sensitive keys."""
    return _MASK_RE.sub(r"\1=***MASKED***", text)


def mask_dict(data: dict) -> dict:
    """Recursively mask sensitive keys inside arbitrary JSON-like structures."""
    out: dict = {}
    for k, v in data.items():
        if any(p in str(k).lower() for p in settings.pii_fields):
            out[k] = "***MASKED***"
        elif isinstance(v, dict):
            out[k] = mask_dict(v)
        elif isinstance(v, list):
            out[k] = [mask_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = v
    return out


def redact_for_llm(payload: dict) -> dict:
    """Public entry point: mask any payload before it is passed to an LLM."""
    return mask_dict(payload)


# --------------------------------------------------------------------------- #
# Prompt-injection guard
# --------------------------------------------------------------------------- #

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"you are now (a|an) ",
    r"system prompt",
    r"<\|?im_start\|?>",
    r"<\|?system\|?>",
    r"### System:",
    r"reveal your (instructions|prompt|rules)",
    r"act as (dan|jailbreak)",
]


def detect_prompt_injection(text: str) -> bool:
    """Heuristic guard: return True if the text looks like an injection.

    This is a first line of defense, not a replacement for model-level
    input classifiers. Application-derived content should be treated as
    untrusted data and rendered, never executed as instructions.
    """
    lowered = text.lower()
    return any(re.search(p, lowered) for p in _INJECTION_PATTERNS)


def sanitize_untrusted_content(content: str) -> str:
    """Wrap untrusted (application) content so the model treats it as data."""
    if detect_prompt_injection(content):
        logger.warning("Prompt-injection pattern detected; content quarantined.")
        return "<UNTRUSTED CONTENT QUARANTINED FOR SECURITY REVIEW>"
    return content


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #

class Role(str, Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"


# Tool -> minimum role required to execute it.
TOOL_PERMISSIONS: dict[str, Role] = {
    "execute_playwright_test": Role.ENGINEER,
    "create_test_case": Role.ENGINEER,
    "update_test_case": Role.ENGINEER,
    "apply_self_healing": Role.ENGINEER,
    "capture_screenshot": Role.ENGINEER,
    "discover_application": Role.ENGINEER,
    "inspect_page": Role.VIEWER,
    "get_dom": Role.VIEWER,
    "get_network_logs": Role.VIEWER,
    "query_test_history": Role.VIEWER,
    "search_requirements": Role.VIEWER,
    "search_test_cases": Role.VIEWER,
    "analyze_failure": Role.VIEWER,
}


@dataclass
class Principal:
    """Authenticated caller context."""

    user_id: str
    role: Role = Role.VIEWER
    scopes: set[str] = field(default_factory=set)


def can_execute(principal: Principal | None, tool_name: str) -> bool:
    """Return whether ``principal`` may run ``tool_name``.

    In unauthenticated dev mode everything is allowed; otherwise the
    minimum role from ``TOOL_PERMISSIONS`` is enforced.
    """
    if settings.allow_unauthenticated or principal is None:
        return True
    required = TOOL_PERMISSIONS.get(tool_name, Role.ADMIN)
    order = {Role.VIEWER: 0, Role.ENGINEER: 1, Role.ADMIN: 2}
    return order[principal.role] >= order[required]


# --------------------------------------------------------------------------- #
# Audit logging
# --------------------------------------------------------------------------- #

def audit_event(event_type: str, actor: str, detail: dict) -> None:
    """Append a structured audit record. Production: persist to the
    ``audit_logs`` table (see models.AuditLog). For now, structured logging.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "actor": actor,
        "detail_hash": hashlib.sha256(str(detail).encode()).hexdigest()[:16],
    }
    logger.info("AUDIT %s", record)


# --------------------------------------------------------------------------- #
# JWT authentication (HS256)
# --------------------------------------------------------------------------- #

import jwt as _pyjwt  # noqa: E402


def create_token(
    user_id: str,
    role: str = "viewer",
    expires_minutes: int = 60,
    secret: str | None = None,
) -> str:
    """Mint a signed JWT carrying the caller's identity + role."""
    secret = secret or settings.secret_key
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return _pyjwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str | None = None) -> dict | None:
    """Verify + decode a JWT. Returns None on any validation failure."""
    secret = secret or settings.secret_key
    try:
        return _pyjwt.decode(token, secret, algorithms=["HS256"])
    except _pyjwt.PyJWTError:
        return None
