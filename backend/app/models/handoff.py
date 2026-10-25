"""Handoff and ValidationIssue domain schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, field_validator
from app.models.common import HandoffIQBaseModel, ensure_utc, utcnow


class IssueType(str, Enum):
    """Categorization of discrepancies found during handoff validation."""

    omission = "omission"
    semantic_drift = "semantic_drift"
    weakened_constraint = "weakened_constraint"
    contradiction = "contradiction"
    invented_requirement = "invented_requirement"
    suspicious_instruction = "suspicious_instruction"
    schema_error = "schema_error"
    implementation_gap = "implementation_gap"
    test_failure = "test_failure"


class IssueSeverity(str, Enum):
    """Impact severity of a validation issue."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RepairStatus(str, Enum):
    """Current state of resolution for a validation issue."""

    not_needed = "not_needed"
    pending = "pending"
    repaired = "repaired"
    unresolved = "unresolved"
    rejected = "rejected"


class ValidationIssue(HandoffIQBaseModel):
    """Validation issue identified during a handoff evaluation."""

    id: str = Field(
        default_factory=lambda: f"ISSUE-{uuid4().hex[:8].upper()}",
        description="Unique identifier for the validation issue"
    )
    requirement_id: Optional[str] = Field(
        default=None,
        description="ID of the related requirement, if applicable"
    )
    issue_type: IssueType = Field(
        ...,
        description="Classification of the discrepancy"
    )
    severity: IssueSeverity = Field(
        ...,
        description="Severity level of the issue"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Detailed description of the detected discrepancy"
    )
    original_value: Optional[str] = Field(
        default=None,
        description="Original expected requirement or constraint value"
    )
    observed_value: Optional[str] = Field(
        default=None,
        description="Observed value produced in the handoff"
    )
    repair_status: RepairStatus = Field(
        default=RepairStatus.pending,
        description="Current repair status of the issue"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Snippets, logs, or references substantiating the issue"
    )


class HandoffStatus(str, Enum):
    """Validation status for context passed between agents."""

    pending = "pending"
    validated = "validated"
    repaired = "repaired"
    blocked = "blocked"
    awaiting_review = "awaiting_review"
    review_required = "review_required"
    failed = "failed"


class Handoff(HandoffIQBaseModel):
    """Context and state transferred from one agent to the next."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the handoff"
    )
    task_id: UUID = Field(
        ...,
        description="Associated task identifier"
    )
    source_agent: str = Field(
        ...,
        min_length=1,
        description="Identifier or role of the agent handing off context"
    )
    target_agent: str = Field(
        ...,
        min_length=1,
        description="Identifier or role of the receiving agent"
    )
    status: HandoffStatus = Field(
        default=HandoffStatus.pending,
        description="Integrity and validation status of this handoff"
    )
    requirement_ids: List[str] = Field(
        default_factory=list,
        description="Identifiers of requirements carried in this handoff"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured context and state payload"
    )
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="Validation issues detected during handoff analysis"
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="Timestamp of handoff creation in UTC"
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_utc_datetime(cls, value: datetime) -> datetime:
        """Ensure created_at is UTC timezone-aware."""
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value
