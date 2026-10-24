"""Mutation Lab orchestration service managing experiment lifecycles."""

from typing import List, Optional
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import (
    ExperimentNotFoundError,
    InvalidMutationTypeError,
    TaskNotFoundError,
)
from app.models.experiment import Experiment, ExperimentStatus, MutationType
from app.repositories.base import TaskRepository
from app.repositories.experiment_repository import (
    ExperimentRepository,
    get_experiment_repository,
)
from app.repositories.in_memory import get_task_repository
from app.services.handoff_service import get_handoff_service
from app.services.mutation_lab.evaluator import MutationEvaluator
from app.services.mutation_lab.manager import ExperimentExecutionManager
from app.services.mutation_lab.mutations import SUPPORTED_MUTATION_TYPES


class MutationLabService:
    """Service for managing mutation experiment configurations and executions."""

    def __init__(
        self,
        task_repository: TaskRepository,
        experiment_repository: ExperimentRepository,
        execution_manager: ExperimentExecutionManager,
    ) -> None:
        self.task_repo = task_repository
        self.experiment_repo = experiment_repository
        self.manager = execution_manager

    async def create_experiment(
        self,
        task_id: UUID,
        mutation_types: List[str],
        runs: int = 1,
    ) -> Experiment:
        """Register and queue an evaluation experiment comparing baseline and HandoffIQ.

        Args:
            task_id: UUID of benchmark task.
            mutation_types: List of mutation types to evaluate.
            runs: Number of experiment iterations.

        Returns:
            The queued Experiment model.
        """
        # 1. Validate task existence
        task = await self.task_repo.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with id '{task_id}' was not found.")

        # 2. Validate requested mutation types
        invalid_types = [m for m in mutation_types if m not in SUPPORTED_MUTATION_TYPES]
        if invalid_types:
            raise InvalidMutationTypeError(
                invalid_types=invalid_types,
                supported_types=SUPPORTED_MUTATION_TYPES,
            )

        if not mutation_types:
            raise InvalidMutationTypeError(
                invalid_types=["empty_list"],
                supported_types=SUPPORTED_MUTATION_TYPES,
            )

        settings = get_settings()

        # 3. Create initial queued experiment
        experiment = Experiment(
            task_id=task_id,
            name=f"Mutation Lab - {', '.join(mutation_types)}",
            description=f"Evaluation comparing baseline against HandoffIQ under mutations: {mutation_types}",
            status=ExperimentStatus.queued,
            mutation_types=mutation_types,
            runs=runs,
            is_simulated=settings.MOCK_MODE,
            configuration={
                "task_id": str(task_id),
                "mutation_types": mutation_types,
                "runs": runs,
                "is_simulated": settings.MOCK_MODE,
            },
            metrics={},
        )

        created = await self.experiment_repo.create_experiment(experiment)

        # 4. Trigger managed background execution
        await self.manager.queue_and_start_experiment(created.id)

        return created

    async def get_experiment(self, experiment_id: UUID) -> Experiment:
        """Retrieve an experiment by its unique UUID."""
        experiment = await self.experiment_repo.get_experiment(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError(experiment_id)
        return experiment

    async def list_experiments(self) -> List[Experiment]:
        """List all experiments."""
        return await self.experiment_repo.list_experiments()


_mutation_evaluator: Optional[MutationEvaluator] = None
_experiment_manager: Optional[ExperimentExecutionManager] = None
_mutation_lab_service: Optional[MutationLabService] = None


def get_mutation_evaluator() -> MutationEvaluator:
    global _mutation_evaluator
    if _mutation_evaluator is None:
        _mutation_evaluator = MutationEvaluator(handoff_service=get_handoff_service())
    return _mutation_evaluator


def get_experiment_manager() -> ExperimentExecutionManager:
    global _experiment_manager
    if _experiment_manager is None:
        _experiment_manager = ExperimentExecutionManager(
            experiment_repo=get_experiment_repository(),
            task_repo=get_task_repository(),
            evaluator=get_mutation_evaluator(),
        )
    return _experiment_manager


def get_mutation_lab_service() -> MutationLabService:
    global _mutation_lab_service
    if _mutation_lab_service is None:
        _mutation_lab_service = MutationLabService(
            task_repository=get_task_repository(),
            experiment_repository=get_experiment_repository(),
            execution_manager=get_experiment_manager(),
        )
    return _mutation_lab_service
