# HandoffIQ - Backend Foundation

Backend service for **HandoffIQ**, a multi-agent AI reliability and context handoff orchestration platform.

This foundation establishes the core application configuration, shared Pydantic v2 domain schemas, OpenAPI documentation, centralized error handling, and test suites.

---

## 1. Prerequisites

- **Python**: Version 3.11 or higher (Tested with Python 3.11+)
- **Operating System**: Windows, macOS, or Linux

---

## 2. Virtual Environment Setup

Create and activate an isolated Python virtual environment inside the `backend` directory:

### Windows (PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Windows (CMD)
```cmd
cd backend
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### macOS / Linux (bash/zsh)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Dependency Installation

With the virtual environment active, install all required dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Environment Variable Configuration

Create a local `.env` configuration file from the provided `.env.example`:

### Windows (PowerShell)
```powershell
Copy-Item .env.example .env
```

### macOS / Linux
```bash
cp .env.example .env
```

### Configuration Parameters

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | string | `HandoffIQ` | Application name |
| `APP_ENV` | string | `development` | Operating environment (`development`, `staging`, `production`) |
| `API_PREFIX` | string | `/api` | Base routing prefix for application endpoints |
| `FRONTEND_ORIGIN` | string | `http://localhost:3000` | Allowed CORS origin for the React frontend |
| `SUPABASE_URL` | string | `http://localhost:54321` | Supabase API connection URL |
| `SUPABASE_ANON_KEY` | string | `placeholder-anon-key` | Supabase public anonymous API key |
| `SUPABASE_SERVICE_ROLE_KEY` | string (secret) | `placeholder-service-role-key` | Supabase admin service-role key (**NEVER EXPOSE**) |
| `GEMINI_API_KEY` | string (secret) | `placeholder-gemini-key` | Google Gemini API key (**NEVER EXPOSE**) |
| `MOCK_MODE` | boolean | `true` | When `true`, enables mock data without external cloud dependencies |

> [!WARNING]
> Never commit `.env` or hard-code real credentials. The service role key and Gemini API key are kept private and never exposed via any API endpoint.

---

## 5. Database Migrations & Persistence Modes

HandoffIQ supports two persistence modes controlled by the `MOCK_MODE` environment variable:

1. **Local Development (`MOCK_MODE=true`)**: Runs entirely in-memory with zero external dependencies. No Supabase credentials or database needed.
2. **Persistent Storage (`MOCK_MODE=false`)**: Stores all tasks, canonical requirements, handoffs, and workflow events in PostgreSQL on Supabase.
   - If `MOCK_MODE=false` and `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` are missing or placeholder values, the application **fails immediately with `ConfigurationError`** to prevent silent data loss.

### Running SQL Migrations
Apply the initial PostgreSQL schema and Row Level Security (RLS) policies:
```bash
# Apply via Supabase CLI
supabase db push

# Or execute SQL migration script directly in Supabase SQL Editor
# File: backend/migrations/001_initial_schema.sql
```

For full database architecture and RLS policy documentation, see:
- [backend/docs/DATABASE_AND_RLS.md](docs/DATABASE_AND_RLS.md)

---

## 6. Startup Commands

Start the FastAPI application with Uvicorn:

### Exact Uvicorn Startup Command
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

By default, the server will be accessible at:
- Base API: `http://localhost:8000`
- API Prefix: `http://localhost:8000/api`

---

## 7. Testing

Run the automated test suite using `pytest`:

### Exact Pytest Command
From within the `backend` directory:
```bash
pytest tests -v
```

Or from the repository root:
```bash
pytest backend/tests -v
```

---

## 8. Endpoints & API Documentation

| Endpoint | Method | Status | Description |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | `200` | Root health check and mock mode diagnostic |
| `/api/health` | `GET` | `200` | Prefixed health check endpoint |
| `/api/tasks` | `POST` | `201` | Register task, audit events & extract requirements |
| `/api/tasks` | `GET` | `200` | List all registered tasks |
| `/api/tasks/{task_id}` | `GET` | `200` / `404` | Get task details, requirements, runs, and summary |
| `/api/tasks/{task_id}/requirements` | `GET` | `200` / `404` | Get canonical requirements for a task |
| `/api/tasks/{task_id}/events` | `GET` | `200` / `404` | Get workflow audit log events for a task |
| `/api/tasks/{task_id}/handoffs` | `POST` | `201` / `404` | Submit handoff for validation, auto-repair, and audit |
| `/api/tasks/{task_id}/handoffs` | `GET` | `200` / `404` | List all handoffs recorded for a task |
| `/openapi.json` | `GET` | `200` | Raw OpenAPI 3.1 specification schema |
| `/docs` | `GET` | `200` | Interactive Swagger UI documentation |
| `/redoc` | `GET` | `200` | ReDoc alternative API documentation |

### Example Task Registration Request
`POST /api/tasks`
```json
{
  "title": "Expense Tracker",
  "original_request": "Build a responsive expense tracker with login and a dark theme."
}
```

### Example Task Registration Response (HTTP 201)
```json
{
  "task": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Expense Tracker",
    "original_request": "Build a responsive expense tracker with login and a dark theme.",
    "status": "queued",
    "created_at": "2026-10-24T10:30:00.000000Z",
    "updated_at": "2026-10-24T10:30:00.000000Z",
    "current_stage": "registration",
    "progress": 0
  },
  "requirements": [
    {
      "id": "R001",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "original_text": "Core capability: Build a responsive expense tracker with login and a dark theme.",
      "priority": "critical",
      "status": "registered",
      "description": "Implement the primary functional requirements described in the user request.",
      "related_files": ["src/App.tsx", "backend/app/main.py"],
      "related_test_ids": ["TEST-CORE-001"]
    }
  ],
  "events": [
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "task_created",
      "stage": "registration",
      "message": "Task 'Expense Tracker' created.",
      "timestamp": "2026-10-24T10:30:00.000000Z",
      "metadata": {"task_id": "550e8400-e29b-41d4-a716-446655440000", "title": "Expense Tracker"}
    }
  ]
}
```

### Example Handoff Validation Request
`POST /api/tasks/{task_id}/handoffs`
```json
{
  "source_agent": "researcher",
  "target_agent": "coder",
  "requirement_ids": ["R001"],
  "payload": {
    "architecture_spec": "spec_v1.md",
    "components": ["Login", "ExpenseList"]
  },
  "auto_repair": true
}
```

### Example Handoff Validation Response (HTTP 201)
```json
{
  "handoff": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_agent": "researcher",
    "target_agent": "coder",
    "status": "repaired",
    "requirement_ids": ["R001", "R002", "R003", "R004"],
    "payload": {"architecture_spec": "spec_v1.md", "components": ["Login", "ExpenseList"]},
    "issues": [
      {
        "id": "ISSUE-A1B2C3D4",
        "requirement_id": "R002",
        "issue_type": "omission",
        "severity": "high",
        "description": "Canonical requirement R002 is missing from the handoff requirement_ids.",
        "repair_status": "repaired",
        "evidence": ["Canonical requirement 'R002' not found in handoff ids"]
      }
    ],
    "created_at": "2026-10-24T10:31:00.000000Z"
  },
  "repaired": true,
  "issues_count": 3
}
```

---

## 9. AI Semantic Validation Provider

For AI-powered semantic drift and constraint weakening analysis, refer to the interface specification in:
- [backend/docs/SEMANTIC_PROVIDER_SPEC.md](docs/SEMANTIC_PROVIDER_SPEC.md)

---

## 10. Architecture Overview

```
backend/
├── app/
│   ├── api/             # Central API routers and endpoints
│   │   ├── routes/
│   │   │   └── health.py # Health diagnostics endpoint
│   │   └── router.py    # Main API router aggregator
│   ├── core/            # Configuration, security, errors
│   │   ├── config.py    # Typed Pydantic settings & secrets protection
│   │   └── errors.py    # Standard error handlers and exception types
│   ├── models/          # Shared Pydantic v2 domain schemas
│   │   ├── agent_run.py
│   │   ├── artifact.py
│   │   ├── common.py
│   │   ├── event.py
│   │   ├── experiment.py
│   │   ├── handoff.py
│   │   ├── recovery.py
│   │   ├── requirement.py
│   │   ├── task.py
│   │   └── test_result.py
│   ├── repositories/    # Data persistence interfaces (clean boundary)
│   ├── services/        # Business logic & AI orchestration interfaces
│   └── main.py          # FastAPI application factory and CORS middleware
├── tests/
│   ├── test_health.py   # Health, startup, CORS, and security tests
│   └── test_schemas.py  # Pydantic v2 schema validation & boundary tests
├── .env.example         # Environment template with safe defaults
├── .gitignore           # Git ignore rules for Python, virtualenv, and secrets
├── requirements.txt     # Python production and test dependencies
└── README.md            # This documentation
```
