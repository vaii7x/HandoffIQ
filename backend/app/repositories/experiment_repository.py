"""Experiment repository abstraction and in-memory persistence implementation."""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID

from app.models.experiment import Experiment


class ExperimentRepository(ABC):
    """Abstract interface for experiment persistence and retrieval."""

    @abstractmethod
    async def create_experiment(self, experiment: Experiment) -> Experiment:
        """Store a newly registered evaluation experiment."""
        pass

    @abstractmethod
    async def get_experiment(self, experiment_id: UUID) -> Optional[Experiment]:
        """Retrieve an experiment by its unique UUID."""
        pass

    @abstractmethod
    async def list_experiments(self) -> List[Experiment]:
        """List all experiments sorted chronologically descending."""
        pass

    @abstractmethod
    async def update_experiment(self, experiment: Experiment) -> Experiment:
        """Update an existing experiment record (e.g. status, metrics, completed_at)."""
        pass


class InMemoryExperimentRepository(ExperimentRepository):
    """Thread-safe in-memory store for experiments."""

    def __init__(self) -> None:
        self._experiments: Dict[UUID, Experiment] = {}
        self._lock = asyncio.Lock()

    async def create_experiment(self, experiment: Experiment) -> Experiment:
        async with self._lock:
            stored = experiment.model_copy()
            self._experiments[stored.id] = stored
            return stored.model_copy()

    async def get_experiment(self, experiment_id: UUID) -> Optional[Experiment]:
        async with self._lock:
            exp = self._experiments.get(experiment_id)
            return exp.model_copy() if exp else None

    async def list_experiments(self) -> List[Experiment]:
        async with self._lock:
            items = list(self._experiments.values())
            items.sort(key=lambda e: e.created_at, reverse=True)
            return [e.model_copy() for e in items]

    async def update_experiment(self, experiment: Experiment) -> Experiment:
        async with self._lock:
            stored = experiment.model_copy()
            self._experiments[stored.id] = stored
            return stored.model_copy()


_in_memory_experiment_repository = InMemoryExperimentRepository()


def get_experiment_repository() -> ExperimentRepository:
    """Dependency provider returning active experiment repository singleton."""
    return _in_memory_experiment_repository
