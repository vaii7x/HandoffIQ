"""Tests for handoff submission, validation rules, safe repair, and event recording."""

from typing import List
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.handoff import (
    Handoff,
    HandoffStatus,
    IssueSeverity,
    IssueType,
    RepairStatus,
    ValidationIssue,
)
from app.models.requirement import Requirement
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
    SemanticValidationProvider,
    set_semantic_validation_provider,
)


@pytest.fixture(autouse=True)
def reset_repositories() -> None:
    """Clear repositories and reset default semantic provider before each test."""
    _in_memory_repository._tasks.clear()
    _in_memory_repository._requirements.clear()
    _in_memory_repository._events.clear()
    _in_memory_repository._agent_runs.clear()
    _in_memory_repository._req_counters.clear()
    _in_memory_handoff_repository._handoffs.clear()
    _in_memory_handoff_repository._task_index.clear()
    set_semantic_validation_provider(NoOpSemanticValidationProvider())


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_task(client: TestClient) -> dict:
    """Create a standard task with canonical requirements for testing."""
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Expense Tracker",
            "original_request": "Build a responsive expense tracker with login and a dark theme.",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_valid_handoff_validated(client: TestClient, sample_task: dict) -> None:
    """Verify a valid handoff containing all canonical requirements passes with status 'validated'."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_req_ids,
        "payload": {
            "architecture_spec": "expense_tracker_v1.md",
            "components": ["Login", "ExpenseList", "ThemeToggle"],
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201

    data = resp.json()
    assert data["repaired"] is False
    assert data["issues_count"] == 0

    handoff = data["handoff"]
    assert handoff["status"] == "validated"
    assert handoff["source_agent"] == "researcher"
    assert handoff["target_agent"] == "coder"
    assert handoff["issues"] == []

    # Verify handoff_validated event was recorded
    events_resp = client.get(f"/api/tasks/{task_id}/events")
    event_types = [e["event_type"] for e in events_resp.json()["events"]]
    assert "handoff_validated" in event_types


def test_recoverable_omissions_repaired_and_revalidated(client: TestClient, sample_task: dict) -> None:
    """Verify missing canonical requirements are safely restored, revalidated, and audited."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]
    assert len(canonical_req_ids) >= 4

    # Intentionally omit all but the first requirement
    partial_req_ids = [canonical_req_ids[0]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": partial_req_ids,
        "payload": {"context": "initial partial research"},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    # Verify auto repair succeeded
    assert data["repaired"] is True
    handoff = data["handoff"]
    assert handoff["status"] == "repaired"

    # Verify all canonical requirement IDs are now present in handoff
    for req_id in canonical_req_ids:
        assert req_id in handoff["requirement_ids"]

    # Verify issues record omission with repair_status='repaired'
    for issue in handoff["issues"]:
        assert issue["issue_type"] == "omission"
        assert issue["repair_status"] == "repaired"

    # Verify handoff_repaired events were recorded for each restored requirement
    events_resp = client.get(f"/api/tasks/{task_id}/events")
    events = events_resp.json()["events"]
    repair_events = [e for e in events if e["event_type"] == "handoff_repaired"]
    assert len(repair_events) == len(canonical_req_ids) - 1


def test_unknown_requirement_id_flagged(client: TestClient, sample_task: dict) -> None:
    """Verify unknown requirement IDs are flagged as invented_requirement and block the handoff."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]

    # Inject an invented requirement ID
    bogus_ids = canonical_req_ids + ["R999"]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": bogus_ids,
        "payload": {"context": "spec with unknown requirement"},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"

    invented_issues = [
        iss for iss in handoff["issues"] if iss["issue_type"] == "invented_requirement"
    ]
    assert len(invented_issues) == 1
    assert invented_issues[0]["observed_value"] == "R999"
    assert invented_issues[0]["repair_status"] == "unresolved"


def test_structural_errors_flagged(client: TestClient, sample_task: dict) -> None:
    """Verify empty or invalid payload structures are flagged as schema_error."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]

    # Empty dictionary payload
    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_req_ids,
        "payload": {},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"

    schema_issues = [
        iss for iss in handoff["issues"] if iss["issue_type"] == "schema_error"
    ]
    assert len(schema_issues) >= 1
    assert schema_issues[0]["repair_status"] == "unresolved"


def test_explicit_contradiction_detected_and_blocked(client: TestClient, sample_task: dict) -> None:
    """Verify explicit logical contradictions are flagged as contradiction and cannot be auto-repaired."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]

    # Payload specifies skip_auth: true when canonical requirements mandate auth
    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_req_ids,
        "payload": {
            "architecture": "spec.md",
            "skip_auth": True,  # Explicit contradiction!
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"

    contradiction_issues = [
        iss for iss in handoff["issues"] if iss["issue_type"] == "contradiction"
    ]
    assert len(contradiction_issues) >= 1
    assert contradiction_issues[0]["severity"] == "critical"
    assert contradiction_issues[0]["repair_status"] == "unresolved"

    # Verify handoff_blocked event was recorded
    events_resp = client.get(f"/api/tasks/{task_id}/events")
    event_types = [e["event_type"] for e in events_resp.json()["events"]]
    assert "handoff_blocked" in event_types


def test_preservation_of_canonical_requirements(client: TestClient, sample_task: dict) -> None:
    """Verify handoff validation and repair never alters the task's canonical requirement text."""
    task_id = sample_task["task"]["id"]
    original_reqs_before = client.get(f"/api/tasks/{task_id}/requirements").json()["requirements"]

    # Submit a handoff with missing IDs and contradictions
    client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "researcher",
            "target_agent": "coder",
            "requirement_ids": [],
            "payload": {"skip_auth": True},
            "auto_repair": True,
        },
    )

    original_reqs_after = client.get(f"/api/tasks/{task_id}/requirements").json()["requirements"]
    assert len(original_reqs_before) == len(original_reqs_after)
    for b, a in zip(original_reqs_before, original_reqs_after):
        assert b["id"] == a["id"]
        assert b["original_text"] == a["original_text"]
        assert b["priority"] == a["priority"]


def test_injected_semantic_provider(client: TestClient, sample_task: dict) -> None:
    """Verify an injected custom semantic provider successfully reports semantic_drift issues."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]

    # Define mock AI semantic provider
    class MockAISemanticProvider(SemanticValidationProvider):
        @property
        def provider_name(self) -> str:
            return "mock_gemini_semantic_analyzer"

        async def analyze(
            self,
            task_id: UUID,
            requirements: List[Requirement],
            handoff: Handoff,
        ) -> List[ValidationIssue]:
            return [
                ValidationIssue(
                    requirement_id="R001",
                    issue_type=IssueType.semantic_drift,
                    severity=IssueSeverity.high,
                    description="AI analysis detected subtle semantic scope creep in expense categories.",
                    original_value="Standard expense categorization",
                    observed_value="Cryptocurrency portfolio trading",
                    repair_status=RepairStatus.unresolved,
                    evidence=["Handoff payload mentions crypto derivatives trading"],
                )
            ]

    set_semantic_validation_provider(MockAISemanticProvider())

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_req_ids,
        "payload": {"context": "research on crypto expenses"},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"
    drift_issues = [
        iss for iss in handoff["issues"] if iss["issue_type"] == "semantic_drift"
    ]
    assert len(drift_issues) == 1
    assert "crypto derivatives trading" in drift_issues[0]["evidence"][0]


def test_list_handoffs_endpoint(client: TestClient, sample_task: dict) -> None:
    """Verify GET /api/tasks/{task_id}/handoffs lists all registered handoffs."""
    task_id = sample_task["task"]["id"]
    canonical_req_ids = [r["id"] for r in sample_task["requirements"]]

    # Submit two handoffs
    client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "researcher",
            "target_agent": "coder",
            "requirement_ids": canonical_req_ids,
            "payload": {"phase": "architecture"},
        },
    )
    client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "coder",
            "target_agent": "tester",
            "requirement_ids": canonical_req_ids,
            "payload": {"phase": "code_complete"},
        },
    )

    resp = client.get(f"/api/tasks/{task_id}/handoffs")
    assert resp.status_code == 200
    data = resp.json()
    assert "handoffs" in data
    assert len(data["handoffs"]) == 2
    assert data["handoffs"][0]["source_agent"] == "researcher"
    assert data["handoffs"][1]["source_agent"] == "coder"


def test_missing_task_returns_404(client: TestClient) -> None:
    """Verify submitting or retrieving handoffs for a nonexistent task returns 404 TASK_NOT_FOUND."""
    fake_id = str(uuid4())

    post_resp = client.post(
        f"/api/tasks/{fake_id}/handoffs",
        json={
            "source_agent": "researcher",
            "target_agent": "coder",
            "requirement_ids": ["R001"],
            "payload": {"test": "data"},
        },
    )
    assert post_resp.status_code == 404
    assert post_resp.json() == {
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "Task not found",
        }
    }

    get_resp = client.get(f"/api/tasks/{fake_id}/handoffs")
    assert get_resp.status_code == 404
    assert get_resp.json() == {
        "error": {
            "code": "TASK_NOT_FOUND",
            "message": "Task not found",
        }
    }
