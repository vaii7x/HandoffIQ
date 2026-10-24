"""Managed background execution coordinator for evaluation experiments."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, Optional, Set
from uuid import UUID

from app.core.errors import ExperimentNotFoundError, TaskNotFoundError
from app.models.experiment import ExperimentStatus
from app.repositories.base import TaskRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.services.mutation_lab.evaluator import MutationEvaluator

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExperimentExecutionManager:
    """Coordinates managed background execution and concurrency control for experiments."""

    def __init__(
        self,
        experiment_repo: ExperimentRepository,
        task_repo: TaskRepository,
        evaluator: MutationEvaluator,
    ) -> None:
        self.experiment_repo = experiment_repo
        self.task_repo = task_repo
        self.evaluator = evaluator
        self._running_experiments: Set[UUID] = set()
        self._active_jobs: Dict[UUID, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def queue_and_start_experiment(self, experiment_id: UUID) -> None:
        """Launch managed background execution for an experiment."""
        async with self._lock:
            self._running_experiments.add(experiment_id)

        job = asyncio.create_task(self._managed_run_wrapper(experiment_id))
        self._active_jobs[experiment_id] = job

    async def _managed_run_wrapper(self, experiment_id: UUID) -> None:
        """Run wrapper updating experiment states from running to completed or failed."""
        try:
            experiment = await self.experiment_repo.get_experiment(experiment_id)
            if not experiment:
                raise ExperimentNotFoundError(experiment_id)

            # Transition to running
            experiment = experiment.model_copy(update={"status": ExperimentStatus.running})
            await self.experiment_repo.update_experiment(experiment)

            if not experiment.task_id:
                raise TaskNotFoundError("Experiment missing target task ID.")

            task = await self.task_repo.get_task(experiment.task_id)
            if not task:
                raise TaskNotFoundError(f"Task '{experiment.task_id}' not found.")

            canonical_reqs = await self.task_repo.get_requirements(experiment.task_id)

            # Execute evaluation
            evaluation_results = await self.evaluator.evaluate_experiment(
                task=task,
                canonical_requirements=canonical_reqs,
                mutation_types=experiment.mutation_types,
                runs=experiment.runs,
            )

            # Mark completed with recorded metrics
            config = dict(experiment.configuration)
            config.update({
                "mutations": evaluation_results.get("mutations", []),
                "runs": experiment.runs,
                "is_simulated": evaluation_results.get("is_simulated", True),
                "limitations": evaluation_results.get("limitations", []),
                "statistical_significance": evaluation_results.get("statistical_significance", {}),
            })

            metrics = {
                "baseline_metrics": evaluation_results.get("baseline_metrics", {}),
                "handoffiq_metrics": evaluation_results.get("handoffiq_metrics", {}),
                "comparison": evaluation_results.get("comparison", {}),
                "runs_completed": experiment.runs,
            }

            experiment = experiment.model_copy(
                update={
                    "status": ExperimentStatus.completed,
                    "configuration": config,
                    "metrics": metrics,
                    "completed_at": utcnow(),
                }
            )
            await self.experiment_repo.update_experiment(experiment)

        except Exception as exc:
            logger.error("Unhandled error in experiment %s execution: %s", experiment_id, exc)
            exp = await self.experiment_repo.get_experiment(experiment_id)
            if exp:
                updated = exp.model_copy(
                    update={
                        "status": ExperimentStatus.failed,
                        "metrics": {"error": str(exc)},
                        "completed_at": utcnow(),
                    }
                )
                await self.experiment_repo.update_experiment(updated)
        finally:
            async with self._lock:
                self._running_experiments.discard(experiment_id)
                self._active_jobs.pop(experiment_id, None)

    async def wait_for_completion(self, experiment_id: UUID, timeout: float = 10.0) -> None:
        """Helper for test suites and consumers to await background experiment completion."""
        job = self._active_jobs.get(experiment_id)
        if job and not job.done():
            await asyncio.wait_for(job, timeout=timeout)
