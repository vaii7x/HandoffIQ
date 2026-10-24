"""Recovery domain schema."""

from enum import Enum
from typing import List
from uuid import UUID, uuid4
from pydantic import Field
from app.models.common import HandoffIQBaseModel


class RecoveryStatus(str, Enum):
    """Lifecycle status of an automated recovery/repair attempt."""

    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class RecoveryAttempt(HandoffIQBaseModel):
    """Attempted self-correction or repair loop triggered after validation or test failures."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the recovery attempt"
    )
    task_id: UUID = Field(
        ...,
        description="Associated task identifier"
    )
    requirement_ids: List[str] = Field(
        default_factory=list,
        description="Identifiers of requirements being addressed in this recovery"
    )
    failure_summary: str = Field(
        ...,
        min_length=1,
        description="Summary of the failure causing this recovery attempt"
    )
    repair_summary: str = Field(
        default="",
        description="Summary of changes applied or proposed during the repair attempt"
    )
    status: RecoveryStatus = Field(
        default=RecoveryStatus.pending,
        description="Current status of the recovery attempt"
    )
    attempt_number: int = Field(
        default=1,
        ge=1,
        description="Sequential attempt counter (1-based)"
    )
    test_result_ids: List[str] = Field(
        default_factory=list,
        description="Test result IDs associated with this recovery phase"
    )
