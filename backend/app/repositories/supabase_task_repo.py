"""Supabase implementation of TaskRepository."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.errors import AppError, DatabaseError, EntityNotFoundError, TaskNotFoundError
from app.core.supabase import get_supabase_client
from app.models.agent_run import AgentRun
from app.models.event import WorkflowEvent
from app.models.requirement import Requirement
from app.models.task import Task
from app.repositories.base import TaskRepository


def _handle_db_exception(exc: Exception, action: str) -> None:
    """Translate PostgREST / network exceptions to standard application errors."""
    if isinstance(exc, AppError):
        raise exc

    msg = str(exc)
    msg_lower = msg.lower()

    if "duplicate key" in msg_lower or "unique constraint" in msg_lower:
        raise DatabaseError(
            message=f"Unique constraint violation during {action}.",
            code="CONSTRAINT_VIOLATION",
            status_code=409,
            details=msg,
        )
    if "timeout" in msg_lower or "timed out" in msg_lower:
        raise DatabaseError(
            message=f"Database timeout during {action}.",
            code="DATABASE_TIMEOUT",
            status_code=503,
            details=msg,
        )
    if "connection" in msg_lower or "failed to connect" in msg_lower:
        raise DatabaseError(
            message=f"Database connection error during {action}.",
            code="DATABASE_CONNECTION_ERROR",
            status_code=503,
            details=msg,
        )

    raise DatabaseError(
        message=f"Database operation failed during {action}.",
        code="DATABASE_ERROR",
        status_code=500,
        details=msg,
    )


class SupabaseTaskRepository(TaskRepository):
    """PostgreSQL/Supabase backed repository for tasks, requirements, and events."""

    def __init__(self, client=None) -> None:
        self._client = client

    @property
    def client(self):
        if self._client is not None:
            return self._client
        return get_supabase_client()

    async def create_task(self, task: Task) -> Task:
        data = {
            "id": str(task.id),
            "title": task.title,
            "original_request": task.original_request,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "current_stage": task.current_stage,
            "progress": task.progress,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
        try:
            res = self.client.table("tasks").insert(data).execute()
            if not res.data:
                raise DatabaseError("Failed to insert task record.")
            return Task(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, "create_task")

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        try:
            res = self.client.table("tasks").select("*").eq("id", str(task_id)).execute()
            if not res.data:
                return None
            return Task(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"get_task({task_id})")

    async def list_tasks(self) -> List[Task]:
        try:
            res = self.client.table("tasks").select("*").order("created_at", desc=True).execute()
            return [Task(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, "list_tasks")

    async def update_task(self, task: Task) -> Task:
        data = {
            "title": task.title,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "current_stage": task.current_stage,
            "progress": task.progress,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            res = self.client.table("tasks").update(data).eq("id", str(task.id)).execute()
            if not res.data:
                raise TaskNotFoundError()
            return Task(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"update_task({task.id})")

    async def get_next_requirement_id(self, task_id: UUID) -> str:
        try:
            res = self.client.table("requirements").select("id").eq("task_id", str(task_id)).execute()
            existing_ids = [row["id"] for row in (res.data or [])]
            max_num = 0
            for rid in existing_ids:
                match = re.search(r"R(\d+)", rid)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
            return f"R{max_num + 1:03d}"
        except Exception as exc:
            _handle_db_exception(exc, f"get_next_requirement_id({task_id})")

    async def add_requirements(self, task_id: UUID, requirements: List[Requirement]) -> List[Requirement]:
        if not requirements:
            return []

        rows = [
            {
                "id": req.id,
                "task_id": str(task_id),
                "original_text": req.original_text,
                "priority": req.priority.value if hasattr(req.priority, "value") else str(req.priority),
                "status": req.status.value if hasattr(req.status, "value") else str(req.status),
                "description": req.description,
                "related_files": req.related_files,
                "related_test_ids": req.related_test_ids,
            }
            for req in requirements
        ]
        try:
            res = self.client.table("requirements").insert(rows).execute()
            return [Requirement(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"add_requirements({task_id})")

    async def get_requirements(self, task_id: UUID) -> List[Requirement]:
        try:
            # Check if task exists first
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError()

            res = (
                self.client.table("requirements")
                .select("*")
                .eq("task_id", str(task_id))
                .order("id", desc=False)
                .execute()
            )
            return [Requirement(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"get_requirements({task_id})")

    async def get_requirement(self, task_id: UUID, requirement_id: str) -> Optional[Requirement]:
        try:
            res = (
                self.client.table("requirements")
                .select("*")
                .eq("task_id", str(task_id))
                .eq("id", requirement_id)
                .execute()
            )
            if not res.data:
                return None
            return Requirement(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"get_requirement({task_id}, {requirement_id})")

    async def update_requirement(self, task_id: UUID, requirement: Requirement) -> Requirement:
        try:
            # Retrieve existing to guarantee original_text is preserved
            existing = await self.get_requirement(task_id, requirement.id)
            if not existing:
                raise EntityNotFoundError("Requirement", requirement.id)

            data = {
                "priority": requirement.priority.value if hasattr(requirement.priority, "value") else str(requirement.priority),
                "status": requirement.status.value if hasattr(requirement.status, "value") else str(requirement.status),
                "description": requirement.description,
                "related_files": requirement.related_files,
                "related_test_ids": requirement.related_test_ids,
                # Strictly preserve original_text
                "original_text": existing.original_text,
            }
            res = (
                self.client.table("requirements")
                .update(data)
                .eq("task_id", str(task_id))
                .eq("id", requirement.id)
                .execute()
            )
            if not res.data:
                raise EntityNotFoundError("Requirement", requirement.id)
            row = dict(res.data[0])
            if "id" not in row:
                row["id"] = requirement.id
            if "task_id" not in row:
                row["task_id"] = str(task_id)
            return Requirement(**row)
        except Exception as exc:
            _handle_db_exception(exc, f"update_requirement({task_id}, {requirement.id})")

    async def add_event(self, event: WorkflowEvent) -> WorkflowEvent:
        data = {
            "id": str(event.id),
            "task_id": str(event.task_id),
            "event_type": event.event_type,
            "stage": event.stage,
            "message": event.message,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
        }
        try:
            res = self.client.table("workflow_events").insert(data).execute()
            if not res.data:
                raise DatabaseError("Failed to insert workflow event record.")
            return WorkflowEvent(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"add_event({event.task_id})")

    async def get_events(self, task_id: UUID) -> List[WorkflowEvent]:
        try:
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError()

            res = (
                self.client.table("workflow_events")
                .select("*")
                .eq("task_id", str(task_id))
                .order("timestamp", desc=False)
                .execute()
            )
            return [WorkflowEvent(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"get_events({task_id})")

    async def get_agent_runs(self, task_id: UUID) -> List[AgentRun]:
        try:
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError()

            res = (
                self.client.table("agent_runs")
                .select("*")
                .eq("task_id", str(task_id))
                .execute()
            )
            return [AgentRun(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"get_agent_runs({task_id})")
