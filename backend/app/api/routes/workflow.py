"""Workflow execution endpoints."""

from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.services.workflow_engine import TaskExecutionManager, get_execution_manager

router = APIRouter(prefix="/tasks/{task_id}", tags=["Workflow"])


class WorkflowRunResponse(BaseModel):
    """Response returned when initiating a workflow run."""

    task_id: UUID
    status: str = Field(default="running", description="Status of the task")
    current_stage: str = Field(default="research", description="Current execution stage")
    message: str = Field(default="Workflow started", description="Status notification message")


@router.post(
    "/run",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Start task execution workflow",
    description="Starts the background multi-agent workflow (Researcher -> Handoff -> Coder -> Reviewer -> Tester -> Verification).",
)
async def run_task_workflow(
    task_id: UUID,
    manager: TaskExecutionManager = Depends(get_execution_manager),
) -> WorkflowRunResponse:
    """Trigger managed background execution for the specified task."""
    result = await manager.start_task_run(task_id)
    return WorkflowRunResponse(
        task_id=result["task_id"],
        status=result["status"],
        current_stage=result["current_stage"],
        message=result["message"],
    )
