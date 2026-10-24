"""Task routes providing registration, retrieval, requirements, and events."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.models.agent_run import AgentRun
from app.models.event import WorkflowEvent
from app.models.requirement import Requirement
from app.models.task import Task
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class CreateTaskRequest(BaseModel):
    """Payload to register a new user task."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable title for the task",
        examples=["Expense Tracker"],
    )
    original_request: str = Field(
        ...,
        min_length=1,
        description="Original, unmodified user request prompt",
        examples=["Build a responsive expense tracker with login and a dark theme."],
    )


class CreateTaskResponse(BaseModel):
    """Response returned upon successful task registration."""

    task: Task
    requirements: List[Requirement] = Field(default_factory=list)
    events: List[WorkflowEvent] = Field(default_factory=list)


class TaskListResponse(BaseModel):
    """Response containing list of all registered tasks."""

    tasks: List[Task] = Field(default_factory=list)


class TaskSummary(BaseModel):
    """Aggregated verification metrics for a task."""

    total_requirements: int = 0
    verified_requirements: int = 0
    failed_requirements: int = 0
    open_issues: int = 0


class TaskDetailResponse(BaseModel):
    """Detailed response for a single task including requirements, agent runs, and summary."""

    task: Task
    requirements: List[Requirement] = Field(default_factory=list)
    agent_runs: List[AgentRun] = Field(default_factory=list)
    summary: TaskSummary


class TaskRequirementsResponse(BaseModel):
    """Response containing requirements for a specific task."""

    requirements: List[Requirement] = Field(default_factory=list)


class TaskEventsResponse(BaseModel):
    """Response containing audit workflow events for a task."""

    events: List[WorkflowEvent] = Field(default_factory=list)


@router.post(
    "",
    response_model=CreateTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new task",
    description="Registers a new task, stores the original request, audits events, and extracts requirements.",
)
async def create_task(
    payload: CreateTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    """Create task, trigger candidate requirement extraction, and record audit events."""
    task, requirements, events = await service.create_task_with_requirements(
        title=payload.title,
        original_request=payload.original_request,
    )
    return CreateTaskResponse(
        task=task,
        requirements=requirements,
        events=events,
    )


@router.get(
    "",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all tasks",
    description="Retrieve all registered tasks sorted by creation date descending.",
)
async def list_tasks(
    service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    """List all tasks."""
    tasks = await service.list_tasks()
    return TaskListResponse(tasks=tasks)


@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task details",
    description="Retrieve detailed task state, requirements, agent runs, and summary metrics.",
)
async def get_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    """Retrieve detailed task information."""
    detail = await service.get_task_detail(task_id)
    return TaskDetailResponse(
        task=detail["task"],
        requirements=detail["requirements"],
        agent_runs=detail["agent_runs"],
        summary=TaskSummary(**detail["summary"]),
    )


@router.get(
    "/{task_id}/requirements",
    response_model=TaskRequirementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task requirements",
    description="Retrieve all canonical requirements registered for a task.",
)
async def get_task_requirements(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskRequirementsResponse:
    """Retrieve requirements for a task."""
    requirements = await service.get_requirements(task_id)
    return TaskRequirementsResponse(requirements=requirements)


@router.get(
    "/{task_id}/events",
    response_model=TaskEventsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task workflow events",
    description="Retrieve the chronological workflow audit log for a task.",
)
async def get_task_events(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskEventsResponse:
    """Retrieve workflow audit events for a task."""
    events = await service.get_events(task_id)
    return TaskEventsResponse(events=events)
