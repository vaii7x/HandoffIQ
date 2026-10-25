"""CodeArtifact domain schema."""

from typing import List
from uuid import UUID, uuid4
from pydantic import Field
from app.models.common import HandoffIQBaseModel


class CodeArtifact(HandoffIQBaseModel):
    """Generated or modified code file produced during workflow execution."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the code artifact"
    )
    task_id: UUID = Field(
        ...,
        description="Associated task identifier"
    )
    path: str = Field(
        ...,
        min_length=1,
        description="File path relative to the target repository/project root"
    )
    language: str = Field(
        ...,
        min_length=1,
        description="Programming language (e.g. python, typescript, html)"
    )
    content: str = Field(
        ...,
        description="Source code or text content"
    )
    requirement_ids: List[str] = Field(
        default_factory=list,
        description="Requirement identifiers linked to this artifact"
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Artifact revision version number (1-based)"
    )
