"""Abstract interfaces and models for isolated test execution and runner adapters."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.test_result import TestResult, TestStatus


class TestType(str, Enum):
    """Classification of test execution."""

    compilation = "compilation"
    linting = "linting"
    unit_test = "unit_test"
    integration_test = "integration_test"
    browser_test = "browser_test"


class IsolationLevel(str, Enum):
    """Tier of process/sandbox isolation applied."""

    disabled = "disabled"
    mock_sandbox = "mock_sandbox"
    process_restricted = "process_restricted"
    container = "container"


class TestExecutionConfig(BaseModel):
    """Configuration provided to an isolated test runner invocation."""

    workspace_path: str = Field(description="Canonical path to the project workspace")
    tool: str = Field(default="pytest", description="Test runner tool name")
    test_type: str = Field(
        default=TestType.unit_test.value,
        description="Classification: compilation, linting, unit_test, integration_test, browser_test",
    )
    timeout_seconds: int = Field(default=30, ge=1, description="Execution timeout in seconds")
    test_paths: Optional[List[str]] = Field(
        default=None, description="Specific test files or test paths to target"
    )
    extra_env: Dict[str, str] = Field(
        default_factory=dict, description="Safe environment variable additions"
    )
    isolated_sandbox: bool = Field(
        default=True, description="Enforce process isolation and secret stripping"
    )
    command_override: Optional[List[str]] = Field(
        default=None, description="Explicit test command arguments override"
    )


class TestExecutionResult(BaseModel):
    """Summary outcome of a test suite execution run."""

    tool: str = Field(description="Tool used (pytest, npm_test, playwright, etc.)")
    test_type: str = Field(description="Classification of test")
    exit_code: int = Field(description="Process exit code")
    results: List[TestResult] = Field(
        default_factory=list, description="Extracted individual test results"
    )
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    duration_ms: int = Field(default=0, ge=0, description="Total execution duration in milliseconds")
    isolation_level: str = Field(
        default=IsolationLevel.process_restricted.value,
        description="Applied isolation level ('disabled', 'mock_sandbox', 'process_restricted', 'container')",
    )
    sandbox_error: Optional[str] = Field(
        default=None, description="Error explanation if sandbox execution failed or was disabled"
    )
    is_sandbox_disabled: bool = Field(
        default=False, description="Flag indicating execution was blocked due to sandbox unavailability"
    )


class TestRunner(ABC):
    """Interface for isolated project test runners."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the test runner."""
        pass

    @abstractmethod
    def supports_project(self, workspace_path: str) -> bool:
        """Determine whether this runner can execute tests in the given workspace."""
        pass

    @abstractmethod
    async def run_tests(
        self,
        config: TestExecutionConfig,
        requirement_ids: List[str],
        task_id: Optional[Any] = None,
    ) -> TestExecutionResult:
        """Execute tests in an isolated environment and parse results."""
        pass
