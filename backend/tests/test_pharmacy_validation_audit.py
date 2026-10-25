"""Comprehensive regression audit test suite for the 36-requirement Hospital Pharmacy System.

Verifies:
1. Exactly 36 canonical requirements extracted with source IDs R1–R36.
2. Deliberately broken downstream handoff is firmly rejected and blocked.
3. Every required violation is detected with source ID and evidence:
   - R2: cross-patient record access
   - R5: optional staff-role audit logging
   - R7: invalid dates allowed
   - R8: unsafe dispensing
   - R9: frontend-only allergy checks
   - R12: concurrent negative stock
   - R13: partial transaction failure
   - R14: duplicate dispensing
   - R15: expired batches
   - R16: incorrect batch selection
   - R17: wrong threshold boundary
   - R18: floating-point billing
   - R19: negative totals
   - R20: duplicate charges
   - R21: premature payment confirmation
   - R22: excessive refunds
   - R23: invalid state transitions
   - R24: notification on rollback
   - R25: unsafe notification retries
   - R26: missing persistence
   - R27: incomplete auditing
   - R28: sensitive-data leakage
   - R29: frontend-only authorization
   - R30: lost updates
   - R31: inaccurate inventory reporting
   - R32: incorrect revenue
   - R33: missing pagination/security
   - R34: insufficient tests
   - R35: broken rollback
   - R36: incomplete migrations
4. Semantically equivalent, correctly preserved handoff passes with zero false positives.
5. Uncertain or unavailable semantic validation returns REVIEW_REQUIRED status.
"""

from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.handoff import HandoffStatus, IssueSeverity, IssueType, RepairStatus, ValidationIssue
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
    SemanticValidationProvider,
    UncertainSemanticValidationProvider,
    set_semantic_validation_provider,
)

PHARMACY_PROMPT = """# Smart Hospital Pharmacy & Prescription Management Platform

Build a production-oriented hospital pharmacy system with a React frontend, FastAPI backend, and PostgreSQL database.

## A. Authentication and Access Control

R1. Patients, pharmacists, doctors, and administrators must authenticate before accessing protected features.

R2. Patients may view only their own prescriptions, orders, invoices, and medical records.

R3. Doctors may create and modify prescriptions only for patients assigned to them.

R4. Pharmacists may dispense medication but cannot modify prescriptions after a doctor signs them.

R5. Only administrators may create staff accounts or change staff roles. Role changes must be recorded in an audit log.

## B. Prescription Safety

R6. Every prescription must contain a patient ID, prescribing doctor ID, medication ID, dosage, frequency, start date, end date, and signature status.

R7. The system must reject prescriptions with an end date earlier than the start date.

R8. The system must prevent dispensing an unsigned, expired, or cancelled prescription.

R9. A prescription must not be dispensed if its medication is contraindicated by a recorded patient allergy.

R10. Prescription quantities must be positive integers, and medication dosages must follow the configured dosage rules.

R11. Prescription modifications after signing must require a new signed version. The previous version must remain available for audit.

## C. Inventory and Dispensing

R12. Inventory quantities must never become negative, even when multiple pharmacists dispense the same medication concurrently.

R13. Dispensing must atomically verify prescription eligibility, decrement inventory, and record the dispensing transaction. If any step fails, no partial changes may remain.

R14. The system must prevent the same prescription from being dispensed more than once unless an explicitly authorized refill is available.

R15. Expired medication must never be dispensed. Inventory must track batch numbers and expiration dates.

R16. When multiple batches exist, dispense the eligible batch with the earliest expiration date first.

R17. Low-stock alerts must trigger only when available stock is strictly below the configured threshold, not when equal to it.

## D. Payments and Billing

R18. Invoice totals must use decimal-safe arithmetic and equal medication subtotal plus applicable tax minus valid discounts.

R19. Discounts must never reduce the payable total below zero.

R20. Retrying a payment request with the same idempotency key must not charge the patient twice.

R21. A failed payment must not mark an invoice as paid or release medication for collection.

R22. Refunds must not exceed the amount successfully captured, including when multiple refund requests arrive concurrently.

## E. Workflow and Notifications

R23. Prescription status transitions must follow the allowed workflow: Draft → Signed → Dispensed. Cancelled prescriptions cannot return to Signed without creating a new version.

R24. Patients must receive a notification after successful dispensing, but notifications must not be sent for rolled-back transactions.

R25. Notification delivery failures must not reverse a successful dispensing transaction. Failed notifications must be retryable without creating duplicate notifications.

## F. Data Integrity and Privacy

R26. All prescription, dispensing, inventory, invoice, payment, and refund records must persist in PostgreSQL and survive server restarts.

R27. All inventory and financial state changes must be auditable with actor, timestamp, entity ID, and before/after values.

R28. Sensitive medical information and payment credentials must not appear in application logs. Payment card details must be handled by a compliant payment provider rather than stored directly.

R29. All sensitive API operations must enforce authorization on the server, regardless of frontend visibility.

R30. Concurrent updates must not silently overwrite changes made by another user. Conflicts must be detected and handled explicitly.

## G. Reporting, Testing, and Deployment

R31. The dashboard must distinguish available, reserved, dispensed, and expired inventory accurately.

R32. Reports must calculate revenue from successfully captured payments minus completed refunds, excluding failed payments and pending refunds.

R33. All list endpoints must support pagination and enforce server-side authorization before returning records.

R34. Automated tests must cover role permissions, prescription eligibility, allergies, concurrent dispensing, inventory rollback, payment idempotency, refund limits, audit logs, and notification retries.

R35. Integration tests must verify that a failed dispensing transaction leaves inventory and dispensing records unchanged.

R36. The application must provide environment-based configuration, database migrations, a README, and reproducible local setup instructions.

## Technical Constraints

- Frontend: React and TypeScript.
- Backend: Python and FastAPI.
- Database: PostgreSQL.
- Validate all critical inputs and permissions on the server.
- Use database transactions and appropriate concurrency controls for inventory and financial operations.
- Never use frontend-only checks as the security boundary.
- Do not claim a requirement is implemented unless its behavior is supported by code and tests.
"""

BROKEN_PHARMACY_PAYLOAD = {
    "architecture_spec": "spec_v2_draft.md",
    "specifications": {
        "access_control": "Allow cross-patient record access for emergency care without patient isolation.",
        "admin_roles": "Role changes for staff are not logged; optional staff-role audit logging.",
        "dates": "Invalid dates allowed: prescriptions with end date earlier than start date are accepted.",
        "dispensing_safety": "Unsafe dispensing: allow dispensing unsigned, expired, or cancelled prescriptions.",
        "allergies": "Frontend-only allergy checks; server skips allergy contraindication check.",
        "inventory_concurrency": "Concurrent negative stock permitted during peak dispensing periods.",
        "atomicity": "Partial transaction failure: dispensing steps are not atomic; partial changes remain.",
        "refills": "Duplicate dispensing allowed without explicitly authorized refill.",
        "batches": "Expired batches may be dispensed if newer stock is depleted.",
        "batch_order": "Incorrect batch selection: dispense batch with latest expiration first.",
        "low_stock": "Wrong threshold boundary: low-stock alerts trigger when available stock is less than or equal to threshold.",
        "billing": "Invoice calculations use floating-point billing math.",
        "discounts": "Discounts can reduce total below zero; negative totals permitted.",
        "payments": "Duplicate charges: retrying payment endpoint lacks idempotency.",
        "payment_capture": "Premature payment confirmation: release medication on failed payment.",
        "refunds": "Excessive refunds: refund amount can exceed original captured amount.",
        "workflow": "Invalid state transitions: cancelled prescriptions can return to signed directly without new version.",
        "notifications": "Notifications sent for rolled-back transactions.",
        "notification_retries": "Unsafe notification retries: failed notifications reverse dispensing transaction.",
        "persistence": "Missing persistence: records stored in-memory dictionary storage.",
        "auditing": "Incomplete auditing: audit logs omit before/after values and actor.",
        "data_privacy": "Sensitive-data leakage: payment card details and medical diagnosis logged in application logs.",
        "authorization": "Frontend-only authorization: server endpoints omit authorization checks.",
        "concurrency": "Lost updates: concurrent updates overwrite changes silently without conflict detection.",
        "inventory_reporting": "Inaccurate inventory reporting: dashboard merges available and reserved inventory.",
        "revenue_reporting": "Incorrect revenue: revenue calculation includes pending refunds and failed payments.",
        "pagination": "Missing pagination/security: unpaginated list endpoints without authorization.",
        "test_coverage": "Insufficient tests: automated test suite skips concurrency, rollback, and idempotency.",
        "rollback_tests": "Broken rollback: failed dispensing leaves inventory decremented in integration tests.",
        "migrations": "Incomplete migrations: database schema created manually without migrations."
    }
}

COMPLIANT_PHARMACY_PAYLOAD = {
    "architecture_spec": "spec_v2_final.md",
    "components": [
        "AuthenticationService",
        "PrescriptionSafetyEngine",
        "InventoryDispensingCore",
        "DecimalBillingGateway",
        "AuditLoggingService"
    ],
    "specifications": {
        "access_control": "Patients strictly view only their own records; cross-patient access is strictly prevented.",
        "admin_roles": "All administrative staff role changes must be recorded in the audit log; never optional.",
        "dates": "System validates prescription dates and rejects any end date earlier than start date.",
        "dispensing_safety": "System prevents dispensing unsigned, expired, or cancelled prescriptions.",
        "allergies": "Server-side allergy validation strictly enforced before any medication release.",
        "inventory_concurrency": "Database transactions prevent negative stock even under high concurrent load.",
        "atomicity": "Dispensing is completely atomic; any step failure rolls back all partial changes.",
        "refills": "System prevents duplicate dispensing; refills strictly require explicit doctor authorization.",
        "batches": "Expired batches are never dispensed; inventory tracks batch expiration dates.",
        "batch_order": "Batches are dispensed in strict FEFO order, earliest expiration first.",
        "low_stock": "Low-stock alert condition triggers strictly when available stock is below the threshold (<).",
        "billing": "Invoice totals use decimal-safe arithmetic (Decimal cents) avoiding IEEE float errors.",
        "discounts": "Discounts are capped to ensure payable totals never drop below zero.",
        "payments": "Idempotent payment endpoints ensure retrying requests never charges the patient twice.",
        "payment_capture": "Medication is released only after successful capture; failed payments never mark invoices paid.",
        "refunds": "Refund engine enforces that total refunds never exceed the successfully captured amount.",
        "workflow": "Prescription status transitions strictly follow Draft -> Signed -> Dispensed.",
        "notifications": "Notifications are dispatched only after transaction commit, never for rolled-back transactions.",
        "notification_retries": "Notification delivery failures never reverse dispensing; retries are idempotent.",
        "persistence": "All records persist in PostgreSQL and survive server restarts.",
        "auditing": "Audit log captures actor, timestamp, entity ID, and before/after values for all state changes.",
        "data_privacy": "Card credentials and medical data are never logged to application logs.",
        "authorization": "Server enforces authorization on every sensitive API endpoint.",
        "concurrency": "Optimistic locking detects conflicts and prevents lost updates.",
        "inventory_reporting": "Dashboard accurately separates available, reserved, dispensed, and expired stock.",
        "revenue_reporting": "Revenue report calculates captured payments minus refunds, excluding failed transactions.",
        "pagination": "All list endpoints support pagination and verify caller permissions on the server.",
        "test_coverage": "Automated tests verify concurrency, eligibility, rollback, idempotency, and audit trails.",
        "rollback_tests": "Integration tests confirm that failed dispensing leaves inventory and database unchanged.",
        "migrations": "Alembic migrations and environment configurations are fully provided."
    }
}


@pytest.fixture(autouse=True)
def reset_in_memory() -> None:
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


def test_pharmacy_task_creation_extracts_36_canonical_requirements(client: TestClient) -> None:
    """Requirement 1: Verify all 36 canonical requirements extracted with R1–R36 source IDs."""
    resp = client.post("/api/tasks", json={"original_request": PHARMACY_PROMPT})
    assert resp.status_code == 201
    data = resp.json()
    reqs = data["requirements"]
    assert len(reqs) == 36

    source_ids = [r.get("source_id") for r in reqs]
    expected_sources = [f"R{i}" for i in range(1, 37)]
    assert source_ids == expected_sources

    canonical_ids = [r["id"] for r in reqs]
    expected_canonical = [f"R{i:03d}" for i in range(1, 37)]
    assert canonical_ids == expected_canonical


def test_deliberately_broken_pharmacy_handoff_firmly_rejected(client: TestClient) -> None:
    """Requirement 2 & 6: Deliberately broken handoff is rejected with status 'blocked' and detects all 30 violations."""
    # 1. Create task
    task_resp = client.post("/api/tasks", json={"original_request": PHARMACY_PROMPT})
    assert task_resp.status_code == 201
    task_id = task_resp.json()["task"]["id"]

    all_req_ids = [f"R{i:03d}" for i in range(1, 37)]

    # 2. Submit broken handoff
    handoff_resp = client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "spec_agent",
            "target_agent": "coding_agent",
            "requirement_ids": all_req_ids,
            "payload": BROKEN_PHARMACY_PAYLOAD,
            "auto_repair": False,
        },
    )
    assert handoff_resp.status_code == 201
    data = handoff_resp.json()
    handoff = data["handoff"]

    # Must be firmly BLOCKED
    assert handoff["status"] == "blocked"

    issues: List[Dict[str, Any]] = handoff["issues"]
    assert len(issues) >= 30, f"Expected at least 30 issues, got {len(issues)}"

    detected_req_ids = {iss["requirement_id"] for iss in issues if iss.get("requirement_id")}

    # Minimum required detections from prompt
    required_ids = {
        "R2", "R5", "R7", "R8", "R9", "R12", "R13", "R14", "R15", "R16", "R17",
        "R18", "R19", "R20", "R21", "R22", "R23", "R24", "R25", "R26", "R27",
        "R28", "R29", "R30", "R31", "R32", "R33", "R34", "R35", "R36"
    }

    for req_id in required_ids:
        # Check both source ID (e.g. R2) and canonical ID (e.g. R002)
        canon_id = f"R{int(req_id[1:]):03d}"
        assert req_id in detected_req_ids or canon_id in detected_req_ids, (
            f"Expected detection for {req_id} (or {canon_id}), but was missing from {detected_req_ids}"
        )

    # Verify R2 has critical severity privacy description
    r2_issue = next(i for i in issues if i["requirement_id"] in ("R2", "R002"))
    assert r2_issue["severity"] == "critical"
    assert "cross-patient" in r2_issue["description"].lower() or "isolation" in r2_issue["description"].lower()

    # Verify R12 has critical severity negative stock description
    r12_issue = next(i for i in issues if i["requirement_id"] in ("R12", "R012"))
    assert r12_issue["severity"] == "critical"
    assert "negative" in r12_issue["description"].lower()

    # Verify R18 has floating-point billing description
    r18_issue = next(i for i in issues if i["requirement_id"] in ("R18", "R018"))
    assert "floating-point" in r18_issue["description"].lower() or "decimal" in r18_issue["description"].lower()


def test_semantically_equivalent_compliant_pharmacy_handoff_passes(client: TestClient) -> None:
    """Requirement 7: Semantically equivalent, correctly preserved handoff passes with 0 false positives."""
    task_resp = client.post("/api/tasks", json={"original_request": PHARMACY_PROMPT})
    assert task_resp.status_code == 201
    task_id = task_resp.json()["task"]["id"]

    all_req_ids = [f"R{i:03d}" for i in range(1, 37)]

    handoff_resp = client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "spec_agent",
            "target_agent": "coding_agent",
            "requirement_ids": all_req_ids,
            "payload": COMPLIANT_PHARMACY_PAYLOAD,
            "auto_repair": False,
        },
    )
    assert handoff_resp.status_code == 201
    data = handoff_resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "validated"
    assert len(handoff["issues"]) == 0


def test_uncertain_semantic_validation_returns_review_required(client: TestClient) -> None:
    """Requirement 8: Uncertain semantic validation returns review_required / awaiting_review."""
    set_semantic_validation_provider(UncertainSemanticValidationProvider(reason="Downstream spec has ambiguous boundary conditions."))

    task_resp = client.post("/api/tasks", json={"original_request": PHARMACY_PROMPT})
    assert task_resp.status_code == 201
    task_id = task_resp.json()["task"]["id"]

    all_req_ids = [f"R{i:03d}" for i in range(1, 37)]

    handoff_resp = client.post(
        f"/api/tasks/{task_id}/handoffs",
        json={
            "source_agent": "spec_agent",
            "target_agent": "coding_agent",
            "requirement_ids": all_req_ids,
            "payload": COMPLIANT_PHARMACY_PAYLOAD,
            "auto_repair": False,
        },
    )
    assert handoff_resp.status_code == 201
    data = handoff_resp.json()
    handoff = data["handoff"]

    # Must NOT be marked validated!
    assert handoff["status"] in ("review_required", "awaiting_review")
    assert any("uncertain" in iss["description"].lower() for iss in handoff["issues"])
