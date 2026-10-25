"""Regression and audit test suite for canonical requirement extraction and traceability in HandoffIQ.

Verifies:
1. Student Task Manager with 12 explicit source requirements (R1–R12) extracts 12 distinct canonical requirements.
2. Original source IDs (R1–R12) are preserved and traceable.
3. Feature-adjacent requirements (e.g., R1 Authentication vs R5 Task Ownership, R6 Persistence vs R7 Status Update) are not merged.
4. Constraints, thresholds, conditions, idempotency, and security rules are preserved without truncation.
5. A secondary 5-requirement task with numbered items (1–5) extracts 5 distinct canonical requirements.
6. Handoff validator evaluates each requirement independently and reports issues with the corresponding source requirement ID.
"""

from typing import Any, Dict, List
import asyncio
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.handoff import IssueType
from app.models.requirement import Requirement
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.extractor import (
    MockRequirementExtractor,
    RequirementCandidate,
    parse_explicit_requirements,
)
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
    set_semantic_validation_provider,
)


STUDENT_TASK_MANAGER_PROMPT = """Build a Student Task Manager web application.

R1. Students must log in before accessing their personal tasks.
R2. Each task must have a title, description, due date, priority, and completion status.
R3. Task titles must contain between 3 and 100 characters.
R4. Due dates must not be earlier than the task creation date.
R5. Students must only view, edit, and delete their own tasks.
R6. Tasks must be stored persistently in PostgreSQL and survive server restarts.
R7. Marking a task complete must update its status in the database.
R8. The dashboard must show overdue, pending, and completed task counts accurately.
R9. Filter by priority and completion status simultaneously; both filters must apply.
R10. Invalid requests must be rejected by server-side validation.
R11. Repeated identical requests must not create duplicate tasks when an idempotency key is supplied.
R12. Include automated tests for authentication, task ownership, validation, filtering, and persistence.
"""

FIVE_REQ_ORDER_PROMPT = """Create an Order Fulfillment Service.

1. Customers must authenticate with JWT before placing orders.
2. Inventory count must decrease atomically when an order is submitted.
3. Minimum order value must be $15.00 before taxes and shipping.
4. Orders cannot be cancelled after the status moves to 'Shipped'.
5. Deliver comprehensive integration tests for checkout, cancellation, and stock deduction.
"""


@pytest.fixture(autouse=True)
def reset_test_state() -> None:
    """Clear repositories and set deterministic provider before each test."""
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
    return TestClient(app)


class TestExplicitRequirementParsing:
    """Unit tests for parse_explicit_requirements parser."""

    def test_parses_all_12_student_task_requirements(self) -> None:
        candidates = parse_explicit_requirements(STUDENT_TASK_MANAGER_PROMPT)
        assert len(candidates) == 12, f"Expected 12 candidates, got {len(candidates)}"

        source_ids = [c.source_id for c in candidates]
        expected_ids = [f"R{i}" for i in range(1, 13)]
        assert source_ids == expected_ids

    def test_preserves_constraints_and_thresholds(self) -> None:
        candidates = parse_explicit_requirements(STUDENT_TASK_MANAGER_PROMPT)
        c_map = {c.source_id: c for c in candidates}

        # R3 length constraint
        assert "between 3 and 100 characters" in c_map["R3"].description
        # R4 date constraint
        assert "not be earlier than the task creation date" in c_map["R4"].description
        # R6 persistence constraint
        assert "stored persistently in PostgreSQL" in c_map["R6"].description
        assert "survive server restarts" in c_map["R6"].description
        # R9 filter constraint
        assert "simultaneously" in c_map["R9"].description
        assert "both filters must apply" in c_map["R9"].description
        # R11 idempotency constraint
        assert "idempotency key" in c_map["R11"].description
        assert "not create duplicate tasks" in c_map["R11"].description
        # R12 automated testing
        assert "automated tests" in c_map["R12"].description

    def test_does_not_merge_auth_and_ownership(self) -> None:
        candidates = parse_explicit_requirements(STUDENT_TASK_MANAGER_PROMPT)
        c_map = {c.source_id: c for c in candidates}

        assert "R1" in c_map
        assert "R5" in c_map
        assert c_map["R1"].original_text != c_map["R5"].original_text
        assert "log in before accessing" in c_map["R1"].original_text
        assert "only view, edit, and delete their own tasks" in c_map["R5"].original_text

    def test_does_not_merge_persistence_and_status_update(self) -> None:
        candidates = parse_explicit_requirements(STUDENT_TASK_MANAGER_PROMPT)
        c_map = {c.source_id: c for c in candidates}

        assert "R6" in c_map
        assert "R7" in c_map
        assert "survive server restarts" in c_map["R6"].original_text
        assert "Marking a task complete must update its status" in c_map["R7"].original_text

    def test_parses_numeric_5_item_list(self) -> None:
        candidates = parse_explicit_requirements(FIVE_REQ_ORDER_PROMPT)
        assert len(candidates) == 5, f"Expected 5 candidates, got {len(candidates)}"

        source_ids = [c.source_id for c in candidates]
        assert source_ids == ["1", "2", "3", "4", "5"]

        c_map = {c.source_id: c for c in candidates}
        assert "$15.00" in c_map["3"].description
        assert "atomically" in c_map["2"].description
        assert "Shipped" in c_map["4"].description


class TestExtractorIntegration:
    """Integration tests with MockRequirementExtractor."""

    def test_extractor_extracts_12_records(self) -> None:
        extractor = MockRequirementExtractor()
        candidates = asyncio.run(extractor.extract(uuid4(), STUDENT_TASK_MANAGER_PROMPT))
        assert len(candidates) == 12
        assert [c.source_id for c in candidates] == [f"R{i}" for i in range(1, 13)]

    def test_extractor_extracts_5_records(self) -> None:
        extractor = MockRequirementExtractor()
        candidates = asyncio.run(extractor.extract(uuid4(), FIVE_REQ_ORDER_PROMPT))
        assert len(candidates) == 5
        assert [c.source_id for c in candidates] == ["1", "2", "3", "4", "5"]


class TestEndToEndApiExtraction:
    """End-to-end tests through the FastAPI task and requirement endpoints."""

    def test_create_task_extracts_12_canonical_requirements(self, client: TestClient) -> None:
        resp = client.post(
            "/api/tasks",
            json={"original_request": STUDENT_TASK_MANAGER_PROMPT},
        )
        assert resp.status_code == 201
        data = resp.json()
        task_id = data["task"]["id"]
        requirements = data.get("requirements", [])

        # Verify exactly 12 canonical requirements extracted
        assert len(requirements) == 12, f"Expected 12 requirements, got {len(requirements)}"

        # Verify source IDs R1 to R12 are all present and ordered
        source_ids = [r.get("source_id") for r in requirements]
        expected_sources = [f"R{i}" for i in range(1, 13)]
        assert source_ids == expected_sources

        # Verify canonical IDs R001 to R012
        canonical_ids = [r["id"] for r in requirements]
        expected_canonical = [f"R{i:03d}" for i in range(1, 13)]
        assert canonical_ids == expected_canonical

        # Check GET /api/tasks/{task_id}/requirements preserves everything
        req_resp = client.get(f"/api/tasks/{task_id}/requirements")
        assert req_resp.status_code == 200
        fetched_reqs = req_resp.json().get("requirements", [])
        assert len(fetched_reqs) == 12

        # Verify traceability: check R3 has the length bounds
        r3 = next(r for r in fetched_reqs if r.get("source_id") == "R3")
        assert "between 3 and 100 characters" in r3["description"]

        # Verify traceability: check R11 has idempotency
        r11 = next(r for r in fetched_reqs if r.get("source_id") == "R11")
        assert "idempotency" in r11["description"].lower()

    def test_create_task_extracts_5_canonical_requirements(self, client: TestClient) -> None:
        resp = client.post(
            "/api/tasks",
            json={"original_request": FIVE_REQ_ORDER_PROMPT},
        )
        assert resp.status_code == 201
        data = resp.json()
        requirements = data.get("requirements", [])

        assert len(requirements) == 5, f"Expected 5 requirements, got {len(requirements)}"
        source_ids = [r.get("source_id") for r in requirements]
        assert source_ids == ["1", "2", "3", "4", "5"]

        r3 = next(r for r in requirements if r.get("source_id") == "3")
        assert "$15.00" in r3["description"]


class TestHandoffValidationTraceability:
    """Tests ensuring handoff validator evaluates canonical requirements independently and reports by source ID."""

    def test_omission_reports_source_id(self, client: TestClient) -> None:
        # Create 12-requirement task
        task_resp = client.post(
            "/api/tasks",
            json={"original_request": STUDENT_TASK_MANAGER_PROMPT},
        )
        task_id = task_resp.json()["task"]["id"]

        # Submit handoff omitting R11 (idempotency) and R5 (ownership)
        # Using source IDs in requirement_ids
        included_reqs = [f"R{i}" for i in range(1, 13) if i not in (5, 11)]
        handoff_resp = client.post(
            f"/api/tasks/{task_id}/handoffs",
            json={
                "source_agent": "spec_agent",
                "target_agent": "coding_agent",
                "requirement_ids": included_reqs,
                "payload": {
                    "architecture": "FastAPI + React",
                    "omitted_requirements": [
                        "R11 idempotency deferred to v2",
                    ],
                },
                "auto_repair": False,
            },
        )
        assert handoff_resp.status_code == 201
        handoff_data = handoff_resp.json()
        issues = handoff_data["handoff"]["issues"]

        omissions = [i for i in issues if i["issue_type"] == "omission"]
        omitted_ids = {i["requirement_id"] for i in omissions}

        # The issues must reference the source IDs (R5 and R11) or canonical IDs
        assert "R11" in omitted_ids or "R011" in omitted_ids
        assert "R5" in omitted_ids or "R005" in omitted_ids

    def test_contradiction_reports_source_id(self, client: TestClient) -> None:
        task_resp = client.post(
            "/api/tasks",
            json={"original_request": STUDENT_TASK_MANAGER_PROMPT},
        )
        task_id = task_resp.json()["task"]["id"]

        all_reqs = [f"R{i}" for i in range(1, 13)]
        handoff_resp = client.post(
            f"/api/tasks/{task_id}/handoffs",
            json={
                "source_agent": "spec_agent",
                "target_agent": "coding_agent",
                "requirement_ids": all_reqs,
                "payload": {
                    "architecture": "FastAPI + React",
                    "storage_strategy": "In-memory dict storage instead of database persistence.",
                },
                "auto_repair": False,
            },
        )
        assert handoff_resp.status_code == 201
        handoff_data = handoff_resp.json()
        issues = handoff_data["handoff"]["issues"]

        contradictions = [i for i in issues if i["issue_type"] == "contradiction"]
        assert len(contradictions) >= 1
        c_req_ids = {c["requirement_id"] for c in contradictions}
        # R6 is the PostgreSQL persistence requirement
        assert "R6" in c_req_ids or "R006" in c_req_ids

    def test_weakened_constraint_reports_source_id(self, client: TestClient) -> None:
        task_resp = client.post(
            "/api/tasks",
            json={"original_request": STUDENT_TASK_MANAGER_PROMPT},
        )
        task_id = task_resp.json()["task"]["id"]

        all_reqs = [f"R{i}" for i in range(1, 13)]
        handoff_resp = client.post(
            f"/api/tasks/{task_id}/handoffs",
            json={
                "source_agent": "spec_agent",
                "target_agent": "coding_agent",
                "requirement_ids": all_reqs,
                "payload": {
                    "architecture": "FastAPI + React",
                    "validation_strategy": "Client-side only validation for simplicity. Server accepts all inputs.",
                },
                "auto_repair": False,
            },
        )
        assert handoff_resp.status_code == 201
        handoff_data = handoff_resp.json()
        issues = handoff_data["handoff"]["issues"]

        weakened = [i for i in issues if i["issue_type"] == "weakened_constraint"]
        assert len(weakened) >= 1
        w_req_ids = {w["requirement_id"] for w in weakened}
        # R10 specifies server-side validation
        assert "R10" in w_req_ids or "R010" in w_req_ids
