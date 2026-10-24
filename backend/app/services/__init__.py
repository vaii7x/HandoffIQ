"""Service layer interfaces and implementations for HandoffIQ."""

from app.services.extractor import (
    MockRequirementExtractor,
    RequirementCandidate,
    RequirementExtractor,
    get_requirement_extractor,
)
from app.services.handoff_service import HandoffValidationService, get_handoff_service
from app.services.semantic_provider import (
    NoOpSemanticValidationProvider,
    SemanticValidationProvider,
    get_semantic_validation_provider,
    set_semantic_validation_provider,
)
from app.services.task_service import TaskService, get_task_service

__all__ = [
    "RequirementCandidate",
    "RequirementExtractor",
    "MockRequirementExtractor",
    "get_requirement_extractor",
    "TaskService",
    "get_task_service",
    "HandoffValidationService",
    "get_handoff_service",
    "SemanticValidationProvider",
    "NoOpSemanticValidationProvider",
    "get_semantic_validation_provider",
    "set_semantic_validation_provider",
]
