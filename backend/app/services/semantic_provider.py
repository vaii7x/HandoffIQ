"""Semantic validation provider interface and default local implementation."""

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from app.models.handoff import Handoff, ValidationIssue
from app.models.requirement import Requirement


class SemanticValidationProvider(ABC):
    """Abstract interface for AI-powered semantic validation of context handoffs.

    The AI developer implements this interface using Gemini or LLM agents to detect
    subtle semantic drift, weakened constraints, and implementation gaps that cannot
    be reliably detected through deterministic schema or keyword checking.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier of the semantic provider implementation."""
        pass

    @abstractmethod
    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        """Analyze a handoff against canonical requirements and return identified semantic issues.

        Args:
            task_id: The UUID of the parent task.
            requirements: The canonical requirements registered for the task.
            handoff: The handoff payload, source/target agent, and requirement IDs being validated.

        Returns:
            List of detected ValidationIssue objects (e.g. semantic_drift, weakened_constraint).
        """
        pass


class NoOpSemanticValidationProvider(SemanticValidationProvider):
    """Default no-op provider returning no semantic issues.

    Active in local development and test environments where deterministic validation
    is evaluated without live AI infrastructure.
    """

    @property
    def provider_name(self) -> str:
        return "noop_semantic_provider"

    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        return []


_semantic_provider: SemanticValidationProvider = NoOpSemanticValidationProvider()


def get_semantic_validation_provider() -> SemanticValidationProvider:
    """Dependency provider returning the active semantic validation provider."""
    return _semantic_provider


def set_semantic_validation_provider(provider: SemanticValidationProvider) -> None:
    """Configure or inject a custom AI semantic validation provider."""
    global _semantic_provider
    _semantic_provider = provider
