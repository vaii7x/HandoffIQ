"""Requirement domain schema."""

from enum import Enum
import re
from typing import Any, List, Optional
from uuid import UUID
from pydantic import Field, model_validator
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
    source_id: Optional[str] = Field(
        default=None,
        description="Original source identifier such as R1, R2, R12"
    )
    related_files: List[str] = Field(
        default_factory=list,
        description="List of file paths related to or implementing this requirement"
    )
    related_test_ids: List[str] = Field(
        default_factory=list,
        description="List of test identifiers verifying this requirement"
    )

    @model_validator(mode="before")
    @classmethod
    def extract_source_id(cls, data: Any) -> Any:
        """Derive or normalize source_id if present in data, description, or original_text."""
        if isinstance(data, dict):
            source_id = data.get("source_id")
            if not source_id:
                # 1. Extract from description tag [Source: R1]
                desc = data.get("description", "")
                m_desc = re.search(r"\[Source:\s*([^\]]+)\]", desc, re.IGNORECASE)
                if m_desc:
                    data["source_id"] = m_desc.group(1).strip()
                else:
                    # 2. Extract from original_text prefix e.g. "R1. Students..." or "[R1] Students..."
                    ot = data.get("original_text", "")
                    m_ot = re.match(
                        r"^\s*\[?((?:R|REQ-?|REQUIREMENT\s*)?\d+[a-z]?)\]?[\.\:\-\)]\s*",
                        ot,
                        re.IGNORECASE,
                    )
                    if m_ot:
                        raw_sid = m_ot.group(1).strip()
                        data["source_id"] = re.sub(r"\s+", "", raw_sid.upper())
        return data
