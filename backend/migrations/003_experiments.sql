-- ============================================================================
-- Migration 003: Experiments and Mutation Lab Schema
-- ============================================================================

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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_experiments_task_id ON experiments(task_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC);
