"""In-memory implementation of the TaskRepository for local development and testing."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from app.core.errors import EntityNotFoundError, TaskNotFoundError
from app.models.agent_run import AgentRun
from app.models.event import WorkflowEvent
from app.models.requirement import Requirement
from app.models.task import Task
from app.repositories.base import TaskRepository


class InMemoryTaskRepository(TaskRepository):
    """Thread-safe in-memory store for tasks, requirements, and events."""

    def __init__(self) -> None:
        self._tasks: Dict[UUID, Task] = {}
        self._requirements: Dict[UUID, Dict[str, Requirement]] = {}
        self._events: Dict[UUID, List[WorkflowEvent]] = {}
        self._agent_runs: Dict[UUID, List[AgentRun]] = {}
        self._req_counters: Dict[UUID, int] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task: Task) -> Task:
        async with self._lock:
            # Store copy to prevent unintended external mutations
            self._tasks[task.id] = task.model_copy()
            if task.id not in self._requirements:
                self._requirements[task.id] = {}
            if task.id not in self._events:
                self._events[task.id] = []
            if task.id not in self._agent_runs:
                self._agent_runs[task.id] = []
            if task.id not in self._req_counters:
                self._req_counters[task.id] = 0
            return self._tasks[task.id].model_copy()

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            return task.model_copy() if task else None

    async def list_tasks(self) -> List[Task]:
        async with self._lock:
            # Return tasks sorted by creation timestamp descending
            tasks = list(self._tasks.values())
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return [t.model_copy() for t in tasks]

    async def update_task(self, task: Task) -> Task:
        async with self._lock:
            if task.id not in self._tasks:
                raise TaskNotFoundError()
            updated = task.model_copy(update={"updated_at": datetime.now(timezone.utc)})
            self._tasks[task.id] = updated
            return updated.model_copy()

    async def get_next_requirement_id(self, task_id: UUID) -> str:
        async with self._lock:
            count = self._req_counters.get(task_id, 0) + 1
            self._req_counters[task_id] = count
            return f"R{count:03d}"

    async def add_requirements(self, task_id: UUID, requirements: List[Requirement]) -> List[Requirement]:
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError()
            if task_id not in self._requirements:
                self._requirements[task_id] = {}

            saved: List[Requirement] = []
            for req in requirements:
                # Ensure the requirement has original_text unchanged
                stored = req.model_copy()
                self._requirements[task_id][stored.id] = stored
                saved.append(stored.model_copy())
            return saved

    async def get_requirements(self, task_id: UUID) -> List[Requirement]:
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError()
            reqs = list(self._requirements.get(task_id, {}).values())
            # Maintain stable sequential order by requirement ID
            reqs.sort(key=lambda r: r.id)
            return [r.model_copy() for r in reqs]

    async def get_requirement(self, task_id: UUID, requirement_id: str) -> Optional[Requirement]:
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError()
            req = self._requirements.get(task_id, {}).get(requirement_id)
            return req.model_copy() if req else None

    async def update_requirement(self, task_id: UUID, requirement: Requirement) -> Requirement:
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError()
            task_reqs = self._requirements.get(task_id, {})
            if requirement.id not in task_reqs:
                raise EntityNotFoundError("Requirement", requirement.id)

            # Preserve the immutable original_text from the existing stored requirement
            existing = task_reqs[requirement.id]
            updated = requirement.model_copy(
                update={"original_text": existing.original_text}
            )
            task_reqs[requirement.id] = updated
            return updated.model_copy()

    async def add_event(self, event: WorkflowEvent) -> WorkflowEvent:
        async with self._lock:
            if event.task_id not in self._tasks:
                raise TaskNotFoundError()
            if event.task_id not in self._events:
                self._events[event.task_id] = []
            stored = event.model_copy()
            self._events[event.task_id].append(stored)
            return stored.model_copy()

    async def get_events(self, task_id: UUID) -> List[WorkflowEvent]:
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError()
            events = self._events.get(task_id, [])
            return [e.model_copy() for e in events]

    async def get_agent_runs(self, task_id: UUID) -> List[AgentRun]:
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError()
            runs = self._agent_runs.get(task_id, [])
            return [r.model_copy() for r in runs]


# Global repository instance for development / in-memory lifecycle
_in_memory_repository = InMemoryTaskRepository()


def get_task_repository() -> TaskRepository:
    """FastAPI dependency provider returning the configured task repository."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.MOCK_MODE:
        return _in_memory_repository

    from app.repositories.supabase_task_repo import SupabaseTaskRepository

    return SupabaseTaskRepository()
