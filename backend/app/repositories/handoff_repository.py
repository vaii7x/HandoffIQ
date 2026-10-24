"""Handoff repository interface and in-memory implementation."""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID

from app.core.errors import EntityNotFoundError
from app.models.handoff import Handoff


class HandoffRepository(ABC):
    """Abstract interface for handoff persistence and retrieval."""

    @abstractmethod
    async def create_handoff(self, handoff: Handoff) -> Handoff:
        """Store a newly registered handoff."""
        pass

    @abstractmethod
    async def get_handoff(self, handoff_id: UUID) -> Optional[Handoff]:
        """Retrieve a handoff by its unique UUID."""
        pass

    @abstractmethod
    async def list_handoffs_for_task(self, task_id: UUID) -> List[Handoff]:
        """List all handoffs recorded for a task sorted chronologically."""
        pass

    @abstractmethod
    async def update_handoff(self, handoff: Handoff) -> Handoff:
        """Update an existing handoff record (e.g. status, issues, payload)."""
        pass


class InMemoryHandoffRepository(HandoffRepository):
    """Thread-safe in-memory store for handoffs."""

    def __init__(self) -> None:
        self._handoffs: Dict[UUID, Handoff] = {}
        self._task_index: Dict[UUID, List[UUID]] = {}
        self._lock = asyncio.Lock()

    async def create_handoff(self, handoff: Handoff) -> Handoff:
        async with self._lock:
            stored = handoff.model_copy()
            self._handoffs[stored.id] = stored
            if stored.task_id not in self._task_index:
                self._task_index[stored.task_id] = []
            self._task_index[stored.task_id].append(stored.id)
            return stored.model_copy()

    async def get_handoff(self, handoff_id: UUID) -> Optional[Handoff]:
        async with self._lock:
            handoff = self._handoffs.get(handoff_id)
            return handoff.model_copy() if handoff else None

    async def list_handoffs_for_task(self, task_id: UUID) -> List[Handoff]:
        async with self._lock:
            handoff_ids = self._task_index.get(task_id, [])
            handoffs = [
                self._handoffs[hid].model_copy()
                for hid in handoff_ids
                if hid in self._handoffs
            ]
            handoffs.sort(key=lambda h: h.created_at)
            return handoffs

    async def update_handoff(self, handoff: Handoff) -> Handoff:
        async with self._lock:
            if handoff.id not in self._handoffs:
                raise EntityNotFoundError("Handoff", handoff.id)
            stored = handoff.model_copy()
            self._handoffs[stored.id] = stored
            return stored.model_copy()


_in_memory_handoff_repository = InMemoryHandoffRepository()


def get_handoff_repository() -> HandoffRepository:
    """Dependency provider returning the active handoff repository."""
    return _in_memory_handoff_repository
