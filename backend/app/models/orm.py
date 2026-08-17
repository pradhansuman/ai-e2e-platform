"""SQLAlchemy ORM models for the platform's metadata store.

Maps 1:1 to the entity list in spec section 16. Relationships and indexes are
declared explicitly so Postgres can serve the dashboard and the AI tools'
history lookups efficiently.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(Text)
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    spec_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Encrypted-at-rest credential reference; never store raw secrets here.
    credential_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    pages: Mapped[list["Page"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (Index("ix_pages_app_url", "application_id", "url"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    route: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovered_components: Mapped[dict] = mapped_column(JSON, default=dict)

    application: Mapped["Application"] = relationship(back_populates="pages")


class ApiEndpoint(Base):
    __tablename__ = "apis"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_ref: Mapped[str | None] = mapped_column(Text, nullable=True)


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    source: Mapped[str] = mapped_column(String(32))  # user_story | spec | doc
    content: Mapped[str] = mapped_column(Text)
    business_rules: Mapped[list] = mapped_column(JSON, default=list)
    acceptance_criteria: Mapped[list] = mapped_column(JSON, default=list)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    application: Mapped["Application"] = relationship(back_populates="requirements")


class TestCase(Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("test_id", "application_id", name="uq_test_case"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    test_id: Mapped[str] = mapped_column(String(128))
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(512))
    objective: Mapped[str] = mapped_column(Text)
    preconditions: Mapped[list] = mapped_column(JSON, default=list)
    test_data: Mapped[dict] = mapped_column(JSON, default=dict)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    expected_result: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(16), default="medium")
    priority: Mapped[str] = mapped_column(String(8), default="P3", index=True)
    automation_candidate: Mapped[bool] = mapped_column(Boolean, default=True)
    coverage_tags: Mapped[list] = mapped_column(JSON, default=list)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # human review
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    application: Mapped["Application"] = relationship(back_populates="test_cases")


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    trigger: Mapped[str] = mapped_column(String(32), default="manual")  # ci | manual | schedule
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    summary: Mapped[dict] = mapped_column(JSON, default=dict)


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (Index("ix_test_results_run", "run_id", "test_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"))
    test_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step_results: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Failure(Base):
    __tablename__ = "failures"
    __table_args__ = (Index("ix_failures_test", "test_id", "classification"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    result_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_results.id", ondelete="SET NULL"), nullable=True
    )
    test_id: Mapped[str] = mapped_column(String(128))
    classification: Mapped[str] = mapped_column(String(32), index=True)
    root_cause: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    recommended_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_tests: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealingEvent(Base):
    __tablename__ = "healing_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    test_id: Mapped[str] = mapped_column(String(128), index=True)
    original_locator: Mapped[str] = mapped_column(Text)
    new_locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    approval_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FlakinessRecord(Base):
    __tablename__ = "flakiness_records"
    __table_args__ = (Index("ix_flaky_test", "test_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    test_id: Mapped[str] = mapped_column(String(128))
    flakiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    pass_fail_sequence: Mapped[list] = mapped_column(JSON, default=list)
    suspected_cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class TestEvaluation(Base):
    __tablename__ = "test_evaluations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_runs.id", ondelete="SET NULL"), nullable=True
    )
    dataset_name: Mapped[str] = mapped_column(String(255))
    metric: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    sample: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AiTrace(Base):
    __tablename__ = "ai_traces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_runs.id", ondelete="SET NULL"), nullable=True
    )
    langsmith_trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    node: Mapped[str] = mapped_column(String(64))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(255))
    detail_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
