"""Enterprise integrations (Phase 9): Jira / GitHub / Slack adapters.

Message formatting is pure and testable; network delivery goes through a
pluggable transport (defaults to httpx) so tests can inject a recorder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# A transport receives (url, payload, headers) and returns a response dict.
Transport = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]


def _httpx_transport(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:  # pragma: no cover - optional dependency
        return {"ok": False, "error": "httpx not installed"}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=10)
        return {"ok": r.status_code < 400, "status": r.status_code, "body": r.text}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@dataclass
class SlackNotifier:
    """Posts a message block to a Slack incoming webhook."""

    webhook_url: str
    transport: Transport = _httpx_transport

    def format(self, title: str, text: str, *, level: str = "info") -> dict[str, Any]:
        color = {"info": "#36a64f", "warning": "#ffcc00", "error": "#ff0000"}.get(
            level, "#36a64f"
        )
        return {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": text,
                }
            ]
        }

    def notify(self, title: str, text: str, *, level: str = "info") -> dict[str, Any]:
        return self.transport(
            self.webhook_url, self.format(title, text, level=level), {}
        )


@dataclass
class JiraClient:
    """Minimal Jira REST client for issue creation."""

    base_url: str
    email: str
    api_token: str
    project_key: str
    transport: Transport = _httpx_transport

    def _headers(self) -> dict[str, str]:
        import base64

        token = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def format_issue(
        self, summary: str, description: str, *, issue_type: str = "Bug"
    ) -> dict[str, Any]:
        return {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }
        }

    def create_issue(
        self, summary: str, description: str, *, issue_type: str = "Bug"
    ) -> dict[str, Any]:
        return self.transport(
            f"{self.base_url.rstrip('/')}/rest/api/2/issue",
            self.format_issue(summary, description, issue_type=issue_type),
            self._headers(),
        )


@dataclass
class GitHubClient:
    """Minimal GitHub REST client for issue creation / PR comments."""

    token: str
    repo: str  # "owner/repo"
    transport: Transport = _httpx_transport

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        }

    def format_issue(self, title: str, body: str, *, labels: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return payload

    def create_issue(
        self, title: str, body: str, *, labels: list[str] | None = None
    ) -> dict[str, Any]:
        return self.transport(
            f"https://api.github.com/repos/{self.repo}/issues",
            self.format_issue(title, body, labels=labels),
            self._headers(),
        )
