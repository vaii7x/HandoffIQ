"""Experiment domain schema for evaluating multi-agent orchestration configurations and mutation lab."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, field_validator
from app.models.common import HandoffIQBaseModel, ensure_utc, utcnow


class ExperimentStatus(str, Enum):
    """Execution status for an evaluation experiment."""

    draft = "draft"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    archived = "archived"


class MutationType(str, Enum):
    """Supported controlled mutation types for context handoffs."""

    missing_requirement = "missing_requirement"
    weakened_constraint = "weakened_constraint"
    semantic_drift = "semantic_drift"
    contradiction = "contradiction"
    invented_requirement = "invented_requirement"
    suspicious_instruction = "suspicious_instruction"


class MutationRecord(HandoffIQBaseModel):
    """Record of a single controlled mutation applied during an experiment."""

    mutation_type: MutationType = Field(
        ...,
        description="Classification of mutation: missing_requirement, weakened_constraint, semantic_drift, contradiction, invented_requirement, suspicious_instruction",
    )
    original_requirement: Optional[str] = Field(
        default=None,
        description="Original canonical requirement identifier or wording",
    )
    mutated_value: Any = Field(
        ...,
        description="Altered value, injected directive, or omitted requirement",
    )
    expected_detection_outcome: Dict[str, Any] = Field(
        ...,
        description="Expected detection outcome (e.g. should_detect, expected_issue_type, repairable)",
    )


class RepairOutcomes(HandoffIQBaseModel):
    """Counts of repair attempts and resolutions."""

    attempted: int = Field(default=0, ge=0, description="Total repair attempts initiated")
    successful: int = Field(default=0, ge=0, description="Successfully repaired issues")
    unresolved: int = Field(default=0, ge=0, description="Unresolved or unrepairable discrepancies")


class TokenUsageMetric(HandoffIQBaseModel):
    """Token consumption measurement or explicit unavailable status."""

    status: str = Field(
        default="unavailable",
        description="Status of token measurement: 'available' or 'unavailable'",
    )
    prompt_tokens: Optional[int] = Field(default=None, description="Prompt tokens consumed")
    completion_tokens: Optional[int] = Field(default=None, description="Completion tokens consumed")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens consumed or None if unavailable")


class EvaluationMetrics(HandoffIQBaseModel):
    """Detailed recorded metrics for a workflow evaluation run."""

    requirement_preservation_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Proportion of canonical requirements preserved/restored (0.0 to 1.0)",
    )
    preserved_requirements_count: int = Field(default=0, ge=0, description="Number of preserved requirements")
    total_requirements_count: int = Field(default=0, ge=0, description="Total canonical requirements evaluated")
    task_success: bool = Field(default=False, description="Whether the workflow run completed successfully without blocking failures")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Actual measured wall-clock execution time in milliseconds")
    token_usage: TokenUsageMetric = Field(default_factory=TokenUsageMetric, description="Token usage metrics or explicit unavailable indicator")
    errors_detected: int = Field(default=0, ge=0, description="Count of validation discrepancies detected")
    error_detection_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of detected mutation errors to expected mutations")
    false_positives: int = Field(default=0, ge=0, description="Count of false-positive issues detected")
    repair_outcomes: RepairOutcomes = Field(default_factory=RepairOutcomes, description="Breakdown of repair attempts")


class Experiment(HandoffIQBaseModel):
    """Experiment comparing agent configurations, prompt revisions, or handoff heuristics."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the experiment",
    )
    task_id: Optional[UUID] = Field(
        default=None,
        description="ID of the task used as benchmark baseline",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the evaluation experiment",
    )
    description: Optional[str] = Field(
        default=None,
        description="Hypothesis or details of what is being tested",
    )
    status: ExperimentStatus = Field(
        default=ExperimentStatus.draft,
        description="Current state of the experiment",
    )
    mutation_types: List[str] = Field(
        default_factory=list,
        description="List of mutation types applied in this experiment",
    )
    runs: int = Field(
        default=1,
        ge=1,
        description="Number of evaluation runs executed",
    )
    is_simulated: bool = Field(
        default=True,
        description="Explicit flag indicating whether results were simulated in mock mode",
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters, mutation fixtures, and benchmark configuration",
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recorded evaluation metrics comparing baseline and HandoffIQ",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="UTC creation timestamp",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC completion timestamp",
    )

    @field_validator("created_at", "completed_at", mode="before")
    @classmethod
    def validate_utc_datetime(cls, value: Optional[datetime]) -> Optional[datetime]:
        """Ensure timestamp is UTC timezone-aware."""
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value
