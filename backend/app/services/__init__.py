"""Service layer interfaces and implementations for HandoffIQ."""

from app.services.extractor import (
    MockRequirementExtractor,
    RequirementCandidate,
    RequirementExtractor,
    get_requirement_extractor,
)
from app.services.task_service import TaskService, get_task_service

__all__ = [
    "RequirementCandidate",
    "RequirementExtractor",
    "MockRequirementExtractor",
    "get_requirement_extractor",
    "TaskService",
    "get_task_service",
]
