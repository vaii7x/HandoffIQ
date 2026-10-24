"""Handoff API endpoints for submitting and retrieving context handoffs."""

from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.models.handoff import Handoff
from app.services.handoff_service import HandoffValidationService, get_handoff_service

router = APIRouter(prefix="/tasks/{task_id}/handoffs", tags=["Handoffs"])


class SubmitHandoffRequest(BaseModel):
    """Payload to submit an agent handoff for validation."""

    source_agent: str = Field(
        ...,
        min_length=1,
        description="Role or identifier of the handing-off agent",
        examples=["researcher"],
    )
    target_agent: str = Field(
        ...,
        min_length=1,
        description="Role or identifier of the receiving agent",
        examples=["coder"],
    )
    requirement_ids: List[str] = Field(
        default_factory=list,
        description="Requirement IDs conveyed in this handoff",
        examples=[["R001", "R002"]],
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Passive JSON context data passed between agents",
        examples=[{"architecture_spec": "spec_v1.md", "status": "draft"}],
    )
    auto_repair: bool = Field(
        default=True,
        description="Whether to automatically restore recoverable canonical requirement omissions",
    )


class SubmitHandoffResponse(BaseModel):
    """Response returned upon handoff validation."""

    handoff: Handoff
    repaired: bool = Field(description="Whether automated safe repair was executed")
    issues_count: int = Field(description="Total number of issues tracked on this handoff")


class HandoffListResponse(BaseModel):
    """List of all handoffs recorded for a task."""

    handoffs: List[Handoff] = Field(default_factory=list)


@router.post(
    "",
    response_model=SubmitHandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and validate an agent handoff",
    description="Validates a context handoff against task requirements, optionally repairs omissions, and records audit events.",
)
async def submit_handoff(
    task_id: UUID,
    payload: SubmitHandoffRequest,
    service: HandoffValidationService = Depends(get_handoff_service),
) -> SubmitHandoffResponse:
    """Submit a context handoff for deterministic checks, semantic analysis, and safe repair."""
    handoff, was_repaired = await service.submit_and_validate_handoff(
        task_id=task_id,
        source_agent=payload.source_agent,
        target_agent=payload.target_agent,
        requirement_ids=payload.requirement_ids,
        payload=payload.payload,
        auto_repair=payload.auto_repair,
    )
    return SubmitHandoffResponse(
        handoff=handoff,
        repaired=was_repaired,
        issues_count=len(handoff.issues),
    )


@router.get(
    "",
    response_model=HandoffListResponse,
    status_code=status.HTTP_200_OK,
    summary="List handoffs for a task",
    description="Retrieve all context handoffs recorded for the specified task in chronological order.",
)
async def list_handoffs(
    task_id: UUID,
    service: HandoffValidationService = Depends(get_handoff_service),
) -> HandoffListResponse:
    """Retrieve all handoffs for a given task."""
    handoffs = await service.list_handoffs_for_task(task_id)
    return HandoffListResponse(handoffs=handoffs)
