"""Comprehensive tests for all shared Pydantic v2 schemas and validation constraints."""

from datetime import datetime, timezone
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from app.models import (
    AgentRun,
    AgentRunStatus,
    AgentType,
    CodeArtifact,
    Experiment,
    ExperimentStatus,
    Handoff,
    HandoffStatus,
    IssueSeverity,
    IssueType,
    RecoveryAttempt,
    RecoveryStatus,
    RepairStatus,
    Requirement,
    RequirementPriority,
    RequirementStatus,
    Task,
    TaskStatus,
    TestResult,
    TestStatus,
    ValidationIssue,
    WorkflowEvent,
    ensure_utc,
)


# ============================================================================
# Task Model Tests
# ============================================================================

def test_task_creation_valid() -> None:
    """Verify task instantiates with valid data and default values."""
    task = Task(
        title="Implement Auth Flow",
        original_request="Create Supabase JWT auth integration",
    )
    assert isinstance(task.id, UUID)
    assert task.title == "Implement Auth Flow"
    assert task.status == TaskStatus.queued
    assert task.progress == 0
    assert task.created_at.tzinfo == timezone.utc
    assert task.updated_at.tzinfo == timezone.utc


def test_task_progress_boundaries() -> None:
    """Verify progress allows 0 and 100, but rejects < 0 and > 100."""
    # Valid boundaries
    task_min = Task(title="T1", original_request="Req", progress=0)
    assert task_min.progress == 0
    task_max = Task(title="T2", original_request="Req", progress=100)
    assert task_max.progress == 100

    # Below minimum
    with pytest.raises(ValidationError) as exc_info:
        Task(title="T3", original_request="Req", progress=-1)
    assert "greater than or equal to 0" in str(exc_info.value)

    # Above maximum
    with pytest.raises(ValidationError) as exc_info:
        Task(title="T4", original_request="Req", progress=101)
    assert "less than or equal to 100" in str(exc_info.value)


def test_task_status_enum_validation() -> None:
    """Verify valid task statuses and rejection of invalid enum values."""
    valid_statuses = ["queued", "running", "completed", "failed", "awaiting_review", "cancelled"]
    for s in valid_statuses:
        task = Task(title="T", original_request="R", status=s)
        assert task.status == s

    with pytest.raises(ValidationError):
        Task(title="T", original_request="R", status="invalid_status")


def test_task_serialization_json() -> None:
    """Verify UUID and datetime serialization in JSON mode."""
    task = Task(title="Serialization Test", original_request="Verify JSON output")
    dump = task.model_dump(mode="json")
    assert isinstance(dump["id"], str)
    assert isinstance(dump["created_at"], str)
    assert dump["status"] == "queued"


# ============================================================================
# Requirement Model Tests
# ============================================================================

def test_requirement_valid() -> None:
    """Verify valid requirement instantiation."""
    task_id = uuid4()
    req = Requirement(
        id="R001",
        task_id=task_id,
        original_text="System must sanitize all user inputs.",
        priority=RequirementPriority.high,
        status=RequirementStatus.registered,
        description="SQL injection and XSS prevention",
        related_files=["backend/app/core/security.py"],
        related_test_ids=["TEST-01"],
    )
    assert req.id == "R001"
    assert req.task_id == task_id
    assert req.original_text == "System must sanitize all user inputs."
    assert req.priority == RequirementPriority.high


def test_requirement_id_pattern() -> None:
    """Verify requirement ID must conform to pattern like R001."""
    task_id = uuid4()
    # Valid IDs
    assert Requirement(id="R001", task_id=task_id, original_text="Text").id == "R001"
    assert Requirement(id="R100", task_id=task_id, original_text="Text").id == "R100"
    assert Requirement(id="R9999", task_id=task_id, original_text="Text").id == "R9999"

    # Invalid IDs
    with pytest.raises(ValidationError):
        Requirement(id="INVALID", task_id=task_id, original_text="Text")

    with pytest.raises(ValidationError):
        Requirement(id="123", task_id=task_id, original_text="Text")


def test_requirement_original_text_immutable() -> None:
    """Verify original_text is frozen and cannot be modified after instantiation."""
    task_id = uuid4()
    req = Requirement(id="R001", task_id=task_id, original_text="Immutable constraint")
    with pytest.raises(ValidationError):
        req.original_text = "Modified constraint"


def test_requirement_enums() -> None:
    """Verify RequirementPriority and RequirementStatus enums."""
    task_id = uuid4()
    for p in ["low", "medium", "high", "critical"]:
        req = Requirement(id="R001", task_id=task_id, original_text="T", priority=p)
        assert req.priority == p

    with pytest.raises(ValidationError):
        Requirement(id="R001", task_id=task_id, original_text="T", priority="ultra_high")

    for s in [
        "registered", "preserved", "altered", "missing", "conflicting",
        "implemented", "tested", "verified", "failed", "awaiting_review"
    ]:
        req = Requirement(id="R001", task_id=task_id, original_text="T", status=s)
        assert req.status == s

    with pytest.raises(ValidationError):
        Requirement(id="R001", task_id=task_id, original_text="T", status="non_existent")


# ============================================================================
# AgentRun Model Tests
# ============================================================================

def test_agent_run_valid() -> None:
    """Verify agent run creation and enum validations."""
    task_id = uuid4()
    run = AgentRun(
        task_id=task_id,
        agent_type=AgentType.researcher,
        status=AgentRunStatus.running,
        started_at=datetime.now(timezone.utc),
        summary="Gathering API documentation",
    )
    assert run.agent_type == "researcher"
    assert run.status == "running"
    assert run.summary == "Gathering API documentation"


def test_agent_run_enums() -> None:
    """Verify AgentType and AgentRunStatus rejection of invalid values."""
    task_id = uuid4()
    for t in ["researcher", "coder", "tester", "reviewer"]:
        assert AgentRun(task_id=task_id, agent_type=t).agent_type == t

    with pytest.raises(ValidationError):
        AgentRun(task_id=task_id, agent_type="hacker")

    for s in ["queued", "running", "completed", "failed", "awaiting_review"]:
        assert AgentRun(task_id=task_id, agent_type="coder", status=s).status == s

    with pytest.raises(ValidationError):
        AgentRun(task_id=task_id, agent_type="coder", status="aborted")


# ============================================================================
# ValidationIssue & Handoff Model Tests
# ============================================================================

def test_validation_issue_and_handoff() -> None:
    """Verify handoff containing validation issues."""
    task_id = uuid4()
    issue = ValidationIssue(
        requirement_id="R001",
        issue_type=IssueType.semantic_drift,
        severity=IssueSeverity.high,
        description="Changed password requirement from 12 chars to 6 chars",
        original_value=">= 12 characters",
        observed_value=">= 6 characters",
        repair_status=RepairStatus.pending,
        evidence=["auth_service.py line 42"],
    )
    assert issue.issue_type == "semantic_drift"
    assert issue.severity == "high"
    assert issue.repair_status == "pending"

    handoff = Handoff(
        task_id=task_id,
        source_agent="researcher",
        target_agent="coder",
        status=HandoffStatus.validated,
        requirement_ids=["R001"],
        payload={"spec": "architecture_v1.md"},
        issues=[issue],
    )
    assert handoff.source_agent == "researcher"
    assert handoff.target_agent == "coder"
    assert len(handoff.issues) == 1
    assert handoff.issues[0].id == issue.id

    # Test serialization to JSON
    dump = handoff.model_dump(mode="json")
    assert isinstance(dump["id"], str)
    assert isinstance(dump["task_id"], str)
    assert isinstance(dump["created_at"], str)


def test_issue_type_and_severity_enums() -> None:
    """Verify validation of issue types and severities."""
    for it in [
        "omission", "semantic_drift", "weakened_constraint", "contradiction",
        "invented_requirement", "suspicious_instruction", "schema_error",
        "implementation_gap", "test_failure"
    ]:
        issue = ValidationIssue(issue_type=it, severity="medium", description="desc")
        assert issue.issue_type == it

    with pytest.raises(ValidationError):
        ValidationIssue(issue_type="unknown_issue", severity="low", description="desc")


# ============================================================================
# CodeArtifact, TestResult, RecoveryAttempt Tests
# ============================================================================

def test_code_artifact_validation() -> None:
    """Verify CodeArtifact fields and version boundary constraint."""
    task_id = uuid4()
    artifact = CodeArtifact(
        task_id=task_id,
        path="src/index.ts",
        language="typescript",
        content="console.log('hello');",
        requirement_ids=["R001"],
        version=1,
    )
    assert artifact.version == 1

    # Version must be >= 1
    with pytest.raises(ValidationError):
        CodeArtifact(
            task_id=task_id,
            path="src/index.ts",
            language="typescript",
            content="test",
            version=0,
        )


def test_test_result_validation() -> None:
    """Verify TestResult enums and optional duration."""
    task_id = uuid4()
    res = TestResult(
        task_id=task_id,
        requirement_ids=["R001"],
        test_name="test_password_length",
        tool="pytest",
        status=TestStatus.passed,
        output="1 passed in 0.04s",
        duration_ms=40,
    )
    assert res.status == "passed"
    assert res.duration_ms == 40

    # Duration must be >= 0
    with pytest.raises(ValidationError):
        TestResult(
            task_id=task_id,
            test_name="t",
            tool="tool",
            status="passed",
            duration_ms=-5,
        )


def test_recovery_attempt_validation() -> None:
    """Verify RecoveryAttempt schema and attempt number."""
    task_id = uuid4()
    rec = RecoveryAttempt(
        task_id=task_id,
        requirement_ids=["R001"],
        failure_summary="Test assertion failed on line 20",
        repair_summary="Increased min character length to 12",
        status=RecoveryStatus.succeeded,
        attempt_number=1,
        test_result_ids=["TR-101"],
    )
    assert rec.status == "succeeded"
    assert rec.attempt_number == 1

    # Attempt number must be >= 1
    with pytest.raises(ValidationError):
        RecoveryAttempt(
            task_id=task_id,
            failure_summary="Failed",
            attempt_number=0,
        )


# ============================================================================
# WorkflowEvent & Experiment Tests
# ============================================================================

def test_workflow_event() -> None:
    """Verify WorkflowEvent instantiation and timestamp timezone."""
    task_id = uuid4()
    event = WorkflowEvent(
        task_id=task_id,
        event_type="stage_transition",
        stage="architecture_review",
        message="Transitioning from research to implementation",
        metadata={"user": "farhan"},
    )
    assert event.event_type == "stage_transition"
    assert event.timestamp.tzinfo == timezone.utc
    dump = event.model_dump(mode="json")
    assert isinstance(dump["timestamp"], str)


def test_experiment_validation() -> None:
    """Verify Experiment model and ExperimentStatus enum."""
    exp = Experiment(
        name="Prompt Drift Evaluation",
        description="Comparing strict requirement prompt vs baseline prompt",
        status=ExperimentStatus.running,
        configuration={"model": "gemini-1.5-pro", "temperature": 0.2},
        metrics={"drift_rate": 0.05},
    )
    assert exp.status == "running"
    assert exp.metrics["drift_rate"] == 0.05

    with pytest.raises(ValidationError):
        Experiment(name="Test", status="invalid_status")
