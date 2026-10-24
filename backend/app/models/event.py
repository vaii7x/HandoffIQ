"""WorkflowEvent domain schema."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4
from pydantic import Field, field_validator
from app.models.common import HandoffIQBaseModel, ensure_utc, utcnow


class WorkflowEvent(HandoffIQBaseModel):
    """Audit log entry capturing state transitions, handoff checks, and workflow events."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the event"
    )
    task_id: UUID = Field(
        ...,
        description="Associated task identifier"
    )
    event_type: str = Field(
        ...,
        min_length=1,
        description="Type of event (e.g. stage_transition, handoff_validated, test_executed)"
    )
    stage: str = Field(
        ...,
        min_length=1,
        description="Workflow stage where the event occurred"
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable event message"
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when the event occurred"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata relevant to the event"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_utc_datetime(cls, value: datetime) -> datetime:
        """Ensure timestamp is UTC timezone-aware."""
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value
