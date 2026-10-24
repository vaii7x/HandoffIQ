-- ============================================================================
-- HandoffIQ - Database Schema Migration 002
-- Code artifacts, test execution outcomes, and automated recovery loops
-- Target: PostgreSQL 15+ / Supabase
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Code Artifacts Table
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. Test Results Table
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 3. Recovery Attempts Table
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- Row Level Security (RLS)
-- ----------------------------------------------------------------------------
ALTER TABLE code_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE recovery_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read on code_artifacts" ON code_artifacts
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow anon read on code_artifacts" ON code_artifacts
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow authenticated read on test_results" ON test_results
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow anon read on test_results" ON test_results
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow authenticated read on recovery_attempts" ON recovery_attempts
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow anon read on recovery_attempts" ON recovery_attempts
    FOR SELECT TO anon USING (true);
