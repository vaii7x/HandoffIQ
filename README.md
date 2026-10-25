# HandoffIQ

> Reliable context handoffs for multi-agent AI workflows with structured state verification, drift detection, and automated specification repair.

HandoffIQ is an AI developer platform that prevents requirement loss and silent context corruption across multi-agent workflows (Research → Validate → Code → Test → Deploy). It extracts authoritative requirements, audits every agent-to-agent transition, flags missing or weakened constraints, and repairs defects before downstream code generation.

---

## 1. Repository Structure

The repository is organized into two primary project directories:

```
HandoffIQ/
├── frontend/                # React 18 + TypeScript + Vite + Tailwind CSS
│   ├── src/                 # Application components, pages, services, and hooks
│   ├── tests/               # Frontend scenario, abort resilience, and demo test suites
│   ├── index.html           # SPA entry point
│   ├── vite.config.ts       # Bundler configuration and API reverse-proxy (:8000)
│   ├── tsconfig.json        # TypeScript compiler options and path aliases
│   ├── tailwind.config.js   # Tailwind theme, typography, and styling
│   ├── package.json         # Frontend scripts and dependencies
│   └── .env.example         # Frontend environment variable template
├── backend/                 # Python 3.11+ FastAPI + Pydantic v2
│   ├── app/                 # FastAPI routes, models, agents, and validation engine
│   ├── tests/               # Pytest test suites (unit, validation audit, demo tests)
│   ├── migrations/          # PostgreSQL initial schema and RLS policies
│   ├── requirements.txt     # Python backend dependencies
│   └── .env.example         # Backend environment variable template
├── .gitignore               # Repository-wide ignore rules
└── README.md                # Project documentation
```

---

## 2. Quickstart

### Prerequisites
- **Node.js**: Version 18 or higher (LTS recommended)
- **Python**: Version 3.11 or higher

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the local development server**:
   ```bash
   npm run dev
   ```
   The frontend runs at [http://localhost:3000](http://localhost:3000). Requests to `/api/*` are automatically proxied to the FastAPI backend at `http://127.0.0.1:8000`.

4. **Build for production**:
   ```bash
   npm run build
   ```

5. **Run frontend tests**:
   ```bash
   npm test
   ```

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a Python virtual environment**:

   **Windows (PowerShell)**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux (bash/zsh)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Key configuration settings in `backend/.env`:
   - `MOCK_MODE=true`: Enables standalone local mock execution without requiring external API keys.
   - `MOCK_MODE=false`: Enables full live persistence (requires Supabase and Gemini credentials).
   - `FRONTEND_ORIGIN=http://localhost:3000`: Allowed CORS origin for the Vite frontend.

5. **Start the backend server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be available at [http://localhost:8000](http://localhost:8000) (interactive OpenAPI docs at `http://localhost:8000/docs`).

6. **Run backend tests**:
   ```bash
   pytest tests -v
   ```

---

## 3. Testing Suites

### Frontend Tests
Run all frontend test suites from inside `frontend/`:
```bash
cd frontend
npm test
```
Or run individual test suites:
```bash
# Validation scenario matrix (11 scenarios)
node --experimental-strip-types tests/test_validation_scenarios.ts

# Demo Mode 5-step walkthrough & deterministic oracle
node --experimental-strip-types tests/test_demo_mode.ts

# API resilience, abort signal handling & timeouts
node --experimental-strip-types tests/test_api_abort_resilience.ts
```

### Backend Tests
Run all backend pytest suites:
```bash
# From within the backend directory:
cd backend
pytest tests -q

# Or from the repository root:
python -m pytest backend/tests -q
```

---

## 4. Modes of Operation

1. **Demo Mode**:
   - An interactive, deterministic 5-step demonstration (Canonical Requirements → Downstream Handoff → Validation Findings → Specification Repairs → Revalidation).
   - Operates with an isolated fictional hospital pharmacy system without requiring external API keys.
   - Can be launched directly from the New Task landing page via the **Start Demo** button.

2. **Live Multi-Agent Workflow**:
   - Accepts custom project requirements.
   - Runs Research (canonical requirement extraction) → Validation (context drift audit) → Code Generation → Testing → Deployment.
   - Enforces strict validation gates: code generation is held until all discrepancies are resolved or repaired.

---

## 5. Security & Isolation
- Environment files (`.env`), API keys, and secrets are strictly excluded from source control.
- Generated task workspaces (`backend/workspaces/`), build outputs (`frontend/dist/`), and caches are ignored via `.gitignore`.
