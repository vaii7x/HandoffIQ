"""Supabase implementation of TaskRepository."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.errors import AppError, DatabaseError, EntityNotFoundError, TaskNotFoundError
from app.core.supabase import get_supabase_client
from app.models.agent_run import AgentRun
from app.models.artifact import CodeArtifact
from app.models.event import WorkflowEvent
from app.models.recovery import RecoveryAttempt
from app.models.requirement import Requirement
from app.models.task import Task
from app.models.test_result import TestResult
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

    async def add_agent_run(self, run: AgentRun) -> AgentRun:
        data = {
            "id": str(run.id),
            "task_id": str(run.task_id),
            "agent_type": run.agent_type.value if hasattr(run.agent_type, "value") else str(run.agent_type),
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "summary": run.summary,
            "error": run.error,
        }
        try:
            res = self.client.table("agent_runs").insert(data).execute()
            if not res.data:
                raise DatabaseError("Failed to insert agent run.")
            return AgentRun(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"add_agent_run({run.task_id})")

    async def update_agent_run(self, run: AgentRun) -> AgentRun:
        data = {
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "summary": run.summary,
            "error": run.error,
        }
        try:
            res = self.client.table("agent_runs").update(data).eq("id", str(run.id)).execute()
            if not res.data:
                # If row doesn't exist, insert it
                return await self.add_agent_run(run)
            return AgentRun(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"update_agent_run({run.id})")

    async def add_artifact(self, task_id: UUID, artifact: CodeArtifact) -> CodeArtifact:
        data = {
            "id": str(artifact.id),
            "task_id": str(task_id),
            "path": artifact.path,
            "language": artifact.language,
            "content": artifact.content,
            "requirement_ids": artifact.requirement_ids,
            "version": artifact.version,
        }
        try:
            res = self.client.table("code_artifacts").insert(data).execute()
            if not res.data:
                raise DatabaseError("Failed to insert code artifact.")
            return CodeArtifact(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"add_artifact({task_id})")

    async def get_artifacts(self, task_id: UUID) -> List[CodeArtifact]:
        try:
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError()
            res = self.client.table("code_artifacts").select("*").eq("task_id", str(task_id)).execute()
            return [CodeArtifact(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"get_artifacts({task_id})")

    async def add_test_result(self, task_id: UUID, test_result: TestResult) -> TestResult:
        data = {
            "id": str(test_result.id),
            "task_id": str(task_id),
            "test_name": test_result.test_name,
            "tool": test_result.tool,
            "test_type": test_result.test_type,
            "status": test_result.status.value if hasattr(test_result.status, "value") else str(test_result.status),
            "output": test_result.output,
            "duration_ms": test_result.duration_ms,
            "requirement_ids": test_result.requirement_ids,
        }
        try:
            res = self.client.table("test_results").insert(data).execute()
            if not res.data:
                raise DatabaseError("Failed to insert test result.")
            return TestResult(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"add_test_result({task_id})")

    async def get_test_results(self, task_id: UUID) -> List[TestResult]:
        try:
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError()
            res = self.client.table("test_results").select("*").eq("task_id", str(task_id)).execute()
            return [TestResult(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"get_test_results({task_id})")

    async def add_recovery_attempt(self, task_id: UUID, recovery: RecoveryAttempt) -> RecoveryAttempt:
        data = {
            "id": str(recovery.id),
            "task_id": str(task_id),
            "requirement_ids": recovery.requirement_ids,
            "failure_summary": recovery.failure_summary,
            "repair_summary": recovery.repair_summary,
            "status": recovery.status.value if hasattr(recovery.status, "value") else str(recovery.status),
            "attempt_number": recovery.attempt_number,
            "test_result_ids": recovery.test_result_ids,
            "regressions": recovery.regressions,
            "unresolved_failures": recovery.unresolved_failures,
        }
        try:
            res = self.client.table("recovery_attempts").insert(data).execute()
            if not res.data:
                raise DatabaseError("Failed to insert recovery attempt.")
            return RecoveryAttempt(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"add_recovery_attempt({task_id})")

    async def get_recovery_attempts(self, task_id: UUID) -> List[RecoveryAttempt]:
        try:
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError()
            res = (
                self.client.table("recovery_attempts")
                .select("*")
                .eq("task_id", str(task_id))
                .order("attempt_number", desc=False)
                .execute()
            )
            return [RecoveryAttempt(**row) for row in res.data]
        except Exception as exc:
            _handle_db_exception(exc, f"get_recovery_attempts({task_id})")

    async def update_recovery_attempt(self, recovery: RecoveryAttempt) -> RecoveryAttempt:
        data = {
            "status": recovery.status.value if hasattr(recovery.status, "value") else str(recovery.status),
            "repair_summary": recovery.repair_summary,
            "regressions": recovery.regressions,
            "unresolved_failures": recovery.unresolved_failures,
            "test_result_ids": recovery.test_result_ids,
        }
        try:
            res = (
                self.client.table("recovery_attempts")
                .update(data)
                .eq("id", str(recovery.id))
                .execute()
            )
            if not res.data:
                return await self.add_recovery_attempt(recovery.task_id, recovery)
            return RecoveryAttempt(**res.data[0])
        except Exception as exc:
            _handle_db_exception(exc, f"update_recovery_attempt({recovery.id})")
