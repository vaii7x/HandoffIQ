"""Injectable AI repair service interfaces and deterministic mock implementations."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.models.artifact import CodeArtifact
from app.models.recovery import RecoveryAttempt
from app.models.requirement import Requirement
from app.models.test_result import TestResult


class RepairInput(BaseModel):
    """Context delivered to the repair service to synthesize a correction patch."""

    task_id: UUID
    workspace_path: str
    failed_tests: List[TestResult]
    requirements: List[Requirement]
    attempt_number: int
    previous_attempts: List[RecoveryAttempt] = Field(default_factory=list)


class RepairOutput(BaseModel):
    """Proposed correction from the repair service."""

    repair_summary: str = Field(description="Explanation of the fix")
    artifacts: List[CodeArtifact] = Field(
        default_factory=list, description="Code artifacts/patches to apply to the workspace"
    )
    should_retry: bool = Field(
        default=True, description="Whether another test execution should be attempted"
    )


class AIRepairService(ABC):
    """Injectable interface for AI-driven code repair."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def generate_repair(self, input_data: RepairInput) -> RepairOutput:
        """Generate code patches to resolve test failures."""
        pass


class MockAIRepairService(AIRepairService):
    """Deterministic mock repair service for unit tests and local development."""

    def __init__(
        self,
        auto_succeed: bool = True,
        cause_regression: bool = False,
        fixed_artifacts: Optional[List[CodeArtifact]] = None,
    ) -> None:
        self.auto_succeed = auto_succeed
        self.cause_regression = cause_regression
        self.fixed_artifacts = fixed_artifacts

    @property
    def name(self) -> str:
        return "mock_ai_repair"

    async def generate_repair(self, input_data: RepairInput) -> RepairOutput:
        req_ids = [r.id for r in input_data.requirements]

        if self.fixed_artifacts is not None:
            return RepairOutput(
                repair_summary="Applied configured mock patch artifacts.",
                artifacts=self.fixed_artifacts,
                should_retry=True,
            )

        # Default mock repair: generates a patched file
        target_path = "src/repaired_feature.js"
        patch = CodeArtifact(
            task_id=input_data.task_id,
            path=target_path,
            language="javascript",
            content=f"// Automated repair for {', '.join(req_ids)}\nexport const status = 'repaired';\n",
            requirement_ids=req_ids,
            version=input_data.attempt_number,
        )

        return RepairOutput(
            repair_summary=f"Repaired {len(input_data.failed_tests)} test failures by updating {target_path}.",
            artifacts=[patch],
            should_retry=True,
        )


# Global repair service injection registry
_repair_service_instance: Optional[AIRepairService] = None


def get_repair_service() -> AIRepairService:
    """Retrieve the registered AIRepairService."""
    global _repair_service_instance
    if _repair_service_instance is None:
        _repair_service_instance = MockAIRepairService()
    return _repair_service_instance


def set_repair_service(service: AIRepairService) -> None:
    """Register an injected AI repair service implementation."""
    global _repair_service_instance
    _repair_service_instance = service
