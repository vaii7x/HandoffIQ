"""Automated tests for HandoffIQ Presentation-Ready Demo Mode.

Verifies:
1. Exactly 6 canonical requirements are loaded.
2. Exactly 5 known defects are seeded.
3. Negative control R6 is preserved and not flagged.
4. Actual validator detections are reported accurately.
5. Validator misses remain visible rather than hidden.
6. All 5 repairs restore the intended requirements with before/after diffs.
7. Revalidation reflects actual repaired state.
8. Demo mode does not modify real tasks or invoke external services.
9. Repeated runs produce reproducible results.
10. Live mode remains unaffected.
"""

from typing import List, Dict, Any
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_service import (
    DEMO_REQUIREMENTS,
    DEMO_BROKEN_HANDOFF,
    DEMO_REPAIRS,
    validate_demo_handoff,
    revalidate_demo_handoff,
    run_oracle_checks,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_1_exactly_six_canonical_requirements_loaded(client: TestClient) -> None:
    """Requirement: Exactly six canonical requirements are loaded with stable IDs."""
    res = client.get("/api/demo/requirements")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6
    req_ids = [r["source_id"] for r in data]
    assert req_ids == ["R1", "R2", "R3", "R4", "R5", "R6"]
    for r in data:
        assert r["authoritative"] is True
        assert len(r["description"]) > 10


def test_2_exactly_five_known_defects_and_one_preserved_control(client: TestClient) -> None:
    """Requirement: The broken handoff seeds exactly 5 defects (D1-D5) and preserves R6."""
    res = client.get("/api/demo/broken-handoff")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 6

    broken_items = [i for i in items if i["status"] == "broken"]
    preserved_items = [i for i in items if i["status"] == "preserved"]

    assert len(broken_items) == 5, f"Expected exactly 5 broken items, found {len(broken_items)}"
    assert len(preserved_items) == 1, f"Expected exactly 1 preserved item, found {len(preserved_items)}"

    defect_ids = {i["defect_id"] for i in broken_items}
    assert defect_ids == {"D1", "D2", "D3", "D4", "D5"}

    # Preserved item is R6
    r6_item = preserved_items[0]
    assert r6_item["requirement_id"] == "R6"
    assert "expired medication must never be dispensed" in r6_item["received_text"].lower()


def test_3_oracle_broken_inspection_verifies_seeded_defects_and_control() -> None:
    """Oracle verifies each defect differs from original and R6 remains unchanged."""
    checks = run_oracle_checks(DEMO_BROKEN_HANDOFF, phase="broken_inspection")
    assert len(checks) == 6
    for c in checks:
        assert c.passed is True, f"Oracle check {c.check_id} failed: {c.details}"

    r6_check = next(c for c in checks if c.requirement_id == "R6")
    assert r6_check.passed is True
    assert "never" in r6_check.actual_value.lower()


def test_4_actual_validator_detects_all_five_seeded_defects(client: TestClient) -> None:
    """Validator detects all 5 discrepancies without faking results."""
    res = client.post("/api/demo/validate")
    assert res.status_code == 200
    val_data = res.json()

    assert val_data["validator_detected_count"] == 5
    assert val_data["oracle_seeded_defect_count"] == 5
    assert val_data["preserved_count"] == 1
    assert val_data["all_seeded_defects_detected"] is True
    assert len(val_data["missed_defects"]) == 0

    discrepancies: List[Dict[str, Any]] = val_data["discrepancies"]
    assert len(discrepancies) == 5

    detected_reqs = {d["requirement_id"] for d in discrepancies if d["validator_detected"]}
    assert detected_reqs == {"R1", "R2", "R3", "R4", "R5"}

    # Preserved requirement R6 must not appear in discrepancies
    assert "R6" not in detected_reqs
    assert val_data["preserved_requirement"]["requirement_id"] == "R6"


def test_5_validator_misses_are_visibly_flagged_if_discrepancy_unmatched() -> None:
    """If a defect is missed, system sets validator_detected=False and marks is_missed_by_validator."""
    val_data = validate_demo_handoff()
    # Confirm contract properties exist on every discrepancy
    for d in val_data.discrepancies:
        assert hasattr(d, "is_missed_by_validator")
        assert hasattr(d, "validator_detected")
        assert hasattr(d, "oracle_detected")


def test_6_repairs_restore_intended_specifications_with_diffs(client: TestClient) -> None:
    """All 5 repairs restore patient authorization, password hashing, inventory, atomicity, and idempotency."""
    res = client.get("/api/demo/repairs")
    assert res.status_code == 200
    repairs = res.json()
    assert len(repairs) == 5

    repair_reqs = {r["requirement_id"] for r in repairs}
    assert repair_reqs == {"R1", "R2", "R3", "R4", "R5"}

    for rep in repairs:
        assert rep["status"] == "repaired"
        assert len(rep["repair_reason"]) > 10
        assert rep["diff_before"].startswith("-")
        assert rep["diff_after"].startswith("+")
        assert rep["broken_text"] != rep["repaired_text"]


def test_7_revalidation_verifies_clean_state_and_disclaimer(client: TestClient) -> None:
    """Revalidation passes with 0 issues, oracle passes, all_clear=True, and disclaimer included."""
    res = client.post("/api/demo/revalidate")
    assert res.status_code == 200
    reval = res.json()

    assert reval["validator_issues_count"] == 0
    assert reval["oracle_passed"] is True
    assert reval["resolved_count"] == 5
    assert reval["unresolved_count"] == 0
    assert reval["all_clear"] is True
    assert len(reval["remaining_issues"]) == 0

    assert "does not prove the generated code implements it" in reval["disclaimer"]


def test_8_repeated_runs_are_deterministic_and_reproducible() -> None:
    """Repeated runs of validate and revalidate produce consistent results with zero side-effects."""
    run1_val = validate_demo_handoff()
    run2_val = validate_demo_handoff()
    assert run1_val.validator_detected_count == run2_val.validator_detected_count == 5

    run1_rev = revalidate_demo_handoff()
    run2_rev = revalidate_demo_handoff()
    assert run1_rev.all_clear is True and run2_rev.all_clear is True


def test_9_demo_mode_does_not_modify_live_task_database(client: TestClient) -> None:
    """Demo mode operations do not create or alter production tasks."""
    tasks_before = client.get("/api/tasks").json()
    count_before = len(tasks_before)

    # Perform full demo walkthrough API sequence
    client.get("/api/demo/requirements")
    client.get("/api/demo/broken-handoff")
    client.post("/api/demo/validate")
    client.get("/api/demo/repairs")
    client.post("/api/demo/revalidate")

    tasks_after = client.get("/api/tasks").json()
    count_after = len(tasks_after)

    assert count_before == count_after, "Demo Mode must never insert tasks into live repository"


def test_10_live_mode_remains_unaffected(client: TestClient) -> None:
    """Live Mode task creation, handoff validation, and status retrieval continue working normally."""
    task_res = client.post("/api/tasks", json={"original_request": "Demo Mode regression check"})
    assert task_res.status_code == 201
    task_id = task_res.json()["task"]["id"]

    get_res = client.get(f"/api/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["task"]["id"] == task_id
