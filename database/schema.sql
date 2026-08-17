-- Reference SQL schema for the platform metadata store (spec section 16).
-- The application uses SQLAlchemy + Alembic for migrations; this file serves
-- as a bootstrap for the docker-compose Postgres init and as documentation.

CREATE TABLE IF NOT EXISTS applications (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    url           TEXT NOT NULL,
    repo_url      TEXT,
    spec_url      TEXT,
    credential_ref TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pages (
    id            TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    url           TEXT NOT NULL,
    title         TEXT,
    route         TEXT,
    discovered_components JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_pages_app_url ON pages(application_id, url);

CREATE TABLE IF NOT EXISTS apis (
    id            TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    method        TEXT NOT NULL,
    path          TEXT NOT NULL,
    description   TEXT,
    schema_ref    TEXT
);

CREATE TABLE IF NOT EXISTS requirements (
    id            TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    source        TEXT NOT NULL,
    content       TEXT NOT NULL,
    business_rules JSONB NOT NULL DEFAULT '[]',
    acceptance_criteria JSONB NOT NULL DEFAULT '[]',
    gaps          JSONB NOT NULL DEFAULT '[]',
    embedding_id  TEXT
);

CREATE TABLE IF NOT EXISTS test_cases (
    id            TEXT PRIMARY KEY,
    test_id       TEXT NOT NULL,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    objective     TEXT NOT NULL,
    preconditions JSONB NOT NULL DEFAULT '[]',
    test_data     JSONB NOT NULL DEFAULT '{}',
    steps         JSONB NOT NULL DEFAULT '[]',
    expected_result TEXT NOT NULL,
    risk          TEXT NOT NULL DEFAULT 'medium',
    priority      TEXT NOT NULL DEFAULT 'P3',
    automation_candidate BOOLEAN NOT NULL DEFAULT TRUE,
    coverage_tags JSONB NOT NULL DEFAULT '[]',
    ai_generated  BOOLEAN NOT NULL DEFAULT FALSE,
    accepted      BOOLEAN,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (test_id, application_id)
);
CREATE INDEX IF NOT EXISTS ix_test_cases_priority ON test_cases(priority);

CREATE TABLE IF NOT EXISTS test_runs (
    id            TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    run_id        TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    trigger       TEXT NOT NULL DEFAULT 'manual',
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    summary       JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_test_runs_run_id ON test_runs(run_id);

CREATE TABLE IF NOT EXISTS test_results (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    test_id       TEXT NOT NULL,
    status        TEXT NOT NULL,
    duration_ms   INTEGER,
    step_results  JSONB NOT NULL DEFAULT '[]',
    evidence      JSONB NOT NULL DEFAULT '{}',
    executed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_test_results_run ON test_results(run_id, test_id);
CREATE INDEX IF NOT EXISTS ix_test_results_test ON test_results(test_id);

CREATE TABLE IF NOT EXISTS failures (
    id            TEXT PRIMARY KEY,
    result_id     TEXT REFERENCES test_results(id) ON DELETE SET NULL,
    test_id       TEXT NOT NULL,
    classification TEXT NOT NULL,
    root_cause    TEXT NOT NULL,
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 0,
    evidence      JSONB NOT NULL DEFAULT '[]',
    recommended_fix TEXT,
    affected_tests JSONB NOT NULL DEFAULT '[]',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_failures_test ON failures(test_id, classification);

CREATE TABLE IF NOT EXISTS healing_events (
    id            TEXT PRIMARY KEY,
    test_id       TEXT NOT NULL,
    original_locator TEXT NOT NULL,
    new_locator   TEXT,
    reason        TEXT NOT NULL,
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 0,
    evidence      JSONB NOT NULL DEFAULT '[]',
    approval_status TEXT NOT NULL DEFAULT 'pending',
    approved_by   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_healing_test ON healing_events(test_id);

CREATE TABLE IF NOT EXISTS flakiness_records (
    id            TEXT PRIMARY KEY,
    test_id       TEXT NOT NULL,
    flakiness_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_runs    INTEGER NOT NULL DEFAULT 0,
    pass_fail_sequence JSONB NOT NULL DEFAULT '[]',
    suspected_cause TEXT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_flaky_test ON flakiness_records(test_id);

CREATE TABLE IF NOT EXISTS test_evaluations (
    id            TEXT PRIMARY KEY,
    run_id        TEXT REFERENCES test_runs(id) ON DELETE SET NULL,
    dataset_name  TEXT NOT NULL,
    metric        TEXT NOT NULL,
    score         DOUBLE PRECISION NOT NULL,
    sample        TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_traces (
    id            TEXT PRIMARY KEY,
    run_id        TEXT REFERENCES test_runs(id) ON DELETE SET NULL,
    langsmith_trace_id TEXT,
    node          TEXT NOT NULL,
    tokens_in     INTEGER NOT NULL DEFAULT 0,
    tokens_out    INTEGER NOT NULL DEFAULT 0,
    latency_ms    INTEGER NOT NULL DEFAULT 0,
    payload       JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id            TEXT PRIMARY KEY,
    event_type    TEXT NOT NULL,
    actor         TEXT NOT NULL,
    detail_hash   TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_event ON audit_logs(event_type);
