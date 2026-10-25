"""Tests for code generation request lifecycle, retry reliability, deduplication, and error boundaries."""

import asyncio
from typing import List
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.artifact import CodeArtifact
from app.models.task import TaskStatus
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.agents.gemini_coder import GeminiCoderService
from app.services.agents.base import CoderInput, ContextMapOutput
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
    set_semantic_validation_provider,
)
from app.services.workflow_engine import get_execution_manager


@pytest.fixture(autouse=True)
def reset_repositories() -> None:
    _in_memory_repository._tasks.clear()
    _in_memory_repository._requirements.clear()
    _in_memory_repository._events.clear()
    _in_memory_repository._artifacts.clear()
    _in_memory_repository._test_results.clear()
    _in_memory_repository._agent_runs.clear()
    _in_memory_repository._req_counters.clear()
    _in_memory_handoff_repository._handoffs.clear()
    _in_memory_handoff_repository._task_index.clear()
    set_semantic_validation_provider(NoOpSemanticValidationProvider())
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
            "title": "Expense Tracker",
            "original_request": "Build a responsive expense tracker with login and a dark theme.",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_1_successful_generation_and_artifacts(client: TestClient, sample_task: dict) -> None:
    """Test 1: Successful code generation runs cleanly and produces artifacts."""
    task_id = sample_task["task"]["id"]
    manager = get_execution_manager()

    resp = client.post(f"/api/tasks/{task_id}/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # Await background completion
    asyncio.run(manager.wait_for_completion(UUID(task_id), timeout=10.0))

    # Verify task state is completed
    task_resp = client.get(f"/api/tasks/{task_id}")
    assert task_resp.status_code == 200
    data = task_resp.json()
    assert data["task"]["status"] == "completed"

    # Verify artifacts were generated
    art_resp = client.get(f"/api/tasks/{task_id}/artifacts")
    assert art_resp.status_code == 200
    artifacts = art_resp.json()["artifacts"]
    assert len(artifacts) > 0


def test_2_retry_after_failure_no_duplicates(client: TestClient, sample_task: dict) -> None:
    """Test 2 & 7: Retry after failure succeeds and does not duplicate artifacts or records."""
    task_id = sample_task["task"]["id"]
    manager = get_execution_manager()

    # Pre-seed an artifact to test upsert
    artifact = CodeArtifact(
        task_id=UUID(task_id),
        path="src/index.ts",
        language="typescript",
        content="// initial v1 content",
        requirement_ids=["R001"],
    )
    asyncio.run(_in_memory_repository.add_artifact(UUID(task_id), artifact))

    # Mark task failed initially
    task = asyncio.run(_in_memory_repository.get_task(UUID(task_id)))
    asyncio.run(
        _in_memory_repository.update_task(
            task.model_copy(update={"status": TaskStatus.failed})
        )
    )

    # Trigger retry via /run
    resp = client.post(f"/api/tasks/{task_id}/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # Await background completion
    asyncio.run(manager.wait_for_completion(UUID(task_id), timeout=10.0))

    # Verify completed
    task_resp = client.get(f"/api/tasks/{task_id}")
    assert task_resp.json()["task"]["status"] == "completed"

    # Check artifacts: ensure no duplicate paths
    art_resp = client.get(f"/api/tasks/{task_id}/artifacts")
    artifacts = art_resp.json()["artifacts"]
    paths = [a["path"] for a in artifacts]
    assert len(paths) == len(set(paths)), f"Duplicate artifact paths found: {paths}"


def test_3_duplicate_concurrent_run_prevention(client: TestClient, sample_task: dict) -> None:
    """Test 3: Prevent duplicate clicks from creating concurrent jobs."""
    task_id = sample_task["task"]["id"]
    manager = get_execution_manager()

    # Manually register task as running
    manager._running_tasks.add(UUID(task_id))

    # Attempt second run
    resp = client.post(f"/api/tasks/{task_id}/run")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TASK_ALREADY_RUNNING"


def test_4_gemini_permanent_auth_failure_no_infinite_loop() -> None:
    """Test 6: Gemini authentication failure does not retry indefinitely and falls back safely."""
    coder = GeminiCoderService()

    class MockUnauthenticatedError(Exception):
        pass

    with patch.object(coder, "_generate_with_gemini", side_effect=MockUnauthenticatedError("401 API_KEY_INVALID: API key not valid")):
        # Should gracefully log safe diagnostic and use deterministic fallback without crashing
        input_data = CoderInput(
            task_id=uuid4(),
            requirements=[],
            context_map=ContextMapOutput(),
        )
        output = asyncio.run(coder.execute(input_data))
        assert len(output.artifacts) > 0


def test_5_starting_new_task_immediately_after_failed_task(client: TestClient, sample_task: dict) -> None:
    """Test 9: Starting a new task immediately after a failed task maintains task isolation."""
    task_id_1 = sample_task["task"]["id"]

    # Mark task 1 as failed
    task1 = asyncio.run(_in_memory_repository.get_task(UUID(task_id_1)))
    asyncio.run(
        _in_memory_repository.update_task(
            task1.model_copy(update={"status": TaskStatus.failed})
        )
    )

    # Immediately create task 2
    resp2 = client.post(
        "/api/tasks",
        json={
            "title": "Calculator",
            "original_request": "Build a command line calculator.",
        },
    )
    assert resp2.status_code == 201
    task_id_2 = resp2.json()["task"]["id"]
    assert task_id_2 != task_id_1

    # Task 2 should be in queued/registration state with clean error
    task2_status = client.get(f"/api/tasks/{task_id_2}").json()
    assert task2_status["task"]["status"] != "failed"

    # Task 1 remains isolated
    task1_status = client.get(f"/api/tasks/{task_id_1}").json()
    assert task1_status["task"]["status"] == "failed"
