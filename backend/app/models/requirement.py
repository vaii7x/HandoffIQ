"""Requirement domain schema."""

from enum import Enum
from typing import List
from uuid import UUID
from pydantic import Field
from app.models.common import HandoffIQBaseModel


class RequirementPriority(str, Enum):
    """Priority level assigned to a requirement."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RequirementStatus(str, Enum):
    """Lifecycle and integrity status of a requirement across agent handoffs."""

    registered = "registered"
    preserved = "preserved"
    altered = "altered"
    missing = "missing"
    conflicting = "conflicting"
    implemented = "implemented"
    tested = "tested"
    verified = "verified"
    failed = "failed"
    awaiting_review = "awaiting_review"


class Requirement(HandoffIQBaseModel):
    """Extracted requirement tracking fidelity across multi-agent workflows."""

    id: str = Field(
        ...,
        pattern=r"^R\d+$",
        description="Requirement identifier such as R001",
        examples=["R001", "R002", "R101"],
    )
    task_id: UUID = Field(
        ...,
        description="Associated task identifier"
    )
    original_text: str = Field(
        ...,
        min_length=1,
        frozen=True,
        description="Immutable original text of the requirement"
    )
    priority: RequirementPriority = Field(
        default=RequirementPriority.medium,
        description="Priority of the requirement"
    )
    status: RequirementStatus = Field(
        default=RequirementStatus.registered,
        description="Current verification and fidelity status"
    )
    description: str = Field(
        default="",
        description="Detailed description or context of the requirement"
    )
    related_files: List[str] = Field(
        default_factory=list,
        description="List of file paths related to or implementing this requirement"
    )
    related_test_ids: List[str] = Field(
        default_factory=list,
        description="List of test identifiers verifying this requirement"
    )
