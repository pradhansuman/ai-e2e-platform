"""Enterprise platform scaffold (Phase 9): multi-tenancy, RBAC, audit.

Core abstractions for the product surface — organizations, projects, roles,
permissions, and an append-only audit log. This is the *authorization* layer,
kept storage-agnostic (in-memory) so it can back any datastore.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Permissions + roles
# --------------------------------------------------------------------------- #
PERMISSIONS = (
    "project.read",
    "project.write",
    "test.read",
    "test.run",
    "test.heal",
    "test.generate",
    "report.read",
    "org.manage",
    "org.billing",
)

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": set(PERMISSIONS),
    "admin": {
        "project.read", "project.write",
        "test.read", "test.run", "test.heal", "test.generate",
        "report.read", "org.manage",
    },
    "member": {
        "project.read",
        "test.read", "test.run", "test.heal", "test.generate",
        "report.read",
    },
    "viewer": {"project.read", "test.read", "report.read"},
}

ROLES = tuple(ROLE_PERMISSIONS.keys())


def role_can(role: str, permission: str) -> bool:
    if role not in ROLE_PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS[role]


# --------------------------------------------------------------------------- #
# Tenancy
# --------------------------------------------------------------------------- #
@dataclass
class Organization:
    id: str
    name: str


@dataclass
class Project:
    id: str
    org_id: str
    name: str


@dataclass
class Membership:
    org_id: str
    user_id: str
    role: str


@dataclass
class AuditEvent:
    actor: str
    action: str
    resource: str
    details: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Access control + audit
# --------------------------------------------------------------------------- #
class AccessControl:
    """In-memory RBAC over organizations and projects."""

    def __init__(self) -> None:
        self.orgs: dict[str, Organization] = {}
        self.projects: dict[str, Project] = {}
        self.memberships: list[Membership] = []
        self.audit: list[AuditEvent] = []

    # -- tenancy ----------------------------------------------------------- #
    def create_org(self, org_id: str, name: str) -> Organization:
        self.orgs[org_id] = Organization(org_id, name)
        return self.orgs[org_id]

    def create_project(self, project_id: str, org_id: str, name: str) -> Project:
        if org_id not in self.orgs:
            raise KeyError(f"unknown org {org_id!r}")
        self.projects[project_id] = Project(project_id, org_id, name)
        return self.projects[project_id]

    def add_member(self, org_id: str, user_id: str, role: str) -> None:
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"unknown role {role!r}")
        if org_id not in self.orgs:
            raise KeyError(f"unknown org {org_id!r}")
        self.memberships.append(Membership(org_id, user_id, role))

    def role_of(self, user_id: str, org_id: str) -> str | None:
        for m in self.memberships:
            if m.org_id == org_id and m.user_id == user_id:
                return m.role
        return None

    # -- authz ------------------------------------------------------------- #
    def authorize(self, user_id: str, org_id: str, permission: str) -> bool:
        role = self.role_of(user_id, org_id)
        allowed = role is not None and role_can(role, permission)
        self.audit.append(
            AuditEvent(user_id, "authorize", permission, {"org_id": org_id, "allowed": allowed})
        )
        return allowed

    def can_heal(self, user_id: str, org_id: str) -> bool:
        return self.authorize(user_id, org_id, "test.heal")

    # -- audit ------------------------------------------------------------- #
    def audit_for(self, actor: str) -> list[AuditEvent]:
        return [e for e in self.audit if e.actor == actor]

    def usage_summary(self, org_id: str) -> dict[str, Any]:
        """Per-org usage counters (foundation for usage limits / cost controls)."""
        members = [m for m in self.memberships if m.org_id == org_id]
        projects = [p for p in self.projects.values() if p.org_id == org_id]
        return {
            "org_id": org_id,
            "members": len(members),
            "projects": len(projects),
            "audit_events": len(self.audit),
        }
