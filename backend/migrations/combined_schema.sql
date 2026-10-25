-- ============================================================================
-- HandoffIQ - Complete Database Schema Migration (PostgreSQL / Supabase)
-- Apply this file in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/krvemzxxkjezawvvmvav/sql/new
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL CHECK (char_length(title) >= 1),
    original_request TEXT NOT NULL CHECK (char_length(original_request) >= 1),
    status VARCHAR(50) NOT NULL DEFAULT 'queued' 
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'awaiting_review', 'cancelled')),
    current_stage VARCHAR(100) DEFAULT 'registration',
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);

-- 2. Canonical Requirements Table
CREATE TABLE IF NOT EXISTS requirements (
    id VARCHAR(50) NOT NULL,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL CHECK (char_length(original_text) >= 1),
    priority VARCHAR(50) NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(50) NOT NULL DEFAULT 'registered'
        CHECK (status IN ('registered', 'preserved', 'altered', 'missing', 'conflicting', 'implemented', 'tested', 'verified', 'failed', 'awaiting_review')),
    description TEXT NOT NULL DEFAULT '',
    related_files JSONB NOT NULL DEFAULT '[]'::jsonb,
    related_test_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT pk_requirements PRIMARY KEY (task_id, id),
    CONSTRAINT uq_task_requirement UNIQUE (task_id, id)
);

CREATE INDEX IF NOT EXISTS idx_requirements_task_id ON requirements (task_id);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements (status);

-- 3. Handoffs Table
CREATE TABLE IF NOT EXISTS handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    source_agent VARCHAR(100) NOT NULL CHECK (char_length(source_agent) >= 1),
    target_agent VARCHAR(100) NOT NULL CHECK (char_length(target_agent) >= 1),
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'validated', 'repaired', 'blocked', 'awaiting_review', 'failed')),
    requirement_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_handoffs_task_id ON handoffs (task_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_status ON handoffs (status);
CREATE INDEX IF NOT EXISTS idx_handoffs_created_at ON handoffs (created_at DESC);

-- 4. Validation Issues Table
CREATE TABLE IF NOT EXISTS validation_issues (
    id VARCHAR(100) PRIMARY KEY,
    handoff_id UUID NOT NULL REFERENCES handoffs(id) ON DELETE CASCADE,
    requirement_id VARCHAR(50),
    issue_type VARCHAR(50) NOT NULL
        CHECK (issue_type IN ('omission', 'semantic_drift', 'weakened_constraint', 'contradiction', 'invented_requirement', 'suspicious_instruction', 'schema_error', 'implementation_gap', 'test_failure')),
    severity VARCHAR(50) NOT NULL
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL CHECK (char_length(description) >= 1),
    original_value TEXT,
    observed_value TEXT,
    repair_status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (repair_status IN ('not_needed', 'pending', 'repaired', 'unresolved', 'rejected')),
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_validation_issues_handoff_id ON validation_issues (handoff_id);
CREATE INDEX IF NOT EXISTS idx_validation_issues_type ON validation_issues (issue_type);

-- 5. Workflow Events Table
CREATE TABLE IF NOT EXISTS workflow_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL CHECK (char_length(event_type) >= 1),
    stage VARCHAR(100) NOT NULL CHECK (char_length(stage) >= 1),
    message TEXT NOT NULL CHECK (char_length(message) >= 1),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_workflow_events_task_id ON workflow_events (task_id, timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_workflow_events_type ON workflow_events (event_type);

-- 6. Agent Runs Table
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL
        CHECK (agent_type IN ('researcher', 'coder', 'tester', 'reviewer')),
    status VARCHAR(50) NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'awaiting_review')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    summary TEXT NOT NULL DEFAULT '',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_task_id ON agent_runs (task_id);

-- 7. Code Artifacts Table
CREATE TABLE IF NOT EXISTS code_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    path TEXT NOT NULL CHECK (char_length(path) >= 1),
    language VARCHAR(50) NOT NULL CHECK (char_length(language) >= 1),
    content TEXT NOT NULL,
    requirement_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_code_artifacts_task_id ON code_artifacts (task_id);

-- 8. Test Results Table
CREATE TABLE IF NOT EXISTS test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    requirement_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    test_name TEXT NOT NULL CHECK (char_length(test_name) >= 1),
    tool VARCHAR(100) NOT NULL CHECK (char_length(tool) >= 1),
    test_type VARCHAR(50) NOT NULL DEFAULT 'unit_test'
        CHECK (test_type IN ('compilation', 'linting', 'unit_test', 'integration_test', 'browser_test')),
    status VARCHAR(50) NOT NULL
        CHECK (status IN ('passed', 'failed', 'skipped', 'error')),
    output TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER CHECK (duration_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_test_results_task_id ON test_results (task_id);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results (status);

-- 9. Recovery Attempts Table
CREATE TABLE IF NOT EXISTS recovery_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    requirement_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    failure_summary TEXT NOT NULL CHECK (char_length(failure_summary) >= 1),
    repair_summary TEXT NOT NULL DEFAULT '',
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    test_result_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    regressions JSONB NOT NULL DEFAULT '[]'::jsonb,
    unresolved_failures JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_recovery_attempts_task_id ON recovery_attempts (task_id, attempt_number ASC);
CREATE INDEX IF NOT EXISTS idx_recovery_attempts_status ON recovery_attempts (status);

-- 10. Experiments Table
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'queued' CHECK (status IN ('draft', 'queued', 'running', 'completed', 'failed', 'archived')),
    mutation_types TEXT[] NOT NULL DEFAULT '{}',
    runs INT NOT NULL DEFAULT 1 CHECK (runs >= 1),
    is_simulated BOOLEAN NOT NULL DEFAULT true,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_experiments_task_id ON experiments(task_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC);

-- Enable RLS
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE handoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE recovery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
