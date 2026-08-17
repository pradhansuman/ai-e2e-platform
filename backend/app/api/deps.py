"""API dependencies: authentication and RBAC."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from ..config import settings
from ..security import Principal, Role, decode_token


def get_principal(
    authorization: str | None = Header(default=None),
) -> Principal | None:
    """Resolve the caller. In dev (allow_unauthenticated) this is a no-op;
    otherwise a bearer token (JWT or admin token) is required."""
    if settings.allow_unauthenticated:
        return Principal(user_id="dev", role=Role.ADMIN, scopes={"*"})
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    if settings.admin_api_token and token == settings.admin_api_token:
        return Principal(user_id="admin", role=Role.ADMIN, scopes={"*"})

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    try:
        role = Role(payload.get("role", "viewer"))
    except ValueError:
        role = Role.VIEWER
    return Principal(
        user_id=payload.get("sub", "unknown"),
        role=role,
        scopes=set(payload.get("scopes", [])),
    )


PrincipalDep = Depends(get_principal)
