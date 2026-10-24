"""Tests for task registration, requirement extraction, event logging, and retrieval."""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.in_memory import _in_memory_repository


@pytest.fixture(autouse=True)
def reset_in_memory_repository() -> None:
    """Clear in-memory repository state before each test."""
    _in_memory_repository._tasks.clear()
    _in_memory_repository._requirements.clear()
    _in_memory_repository._events.clear()
    _in_memory_repository._agent_runs.clear()
    _in_memory_repository._req_counters.clear()


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI test client."""
    return TestClient(app)


def test_create_task_success(client: TestClient) -> None:
    """Verify POST /api/tasks creates task, extracts requirements in mock mode, and records events."""
    payload = {
        "title": "Expense Tracker",
        "original_request": "Build a responsive expense tracker with login and a dark theme.",
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "task" in data
    assert "requirements" in data
    assert "events" in data

    # 1. Verify Task fields
    task = data["task"]
    assert task["title"] == "Expense Tracker"
    assert task["original_request"] == payload["original_request"]
    assert task["status"] == "queued"
    assert task["current_stage"] == "registration"
    assert task["progress"] == 0
    assert "id" in task
    assert "created_at" in task
    assert "updated_at" in task

    # 2. Verify Canonical Requirements extracted
    requirements = data["requirements"]
    assert len(requirements) >= 4  # Core, Auth, Responsive, Dark Theme, Data Tracking
    req_ids = [r["id"] for r in requirements]
    assert req_ids == [f"R{i:03d}" for i in range(1, len(requirements) + 1)]

    # Check first requirement is R001 with registered status
    r1 = requirements[0]
    assert r1["id"] == "R001"
    assert r1["status"] == "registered"
    assert r1["priority"] in ["low", "medium", "high", "critical"]
    assert len(r1["original_text"]) > 0

    # 3. Verify Workflow Events recorded
    events = data["events"]
    event_types = [e["event_type"] for e in events]
    assert "task_created" in event_types
    assert "requirement_extraction_started" in event_types
    assert "requirement_registered" in event_types
    assert "requirement_extraction_completed" in event_types


def test_stable_requirement_ids_per_task(client: TestClient) -> None:
    """Verify requirement IDs start from R001 for each newly registered task."""
    resp1 = client.post(
        "/api/tasks",
        json={"title": "Task 1", "original_request": "Implement login"},
    )
    assert resp1.status_code == 201
    reqs1 = resp1.json()["requirements"]
    assert reqs1[0]["id"] == "R001"

    resp2 = client.post(
        "/api/tasks",
        json={"title": "Task 2", "original_request": "Implement dashboard"},
    )
    assert resp2.status_code == 201
    reqs2 = resp2.json()["requirements"]
    assert reqs2[0]["id"] == "R001"


def test_list_tasks(client: TestClient) -> None:
    """Verify GET /api/tasks lists all registered tasks."""
    client.post("/api/tasks", json={"title": "Alpha", "original_request": "Do Alpha"})
    client.post("/api/tasks", json={"title": "Beta", "original_request": "Do Beta"})

    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert len(data["tasks"]) == 2
    titles = [t["title"] for t in data["tasks"]]
    assert "Alpha" in titles
    assert "Beta" in titles


def test_get_task_detail(client: TestClient) -> None:
    """Verify GET /api/tasks/{task_id} returns task, requirements, agent_runs, and summary."""
    create_resp = client.post(
        "/api/tasks",
        json={
            "title": "Expense Tracker",
            "original_request": "Build a responsive expense tracker with login and a dark theme.",
        },
    )
    task_id = create_resp.json()["task"]["id"]

    detail_resp = client.get(f"/api/tasks/{task_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["task"]["id"] == task_id
    assert isinstance(detail["requirements"], list)
    assert len(detail["requirements"]) > 0
    assert detail["agent_runs"] == []
    assert detail["summary"] == {
        "total_requirements": len(detail["requirements"]),
        "verified_requirements": 0,
        "failed_requirements": 0,
        "open_issues": 0,
    }


def test_get_task_requirements(client: TestClient) -> None:
    """Verify GET /api/tasks/{task_id}/requirements returns canonical requirements."""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "Test Req", "original_request": "Build dark theme dashboard"},
    )
    task_id = create_resp.json()["task"]["id"]

    resp = client.get(f"/api/tasks/{task_id}/requirements")
    assert resp.status_code == 200
    data = resp.json()
    assert "requirements" in data
    assert len(data["requirements"]) > 0
    assert data["requirements"][0]["id"] == "R001"


def test_get_task_events(client: TestClient) -> None:
    """Verify GET /api/tasks/{task_id}/events returns chronological workflow events."""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "Audit Task", "original_request": "Simple request"},
    )
    task_id = create_resp.json()["task"]["id"]

    resp = client.get(f"/api/tasks/{task_id}/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert len(data["events"]) >= 3  # created, extraction started, completed
    for ev in data["events"]:
        assert ev["task_id"] == task_id
        assert "timestamp" in ev


def test_missing_task_returns_404(client: TestClient) -> None:
    """Verify nonexistent task IDs return HTTP 404 with TASK_NOT_FOUND error code."""
    non_existent_id = str(uuid4())

    endpoints = [
        f"/api/tasks/{non_existent_id}",
        f"/api/tasks/{non_existent_id}/requirements",
        f"/api/tasks/{non_existent_id}/events",
    ]

    for endpoint in endpoints:
        resp = client.get(endpoint)
        assert resp.status_code == 404
        data = resp.json()
        assert data == {
            "error": {
                "code": "TASK_NOT_FOUND",
                "message": "Task not found",
            }
        }


def test_extraction_failure_preserves_task(client: TestClient) -> None:
    """Verify task is preserved and failure event recorded if requirement extraction fails."""
    payload = {
        "title": "Failing Extraction Task",
        "original_request": "Please test this with __FORCE_EXTRACTION_FAILURE__ included.",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 201

    data = resp.json()
    # Task and original request preserved
    assert data["task"]["title"] == "Failing Extraction Task"
    assert data["task"]["original_request"] == payload["original_request"]
    assert data["requirements"] == []

    # Failure event recorded
    events = data["events"]
    failure_events = [e for e in events if e["event_type"] == "requirement_extraction_failed"]
    assert len(failure_events) == 1
    assert "Simulated requirement extraction failure" in failure_events[0]["message"]


def test_invalid_task_payload_rejected(client: TestClient) -> None:
    """Verify request validation rejects missing or empty fields."""
    # Missing original_request
    resp1 = client.post("/api/tasks", json={"title": "No Request"})
    assert resp1.status_code == 422

    # Empty title
    resp2 = client.post("/api/tasks", json={"title": "", "original_request": "Valid"})
    assert resp2.status_code == 422

    # Empty original_request
    resp3 = client.post("/api/tasks", json={"title": "Valid", "original_request": ""})
    assert resp3.status_code == 422


@pytest.mark.anyio
async def test_task_status_change_event() -> None:
    """Verify task status transition records a task_status_changed workflow event."""
    from app.services.task_service import get_task_service
    from app.models.task import TaskStatus

    service = get_task_service()
    task, _, _ = await service.create_task_with_requirements(
        title="Status Test Task",
        original_request="Verify status change event",
    )
    assert task.status == TaskStatus.queued

    updated = await service.update_task_status(
        task_id=task.id,
        status=TaskStatus.running,
        current_stage="implementation",
        progress=25,
    )
    assert updated.status == TaskStatus.running
    assert updated.progress == 25

    events = await service.get_events(task.id)
    status_events = [e for e in events if e.event_type == "task_status_changed"]
    assert len(status_events) == 1
    assert "queued" in status_events[0].message
    assert "running" in status_events[0].message


@pytest.mark.anyio
async def test_update_requirement_preserves_original_and_audits() -> None:
    """Verify requirement editing preserves original_text and records requirement_updated event."""
    from app.services.task_service import get_task_service
    from app.models.requirement import RequirementStatus

    service = get_task_service()
    task, requirements, _ = await service.create_task_with_requirements(
        title="Requirement Edit Task",
        original_request="Build responsive dark theme app",
    )
    assert len(requirements) > 0
    target_req = requirements[0]
    original_wording = target_req.original_text

    updated = await service.update_requirement(
        task_id=task.id,
        requirement_id=target_req.id,
        status=RequirementStatus.implemented,
        description="Updated implementation note",
    )

    # Verify original wording is strictly preserved
    assert updated.original_text == original_wording
    assert updated.status == RequirementStatus.implemented
    assert updated.description == "Updated implementation note"

    # Verify requirement_updated event was recorded
    events = await service.get_events(task.id)
    req_update_events = [e for e in events if e.event_type == "requirement_updated"]
    assert len(req_update_events) == 1
    assert req_update_events[0].metadata["requirement_id"] == target_req.id
