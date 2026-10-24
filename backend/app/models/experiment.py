"""Experiment domain schema for evaluating multi-agent orchestration configurations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import Field, field_validator
from app.models.common import HandoffIQBaseModel, ensure_utc, utcnow


class ExperimentStatus(str, Enum):
    """Execution status for an evaluation experiment."""

    draft = "draft"
    running = "running"
    completed = "completed"
    archived = "archived"


class Experiment(HandoffIQBaseModel):
    """Experiment comparing agent configurations, prompt revisions, or handoff heuristics."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the experiment"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the evaluation experiment"
    )
    description: Optional[str] = Field(
        default=None,
        description="Hypothesis or details of what is being tested"
    )
    status: ExperimentStatus = Field(
        default=ExperimentStatus.draft,
        description="Current state of the experiment"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters, prompt versions, or model configs being benchmarked"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recorded metrics such as fidelity score, drift rate, test pass rate"
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="UTC creation timestamp"
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_utc_datetime(cls, value: datetime) -> datetime:
        """Ensure timestamp is UTC timezone-aware."""
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value
