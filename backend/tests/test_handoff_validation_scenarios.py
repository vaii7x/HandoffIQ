"""Test suite verifying all 7 handoff validation scenarios end-to-end.

Scenarios verified:
1. 5 requirements preserved, 0 discrepancies.
2. 3 discrepancies detected, 0 repaired.
3. 3 discrepancies detected, all 3 repaired and successfully revalidated.
4. 3 discrepancies detected, 2 repaired and 1 unresolved.
5. A requirement weakened without changing its ID.
6. A requirement missing entirely from received handoff.
7. Contradictory or ambiguous requirements that need review.
"""

from typing import List
from uuid import UUID
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.handoff import IssueType, RepairStatus
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
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
    _in_memory_handoff_repository._handoffs.clear()
    _in_memory_handoff_repository._task_index.clear()
    set_semantic_validation_provider(NoOpSemanticValidationProvider())


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def five_requirement_task(client: TestClient) -> dict:
    """Create a canonical task with exactly 5 canonical requirements."""
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Expense Tracker",
            "original_request": "Build a responsive expense tracker with login and a dark theme.",
        },
    )
    assert resp.status_code == 201
    task_data = resp.json()
    assert len(task_data["requirements"]) == 5, f"Expected 5 canonical reqs, got {len(task_data['requirements'])}"
    return task_data


def test_scenario_1_five_requirements_zero_discrepancies(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 1: 5 requirements preserved, 0 discrepancies."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]
    assert len(canonical_ids) == 5

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "expense_tracker_spec.md",
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
    assert handoff["issues"] == []
    assert len(handoff["requirement_ids"]) == 5

    # Verification: 5 requirements preserved, 0 discrepancies
    repaired_count = len([i for i in handoff["issues"] if i["repair_status"] == "repaired"])
    unresolved_count = len([i for i in handoff["issues"] if i["repair_status"] == "unresolved"])
    assert repaired_count == 0
    assert unresolved_count == 0


def test_scenario_2_three_discrepancies_zero_repaired(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 2: 3 discrepancies detected, 0 repaired."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]

    # 3 discrepancies:
    # 1. Invented requirement ID (R999)
    # 2. Explicit contradiction (skip_auth=True)
    # 3. Weakened constraint (allow_anonymous=True)
    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids + ["R999"],
        "payload": {
            "skip_auth": True,
            "allow_anonymous": True,
        },
        "auto_repair": False,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"
    assert len(handoff["issues"]) == 3

    issue_types = {i["issue_type"] for i in handoff["issues"]}
    assert "invented_requirement" in issue_types
    assert "contradiction" in issue_types
    assert "weakened_constraint" in issue_types

    repaired_count = len([i for i in handoff["issues"] if i["repair_status"] == "repaired"])
    unresolved_count = len([i for i in handoff["issues"] if i["repair_status"] == "unresolved"])
    assert repaired_count == 0
    assert unresolved_count == 3


def test_scenario_3_three_discrepancies_all_three_repaired(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 3: 3 discrepancies detected, all 3 repaired and successfully revalidated."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]

    # Omit 3 requirements (keep only first 2)
    partial_ids = canonical_ids[:2]
    omitted_ids = set(canonical_ids[2:])
    assert len(omitted_ids) == 3

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": partial_ids,
        "payload": {"module": "auth_core"},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["repaired"] is True
    handoff = data["handoff"]
    assert handoff["status"] == "repaired"

    # All 3 detected discrepancies are omissions and all 3 are repaired
    assert len(handoff["issues"]) == 3
    for issue in handoff["issues"]:
        assert issue["issue_type"] == "omission"
        assert issue["repair_status"] == "repaired"
        assert issue["requirement_id"] in omitted_ids

    # Post-repair revalidation verified all 5 requirements restored
    assert len(handoff["requirement_ids"]) == 5
    for req_id in canonical_ids:
        assert req_id in handoff["requirement_ids"]

    repaired_count = len([i for i in handoff["issues"] if i["repair_status"] == "repaired"])
    unresolved_count = len([i for i in handoff["issues"] if i["repair_status"] == "unresolved"])
    assert repaired_count == 3
    assert unresolved_count == 0


def test_scenario_4_three_discrepancies_two_repaired_one_unresolved(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 4: 3 discrepancies detected, 2 repaired and 1 unresolved."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]

    # Omit 2 requirements (R004, R005) + 1 explicit contradiction (skip_auth=True)
    partial_ids = canonical_ids[:3]
    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": partial_ids,
        "payload": {
            "skip_auth": True,  # Critical contradiction (cannot be auto-repaired)
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["repaired"] is True
    handoff = data["handoff"]
    # Blocked because contradiction is unresolved
    assert handoff["status"] == "blocked"

    # Total 3 discrepancies
    assert len(handoff["issues"]) == 3
    repaired_issues = [i for i in handoff["issues"] if i["repair_status"] == "repaired"]
    unresolved_issues = [i for i in handoff["issues"] if i["repair_status"] == "unresolved"]

    assert len(repaired_issues) == 2
    for issue in repaired_issues:
        assert issue["issue_type"] == "omission"

    assert len(unresolved_issues) == 1
    assert unresolved_issues[0]["issue_type"] == "contradiction"

    # Reconciliation: total (3) == repaired (2) + unresolved (1)
    assert len(handoff["issues"]) == len(repaired_issues) + len(unresolved_issues)


def test_scenario_5_requirement_weakened_without_changing_id(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 5: A requirement weakened without changing its ID."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]

    # All canonical IDs are present, but security constraint is weakened in payload
    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "architecture": "microservices",
            "security_constraint": "optional_auth",  # Weakened constraint!
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"
    assert len(handoff["issues"]) == 1

    issue = handoff["issues"][0]
    assert issue["issue_type"] == "weakened_constraint"
    assert issue["repair_status"] == "unresolved"
    assert issue["severity"] == "high"

    # Requirement ID is still present in requirement_ids, but weakened constraint blocks coding
    assert len(handoff["requirement_ids"]) == 5


def test_scenario_6_requirement_missing_entirely(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 6: A requirement missing entirely from received handoff."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]

    # Omit R005 entirely
    omitted_req = canonical_ids[-1]
    partial_ids = canonical_ids[:-1]

    # 6A: Without auto_repair -> blocks handoff
    resp_no_repair = client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "researcher",
            "target_agent": "coder",
            "requirement_ids": partial_ids,
            "payload": {"module": "standard"},
            "auto_repair": False,
        },
    )
    assert resp_no_repair.status_code == 201
    data_no_repair = resp_no_repair.json()
    handoff_nr = data_no_repair["handoff"]
    assert handoff_nr["status"] == "blocked"
    assert len(handoff_nr["issues"]) == 1
    assert handoff_nr["issues"][0]["issue_type"] == "omission"
    assert handoff_nr["issues"][0]["requirement_id"] == omitted_req
    assert handoff_nr["issues"][0]["repair_status"] == "unresolved"
    assert omitted_req not in handoff_nr["requirement_ids"]

    # 6B: With auto_repair -> repairs and revalidates
    resp_repair = client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "researcher",
            "target_agent": "coder",
            "requirement_ids": partial_ids,
            "payload": {"module": "standard"},
            "auto_repair": True,
        },
    )
    assert resp_repair.status_code == 201
    data_repair = resp_repair.json()
    handoff_r = data_repair["handoff"]
    assert handoff_r["status"] == "repaired"
    assert len(handoff_r["issues"]) == 1
    assert handoff_r["issues"][0]["issue_type"] == "omission"
    assert handoff_r["issues"][0]["requirement_id"] == omitted_req
    assert handoff_r["issues"][0]["repair_status"] == "repaired"
    assert omitted_req in handoff_r["requirement_ids"]


def test_scenario_7_contradictory_requirements_need_review(
    client: TestClient, five_requirement_task: dict
) -> None:
    """Scenario 7: Contradictory or ambiguous requirements that need review."""
    task_id = five_requirement_task["task"]["id"]
    canonical_ids = [r["id"] for r in five_requirement_task["requirements"]]

    # Payload explicitly opposes canonical authentication requirement
    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "auth_enabled": False,  # Direct contradiction with canonical auth requirement
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    handoff = data["handoff"]
    assert handoff["status"] == "blocked"
    assert len(handoff["issues"]) == 1

    issue = handoff["issues"][0]
    assert issue["issue_type"] == "contradiction"
    assert issue["severity"] == "critical"
    assert issue["repair_status"] == "unresolved"
