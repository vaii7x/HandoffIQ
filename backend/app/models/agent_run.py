"""AgentRun domain schema."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import Field, field_validator
from app.models.common import HandoffIQBaseModel, ensure_utc


class AgentType(str, Enum):
    """Types of agents participating in the multi-agent pipeline."""

    researcher = "researcher"
    coder = "coder"
    tester = "tester"
    reviewer = "reviewer"


class AgentRunStatus(str, Enum):
    """Status of an individual agent execution step."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    awaiting_review = "awaiting_review"


class AgentRun(HandoffIQBaseModel):
    """Record of an individual agent's execution phase."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the agent run"
    )
    task_id: UUID = Field(
        ...,
        description="ID of the parent task"
    )
    agent_type: AgentType = Field(
        ...,
        description="Role of the agent executing this phase"
    )
    status: AgentRunStatus = Field(
        default=AgentRunStatus.queued,
        description="Execution status of this agent run"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when agent run started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when agent run finished"
    )
    summary: str = Field(
        default="",
        description="Summary of work or conclusions produced by this agent run"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if this run failed"
    )

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def validate_utc_datetime(cls, value: Optional[datetime]) -> Optional[datetime]:
        """Ensure timestamps are UTC timezone-aware."""
        if isinstance(value, datetime):
            return ensure_utc(value)
        return value
