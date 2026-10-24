"""Task orchestration service managing task registration, requirements, and events."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.errors import TaskNotFoundError
from app.models.agent_run import AgentRun
from app.models.event import WorkflowEvent
from app.models.requirement import Requirement, RequirementPriority, RequirementStatus
from app.models.task import Task, TaskStatus
from app.repositories.base import TaskRepository
from app.repositories.in_memory import get_task_repository
from app.services.extractor import RequirementExtractor, get_requirement_extractor

logger = logging.getLogger(__name__)


class TaskService:
    """Service handling task lifecycle and canonical requirement coordination."""

    def __init__(
        self,
        repository: TaskRepository,
        extractor: RequirementExtractor,
    ) -> None:
        self.repository = repository
        self.extractor = extractor

    async def create_task_with_requirements(
        self,
        title: str,
        original_request: str,
    ) -> Tuple[Task, List[Requirement], List[WorkflowEvent]]:
        """Register a new task, audit events, extract requirements, and record results."""
        # 1. Instantiate and persist the task
        task = Task(
            title=title,
            original_request=original_request,
            status=TaskStatus.queued,
            current_stage="registration",
            progress=0,
        )
        saved_task = await self.repository.create_task(task)

        # 2. Record Task Created event
        await self.repository.add_event(
            WorkflowEvent(
                task_id=saved_task.id,
                event_type="task_created",
                stage="registration",
                message=f"Task '{saved_task.title}' created.",
                metadata={
                    "task_id": str(saved_task.id),
                    "title": saved_task.title,
                },
            )
        )

        # 3. Record Requirement Extraction Started event
        await self.repository.add_event(
            WorkflowEvent(
                task_id=saved_task.id,
                event_type="requirement_extraction_started",
                stage="extraction",
                message="Requirement extraction started.",
                metadata={"extractor": self.extractor.extractor_name},
            )
        )

        extracted_requirements: List[Requirement] = []
        try:
            # 4. Extract candidates using extractor interface
            candidates = await self.extractor.extract(saved_task.id, original_request)

            # 5. Assign canonical sequential IDs (R001, R002, ...) and persist
            for candidate in candidates:
                req_id = await self.repository.get_next_requirement_id(saved_task.id)
                requirement = Requirement(
                    id=req_id,
                    task_id=saved_task.id,
                    original_text=candidate.original_text,
                    description=candidate.description,
                    priority=candidate.priority,
                    status=RequirementStatus.registered,
                    related_files=candidate.related_files,
                    related_test_ids=candidate.related_test_ids,
                )
                extracted_requirements.append(requirement)

                # Record Requirement Registered event
                await self.repository.add_event(
                    WorkflowEvent(
                        task_id=saved_task.id,
                        event_type="requirement_registered",
                        stage="registration",
                        message=f"Requirement {requirement.id} registered: '{requirement.original_text}'",
                        metadata={
                            "requirement_id": requirement.id,
                            "priority": str(requirement.priority),
                        },
                    )
                )

            await self.repository.add_requirements(saved_task.id, extracted_requirements)

            # Record Requirement Extraction Completed event
            await self.repository.add_event(
                WorkflowEvent(
                    task_id=saved_task.id,
                    event_type="requirement_extraction_completed",
                    stage="extraction",
                    message=f"Requirement extraction completed with {len(extracted_requirements)} requirements.",
                    metadata={
                        "count": len(extracted_requirements),
                        "extractor": self.extractor.extractor_name,
                    },
                )
            )

        except Exception as exc:
            logger.error("Failed to extract requirements for task %s: %s", saved_task.id, exc)
            # Preserve the task and original request, record failure event
            await self.repository.add_event(
                WorkflowEvent(
                    task_id=saved_task.id,
                    event_type="requirement_extraction_failed",
                    stage="extraction",
                    message=f"Requirement extraction failed: {str(exc)}",
                    metadata={
                        "error": str(exc),
                        "extractor": self.extractor.extractor_name,
                    },
                )
            )

        # 6. Retrieve all events recorded for the task
        events = await self.repository.get_events(saved_task.id)
        return saved_task, extracted_requirements, events

    async def list_tasks(self) -> List[Task]:
        """Retrieve all registered tasks."""
        return await self.repository.list_tasks()

    async def get_task_detail(self, task_id: UUID) -> Dict[str, Any]:
        """Retrieve detailed task state including requirements, agent runs, and summary."""
        task = await self.repository.get_task(task_id)
        if not task:
            raise TaskNotFoundError()

        requirements = await self.repository.get_requirements(task_id)
        agent_runs = await self.repository.get_agent_runs(task_id)

        # Calculate metrics summary
        total_reqs = len(requirements)
        verified_reqs = sum(
            1 for r in requirements if r.status in [RequirementStatus.verified, "verified"]
        )
        failed_reqs = sum(
            1 for r in requirements if r.status in [RequirementStatus.failed, "failed"]
        )

        summary = {
            "total_requirements": total_reqs,
            "verified_requirements": verified_reqs,
            "failed_requirements": failed_reqs,
            "open_issues": 0,
        }

        return {
            "task": task,
            "requirements": requirements,
            "agent_runs": agent_runs,
            "summary": summary,
        }

    async def get_requirements(self, task_id: UUID) -> List[Requirement]:
        """Retrieve requirements for a specific task."""
        # Ensure task exists
        task = await self.repository.get_task(task_id)
        if not task:
            raise TaskNotFoundError()
        return await self.repository.get_requirements(task_id)

    async def get_events(self, task_id: UUID) -> List[WorkflowEvent]:
        """Retrieve workflow events for a specific task."""
        # Ensure task exists
        task = await self.repository.get_task(task_id)
        if not task:
            raise TaskNotFoundError()
        return await self.repository.get_events(task_id)

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        current_stage: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> Task:
        """Update task status, stage, or progress and record task_status_changed event."""
        task = await self.repository.get_task(task_id)
        if not task:
            raise TaskNotFoundError()

        old_status = task.status
        updates: Dict[str, Any] = {"status": status}
        if current_stage is not None:
            updates["current_stage"] = current_stage
        if progress is not None:
            updates["progress"] = progress

        updated_task = task.model_copy(update=updates)
        saved = await self.repository.update_task(updated_task)

        # Record Task Status Changed event
        await self.repository.add_event(
            WorkflowEvent(
                task_id=task_id,
                event_type="task_status_changed",
                stage=saved.current_stage or "workflow",
                message=f"Task status transitioned from '{old_status}' to '{status}'.",
                metadata={
                    "old_status": str(old_status),
                    "new_status": str(status),
                    "progress": saved.progress,
                    "stage": saved.current_stage,
                },
            )
        )
        return saved

    async def update_requirement(
        self,
        task_id: UUID,
        requirement_id: str,
        status: Optional[RequirementStatus] = None,
        description: Optional[str] = None,
        priority: Optional[RequirementPriority] = None,
        related_files: Optional[List[str]] = None,
        related_test_ids: Optional[List[str]] = None,
    ) -> Requirement:
        """Update an existing requirement, preserving original_text and recording an audit event."""
        task = await self.repository.get_task(task_id)
        if not task:
            raise TaskNotFoundError()

        existing = await self.repository.get_requirement(task_id, requirement_id)
        if not existing:
            raise EntityNotFoundError("Requirement", requirement_id)

        updates: Dict[str, Any] = {}
        changes: Dict[str, Any] = {}
        if status is not None:
            updates["status"] = status
            changes["status"] = str(status)
        if description is not None:
            updates["description"] = description
            changes["description"] = description
        if priority is not None:
            updates["priority"] = priority
            changes["priority"] = str(priority)
        if related_files is not None:
            updates["related_files"] = related_files
            changes["related_files"] = related_files
        if related_test_ids is not None:
            updates["related_test_ids"] = related_test_ids
            changes["related_test_ids"] = related_test_ids

        # Always preserve immutable original_text
        updates["original_text"] = existing.original_text

        updated_req = existing.model_copy(update=updates)
        saved = await self.repository.update_requirement(task_id, updated_req)

        # Record Requirement Updated event
        await self.repository.add_event(
            WorkflowEvent(
                task_id=task_id,
                event_type="requirement_updated",
                stage="management",
                message=f"Requirement {requirement_id} updated.",
                metadata={
                    "requirement_id": requirement_id,
                    "changes": changes,
                },
            )
        )
        return saved


def get_task_service() -> TaskService:
    """Dependency provider creating TaskService with configured repository and extractor."""
    repository = get_task_repository()
    extractor = get_requirement_extractor()
    return TaskService(repository=repository, extractor=extractor)
