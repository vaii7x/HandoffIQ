"""Tests for Supabase repositories, configuration failure handling, and error mapping."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4
import pytest

from app.core.config import Settings
from app.core.errors import (
    ConfigurationError,
    DatabaseError,
    EntityNotFoundError,
    TaskNotFoundError,
)
from app.core.supabase import validate_supabase_config
from app.models.event import WorkflowEvent
from app.models.handoff import Handoff, HandoffStatus, IssueSeverity, IssueType, ValidationIssue
from app.models.requirement import Requirement, RequirementPriority, RequirementStatus
from app.models.task import Task, TaskStatus
from app.repositories.in_memory import (
    InMemoryTaskRepository,
    get_task_repository,
)
from app.repositories.handoff_repository import (
    InMemoryHandoffRepository,
    get_handoff_repository,
)
from app.repositories.supabase_handoff_repo import SupabaseHandoffRepository
from app.repositories.supabase_task_repo import (
    SupabaseTaskRepository,
    _handle_db_exception,
)


# ============================================================================
# 1. Configuration Failure & Switching Tests
# ============================================================================

def test_validate_supabase_config_fails_when_mock_mode_false_and_placeholder() -> None:
    """Verify validate_supabase_config raises ConfigurationError if credentials are placeholders."""
    settings = Settings(
        MOCK_MODE=False,
        SUPABASE_URL="https://placeholder-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="placeholder-service-role-key",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        validate_supabase_config(settings)
    assert "strictly required when MOCK_MODE is disabled" in str(exc_info.value)


def test_validate_supabase_config_allows_mock_mode() -> None:
    """Verify validate_supabase_config passes freely when MOCK_MODE is true."""
    settings = Settings(
        MOCK_MODE=True,
        SUPABASE_URL="https://placeholder-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="placeholder-service-role-key",
    )
    # Should not raise
    validate_supabase_config(settings)


def test_repository_switching_in_mock_mode() -> None:
    """Verify get_task_repository and get_handoff_repository return in-memory stores in mock mode."""
    task_repo = get_task_repository()
    assert isinstance(task_repo, InMemoryTaskRepository)

    handoff_repo = get_handoff_repository()
    assert isinstance(handoff_repo, InMemoryHandoffRepository)


# ============================================================================
# 2. Database Exception Translation Tests
# ============================================================================

def test_handle_db_exception_constraint_violation() -> None:
    """Verify duplicate key exception is translated to 409 CONSTRAINT_VIOLATION."""
    with pytest.raises(DatabaseError) as exc_info:
        _handle_db_exception(Exception("duplicate key value violates unique constraint"), "insert")
    assert exc_info.value.code == "CONSTRAINT_VIOLATION"
    assert exc_info.value.status_code == 409


def test_handle_db_exception_timeout() -> None:
    """Verify connection timeout is translated to 503 DATABASE_TIMEOUT."""
    with pytest.raises(DatabaseError) as exc_info:
        _handle_db_exception(Exception("Query execution timed out after 30000ms"), "select")
    assert exc_info.value.code == "DATABASE_TIMEOUT"
    assert exc_info.value.status_code == 503


def test_handle_db_exception_connection_error() -> None:
    """Verify network connection failure is translated to 503 DATABASE_CONNECTION_ERROR."""
    with pytest.raises(DatabaseError) as exc_info:
        _handle_db_exception(Exception("Failed to connect to host db.supabase.co"), "connect")
    assert exc_info.value.code == "DATABASE_CONNECTION_ERROR"
    assert exc_info.value.status_code == 503


def test_handle_db_exception_generic() -> None:
    """Verify unknown database error is translated to 500 DATABASE_ERROR."""
    with pytest.raises(DatabaseError) as exc_info:
        _handle_db_exception(Exception("Unrecognized internal postgres error"), "query")
    assert exc_info.value.code == "DATABASE_ERROR"
    assert exc_info.value.status_code == 500


# ============================================================================
# 3. Mocked Supabase Task Repository Tests
# ============================================================================

class MockQueryResponse:
    def __init__(self, data):
        self.data = data


class MockTableQuery:
    def __init__(self, data=None):
        self._data = data if data is not None else []

    def select(self, *args, **kwargs):
        return self

    def insert(self, rows, *args, **kwargs):
        if isinstance(rows, list):
            self._data = rows
        else:
            self._data = [rows]
        return self

    def update(self, values, *args, **kwargs):
        if self._data and isinstance(self._data[0], dict):
            updated_row = dict(self._data[0])
            updated_row.update(values)
            self._data = [updated_row]
        else:
            self._data = [values]
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        return MockQueryResponse(self._data)


class MockSupabaseClient:
    def __init__(self):
        self.tables = {}

    def table(self, name: str):
        if name not in self.tables:
            self.tables[name] = MockTableQuery()
        return self.tables[name]


@pytest.mark.anyio
async def test_supabase_task_repo_create_and_get() -> None:
    """Verify SupabaseTaskRepository create_task and get_task with mocked client."""
    mock_client = MockSupabaseClient()
    task_id = uuid4()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Pre-populate table mock response for insert & select
    mock_client.table("tasks")._data = [
        {
            "id": str(task_id),
            "title": "Expense App",
            "original_request": "Build expense app",
            "status": "queued",
            "current_stage": "registration",
            "progress": 0,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    ]

    repo = SupabaseTaskRepository(client=mock_client)
    task = Task(
        id=task_id,
        title="Expense App",
        original_request="Build expense app",
    )
    created = await repo.create_task(task)
    assert created.id == task_id
    assert created.title == "Expense App"

    fetched = await repo.get_task(task_id)
    assert fetched is not None
    assert fetched.id == task_id
    assert fetched.original_request == "Build expense app"


@pytest.mark.anyio
async def test_supabase_task_repo_sequential_req_id() -> None:
    """Verify get_next_requirement_id computes R001, R002 based on existing database rows."""
    mock_client = MockSupabaseClient()
    task_id = uuid4()

    # Initially empty requirements
    mock_client.table("requirements")._data = []
    repo = SupabaseTaskRepository(client=mock_client)
    assert await repo.get_next_requirement_id(task_id) == "R001"

    # Pre-populate existing R001, R002
    mock_client.table("requirements")._data = [
        {"id": "R001"},
        {"id": "R002"},
    ]
    assert await repo.get_next_requirement_id(task_id) == "R003"


@pytest.mark.anyio
async def test_supabase_task_repo_update_requirement_preserves_original_text() -> None:
    """Verify update_requirement preserves immutable original_text even if modified."""
    mock_client = MockSupabaseClient()
    task_id = uuid4()
    original_wording = "Must encrypt all user passwords"

    # Pre-populate existing requirement in mock
    mock_client.table("requirements")._data = [
        {
            "id": "R001",
            "task_id": str(task_id),
            "original_text": original_wording,
            "priority": "high",
            "status": "registered",
            "description": "Initial spec",
            "related_files": [],
            "related_test_ids": [],
        }
    ]

    repo = SupabaseTaskRepository(client=mock_client)
    req_update = Requirement(
        id="R001",
        task_id=task_id,
        original_text=original_wording,
        status=RequirementStatus.implemented,
        description="Updated implementation note",
    )

    updated = await repo.update_requirement(task_id, req_update)
    assert updated.original_text == original_wording
    assert updated.status == RequirementStatus.implemented


# ============================================================================
# 4. Mocked Supabase Handoff Repository Tests
# ============================================================================

@pytest.mark.anyio
async def test_supabase_handoff_repo_create_and_get() -> None:
    """Verify SupabaseHandoffRepository creates and retrieves handoff with child issues."""
    mock_client = MockSupabaseClient()
    task_id = uuid4()
    handoff_id = uuid4()
    now_iso = datetime.now(timezone.utc).isoformat()

    mock_client.table("handoffs")._data = [
        {
            "id": str(handoff_id),
            "task_id": str(task_id),
            "source_agent": "researcher",
            "target_agent": "coder",
            "status": "validated",
            "requirement_ids": ["R001"],
            "payload": {"context": "spec.md"},
            "created_at": now_iso,
        }
    ]

    mock_client.table("validation_issues")._data = [
        {
            "id": "ISSUE-12345678",
            "handoff_id": str(handoff_id),
            "requirement_id": "R001",
            "issue_type": "semantic_drift",
            "severity": "high",
            "description": "Minor drift",
            "repair_status": "unresolved",
            "evidence": ["Evidence snippet"],
        }
    ]

    repo = SupabaseHandoffRepository(client=mock_client)
    issue = ValidationIssue(
        id="ISSUE-12345678",
        requirement_id="R001",
        issue_type=IssueType.semantic_drift,
        severity=IssueSeverity.high,
        description="Minor drift",
        evidence=["Evidence snippet"],
    )
    handoff = Handoff(
        id=handoff_id,
        task_id=task_id,
        source_agent="researcher",
        target_agent="coder",
        status=HandoffStatus.validated,
        requirement_ids=["R001"],
        payload={"context": "spec.md"},
        issues=[issue],
    )

    created = await repo.create_handoff(handoff)
    assert created.id == handoff_id
    assert created.status == HandoffStatus.validated

    fetched = await repo.get_handoff(handoff_id)
    assert fetched is not None
    assert fetched.id == handoff_id
    assert len(fetched.issues) == 1
    assert fetched.issues[0].id == "ISSUE-12345678"
