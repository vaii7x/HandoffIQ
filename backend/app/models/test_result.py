"""TestResult domain schema."""

from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import Field
from app.models.common import HandoffIQBaseModel


class TestStatus(str, Enum):
    """Execution status for a test case."""

    __test__ = False

    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    error = "error"


class TestResult(HandoffIQBaseModel):
    """Outcome of a test executed to verify requirements."""

    __test__ = False

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this test result"
    )
    task_id: UUID = Field(
        ...,
        description="Associated task identifier"
    )
    requirement_ids: List[str] = Field(
        default_factory=list,
        description="Requirement identifiers validated by this test"
    )
    test_name: str = Field(
        ...,
        min_length=1,
        description="Name or identifier of the test"
    )
    tool: str = Field(
        ...,
        min_length=1,
        description="Testing framework or runner utilized (e.g. pytest, jest)"
    )
    test_type: str = Field(
        default="unit_test",
        description="Classification: compilation, linting, unit_test, integration_test, browser_test"
    )
    status: TestStatus = Field(
        ...,
        description="Result status of the test execution"
    )
    output: str = Field(
        default="",
        description="Test execution logs, stack traces, or console output"
    )
    duration_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Duration of the test execution in milliseconds"
    )
