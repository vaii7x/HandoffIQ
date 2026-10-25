"""HandoffIQ Presentation-Ready Demo Mode Service.

Provides deterministic data fixtures, executable validation engine hooks,
independent demo-oracle verification, before/after diffs, and revalidation logic.
Operates completely isolated from production/live task storage.
"""

from typing import Any, Dict, List, Tuple
from uuid import uuid4

from app.models.demo import (
    DemoDiscrepancy,
    DemoHandoffItem,
    DemoRepairItem,
    DemoRequirement,
    DemoRevalidationResponse,
    DemoValidationResponse,
    OracleCheck,
)
from app.models.requirement import Requirement
from app.services.validation_rules import (
    check_deterministic_contradictions,
    check_missing_requirements,
    check_per_requirement_semantics,
    check_semantic_drift,
    check_weakened_constraints,
)

# -----------------------------------------------------------------------------
# 1. Authoritative Canonical Requirements (Fictional Hospital Pharmacy)
# -----------------------------------------------------------------------------

DEMO_REQUIREMENTS: List[DemoRequirement] = [
    DemoRequirement(
        id="R001",
        source_id="R1",
        title="Patient Medical Record Privacy",
        description="Patients may access only their own medical records.",
        category="Authorization & Privacy",
        authoritative=True,
    ),
    DemoRequirement(
        id="R002",
        source_id="R2",
        title="Cryptographic Password Hashing",
        description="Passwords must be securely hashed and never stored in plaintext.",
        category="Authentication Security",
        authoritative=True,
    ),
    DemoRequirement(
        id="R003",
        source_id="R3",
        title="Non-Negative Inventory Invariant",
        description="Inventory must never become negative during concurrent dispensing.",
        category="Inventory Invariants",
        authoritative=True,
    ),
    DemoRequirement(
        id="R004",
        source_id="R4",
        title="Atomic Dispensing Transaction",
        description="Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.",
        category="Transaction Atomicity",
        authoritative=True,
    ),
    DemoRequirement(
        id="R005",
        source_id="R5",
        title="Payment Idempotency Protection",
        description="Repeated payment requests with the same idempotency key must not charge a patient twice.",
        category="Billing Idempotency",
        authoritative=True,
    ),
    DemoRequirement(
        id="R006",
        source_id="R6",
        title="Expired Medication Restriction (Negative Control)",
        description="Expired medication must never be dispensed.",
        category="Dispensing Safety",
        authoritative=True,
    ),
]

# -----------------------------------------------------------------------------
# 2. Downstream Broken Handoff Fixture (5 Seeded Defects + 1 Preserved Control)
# -----------------------------------------------------------------------------

DEMO_BROKEN_HANDOFF: List[DemoHandoffItem] = [
    DemoHandoffItem(
        id="D1",
        requirement_id="R1",
        defect_id="D1",
        status="broken",
        received_text="Patients may access any patient's records if they know the record ID.",
        original_text="Patients may access only their own medical records.",
    ),
    DemoHandoffItem(
        id="D2",
        requirement_id="R2",
        defect_id="D2",
        status="broken",
        received_text="Passwords are stored in plaintext.",
        original_text="Passwords must be securely hashed and never stored in plaintext.",
    ),
    DemoHandoffItem(
        id="D3",
        requirement_id="R3",
        defect_id="D3",
        status="broken",
        received_text="Inventory is decremented without concurrency protection.",
        original_text="Inventory must never become negative during concurrent dispensing.",
    ),
    DemoHandoffItem(
        id="D4",
        requirement_id="R4",
        defect_id="D4",
        status="broken",
        received_text="Inventory changes remain even if writing the dispensing record fails.",
        original_text="Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.",
    ),
    DemoHandoffItem(
        id="D5",
        requirement_id="R5",
        defect_id="D5",
        status="broken",
        received_text="Payment retries can create duplicate charges.",
        original_text="Repeated payment requests with the same idempotency key must not charge a patient twice.",
    ),
    DemoHandoffItem(
        id="R6",
        requirement_id="R6",
        defect_id=None,
        status="preserved",
        received_text="Expired medication must never be dispensed.",
        original_text="Expired medication must never be dispensed.",
    ),
]

# -----------------------------------------------------------------------------
# 3. Deterministic Auto-Repairs (Unambiguous Canonical Restorations)
# -----------------------------------------------------------------------------

DEMO_REPAIRS: List[DemoRepairItem] = [
    DemoRepairItem(
        id="REP-1",
        requirement_id="R1",
        original_text="Patients may access only their own medical records.",
        broken_text="Patients may access any patient's records if they know the record ID.",
        repaired_text="Patients may access only their own medical records. Cross-patient access by record ID is strictly forbidden.",
        repair_reason="Restored strict patient authorization boundary and prohibited cross-patient ID traversal.",
        status="repaired",
        diff_before="- Patients may access any patient's records if they know the record ID.",
        diff_after="+ Patients may access only their own medical records. Cross-patient access by record ID is strictly forbidden.",
    ),
    DemoRepairItem(
        id="REP-2",
        requirement_id="R2",
        original_text="Passwords must be securely hashed and never stored in plaintext.",
        broken_text="Passwords are stored in plaintext.",
        repaired_text="Passwords must be securely hashed using bcrypt/argon2 and never stored in plaintext.",
        repair_reason="Enforced cryptographic hashing requirement and eradicated plaintext credential storage.",
        status="repaired",
        diff_before="- Passwords are stored in plaintext.",
        diff_after="+ Passwords must be securely hashed using bcrypt/argon2 and never stored in plaintext.",
    ),
    DemoRepairItem(
        id="REP-3",
        requirement_id="R3",
        original_text="Inventory must never become negative during concurrent dispensing.",
        broken_text="Inventory is decremented without concurrency protection.",
        repaired_text="Inventory must never become negative during concurrent dispensing, enforced with database row locks or optimistic concurrency.",
        repair_reason="Restored concurrency protection lock to enforce non-negative stock invariant during parallel dispensing.",
        status="repaired",
        diff_before="- Inventory is decremented without concurrency protection.",
        diff_after="+ Inventory must never become negative during concurrent dispensing, enforced with database row locks or optimistic concurrency.",
    ),
    DemoRepairItem(
        id="REP-4",
        requirement_id="R4",
        original_text="Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.",
        broken_text="Inventory changes remain even if writing the dispensing record fails.",
        repaired_text="Dispensing must be atomic: inventory updates and dispensing records must execute within a database transaction that fully rolls back on any step failure.",
        repair_reason="Enforced atomic transaction boundary, ensuring complete rollback upon dispensing record failure.",
        status="repaired",
        diff_before="- Inventory changes remain even if writing the dispensing record fails.",
        diff_after="+ Dispensing must be atomic: inventory updates and dispensing records must execute within a database transaction that fully rolls back on any step failure.",
    ),
    DemoRepairItem(
        id="REP-5",
        requirement_id="R5",
        original_text="Repeated payment requests with the same idempotency key must not charge a patient twice.",
        broken_text="Payment retries can create duplicate charges.",
        repaired_text="Repeated payment requests with the same idempotency key must verify existing payment status and never charge a patient twice.",
        repair_reason="Restored idempotency verification to guarantee idempotent payment capture without duplicate charges.",
        status="repaired",
        diff_before="- Payment retries can create duplicate charges.",
        diff_after="+ Repeated payment requests with the same idempotency key must verify existing payment status and never charge a patient twice.",
    ),
]


def _build_synthetic_requirements() -> List[Requirement]:
    """Instantiate standard internal Requirement models for the validator engine."""
    dummy_task_id = uuid4()
    reqs: List[Requirement] = []
    for r in DEMO_REQUIREMENTS:
        reqs.append(
            Requirement(
                task_id=dummy_task_id,
                id=r.id,
                source_id=r.source_id,
                title=r.title,
                description=r.description,
                original_text=r.description,
                priority="critical",
            )
        )
    return reqs


def _build_payload(handoff_items: List[DemoHandoffItem]) -> Dict[str, Any]:
    """Assemble a structured handoff payload mirroring downstream agent output."""
    spec_lines = [f"- {item.requirement_id}: {item.received_text}" for item in handoff_items]
    return {
        "summary": "Downstream Pharmacy Agent Implementation Specification",
        "handoff_spec": "\n".join(spec_lines),
        "spec_items": {item.requirement_id: item.received_text for item in handoff_items},
    }


# -----------------------------------------------------------------------------
# 4. Deterministic Demo Oracle Implementation
# -----------------------------------------------------------------------------

def run_oracle_checks(items: List[DemoHandoffItem], phase: str = "broken_inspection") -> List[OracleCheck]:
    """Deterministic, transparent test oracle asserting ground-truth conditions.
    
    The oracle does not replace the validator; it acts as an independent
    assertion harness verifying that known defects and negative controls are present.
    """
    item_map = {item.requirement_id: item.received_text for item in items}
    checks: List[OracleCheck] = []

    if phase == "broken_inspection":
        # Check D1: Patient Privacy defect present
        r1_text = item_map.get("R1", "")
        d1_present = "any patient" in r1_text.lower() and "record id" in r1_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-D1",
                requirement_id="R1",
                name="Seeded Defect D1: Cross-Patient Record Access",
                passed=d1_present,
                phase=phase,
                details="Asserts downstream text permits accessing other patient records by record ID.",
                actual_value=r1_text,
                expected_value="Patients may access any patient's records if they know the record ID.",
            )
        )

        # Check D2: Plaintext Password defect present
        r2_text = item_map.get("R2", "")
        d2_present = "plaintext" in r2_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-D2",
                requirement_id="R2",
                name="Seeded Defect D2: Plaintext Password Storage",
                passed=d2_present,
                phase=phase,
                details="Asserts downstream text specifies storing passwords in plaintext.",
                actual_value=r2_text,
                expected_value="Passwords are stored in plaintext.",
            )
        )

        # Check D3: Concurrency Protection defect present
        r3_text = item_map.get("R3", "")
        d3_present = "without concurrency protection" in r3_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-D3",
                requirement_id="R3",
                name="Seeded Defect D3: Negative Stock Concurrency Hazard",
                passed=d3_present,
                phase=phase,
                details="Asserts downstream text decrements inventory without concurrency protection.",
                actual_value=r3_text,
                expected_value="Inventory is decremented without concurrency protection.",
            )
        )

        # Check D4: Atomic Dispensing defect present
        r4_text = item_map.get("R4", "")
        d4_present = "changes remain" in r4_text.lower() and "fails" in r4_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-D4",
                requirement_id="R4",
                name="Seeded Defect D4: Partial Transaction Failure",
                passed=d4_present,
                phase=phase,
                details="Asserts downstream text leaves partial changes when record writing fails.",
                actual_value=r4_text,
                expected_value="Inventory changes remain even if writing the dispensing record fails.",
            )
        )

        # Check D5: Payment Idempotency defect present
        r5_text = item_map.get("R5", "")
        d5_present = "duplicate charges" in r5_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-D5",
                requirement_id="R5",
                name="Seeded Defect D5: Duplicate Payment Retries",
                passed=d5_present,
                phase=phase,
                details="Asserts downstream text permits retries to create duplicate payment charges.",
                actual_value=r5_text,
                expected_value="Payment retries can create duplicate charges.",
            )
        )

        # Check R6: Preserved Negative Control
        r6_text = item_map.get("R6", "")
        r6_preserved = (
            "expired medication must never be dispensed" in r6_text.lower()
            and "never" in r6_text.lower()
        )
        checks.append(
            OracleCheck(
                check_id="ORACLE-R6-CONTROL",
                requirement_id="R6",
                name="Negative Control R6: Preserved Expiration Rule",
                passed=r6_preserved,
                phase=phase,
                details="Asserts requirement R6 was preserved without modification or corruption.",
                actual_value=r6_text,
                expected_value="Expired medication must never be dispensed.",
            )
        )

    else:
        # Phase == 'revalidation'
        # Check R1 repair
        r1_text = item_map.get("R1", "")
        r1_ok = "only their own" in r1_text.lower() and "forbidden" in r1_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-REVALIDATE-R1",
                requirement_id="R1",
                name="Oracle Assertion: Patient Authorization Restored",
                passed=r1_ok,
                phase=phase,
                details="Asserts R1 enforces patient isolation and forbids cross-patient record access.",
                actual_value=r1_text,
                expected_value="Patients may access only their own medical records. Cross-patient access by record ID is strictly forbidden.",
            )
        )

        # Check R2 repair
        r2_text = item_map.get("R2", "")
        r2_ok = "securely hashed" in r2_text.lower() and "never stored in plaintext" in r2_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-REVALIDATE-R2",
                requirement_id="R2",
                name="Oracle Assertion: Cryptographic Hashing Restored",
                passed=r2_ok,
                phase=phase,
                details="Asserts R2 mandates secure hashing and forbids plaintext password storage.",
                actual_value=r2_text,
                expected_value="Passwords must be securely hashed using bcrypt/argon2 and never stored in plaintext.",
            )
        )

        # Check R3 repair
        r3_text = item_map.get("R3", "")
        r3_ok = "never become negative" in r3_text.lower() and ("locks" in r3_text.lower() or "concurrency" in r3_text.lower())
        checks.append(
            OracleCheck(
                check_id="ORACLE-REVALIDATE-R3",
                requirement_id="R3",
                name="Oracle Assertion: Inventory Concurrency Restored",
                passed=r3_ok,
                phase=phase,
                details="Asserts R3 enforces non-negative inventory via concurrency protection.",
                actual_value=r3_text,
                expected_value="Inventory must never become negative during concurrent dispensing, enforced with database row locks or optimistic concurrency.",
            )
        )

        # Check R4 repair
        r4_text = item_map.get("R4", "")
        r4_ok = "atomic" in r4_text.lower() and "rolls back" in r4_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-REVALIDATE-R4",
                requirement_id="R4",
                name="Oracle Assertion: Dispensing Atomicity Restored",
                passed=r4_ok,
                phase=phase,
                details="Asserts R4 enforces complete transaction rollback on failure.",
                actual_value=r4_text,
                expected_value="Dispensing must be atomic: inventory updates and dispensing records must execute within a database transaction that fully rolls back on any step failure.",
            )
        )

        # Check R5 repair
        r5_text = item_map.get("R5", "")
        r5_ok = "idempotency" in r5_text.lower() and "never charge a patient twice" in r5_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-REVALIDATE-R5",
                requirement_id="R5",
                name="Oracle Assertion: Payment Idempotency Restored",
                passed=r5_ok,
                phase=phase,
                details="Asserts R5 prevents duplicate payment captures upon retry.",
                actual_value=r5_text,
                expected_value="Repeated payment requests with the same idempotency key must verify existing payment status and never charge a patient twice.",
            )
        )

        # Check R6 unchanged
        r6_text = item_map.get("R6", "")
        r6_ok = "expired medication must never be dispensed" in r6_text.lower()
        checks.append(
            OracleCheck(
                check_id="ORACLE-REVALIDATE-R6",
                requirement_id="R6",
                name="Oracle Assertion: Negative Control R6 Still Intact",
                passed=r6_ok,
                phase=phase,
                details="Asserts R6 remains unaltered and compliant through the repair cycle.",
                actual_value=r6_text,
                expected_value="Expired medication must never be dispensed.",
            )
        )

    return checks


# -----------------------------------------------------------------------------
# 5. Core Demo Operations: Validation, Repair, Revalidation
# -----------------------------------------------------------------------------

def validate_demo_handoff() -> DemoValidationResponse:
    """Run real validation checks against the broken handoff fixture and compare with oracle."""
    canonical_reqs = _build_synthetic_requirements()
    payload = _build_payload(DEMO_BROKEN_HANDOFF)
    req_ids = [r.source_id for r in DEMO_REQUIREMENTS]

    # Execute actual validator functions
    raw_issues = []
    raw_issues.extend(check_missing_requirements(canonical_reqs, req_ids, payload))
    raw_issues.extend(check_weakened_constraints(canonical_reqs, payload))
    raw_issues.extend(check_deterministic_contradictions(canonical_reqs, payload))
    raw_issues.extend(check_semantic_drift(canonical_reqs, payload))
    raw_issues.extend(check_per_requirement_semantics(canonical_reqs, payload))

    # Map detected issues by requirement ID
    detected_by_req: Dict[str, Any] = {}
    for iss in raw_issues:
        r_id = iss.requirement_id
        if r_id and r_id not in detected_by_req:
            detected_by_req[r_id] = iss

    # Run independent Oracle checks
    oracle_checks = run_oracle_checks(DEMO_BROKEN_HANDOFF, phase="broken_inspection")

    # Match each seeded defect to validator findings
    discrepancies: List[DemoDiscrepancy] = []
    missed_defects: List[str] = []

    seeded_defects = [
        ("R1", "D1", "Authorization & Privacy", "Patients may access only their own medical records.", "Patients may access any patient's records if they know the record ID."),
        ("R2", "D2", "Authentication Security", "Passwords must be securely hashed and never stored in plaintext.", "Passwords are stored in plaintext."),
        ("R3", "D3", "Inventory Invariants", "Inventory must never become negative during concurrent dispensing.", "Inventory is decremented without concurrency protection."),
        ("R4", "D4", "Transaction Atomicity", "Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.", "Inventory changes remain even if writing the dispensing record fails."),
        ("R5", "D5", "Billing Idempotency", "Repeated payment requests with the same idempotency key must not charge a patient twice.", "Payment retries can create duplicate charges."),
    ]

    for req_id, defect_id, category, orig_text, broken_text in seeded_defects:
        raw_issue = detected_by_req.get(req_id)
        validator_detected = raw_issue is not None
        oracle_detected = True

        if not validator_detected:
            missed_defects.append(defect_id)

        explanation = (
            raw_issue.description
            if raw_issue
            else f"VALIDATOR MISSED SEEDED DEFECT: Specification permits '{broken_text}' directly violating canonical requirement."
        )
        severity = (
            raw_issue.severity.value
            if hasattr(raw_issue.severity, "value")
            else str(raw_issue.severity)
        ) if raw_issue else "critical"
        evidence = raw_issue.evidence if raw_issue else [f"Downstream text: '{broken_text}'"]

        discrepancies.append(
            DemoDiscrepancy(
                requirement_id=req_id,
                original_requirement=orig_text,
                received_statement=broken_text,
                category=category,
                severity=severity,
                explanation=explanation,
                evidence=evidence,
                validator_detected=validator_detected,
                oracle_detected=oracle_detected,
                is_missed_by_validator=not validator_detected,
            )
        )

    preserved_item = next(item for item in DEMO_BROKEN_HANDOFF if item.requirement_id == "R6")

    return DemoValidationResponse(
        validator_detected_count=len([d for d in discrepancies if d.validator_detected]),
        oracle_seeded_defect_count=5,
        preserved_count=1,
        discrepancies=discrepancies,
        preserved_requirement=preserved_item,
        oracle_checks=oracle_checks,
        all_seeded_defects_detected=(len(missed_defects) == 0),
        missed_defects=missed_defects,
    )


def revalidate_demo_handoff() -> DemoRevalidationResponse:
    """Run real validation checks and oracle assertions against the repaired handoff fixture."""
    canonical_reqs = _build_synthetic_requirements()

    # Build repaired handoff items
    repaired_items: List[DemoHandoffItem] = []
    repair_map = {rep.requirement_id: rep.repaired_text for rep in DEMO_REPAIRS}

    for item in DEMO_BROKEN_HANDOFF:
        if item.requirement_id in repair_map:
            repaired_items.append(
                DemoHandoffItem(
                    id=item.id,
                    requirement_id=item.requirement_id,
                    defect_id=item.defect_id,
                    status="repaired",
                    received_text=repair_map[item.requirement_id],
                    original_text=item.original_text,
                )
            )
        else:
            repaired_items.append(item)

    payload = _build_payload(repaired_items)
    req_ids = [r.source_id for r in DEMO_REQUIREMENTS]

    # Re-run real validator
    raw_issues = []
    raw_issues.extend(check_missing_requirements(canonical_reqs, req_ids, payload))
    raw_issues.extend(check_weakened_constraints(canonical_reqs, payload))
    raw_issues.extend(check_deterministic_contradictions(canonical_reqs, payload))
    raw_issues.extend(check_semantic_drift(canonical_reqs, payload))
    raw_issues.extend(check_per_requirement_semantics(canonical_reqs, payload))

    remaining_discrepancies = [
        DemoDiscrepancy(
            requirement_id=iss.requirement_id or "UNKNOWN",
            original_requirement=iss.original_value or "",
            received_statement=iss.observed_value or "",
            category=iss.issue_type.value if hasattr(iss.issue_type, "value") else str(iss.issue_type),
            severity=iss.severity.value if hasattr(iss.severity, "value") else str(iss.severity),
            explanation=iss.description,
            evidence=iss.evidence,
            validator_detected=True,
            oracle_detected=False,
            is_missed_by_validator=False,
        )
        for iss in raw_issues
    ]

    # Run Oracle checks on repaired handoff
    oracle_checks = run_oracle_checks(repaired_items, phase="revalidation")
    oracle_all_passed = all(c.passed for c in oracle_checks)

    validator_clean = len(raw_issues) == 0
    all_clear = validator_clean and oracle_all_passed

    return DemoRevalidationResponse(
        validator_issues_count=len(raw_issues),
        oracle_passed=oracle_all_passed,
        resolved_count=5 if all_clear else (5 - len(raw_issues)),
        unresolved_count=len(raw_issues),
        all_clear=all_clear,
        remaining_issues=remaining_discrepancies,
        oracle_checks=oracle_checks,
        disclaimer="Note: A corrected specification does not prove the generated code implements it. Downstream implementation requires automated testing and verification.",
    )
