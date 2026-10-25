# HandoffIQ 🤝

### Verifiable Handoffs for Agentic AI Workflows

HandoffIQ is an Agentic AI project designed to reduce context loss, requirement drift, and inconsistencies when multiple AI agents collaborate on a task.

Instead of blindly trusting one agent's output, HandoffIQ maintains a traceable set of requirements and checks whether critical constraints survive as work moves between agents.

## 🚨 The Problem

Multi-agent AI workflows can lose important details between stages. A research agent may overlook a requirement, a coding agent may interpret it differently, or a security constraint may disappear during a handoff.

These small changes can lead to incorrect implementations, failed tests, and potential security issues.

## 💡 Our Solution

HandoffIQ introduces a requirement-aware verification layer between AI agents.

- **Requirement extraction:** Convert task descriptions into structured, traceable requirements.
- **Canonical requirements:** Assign stable identifiers to requirements so they can be tracked across workflow stages.
- **Handoff validation:** Compare requirements with downstream handoff content to identify missing, altered, weakened, or contradictory constraints.
- **Recovery and repair:** Support recovery workflows and safe repairs where the intended requirement is sufficiently clear.
- **Revalidation:** Check repaired handoffs again before proceeding.
- **Workflow visibility:** Track agent progress, validation results, and relevant workflow events.

The goal is to make agent-to-agent handoffs more transparent, testable, and reliable.

## ⚙️ How It Works

1. **Submit a task** with the requirements and constraints that must be preserved.
2. **Extract requirements** into a structured, traceable representation.
3. **Pass context between agents** as the workflow progresses.
4. **Validate the handoff** against the original requirements.
5. **Review discrepancies** and attempt safe recovery when appropriate.
6. **Revalidate** before continuing the workflow.

```text
Task Input
    ↓
Requirement Extraction
    ↓
Canonical Requirement Set
    ↓
Agent Handoff
    ↓
Requirement Validation
    ↓
Discrepancy Detection
    ↓
Recovery / Repair
    ↓
Revalidation
    ↓
Next Workflow Stage
```

## ✨ Key Features

- Structured requirement tracking
- Requirement-aware agent handoffs
- Validation and discrepancy reporting
- Recovery and repair workflow
- Workflow progress visualization
- Demo Mode for exploring seeded handoff failures
- Automated tests for validation scenarios and demo behavior

*Detection quality depends on the validation logic and the scenarios being tested. HandoffIQ is designed to reduce requirement loss, not guarantee that every possible failure will be detected.*

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Styling | CSS, Tailwind CSS |
| Backend | Python, FastAPI |
| Data validation | Pydantic |
| Database | PostgreSQL via Supabase |
| AI integration | Gemini API |
| Testing | Pytest, TypeScript-based tests |

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or a compatible version
- Node.js and npm
- A Supabase project if using the database-backed configuration
- A Gemini API key if using live Gemini-powered functionality

### 1. Clone the repository

```bash
git clone https://github.com/vaii7x/HandoffIQ.git
cd HandoffIQ
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables using the backend configuration and `.env` example, if provided. Do not commit API keys or service-role secrets.

Start the API:

```bash
uvicorn app.main:app --reload
```

If the backend starts successfully, its interactive API documentation is typically available at `http://127.0.0.1:8000/docs`.

### 3. Set up the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in your terminal.

> **Note:** Environment variable names, database setup steps, and available npm scripts should be checked against the current source code and configuration before running the project in a new environment.

## 🧪 Testing

### Backend

From the `backend` directory, run:

```bash
pytest
```

### Frontend

From the `frontend` directory, run the test command defined in `package.json`. For example, if the project uses a `test` script:

```bash
npm test
```

Use the available test suites to verify requirement extraction, handoff validation, recovery behavior, and demo scenarios.

## 🎬 Demo Mode

HandoffIQ includes a demo experience for examining deliberately seeded handoff failures and the recovery workflow.

Demo Mode is intended to illustrate how requirements can be lost or changed between agents, how discrepancies can be presented, and how repairs can be checked again. Simulated examples should not be interpreted as proof that every live AI-generated failure will be detected.

## 🔐 Security Considerations

- Keep API keys and database secrets in environment variables.
- Never expose Supabase service-role keys in frontend code.
- Validate inputs on the backend.
- Treat AI-generated output as untrusted until it has been checked.
- Use appropriate access controls and approval gates for sensitive operations.

## 🗺️ Future Improvements

- Stronger semantic validation and evaluation
- Expanded regression tests for subtle requirement changes
- Better observability across multi-agent workflows
- More robust recovery for ambiguous or conflicting requirements
- Benchmarking across different models and task types

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome. Open an issue to discuss a proposed change or submit a pull request.

## 📄 License

Add the license applicable to this repository before redistributing or reusing the project.

---

**HandoffIQ — When AI agents hand off tasks, losing context shouldn't mean losing control.**
