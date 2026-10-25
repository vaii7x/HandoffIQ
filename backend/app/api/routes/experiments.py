"""Experiment evaluation and Mutation Lab endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.models.experiment import (
    EvaluationMetrics,
    Experiment,
    ExperimentStatus,
    MutationRecord,
)
from app.services.mutation_lab.service import (
    MutationLabService,
    get_mutation_lab_service,
)

router = APIRouter(prefix="/experiments", tags=["Experiments"])


class CreateExperimentRequest(BaseModel):
    """Payload to create and queue an evaluation experiment."""

    task_id: UUID = Field(
        ...,
        description="ID of the benchmark canonical task",
    )
    mutation_types: List[str] = Field(
        ...,
        min_length=1,
        description="List of mutation types to evaluate (e.g. missing_requirement, weakened_constraint)",
        examples=[["missing_requirement", "weakened_constraint"]],
    )
    runs: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of evaluation runs to execute",
    )


class CreateExperimentResponse(BaseModel):
    """Response returned when an experiment is queued."""

    experiment_id: UUID
    status: str = Field(default="queued")
    message: str = Field(default="Experiment queued")


class ExperimentDetailResponse(BaseModel):
    """Detailed response for an experiment retrieval."""

    experiment_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    task_id: Optional[UUID] = None
    mutation_types: List[str] = Field(default_factory=list)
    runs: int = 1
    is_simulated: bool = True
    mutations: List[MutationRecord] = Field(default_factory=list)
    baseline_metrics: Optional[EvaluationMetrics] = None
    handoffiq_metrics: Optional[EvaluationMetrics] = None
    comparison: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)
    statistical_significance: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    experiment: Optional[Experiment] = None

    @classmethod
    def from_experiment(cls, exp: Experiment) -> "ExperimentDetailResponse":
        """Build response model from an Experiment domain entity."""
        cfg = exp.configuration or {}
        met = exp.metrics or {}

        # Parse mutations list if present
        raw_mutations = cfg.get("mutations", [])
        mutations = [
            m if isinstance(m, MutationRecord) else MutationRecord(**m)
            for m in raw_mutations
        ]

        # Parse metrics if completed
        baseline_raw = met.get("baseline_metrics")
        baseline_metrics = EvaluationMetrics(**baseline_raw) if baseline_raw else None

        handoffiq_raw = met.get("handoffiq_metrics")
        handoffiq_metrics = EvaluationMetrics(**handoffiq_raw) if handoffiq_raw else None

        return cls(
            experiment_id=exp.id,
            name=exp.name,
            description=exp.description,
            status=exp.status.value if isinstance(exp.status, ExperimentStatus) else str(exp.status),
            task_id=exp.task_id,
            mutation_types=exp.mutation_types,
            runs=exp.runs,
            is_simulated=exp.is_simulated,
            mutations=mutations,
            baseline_metrics=baseline_metrics,
            handoffiq_metrics=handoffiq_metrics,
            comparison=met.get("comparison"),
            limitations=cfg.get("limitations", []),
            statistical_significance=cfg.get("statistical_significance"),
            created_at=exp.created_at,
            completed_at=exp.completed_at,
            experiment=exp,
        )


@router.post(
    "",
    response_model=CreateExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and queue an evaluation experiment",
    description="Registers a Mutation Lab experiment comparing baseline and HandoffIQ pipelines under controlled mutations.",
)
async def create_experiment(
    payload: CreateExperimentRequest,
    service: MutationLabService = Depends(get_mutation_lab_service),
) -> CreateExperimentResponse:
    """Create, configure, and queue an evaluation experiment."""
    experiment = await service.create_experiment(
        task_id=payload.task_id,
        mutation_types=payload.mutation_types,
        runs=payload.runs,
    )
    return CreateExperimentResponse(
        experiment_id=experiment.id,
        status="queued",
        message="Experiment queued",
    )


@router.get(
    "/{experiment_id}",
    response_model=ExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve experiment outcome and metrics",
    description="Retrieve recorded baseline and HandoffIQ metrics, mutation details, and experimental limitations.",
)
async def get_experiment(
    experiment_id: UUID,
    service: MutationLabService = Depends(get_mutation_lab_service),
) -> ExperimentDetailResponse:
    """Retrieve full experiment details and comparison metrics."""
    experiment = await service.get_experiment(experiment_id)
    return ExperimentDetailResponse.from_experiment(experiment)
