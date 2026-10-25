"""Pydantic models for HandoffIQ Presentation-Ready Demo Mode."""

from typing import List, Optional
from pydantic import BaseModel, Field


class DemoRequirement(BaseModel):
    id: str
    source_id: str
    title: str
    description: str
    category: str
    authoritative: bool = True


class DemoHandoffItem(BaseModel):
    id: str
    requirement_id: str
    received_text: str
    status: str = Field(description="'broken' or 'preserved'")
    defect_id: Optional[str] = None
    original_text: str


class DemoDiscrepancy(BaseModel):
    requirement_id: str
    original_requirement: str
    received_statement: str
    category: str
    severity: str
    explanation: str
    evidence: List[str]
    validator_detected: bool
    oracle_detected: bool
    is_missed_by_validator: bool = False


class DemoRepairItem(BaseModel):
    id: str
    requirement_id: str
    original_text: str
    broken_text: str
    repaired_text: str
    repair_reason: str
    status: str = "repaired"
    diff_before: str
    diff_after: str


class OracleCheck(BaseModel):
    check_id: str
    requirement_id: str
    name: str
    passed: bool
    phase: str
    details: str
    actual_value: str
    expected_value: str


class DemoValidationResponse(BaseModel):
    validator_detected_count: int
    oracle_seeded_defect_count: int
    preserved_count: int
    discrepancies: List[DemoDiscrepancy]
    preserved_requirement: DemoHandoffItem
    oracle_checks: List[OracleCheck]
    all_seeded_defects_detected: bool
    missed_defects: List[str]


class DemoRevalidationResponse(BaseModel):
    validator_issues_count: int
    oracle_passed: bool
    resolved_count: int
    unresolved_count: int
    all_clear: bool
    remaining_issues: List[DemoDiscrepancy]
    oracle_checks: List[OracleCheck]
    disclaimer: str
