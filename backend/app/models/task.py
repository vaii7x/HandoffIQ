"""Task domain schema."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import Field, field_validator
from app.models.common import HandoffIQBaseModel, ensure_utc, utcnow


class TaskStatus(str, Enum):
    """Execution status for a user task."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    awaiting_review = "awaiting_review"
    cancelled = "cancelled"


class Task(HandoffIQBaseModel):
    """Task entity representing a user's unit of work in HandoffIQ."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the task"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable title for the task"
    )
    original_request: str = Field(
        ...,
        min_length=1,
        description="The original, unmodified user request prompt"
    )
    status: TaskStatus = Field(
        default=TaskStatus.queued,
        description="Current lifecycle status of the task"
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="Timestamp when the task was submitted in UTC"
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        description="Timestamp of last task update in UTC"
    )
    current_stage: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Current workflow stage description"
    )
    progress: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Execution progress percentage (0-100)"
    )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_utc_datetime(cls, value: datetime) -> datetime:
        """Enforce UTC timezone awareness for timestamps."""
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value
