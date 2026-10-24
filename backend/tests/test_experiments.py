"""Tests for Mutation Lab evaluation, metrics calculation, and experiment APIs."""

import asyncio
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.models.experiment import MutationType
from app.repositories.experiment_repository import _in_memory_experiment_repository
from app.repositories.handoff_repository import _in_memory_handoff_repository
from app.repositories.in_memory import _in_memory_repository
from app.services.mutation_lab import get_experiment_manager
from app.services.mutation_lab.mutations import SUPPORTED_MUTATION_TYPES


@pytest.fixture(autouse=True)
def reset_in_memory_state() -> None:
    """Clear repositories and manager jobs before each test."""
    _in_memory_repository._tasks.clear()
    _in_memory_repository._requirements.clear()
    _in_memory_repository._events.clear()
    _in_memory_repository._agent_runs.clear()
    _in_memory_repository._req_counters.clear()
    _in_memory_handoff_repository._handoffs.clear()
    _in_memory_handoff_repository._task_index.clear()
    _in_memory_experiment_repository._experiments.clear()

    manager = get_experiment_manager()
    manager._running_experiments.clear()
    manager._active_jobs.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_task(client: TestClient) -> dict:
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Secure Financial Dashboard",
            "original_request": "Build a responsive financial dashboard with JWT auth and a dark theme.",
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ============================================================================
# 1. Experiment Creation Tests
# ============================================================================

def test_experiment_creation_contract(client: TestClient, sample_task: dict) -> None:
    """Verify POST /api/experiments response structure exactly matches agreed contract."""
    task_id = sample_task["task"]["id"]

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": task_id,
            "mutation_types": ["missing_requirement", "weakened_constraint"],
            "runs": 1,
        },
    )
    assert resp.status_code == 201
    data = resp.json()

    assert "experiment_id" in data
    assert UUID(data["experiment_id"])
    assert data["status"] == "queued"
    assert data["message"] == "Experiment queued"


def test_experiment_creation_invalid_mutation_type(client: TestClient, sample_task: dict) -> None:
    """Verify invalid mutation types are rejected with 422 Unprocessable Entity."""
    task_id = sample_task["task"]["id"]

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": task_id,
            "mutation_types": ["missing_requirement", "completely_unknown_mutation"],
            "runs": 1,
        },
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_MUTATION_TYPE"


def test_experiment_creation_empty_mutation_types(client: TestClient, sample_task: dict) -> None:
    """Verify empty mutation_types list is rejected with 422."""
    task_id = sample_task["task"]["id"]

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": task_id,
            "mutation_types": [],
            "runs": 1,
        },
    )
    assert resp.status_code == 422


def test_experiment_creation_missing_task(client: TestClient) -> None:
    """Verify experiment creation against a non-existent task fails with 404."""
    non_existent_id = str(uuid4())

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": non_existent_id,
            "mutation_types": ["missing_requirement"],
            "runs": 1,
        },
    )
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "TASK_NOT_FOUND"


# ============================================================================
# 2. Experiment Execution & Metric Calculation Tests
# ============================================================================

@pytest.mark.anyio
async def test_metric_calculation_and_baseline_handoffiq_separation(
    client: TestClient, sample_task: dict
) -> None:
    """Verify baseline and HandoffIQ outcomes are separated with actual measurements and clear repair results."""
    task_id = UUID(sample_task["task"]["id"])
    manager = get_experiment_manager()

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": str(task_id),
            "mutation_types": ["missing_requirement"],
            "runs": 2,
        },
    )
    assert resp.status_code == 201
    exp_id = UUID(resp.json()["experiment_id"])

    # Await background evaluation
    await manager.wait_for_completion(exp_id, timeout=10.0)

    # Retrieve experiment
    get_resp = client.get(f"/api/experiments/{exp_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["status"] == "completed"
    assert data["runs"] == 2
    assert "completed_at" in data and data["completed_at"] is not None

    # Verify Baseline Metrics separation
    baseline = data["baseline_metrics"]
    assert baseline is not None
    # In baseline, missing requirement was omitted and never repaired
    assert baseline["requirement_preservation_rate"] < 1.0
    assert baseline["errors_detected"] == 0
    assert baseline["error_detection_rate"] == 0.0
    assert baseline["false_positives"] == 0
    assert baseline["repair_outcomes"]["attempted"] == 0
    assert baseline["repair_outcomes"]["successful"] == 0
    assert baseline["task_success"] is False  # Failed due to missing canonical requirement

    # Verify HandoffIQ Metrics separation
    hiq = data["handoffiq_metrics"]
    assert hiq is not None
    # In HandoffIQ, omission was detected and automatically repaired
    assert hiq["requirement_preservation_rate"] == 1.0
    assert hiq["errors_detected"] >= 1
    assert hiq["error_detection_rate"] > 0.0
    assert hiq["false_positives"] == 0
    assert hiq["repair_outcomes"]["attempted"] >= 1
    assert hiq["repair_outcomes"]["successful"] >= 1
    assert hiq["task_success"] is True

    # Verify Comparison
    comparison = data["comparison"]
    assert comparison is not None
    assert comparison["preservation_improvement"] > 0
    assert comparison["error_detection_advantage"] >= 1
    assert comparison["repairs_performed"] >= 1


# ============================================================================
# 3. Mock-Mode Labeling & Actual vs Unavailable Metrics Tests
# ============================================================================

@pytest.mark.anyio
async def test_mock_mode_labeling_and_unavailable_token_metrics(
    client: TestClient, sample_task: dict
) -> None:
    """Verify mock-mode simulation flag and non-fabricated token metrics."""
    task_id = UUID(sample_task["task"]["id"])
    manager = get_experiment_manager()

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": str(task_id),
            "mutation_types": ["weakened_constraint"],
            "runs": 1,
        },
    )
    exp_id = UUID(resp.json()["experiment_id"])
    await manager.wait_for_completion(exp_id, timeout=10.0)

    data = client.get(f"/api/experiments/{exp_id}").json()

    # 1. Verify mock-mode labeling
    assert data["is_simulated"] is True
    assert any("simulated mock mode" in limit for limit in data["limitations"])

    # 2. Verify actual measured latency (wall clock time > 0)
    assert data["baseline_metrics"]["latency_ms"] >= 0.0
    assert data["handoffiq_metrics"]["latency_ms"] >= 0.0

    # 3. Verify token usage is explicitly UNAVAILABLE, not fabricated
    baseline_token = data["baseline_metrics"]["token_usage"]
    assert baseline_token["status"] == "unavailable"
    assert baseline_token["total_tokens"] is None
    assert baseline_token["prompt_tokens"] is None
    assert baseline_token["completion_tokens"] is None

    hiq_token = data["handoffiq_metrics"]["token_usage"]
    assert hiq_token["status"] == "unavailable"
    assert hiq_token["total_tokens"] is None


# ============================================================================
# 4. Statistical Significance & Limitations Documentation Tests
# ============================================================================

@pytest.mark.anyio
async def test_statistical_significance_warning_and_limitations(
    client: TestClient, sample_task: dict
) -> None:
    """Verify that insufficient runs (<30) explicitly report lack of statistical significance."""
    task_id = UUID(sample_task["task"]["id"])
    manager = get_experiment_manager()

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": str(task_id),
            "mutation_types": ["contradiction"],
            "runs": 2,
        },
    )
    exp_id = UUID(resp.json()["experiment_id"])
    await manager.wait_for_completion(exp_id, timeout=10.0)

    data = client.get(f"/api/experiments/{exp_id}").json()

    # Statistical significance checks
    stat = data["statistical_significance"]
    assert stat is not None
    assert stat["has_statistical_significance"] is False
    assert stat["sample_size"] == 2
    assert "Insufficient sample size" in stat["note"]

    # Explicit limitations documentation
    limitations = data["limitations"]
    assert len(limitations) >= 4
    assert any("Statistical significance" in l for l in limitations)
    assert any("deterministic synthetic fixtures" in l.lower() for l in limitations)
    assert any("Token usage telemetry" in l for l in limitations)


# ============================================================================
# 5. All 6 Mutation Types Verification Tests
# ============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("mut_type", SUPPORTED_MUTATION_TYPES)
async def test_all_supported_mutation_types(
    client: TestClient, sample_task: dict, mut_type: str
) -> None:
    """Verify that all 6 required mutation types execute, record audit entries, and measure outcomes."""
    task_id = UUID(sample_task["task"]["id"])
    manager = get_experiment_manager()

    resp = client.post(
        "/api/experiments",
        json={
            "task_id": str(task_id),
            "mutation_types": [mut_type],
            "runs": 1,
        },
    )
    assert resp.status_code == 201
    exp_id = UUID(resp.json()["experiment_id"])
    await manager.wait_for_completion(exp_id, timeout=10.0)

    data = client.get(f"/api/experiments/{exp_id}").json()
    assert data["status"] == "completed"

    mutations = data["mutations"]
    assert len(mutations) >= 1
    record = mutations[0]
    assert record["mutation_type"] == mut_type
    assert "mutated_value" in record
    assert "expected_detection_outcome" in record
    assert record["expected_detection_outcome"]["should_detect"] is True


def test_get_unknown_experiment_404(client: TestClient) -> None:
    """Verify GET /api/experiments/{experiment_id} returns 404 for unknown experiment ID."""
    unknown_id = str(uuid4())
    resp = client.get(f"/api/experiments/{unknown_id}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "EXPERIMENT_NOT_FOUND"
