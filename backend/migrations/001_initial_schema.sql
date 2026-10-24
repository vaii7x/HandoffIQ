-- ============================================================================
-- HandoffIQ - Database Schema Migration 001
-- Multi-agent reliability, canonical requirements, handoffs, and workflow events
-- Target: PostgreSQL 15+ / Supabase
-- ============================================================================

-- Ensure pgcrypto or gen_random_uuid() is available
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- 1. Tasks Table
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. Canonical Requirements Table
-- Requirement IDs (R001, R002) are scoped and unique per task.
-- original_text is preserved and immutable.
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 3. Handoffs Table
-- Captures state transferred between agents with validation status.
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 4. Validation Issues Table
-- Discrepancies and integrity failures tracked for each handoff.
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 5. Workflow Events Table
-- Append-only audit log of task lifecycle, handoffs, and repairs.
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 6. Agent Runs Table
-- Execution record for agent phases (researcher, coder, tester, reviewer).
-- ----------------------------------------------------------------------------
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

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE handoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

-- Service Role Policy:
-- The backend uses the SUPABASE_SERVICE_ROLE_KEY which automatically bypasses RLS in Supabase.
-- For standard authenticated or anon access, explicit policies are required:

-- Authenticated Users: Read-only access to tasks and artifacts
CREATE POLICY "Authenticated users can read tasks"
    ON tasks FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read requirements"
    ON requirements FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read handoffs"
    ON handoffs FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read validation issues"
    ON validation_issues FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read workflow events"
    ON workflow_events FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read agent runs"
    ON agent_runs FOR SELECT
    TO authenticated
    USING (true);

-- Anonymous Users: Denied by default (no policies defined for anon role).
