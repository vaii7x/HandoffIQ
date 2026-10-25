"""Task routes providing registration, retrieval, requirements, and events."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, AliasChoices, model_validator

from app.models.agent_run import AgentRun
from app.models.event import WorkflowEvent
import io
import os
import zipfile
from pathlib import Path
from fastapi.responses import Response
from app.models.artifact import CodeArtifact
from app.models.test_result import TestResult
from app.models.requirement import Requirement
from app.models.task import Task
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class CreateTaskRequest(BaseModel):
    """Payload to register a new user task."""

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Human-readable title for the task",
        examples=["Expense Tracker"],
    )
    original_request: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("original_request", "requirement"),
        description="Original, unmodified user request prompt",
        examples=["Build a responsive expense tracker with login and a dark theme."],
    )

    @model_validator(mode="before")
    @classmethod
    def populate_default_title(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "title" not in data or data.get("title") is None:
                req = data.get("original_request") or data.get("requirement", "")
                if req:
                    data["title"] = req.strip().split("\n")[0][:60]
        return data


class CreateTaskResponse(BaseModel):
    """Response returned upon successful task registration."""

    task: Task
    requirements: List[Requirement] = Field(default_factory=list)
    events: List[WorkflowEvent] = Field(default_factory=list)
    taskId: Optional[str] = None

    @model_validator(mode="after")
    def populate_task_id(self) -> "CreateTaskResponse":
        if not self.taskId and self.task:
            self.taskId = str(self.task.id)
        return self


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


class TaskArtifactsResponse(BaseModel):
    task_id: UUID
    artifacts: List[CodeArtifact] = Field(default_factory=list)


class TaskTestsResponse(BaseModel):
    task_id: UUID
    tests: List[TestResult] = Field(default_factory=list)


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
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    """Retrieve detailed task information."""
    resolved_id = await service.resolve_task_id(task_id)
    detail = await service.get_task_detail(resolved_id)
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
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskRequirementsResponse:
    """Retrieve requirements for a task."""
    resolved_id = await service.resolve_task_id(task_id)
    requirements = await service.get_requirements(resolved_id)
    return TaskRequirementsResponse(requirements=requirements)


@router.get(
    "/{task_id}/artifacts",
    response_model=TaskArtifactsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get generated code artifacts for a task",
)
async def get_task_artifacts(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskArtifactsResponse:
    resolved_id = await service.resolve_task_id(task_id)
    artifacts = await service.get_artifacts(resolved_id)
    if not artifacts:
        possible_dirs = [
            Path("backend/workspaces") / str(resolved_id),
            Path("workspaces") / str(resolved_id),
            Path("backend/backend/workspaces") / str(resolved_id),
        ]
        workspace_dir = next((d for d in possible_dirs if d.exists()), possible_dirs[0])
        if workspace_dir.exists():
            for root, _, files in os.walk(workspace_dir):
                for f in files:
                    full_p = Path(root) / f
                    if any(p in full_p.parts for p in ["node_modules", ".git", "__pycache__"]) or full_p.suffix.lower() in [".pyc", ".pyo"]:
                        continue
                    rel_p = str(full_p.relative_to(workspace_dir)).replace("\\", "/")
                    ext = full_p.suffix.lower()
                    lang = "typescript" if ext in [".ts", ".tsx"] else "python" if ext == ".py" else "json" if ext == ".json" else "markdown" if ext == ".md" else "text"
                    try:
                        content = full_p.read_text(encoding="utf-8")
                        artifacts.append(CodeArtifact(task_id=resolved_id, path=rel_p, language=lang, content=content))
                    except Exception:
                        pass
    return TaskArtifactsResponse(task_id=resolved_id, artifacts=artifacts)


@router.get(
    "/{task_id}/artifacts/zip",
    status_code=status.HTTP_200_OK,
    summary="Download task code artifacts as ZIP archive",
)
async def download_task_artifacts_zip(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> Response:
    resolved_id = await service.resolve_task_id(task_id)
    artifacts = await service.get_artifacts(resolved_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        possible_dirs = [
            Path("backend/workspaces") / str(resolved_id),
            Path("workspaces") / str(resolved_id),
            Path("backend/backend/workspaces") / str(resolved_id),
        ]
        workspace_dir = next((d for d in possible_dirs if d.exists()), possible_dirs[0])
        written = set()
        if workspace_dir.exists():
            for root, _, files in os.walk(workspace_dir):
                for f in files:
                    full_p = Path(root) / f
                    if any(p in full_p.parts for p in ["node_modules", ".git", "__pycache__"]) or full_p.suffix.lower() in [".pyc", ".pyo"]:
                        continue
                    rel_p = str(full_p.relative_to(workspace_dir)).replace("\\", "/")
                    zf.write(full_p, arcname=rel_p)
                    written.add(rel_p)
        for art in artifacts:
            norm_path = art.path.replace("\\", "/")
            if norm_path not in written:
                zf.writestr(norm_path, art.content)
                written.add(norm_path)
    buf.seek(0)
    zip_bytes = buf.getvalue()
    tid_short = str(resolved_id)[:8]
    filename = f"handoffiq_task_{tid_short}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{task_id}/tests",
    response_model=TaskTestsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verification test results for a task",
)
async def get_task_tests(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskTestsResponse:
    resolved_id = await service.resolve_task_id(task_id)
    tests = await service.get_test_results(resolved_id)
    return TaskTestsResponse(task_id=resolved_id, tests=tests)


@router.get(
    "/{task_id}/recoveries",
    status_code=status.HTTP_200_OK,
    summary="Get recovery and self-healing attempts for a task",
)
async def get_task_recoveries(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    resolved_id = await service.resolve_task_id(task_id)
    recoveries = await service.get_recovery_attempts(resolved_id)
    return {"task_id": resolved_id, "recoveries": recoveries}


@router.get(
    "/{task_id}/events",
    response_model=TaskEventsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task workflow events",
    description="Retrieve the chronological workflow audit log for a task.",
)
async def get_task_events(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskEventsResponse:
    """Retrieve workflow audit events for a task."""
    resolved_id = await service.resolve_task_id(task_id)
    events = await service.get_events(resolved_id)
    return TaskEventsResponse(events=events)
