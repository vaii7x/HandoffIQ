"""Tests for multi-agent workflow orchestration, stage transitions, and execution management."""

import asyncio
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ConfigurationError
from app.main import app
from app.models.agent_run import AgentType
from app.models.requirement import RequirementStatus
from app.models.task import TaskStatus
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.agents.base import ResearchInput
from app.services.agents.mock_agents import (
    MockResearcherService,
    get_coder_service,
    get_researcher_service,
    get_reviewer_service,
    get_tester_service,
)
from app.services.workflow_engine import get_execution_manager


@pytest.fixture(autouse=True)
def reset_in_memory() -> None:
    """Clear repositories and execution manager state before each test."""
    _in_memory_repository._tasks.clear()
    _in_memory_repository._requirements.clear()
    _in_memory_repository._events.clear()
    _in_memory_repository._agent_runs.clear()
    _in_memory_repository._req_counters.clear()
    _in_memory_handoff_repository._handoffs.clear()
    _in_memory_handoff_repository._task_index.clear()
    manager = get_execution_manager()
    manager._running_tasks.clear()
    manager._active_jobs.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_task(client: TestClient) -> dict:
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Expense App",
            "original_request": "Build a responsive expense tracker with login and a dark theme.",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.anyio
async def test_successful_mock_workflow(client: TestClient, sample_task: dict) -> None:
    """Verify end-to-end workflow execution from research through verification."""
    task_id = UUID(sample_task["task"]["id"])
    manager = get_execution_manager()

    # Trigger workflow
    resp = client.post(f"/api/tasks/{task_id}/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == str(task_id)
    assert data["status"] == "running"
    assert data["current_stage"] == "research"
    assert data["message"] == "Workflow started"

    # Wait for background orchestration to finish
    await manager.wait_for_completion(task_id, timeout=10.0)

    # Fetch final task state
    detail_resp = client.get(f"/api/tasks/{task_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    # 1. Verify task status and progress
    task = detail["task"]
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["current_stage"] == "verification"

    # 2. Verify all requirements are verified
    requirements = detail["requirements"]
    assert len(requirements) >= 4
    for req in requirements:
        assert req["status"] == "verified"

    # 3. Verify agent runs were recorded for all 4 roles
    agent_runs = detail["agent_runs"]
    roles = [r["agent_type"] for r in agent_runs]
    assert "researcher" in roles
    assert "coder" in roles
    assert "reviewer" in roles
    assert "tester" in roles

    # 4. Verify summary counts
    assert detail["summary"]["total_requirements"] == len(requirements)
    assert detail["summary"]["verified_requirements"] == len(requirements)
    assert detail["summary"]["failed_requirements"] == 0

    # 5. Verify workflow events contain stage transitions and completion
    events_resp = client.get(f"/api/tasks/{task_id}/events")
    events = events_resp.json()["events"]
    event_types = [e["event_type"] for e in events]
    assert "stage_transition" in event_types
    assert "requirement_verified" in event_types
    assert "workflow_completed" in event_types


@pytest.mark.anyio
async def test_duplicate_run_prevention(client: TestClient, sample_task: dict) -> None:
    """Verify starting an already running task returns HTTP 409 TASK_ALREADY_RUNNING."""
    task_id = UUID(sample_task["task"]["id"])
    manager = get_execution_manager()

    # Manually mark as running
    async with manager._lock:
        manager._running_tasks.add(task_id)

    resp = client.post(f"/api/tasks/{task_id}/run")
    assert resp.status_code == 409
    data = resp.json()
    assert data["error"]["code"] == "TASK_ALREADY_RUNNING"
    assert "already executing" in data["error"]["message"].lower()


@pytest.mark.anyio
async def test_agent_failure_recorded_and_task_not_stuck(client: TestClient) -> None:
    """Verify an agent exception marks task as failed and does not leave it stuck in running."""
    # Create task with failure trigger in prompt
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Failing Agent Task",
            "original_request": "Please execute with __SIMULATE_RESEARCHER_FAILURE__ in prompt.",
        },
    )
    task_id = UUID(resp.json()["task"]["id"])
    manager = get_execution_manager()

    run_resp = client.post(f"/api/tasks/{task_id}/run")
    assert run_resp.status_code == 200

    # Await failure completion
    await manager.wait_for_completion(task_id, timeout=10.0)

    # Verify task state is failed, NOT running
    detail = client.get(f"/api/tasks/{task_id}").json()
    assert detail["task"]["status"] == "failed"
    assert not await manager.is_running(task_id)

    # Verify workflow_failed event
    events = client.get(f"/api/tasks/{task_id}/events").json()["events"]
    failure_events = [e for e in events if e["event_type"] == "workflow_failed"]
    assert len(failure_events) >= 1
    assert "Simulated researcher agent failure" in failure_events[0]["message"]


@pytest.mark.anyio
async def test_testing_failure_marks_requirement_failed(client: TestClient) -> None:
    """Verify failing tests mark requirement as failed and task as failed with evidence."""
    # Create task
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Test Failure Task",
            "original_request": "Build application with __SIMULATE_TEST_FAILURE__ in code.",
        },
    )
    task_id = UUID(resp.json()["task"]["id"])
    manager = get_execution_manager()

    run_resp = client.post(f"/api/tasks/{task_id}/run")
    assert run_resp.status_code == 200

    await manager.wait_for_completion(task_id, timeout=10.0)

    detail = client.get(f"/api/tasks/{task_id}").json()
    assert detail["task"]["status"] == "failed"
    reqs = detail["requirements"]

    # At least one requirement must be failed due to test failure
    failed_reqs = [r for r in reqs if r["status"] == "failed"]
    assert len(failed_reqs) >= 1
    assert detail["summary"]["failed_requirements"] >= 1


@pytest.mark.anyio
async def test_mock_services_disabled_when_mock_mode_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify mock agent services refuse to return fake results when MOCK_MODE is false."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "MOCK_MODE", False)

    mock_researcher = MockResearcherService()
    with pytest.raises(ConfigurationError) as exc_info:
        await mock_researcher.execute(
            ResearchInput(task_id=uuid4(), original_request="Build app")
        )
    assert "cannot be used when MOCK_MODE is disabled" in str(exc_info.value)


def test_run_missing_task_returns_404(client: TestClient) -> None:
    """Verify running a nonexistent task returns 404 TASK_NOT_FOUND."""
    fake_id = str(uuid4())
    resp = client.post(f"/api/tasks/{fake_id}/run")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TASK_NOT_FOUND"
