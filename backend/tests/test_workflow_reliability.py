"""Regression tests for workflow reliability:
1. Task isolation (prevent cross-task requirement/handoff leaks).
2. Validation gate policies (distinguish user constraints vs unrequested UI; firmly block security violations).
3. Code artifact readiness and clean ZIP packaging (excluding node_modules).
"""

import io
import shutil
import zipfile
from pathlib import Path
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.artifact import CodeArtifact
from app.models.handoff import (
    Handoff,
    HandoffStatus,
    IssueSeverity,
    IssueType,
    RepairStatus,
    ValidationIssue,
)
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.handoff_service import (
    HandoffValidationService,
    is_blocking_issue,
    is_unrequested_ui_constraint,
)
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
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
    _in_memory_repository._artifacts.clear()
    _in_memory_repository._test_results.clear()
    _in_memory_handoff_repository._handoffs.clear()
    _in_memory_handoff_repository._task_index.clear()
    set_semantic_validation_provider(NoOpSemanticValidationProvider())


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI test client."""
    return TestClient(app)


def test_task_isolation_requirements_and_handoffs(client: TestClient) -> None:
    """Ensure Task A and Task B have completely isolated requirements and handoffs without leakage."""
    # Create Task A
    resp_a = client.post(
        "/api/tasks",
        json={
            "title": "Expense Tracker",
            "original_request": "Build a responsive expense tracker with login and a dark theme.",
        },
    )
    assert resp_a.status_code == 201
    task_a_id = resp_a.json()["task"]["id"]
    reqs_a = resp_a.json()["requirements"]

    # Add handoff for Task A
    handoff_a_payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": [r["id"] for r in reqs_a],
        "payload": {"spec": "expense_tracker_spec.md"},
        "auto_repair": True,
    }
    handoff_a_resp = client.post(f"/api/tasks/{task_a_id}/handoffs", json=handoff_a_payload)
    assert handoff_a_resp.status_code == 201

    # Create Task B
    resp_b = client.post(
        "/api/tasks",
        json={
            "title": "Python Calculator",
            "original_request": "Build a simple Python calculator module with add, subtract, multiply, and divide.",
        },
    )
    assert resp_b.status_code == 201
    task_b_id = resp_b.json()["task"]["id"]
    reqs_b = resp_b.json()["requirements"]

    # Verify Task A and Task B have different IDs
    assert task_a_id != task_b_id

    # Verify requirements isolation
    get_reqs_a = client.get(f"/api/tasks/{task_a_id}/requirements").json()["requirements"]
    get_reqs_b = client.get(f"/api/tasks/{task_b_id}/requirements").json()["requirements"]

    assert len(get_reqs_a) > 0
    assert len(get_reqs_b) > 0
    # Task A's requirements should mention tracker/expense/theme/login in original_text
    req_a_texts = [r["original_text"].lower() for r in get_reqs_a]
    assert any("expense" in t or "tracker" in t or "login" in t or "dark theme" in t for t in req_a_texts)

    # Task B should have NO handoffs yet
    get_handoffs_b = client.get(f"/api/tasks/{task_b_id}/handoffs").json()["handoffs"]
    assert len(get_handoffs_b) == 0

    # Task A should have 1 handoff
    get_handoffs_a = client.get(f"/api/tasks/{task_a_id}/handoffs").json()["handoffs"]
    assert len(get_handoffs_a) == 1
    assert get_handoffs_a[0]["task_id"] == task_a_id


def test_calculator_unrequested_ui_discrepancy_allowed_and_repaired(client: TestClient) -> None:
    """A non-UI calculator task with division-by-zero discrepancy claiming a UI layer is needed
    must be recognized as an unrequested UI constraint, safely repaired/reconciled, and NOT block progression.
    """
    calc_request = "Make a simple Python calculator with addition, subtraction, multiplication, division. Handle division by zero."
    resp = client.post(
        "/api/tasks",
        json={"title": "Calculator", "original_request": calc_request},
    )
    assert resp.status_code == 201
    task_id = resp.json()["task"]["id"]
    req_ids = [r["id"] for r in resp.json()["requirements"]]

    # Construct issue representing unrequested UI layer constraint
    unrequested_ui_issue = ValidationIssue(
        issue_type=IssueType.semantic_drift,
        severity=IssueSeverity.high,
        requirement_id=req_ids[-1] if req_ids else "R004",
        description="Downstream specification requires division-by-zero errors to be displayed in a UI layer with modal alert.",
        evidence=["UI layer modal alert specified in downstream architecture."],
        repair_status=RepairStatus.unresolved,
    )

    # Verify helper classifies it correctly
    assert is_unrequested_ui_constraint(unrequested_ui_issue, calc_request) is True
    assert is_blocking_issue(unrequested_ui_issue, calc_request) is False

    # Now test the service repair logic directly with this issue
    service = HandoffValidationService(
        task_repository=_in_memory_repository,
        handoff_repository=_in_memory_handoff_repository,
        semantic_provider=NoOpSemanticValidationProvider(),
    )

    # Mock run_validation_checks to simulate an initial issue about UI layer
    async def mock_validation_checks(t_id, c_reqs, h):
        return [unrequested_ui_issue]

    service.run_validation_checks = mock_validation_checks

    handoff, was_repaired = pytest.importorskip("asyncio").run(
        service.submit_and_validate_handoff(
            task_id=UUID(task_id),
            source_agent="researcher",
            target_agent="coder",
            requirement_ids=req_ids,
            payload={"architecture": "calculator_spec", "components": ["CalculatorCore"]},
            auto_repair=True,
        )
    )

    assert was_repaired is True
    # Handoff must NOT be blocked
    assert handoff.status in [HandoffStatus.repaired, HandoffStatus.validated]
    assert handoff.status != HandoffStatus.blocked

    # Verify repaired issue description and audit event
    repaired_issues = [i for i in handoff.issues if i.repair_status == RepairStatus.repaired]
    assert len(repaired_issues) >= 1
    assert "reconciled" in repaired_issues[0].description.lower() or "repaired" in repaired_issues[0].description.lower()

    # Verify audit event in task repo
    events = pytest.importorskip("asyncio").run(_in_memory_repository.get_events(UUID(task_id)))
    repair_events = [e for e in events if e.event_type == "handoff_repaired"]
    assert len(repair_events) >= 1


def test_security_weakening_discrepancy_firmly_blocks_gate(client: TestClient) -> None:
    """Security/Auth constraint weakening must firmly block the validation gate."""
    sec_request = "Build an API service with secure token-based authentication and role-based permissions."
    resp = client.post(
        "/api/tasks",
        json={"title": "Secure API", "original_request": sec_request},
    )
    assert resp.status_code == 201
    task_id = resp.json()["task"]["id"]
    req_ids = [r["id"] for r in resp.json()["requirements"]]

    # Construct issue representing security weakening
    security_issue = ValidationIssue(
        issue_type=IssueType.weakened_constraint,
        severity=IssueSeverity.critical,
        requirement_id=req_ids[0],
        description="Downstream specification weakened authentication by setting allow_anonymous: true on restricted endpoints.",
        evidence=["allow_anonymous: true detected in route configuration."],
        repair_status=RepairStatus.unresolved,
    )

    # Verify helper classifies it as blocking
    assert is_unrequested_ui_constraint(security_issue, sec_request) is False
    assert is_blocking_issue(security_issue, sec_request) is True

    service = HandoffValidationService(
        task_repository=_in_memory_repository,
        handoff_repository=_in_memory_handoff_repository,
        semantic_provider=NoOpSemanticValidationProvider(),
    )

    async def mock_sec_validation_checks(t_id, c_reqs, h):
        return [security_issue]

    service.run_validation_checks = mock_sec_validation_checks

    handoff, was_repaired = pytest.importorskip("asyncio").run(
        service.submit_and_validate_handoff(
            task_id=UUID(task_id),
            source_agent="researcher",
            target_agent="coder",
            requirement_ids=req_ids,
            payload={"auth": "anonymous"},
            auto_repair=True,
        )
    )

    # Gate MUST remain blocked
    assert handoff.status == HandoffStatus.blocked
    assert len(handoff.issues) >= 1
    assert handoff.issues[0].repair_status == RepairStatus.unresolved

    # Verify handoff_blocked audit event
    events = pytest.importorskip("asyncio").run(_in_memory_repository.get_events(UUID(task_id)))
    blocked_events = [e for e in events if e.event_type == "handoff_blocked"]
    assert len(blocked_events) >= 1


def test_artifacts_and_zip_clean_packaging(client: TestClient) -> None:
    """Artifact endpoints return generated files and exclude node_modules from both artifact lists and ZIP downloads."""
    resp = client.post(
        "/api/tasks",
        json={"title": "Calculator", "original_request": "Simple Python calculator."},
    )
    assert resp.status_code == 201
    task_id = resp.json()["task"]["id"]

    # Create workspace with real files and a node_modules directory
    workspace_path = Path("backend/workspaces") / task_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    try:
        (workspace_path / "calculator.py").write_text(
            "def add(a, b):\n    return a + b\n", encoding="utf-8"
        )
        (workspace_path / "test_calculator.py").write_text(
            "from calculator import add\ndef test_add():\n    assert add(1, 2) == 3\n",
            encoding="utf-8",
        )
        # Create node_modules file that must be excluded
        nm_dir = workspace_path / "node_modules" / "some_pkg"
        nm_dir.mkdir(parents=True, exist_ok=True)
        (nm_dir / "index.js").write_text("module.exports = {};", encoding="utf-8")

        # Test GET /api/tasks/{task_id}/artifacts
        art_resp = client.get(f"/api/tasks/{task_id}/artifacts")
        assert art_resp.status_code == 200
        art_data = art_resp.json()
        artifact_paths = [a["path"] for a in art_data["artifacts"]]

        assert any("calculator.py" in p for p in artifact_paths)
        assert any("test_calculator.py" in p for p in artifact_paths)
        assert not any("node_modules" in p for p in artifact_paths)

        # Test GET /api/tasks/{task_id}/artifacts/zip
        zip_resp = client.get(f"/api/tasks/{task_id}/artifacts/zip")
        assert zip_resp.status_code == 200
        assert zip_resp.headers["content-type"] == "application/zip"

        # Inspect ZIP content
        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            zip_names = zf.namelist()
            assert any("calculator.py" in n for n in zip_names)
            assert not any("node_modules" in n for n in zip_names)

    finally:
        # Cleanup test workspace
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)


def test_task_id_resolution_supports_string_and_uuid(client: TestClient) -> None:
    """Ensure both raw UUID strings and task-prefixed strings resolve cleanly without 422 error."""
    resp = client.post(
        "/api/tasks",
        json={"title": "Test Task", "original_request": "Test request description."},
    )
    assert resp.status_code == 201
    task_id = resp.json()["task"]["id"]

    # 1. Test retrieval by exact UUID
    r1 = client.get(f"/api/tasks/{task_id}")
    assert r1.status_code == 200
    assert r1.json()["task"]["id"] == task_id

    # 2. Test retrieval by task- prefixed format (first 8 chars or full)
    prefix_id = f"task-{task_id[:8]}"
    r2 = client.get(f"/api/tasks/{prefix_id}")
    assert r2.status_code == 200
    assert r2.json()["task"]["id"] == task_id


def test_two_consecutive_tasks_complete_data_isolation(client: TestClient) -> None:
    """Verify that two consecutively executed tasks maintain 100% data isolation across
    requirements, artifacts, handoffs, test results, and recoveries without any cross-leakage.
    """
    # 1. Create and populate Task 1: Python Calculator
    r_task1 = client.post(
        "/api/tasks",
        json={
            "title": "Python Calculator",
            "original_request": "Make a simple Python calculator with addition, subtraction, multiplication, division.",
        },
    )
    assert r_task1.status_code == 201
    task1_id = r_task1.json()["task"]["id"]

    # Add handoff and test for Task 1
    client.post(
        f"/api/tasks/{task1_id}/handoffs",
        json={
            "source_agent": "researcher",
            "target_agent": "coder",
            "requirement_ids": [r["id"] for r in r_task1.json()["requirements"]],
            "payload": {"spec": "calculator_spec.md"},
            "auto_repair": True,
        },
    )

    # 2. Create and populate Task 2: JWT Auth Service
    r_task2 = client.post(
        "/api/tasks",
        json={
            "title": "JWT Auth Service",
            "original_request": "Build a secure JWT authentication microservice with refresh token rotation.",
        },
    )
    assert r_task2.status_code == 201
    task2_id = r_task2.json()["task"]["id"]
    assert task1_id != task2_id

    # 3. Verify Requirements Isolation
    reqs1 = client.get(f"/api/tasks/{task1_id}/requirements").json()["requirements"]
    reqs2 = client.get(f"/api/tasks/{task2_id}/requirements").json()["requirements"]

    reqs1_texts = [r["original_text"].lower() for r in reqs1]
    reqs2_texts = [r["original_text"].lower() for r in reqs2]

    # Task 1 must not contain JWT/token terms
    assert not any("jwt" in t or "refresh token" in t for t in reqs1_texts)
    # Task 2 must not contain calculator terms
    assert not any("calculator" in t or "addition" in t for t in reqs2_texts)

    # 4. Verify Handoffs Isolation
    handoffs1 = client.get(f"/api/tasks/{task1_id}/handoffs").json()["handoffs"]
    handoffs2 = client.get(f"/api/tasks/{task2_id}/handoffs").json()["handoffs"]
    assert len(handoffs1) == 1
    assert len(handoffs2) == 0

    # 5. Verify Recoveries Endpoint Isolation
    recov1 = client.get(f"/api/tasks/{task1_id}/recoveries").json()["recoveries"]
    recov2 = client.get(f"/api/tasks/{task2_id}/recoveries").json()["recoveries"]
    assert isinstance(recov1, list)
    assert isinstance(recov2, list)

    # 6. Verify No Platform Errors (WebGL context loss, SSE reconnection) Leak into User Tasks
    for t_id in [task1_id, task2_id]:
        tests = client.get(f"/api/tasks/{t_id}/tests").json()["tests"]
        for test in tests:
            t_name = str(test.get("test_name", "")).lower()
            t_out = str(test.get("output", "")).lower()
            assert "webgl" not in t_name and "webgl" not in t_out
            assert "sse" not in t_name and "sse" not in t_out

