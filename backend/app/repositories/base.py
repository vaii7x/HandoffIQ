"""Abstract repository interfaces defining data access contracts."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.models.agent_run import AgentRun
from app.models.artifact import CodeArtifact
from app.models.event import WorkflowEvent
from app.models.recovery import RecoveryAttempt
from app.models.requirement import Requirement
from app.models.task import Task
from app.models.test_result import TestResult


class TaskRepository(ABC):
    """Abstract interface for task, requirement, and event persistence."""

    @abstractmethod
    async def create_task(self, task: Task) -> Task:
        """Persist a newly registered task."""
        pass

    @abstractmethod
    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """Retrieve a task by its unique UUID."""
        pass

    @abstractmethod
    async def list_tasks(self) -> List[Task]:
        """List all tasks sorted by creation date descending."""
        pass

    @abstractmethod
    async def update_task(self, task: Task) -> Task:
        """Update an existing task's status, progress, or stage."""
        pass

    @abstractmethod
    async def get_next_requirement_id(self, task_id: UUID) -> str:
        """Allocate the next stable sequential requirement ID (e.g. R001, R002) for a task."""
        pass

    @abstractmethod
    async def add_requirements(self, task_id: UUID, requirements: List[Requirement]) -> List[Requirement]:
        """Store canonical requirements associated with a task."""
        pass

    @abstractmethod
    async def get_requirements(self, task_id: UUID) -> List[Requirement]:
        """Retrieve all requirements for a task in creation order."""
        pass

    @abstractmethod
    async def get_requirement(self, task_id: UUID, requirement_id: str) -> Optional[Requirement]:
        """Retrieve a specific requirement by its task-scoped ID."""
        pass

    @abstractmethod
    async def update_requirement(self, task_id: UUID, requirement: Requirement) -> Requirement:
        """Update an existing requirement (status, description, related files/tests)."""
        pass

    @abstractmethod
    async def add_event(self, event: WorkflowEvent) -> WorkflowEvent:
        """Record an immutable workflow audit event."""
        pass

    @abstractmethod
    async def get_events(self, task_id: UUID) -> List[WorkflowEvent]:
        """Retrieve all workflow events recorded for a task sorted chronologically."""
        pass

    @abstractmethod
    async def get_agent_runs(self, task_id: UUID) -> List[AgentRun]:
        """Retrieve agent runs associated with a task."""
        pass

    @abstractmethod
    async def add_agent_run(self, run: AgentRun) -> AgentRun:
        """Record an agent execution phase."""
        pass

    @abstractmethod
    async def update_agent_run(self, run: AgentRun) -> AgentRun:
        """Update an agent execution phase (e.g. status, completed_at, summary, error)."""
        pass

    @abstractmethod
    async def add_artifact(self, task_id: UUID, artifact: CodeArtifact) -> CodeArtifact:
        """Store a generated or patched code artifact."""
        pass

    @abstractmethod
    async def get_artifacts(self, task_id: UUID) -> List[CodeArtifact]:
        """Retrieve all code artifacts generated for a task."""
        pass

    @abstractmethod
    async def add_test_result(self, task_id: UUID, test_result: TestResult) -> TestResult:
        """Record the outcome of a test execution."""
        pass

    @abstractmethod
    async def get_test_results(self, task_id: UUID) -> List[TestResult]:
        """Retrieve all test execution outcomes recorded for a task."""
        pass

    @abstractmethod
    async def add_recovery_attempt(self, task_id: UUID, recovery: RecoveryAttempt) -> RecoveryAttempt:
        """Record a recovery/repair attempt."""
        pass

    @abstractmethod
    async def get_recovery_attempts(self, task_id: UUID) -> List[RecoveryAttempt]:
        """Retrieve all recovery attempts for a task."""
        pass

    @abstractmethod
    async def update_recovery_attempt(self, recovery: RecoveryAttempt) -> RecoveryAttempt:
        """Update a recovery attempt status, repair summary, or regressions."""
        pass
