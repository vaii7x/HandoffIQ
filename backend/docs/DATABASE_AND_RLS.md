# Database Architecture & Row Level Security (RLS) Guide

## 1. Overview

HandoffIQ utilizes a PostgreSQL 15+ database hosted on Supabase for persistent storage of multi-agent tasks, canonical requirements, context handoffs, validation issues, and workflow audit logs.

Persistence is configuration-driven:
- **`MOCK_MODE=true` (Default)**: Uses thread-safe in-memory repositories. No Supabase connection or credentials required.
- **`MOCK_MODE=false`**: Connects to live Supabase Postgres via PostgREST using `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

---

## 2. Running Migrations

The database migration is located at:
`backend/migrations/001_initial_schema.sql`

### Option A: Via Supabase Dashboard (SQL Editor)
1. Open your Supabase project dashboard.
2. Navigate to the **SQL Editor**.
3. Paste the contents of `backend/migrations/001_initial_schema.sql` and click **Run**.

### Option B: Via Supabase CLI
```bash
supabase db push
# Or apply directly via psql:
psql "<YOUR_SUPABASE_DB_CONNECTION_STRING>" -f backend/migrations/001_initial_schema.sql
```

---

## 3. Schema Architecture

| Table | Primary Key | Key Constraints & Relationships | Purpose |
| :--- | :--- | :--- | :--- |
| `tasks` | `id` (UUID) | None | Core user task records, lifecycle status, stage, progress. |
| `requirements` | `(task_id, id)` | `FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE`, `UNIQUE (task_id, id)` | Canonical requirements (`R001`, `R002`, ...). `original_text` is strictly immutable. |
| `handoffs` | `id` (UUID) | `FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE` | Records of context transferred between agents with validation status. |
| `validation_issues` | `id` (text) | `FOREIGN KEY (handoff_id) REFERENCES handoffs(id) ON DELETE CASCADE` | Fine-grained discrepancies (`omission`, `semantic_drift`, `contradiction`, etc.). |
| `workflow_events` | `id` (UUID) | `FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE` | Append-only audit trail with UTC timestamps. |
| `agent_runs` | `id` (UUID) | `FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE` | Execution history of agent roles (researcher, coder, tester, reviewer). |

---

## 4. Security & Row Level Security (RLS) Policies

### Backend Service Role Architecture
- The backend FastAPI application runs as an administrative orchestrator using `SUPABASE_SERVICE_ROLE_KEY`.
- In Supabase, the `service_role` has the `BYPASSRLS` attribute by design, allowing the backend orchestration pipeline to coordinate cross-agent tasks without per-user impersonation barriers.
- **NEVER** expose `SUPABASE_SERVICE_ROLE_KEY` to the browser or frontend clients.

### Client & Authenticated User Policies
Row Level Security is enabled on **all six tables**:
```sql
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE handoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
```

Default policies included in `001_initial_schema.sql`:
- **Anonymous (`anon`) role**: Disallowed by default (no policies permit anonymous read/write).
- **Authenticated (`authenticated`) role**: Read-only access to tasks, requirements, handoffs, issues, events, and runs.

### Production Security Notice
> [!WARNING]
> While RLS is fully enabled and service-role separation is enforced, multi-tenant isolation requires adding a `user_id UUID REFERENCES auth.users(id)` column to `tasks` and restricting `SELECT` / `UPDATE` policies to `auth.uid() = user_id`.
> Do not claim the deployment is multi-tenant production-secure until end-user JWT authentication and tenant-scoped policies are active.

---

## 5. Failure Handling & Error Codes

Database errors from PostgREST/network layers are translated into consistent JSON API errors:

| Failure Mode | API Error Code | HTTP Status | Description |
| :--- | :--- | :--- | :--- |
| Missing Task / Record | `TASK_NOT_FOUND` / `NOT_FOUND` | `404` | Task or entity does not exist in the database. |
| Unique Constraint Violation | `CONSTRAINT_VIOLATION` | `409` | Conflict on duplicate keys (e.g. requirement ID clash). |
| Database Timeout | `DATABASE_TIMEOUT` | `503` | PostgREST or PostgreSQL query timed out. |
| Connection Failure | `DATABASE_CONNECTION_ERROR` | `503` | Unable to connect to Supabase host. |
| Invalid / Missing Configuration | `CONFIGURATION_ERROR` | `500` | Placeholder or missing Supabase credentials when `MOCK_MODE=false`. |
