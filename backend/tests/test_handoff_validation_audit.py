"""Comprehensive audit test suite for HandoffIQ handoff validation pipeline.

Verifies detection of:
1. Plaintext passwords / weak cryptography
2. Missing delivery fees
3. Partial orders allowed (weakened full-order constraint)
4. Non-atomic inventory updates (atomicity / transaction violation)
5. Duplicate-payment risk (missing idempotency guarantee)
6. Authorization gaps (unauthenticated / unrestricted cancellation)
7. Repeated inventory restoration (stock inflation risk)
8. Frontend-only validation (security / integrity regression)
9. Incomplete tests (testing coverage gap)
10. In-memory persistence (database contradiction)
11. Valid semantically equivalent paraphrases (zero false positives)
12. Semantic provider uncertainty and error reporting (never silently compliant)
13. Changed numeric thresholds ($5 flat fee under $30)
"""

from typing import Any, Dict, List
from uuid import UUID
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.handoff import IssueSeverity, IssueType, RepairStatus
from app.models.requirement import Requirement, RequirementPriority, RequirementStatus
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
    SemanticValidationProvider,
    UncertainSemanticValidationProvider,
    set_semantic_validation_provider,
)


@pytest.fixture(autouse=True)
def reset_repositories() -> None:
    """Clear repositories and set default provider before each test."""
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


@pytest.fixture
def food_ordering_task(client: TestClient) -> dict:
    """Create a task representing the complete Food Ordering platform with 10 canonical requirements."""
    # 1. Create task
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Food Ordering Platform",
            "original_request": "Build a robust food ordering backend platform with secure authentication, delivery fees, and order processing.",
        },
    )
    assert resp.status_code == 201
    task_data = resp.json()
    task_id = task_data["task"]["id"]

    # 2. Register all 10 explicit canonical requirements for the food ordering domain
    food_requirements = [
        ("R001", "User authentication with securely hashed passwords using bcrypt or argon2.", RequirementPriority.critical),
        ("R002", "Delivery fee calculation ($5 flat fee on orders under $30, free for orders $30 and above).", RequirementPriority.high),
        ("R003", "Full order placement rejecting partial orders if any ordered item is unavailable.", RequirementPriority.high),
        ("R004", "Atomic inventory deduction within a database transaction to prevent race conditions.", RequirementPriority.critical),
        ("R005", "Idempotent payment processing preventing duplicate charges on retried requests.", RequirementPriority.critical),
        ("R006", "Strict role-based authorization for order cancellation (only order owner or admin).", RequirementPriority.critical),
        ("R007", "Single inventory restoration ensuring stock is restored exactly once upon order cancellation.", RequirementPriority.high),
        ("R008", "Server-side validation of order payload, item prices, and calculated totals.", RequirementPriority.high),
        ("R009", "Complete automated test coverage covering orders, payments, cancellation, and concurrency.", RequirementPriority.high),
        ("R010", "Persistent PostgreSQL database storage for orders, user accounts, and inventory.", RequirementPriority.critical),
    ]

    task_uuid = UUID(task_id)
    _in_memory_repository._requirements[task_uuid] = {
        req_id: Requirement(
            id=req_id,
            task_id=task_uuid,
            original_text=text,
            priority=prio,
            status=RequirementStatus.registered,
            description=f"Detailed spec for {req_id}",
        )
        for req_id, text, prio in food_requirements
    }

    # Return refreshed task info
    task_resp = client.get(f"/api/tasks/{task_id}")
    assert task_resp.status_code == 200
    return task_resp.json()


# ============================================================================
# 10 Broken Food-Ordering Cases
# ============================================================================

def test_broken_case_1_plaintext_passwords(client: TestClient, food_ordering_task: dict) -> None:
    """Case 1: Plaintext password storage violates secure password hashing requirement."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "auth": {
                "password_storage": "plaintext",
                "algorithm": "none",
            },
            "notes": "User passwords stored in plaintext in the database table for quick debugging.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    pwd_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R001"]
    assert len(pwd_issues) >= 1
    issue = pwd_issues[0]
    assert issue["issue_type"] == IssueType.weakened_constraint
    assert issue["severity"] == IssueSeverity.critical
    assert issue["repair_status"] == RepairStatus.unresolved
    assert "plaintext" in issue["observed_value"].lower() or "plaintext" in " ".join(issue["evidence"]).lower()
    assert issue["original_value"] is not None


def test_broken_case_2_missing_delivery_fees(client: TestClient, food_ordering_task: dict) -> None:
    """Case 2: Missing or dropped delivery fee calculation."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "pricing": {
                "delivery_fee": "omitted",
            },
            "out_of_scope": ["delivery fee calculation"],
            "notes": "Delivery fee calculation is omitted from initial implementation.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    fee_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R002"]
    assert len(fee_issues) >= 1
    issue = fee_issues[0]
    assert issue["issue_type"] in [IssueType.omission, IssueType.weakened_constraint]
    assert issue["severity"] == IssueSeverity.high
    assert issue["repair_status"] == RepairStatus.unresolved
    assert len(issue["evidence"]) > 0


def test_broken_case_3_partial_orders_allowed(client: TestClient, food_ordering_task: dict) -> None:
    """Case 3: Allowing partial orders weakens all-or-nothing fulfillment rule."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "order_rules": {
                "allow_partial_fulfillment": True,
            },
            "description": "Allow partial orders if some items are out of stock.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    order_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R003"]
    assert len(order_issues) >= 1
    issue = order_issues[0]
    assert issue["issue_type"] == IssueType.weakened_constraint
    assert issue["severity"] == IssueSeverity.high
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_4_non_atomic_inventory_updates(client: TestClient, food_ordering_task: dict) -> None:
    """Case 4: Non-atomic inventory updates violate database transaction guarantee."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "inventory": {
                "update_type": "non-atomic",
                "transaction": False,
            },
            "notes": "Non-atomic inventory updates performed outside database transaction.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    inv_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R004"]
    assert len(inv_issues) >= 1
    issue = inv_issues[0]
    assert issue["issue_type"] == IssueType.contradiction
    assert issue["severity"] == IssueSeverity.critical
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_5_duplicate_payment_risk(client: TestClient, food_ordering_task: dict) -> None:
    """Case 5: Non-idempotent payment endpoint creates duplicate payment risk."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "payment": {
                "idempotency": False,
                "duplicate_check": "none",
            },
            "architecture": "Payment charges do not use idempotency keys, exposing users to duplicate payment risk.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    pay_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R005"]
    assert len(pay_issues) >= 1
    issue = pay_issues[0]
    assert issue["issue_type"] == IssueType.contradiction
    assert issue["severity"] == IssueSeverity.critical
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_6_authorization_gaps_on_cancel(client: TestClient, food_ordering_task: dict) -> None:
    """Case 6: Cancellation endpoint without authentication/role checks creates authorization gap."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "cancellation": {
                "public_endpoint": True,
                "require_auth": False,
            },
            "notes": "Order cancellation endpoint is public and allows unauthenticated cancellation.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    cancel_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R006"]
    assert len(cancel_issues) >= 1
    issue = cancel_issues[0]
    assert issue["issue_type"] == IssueType.weakened_constraint
    assert issue["severity"] == IssueSeverity.critical
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_7_repeated_inventory_restoration(client: TestClient, food_ordering_task: dict) -> None:
    """Case 7: Repeated inventory restoration on cancellation retries leads to stock inflation."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "cancellation": {
                "inventory_restoration": "on_every_retry",
            },
            "design": "Inventory is restored on every cancel retry, allowing repeated inventory restoration.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    inv_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R007"]
    assert len(inv_issues) >= 1
    issue = inv_issues[0]
    assert issue["issue_type"] == IssueType.weakened_constraint
    assert issue["severity"] == IssueSeverity.high
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_8_frontend_only_validation(client: TestClient, food_ordering_task: dict) -> None:
    """Case 8: Frontend-only price validation permits price tampering."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "validation": {
                "tier": "frontend_only",
                "server_validation": False,
            },
            "notes": "Order prices are validated on the client frontend only.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    val_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R008"]
    assert len(val_issues) >= 1
    issue = val_issues[0]
    assert issue["issue_type"] == IssueType.weakened_constraint
    assert issue["severity"] == IssueSeverity.high
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_9_incomplete_tests(client: TestClient, food_ordering_task: dict) -> None:
    """Case 9: Automated testing gap where key payment and inventory suites are skipped."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "testing": {
                "status": "incomplete",
                "coverage": "0%",
                "skipped_suites": ["payments", "inventory"],
            },
            "notes": "Automated tests are incomplete; payments and concurrency tests skipped.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    test_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R009"]
    assert len(test_issues) >= 1
    issue = test_issues[0]
    assert issue["issue_type"] == IssueType.implementation_gap
    assert issue["severity"] == IssueSeverity.high
    assert issue["repair_status"] == RepairStatus.unresolved


def test_broken_case_10_in_memory_persistence(client: TestClient, food_ordering_task: dict) -> None:
    """Case 10: In-memory dictionary storage directly opposes persistent PostgreSQL requirement."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "database": {
                "type": "in-memory dict",
                "persistence": False,
            },
            "notes": "Store orders in memory dictionary instead of persistent database.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    db_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R010"]
    assert len(db_issues) >= 1
    issue = db_issues[0]
    assert issue["issue_type"] == IssueType.contradiction
    assert issue["severity"] == IssueSeverity.critical
    assert issue["repair_status"] == RepairStatus.unresolved


# ============================================================================
# Valid Case: Semantically Equivalent Paraphrases (Zero False Positives)
# ============================================================================

def test_valid_semantically_equivalent_paraphrases_passes(client: TestClient, food_ordering_task: dict) -> None:
    """Verify that a downstream handoff describing all 10 requirements with realistic engineering paraphrases passes with 0 false positives."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]
    assert len(canonical_ids) == 10

    # Realistic engineering elaboration / paraphrase that fully adheres to canonical specifications
    paraphrased_payload = {
        "spec_name": "food_platform_architecture_v1.md",
        "architecture_summary": "Modular microservices architecture for food delivery ordering.",
        "components": [
            "AuthenticationGateway",
            "OrderPlacementService",
            "InventoryManager",
            "PaymentGatewayClient",
            "PostgresDatabaseAdapter",
        ],
        "subsystems": {
            "security": (
                "Users authenticate using JSON Web Tokens (JWT) with passwords encrypted via bcrypt (cost factor 12). "
                "Sessions are securely signed and verified on every API request."
            ),
            "pricing": (
                "Orders under $30 incur a $5 shipping/delivery surcharge; orders $30 and above receive free delivery. "
                "Subtotals and delivery charges are calculated server-side."
            ),
            "fulfillment": (
                "Partial order fulfillment is strictly prohibited; if any item is out of stock, the entire checkout transaction is aborted."
            ),
            "inventory_control": (
                "Inventory count is decremented within an ACID SQL transaction block with SELECT FOR UPDATE row locking."
            ),
            "payments": (
                "Payment requests require an Idempotency-Key header; duplicate requests return the cached transaction response without re-charging."
            ),
            "cancellation": (
                "Order cancellation endpoint checks user JWT and verifies role (customer owns order or role is admin). "
                "Cancellation handler records a RESTORED event and checks idempotent state to guarantee inventory is restored exactly once."
            ),
            "data_validation": (
                "All prices, payloads, and item subtotals are re-computed and validated on the backend API server."
            ),
            "testing_strategy": (
                "Comprehensive unit and integration test suite implemented with pytest covering orders, payments, transactions, and concurrency."
            ),
            "storage_layer": (
                "Persistent data storage utilizing PostgreSQL relational database with SQLAlchemy models."
            ),
        },
        "delivery_fee": 5,
        "fee_threshold": 30,
    }

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": paraphrased_payload,
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    # Must pass with validated status and ZERO discrepancies
    assert handoff["status"] == "validated", f"Expected validated, got {handoff['status']} with issues: {handoff['issues']}"
    assert handoff["issues"] == []
    assert len(handoff["requirement_ids"]) == 10
    assert data["repaired"] is False
    assert data["issues_count"] == 0


# ============================================================================
# Semantic Provider Uncertainty and Error Handling
# ============================================================================

def test_semantic_provider_uncertainty_blocks_silent_compliance(client: TestClient, food_ordering_task: dict) -> None:
    """When semantic provider cannot establish compliance, it reports as uncertain requiring review; never silently compliant."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    # Inject an uncertain provider
    set_semantic_validation_provider(
        UncertainSemanticValidationProvider(reason="Ambiguous delivery routing rules in architectural handoff context")
    )

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {"module": "routing", "status": "ambiguous_spec"},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert len(handoff["issues"]) >= 1
    uncertain_issues = [i for i in handoff["issues"] if "uncertain" in i["description"].lower() or i["issue_type"] == IssueType.implementation_gap]
    assert len(uncertain_issues) >= 1
    assert uncertain_issues[0]["repair_status"] == RepairStatus.unresolved
    assert uncertain_issues[0]["severity"] == IssueSeverity.medium


def test_semantic_provider_exception_reported_as_uncertain_not_silent(client: TestClient, food_ordering_task: dict) -> None:
    """When semantic analysis throws an exception (e.g. Gemini API failure), it reports an unresolved issue requiring review."""
    class FailingSemanticProvider(SemanticValidationProvider):
        @property
        def provider_name(self) -> str:
            return "failing_ai_provider"

        async def analyze(self, task_id, requirements, handoff):
            raise TimeoutError("Gemini API request timed out after 25 seconds")

    set_semantic_validation_provider(FailingSemanticProvider())

    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {"module": "standard"},
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert len(handoff["issues"]) >= 1
    err_issues = [i for i in handoff["issues"] if "TimeoutError" in " ".join(i["evidence"]) or "failing_ai_provider" in " ".join(i["evidence"])]
    assert len(err_issues) >= 1
    assert err_issues[0]["repair_status"] == RepairStatus.unresolved


# ============================================================================
# Changed Numeric Threshold Detection
# ============================================================================

def test_changed_numeric_threshold_detected(client: TestClient, food_ordering_task: dict) -> None:
    """When a numeric threshold is altered ($10 delivery fee on orders under $50), it is flagged as a discrepancy."""
    task_id = food_ordering_task["task"]["id"]
    canonical_ids = [r["id"] for r in food_ordering_task["requirements"]]

    payload = {
        "source_agent": "researcher",
        "target_agent": "coder",
        "requirement_ids": canonical_ids,
        "payload": {
            "spec": "food_order_v1.md",
            "pricing": {
                "delivery_fee": 10,
                "fee_threshold": 50,
            },
            "description": "$10 delivery fee on orders under $50.",
        },
        "auto_repair": True,
    }

    resp = client.post(f"/api/tasks/{task_id}/handoffs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    handoff = data["handoff"]

    assert handoff["status"] == "blocked"
    threshold_issues = [i for i in handoff["issues"] if i["requirement_id"] == "R002"]
    assert len(threshold_issues) >= 1
    issue = threshold_issues[0]
    assert issue["issue_type"] == IssueType.weakened_constraint
    assert issue["severity"] == IssueSeverity.high
    assert issue["original_value"] == "$5 flat fee on orders under $30"
    assert "10" in str(issue["observed_value"]) or "50" in str(issue["observed_value"])
