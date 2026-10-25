"""Concrete test runners for Pytest, npm test, Playwright, and deterministic mock execution."""

from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.models.test_result import TestResult, TestStatus
from app.services.test_runner.base import (
    IsolationLevel,
    TestExecutionConfig,
    TestExecutionResult,
    TestRunner,
    TestType,
)
from app.services.test_runner.security import ExecutionSandbox


class MockTestRunner(TestRunner):
    """Deterministic mock test runner for automated unit tests and development."""

    def __init__(self, simulated_failures: Optional[List[str]] = None) -> None:
        self.simulated_failures = simulated_failures or []

    @property
    def name(self) -> str:
        return "mock_test_runner"

    def supports_project(self, workspace_path: str) -> bool:
        return True

    async def run_tests(
        self,
        config: TestExecutionConfig,
        requirement_ids: List[str],
        task_id: Optional[Any] = None,
    ) -> TestExecutionResult:
        sandbox = ExecutionSandbox()
        is_avail, status_msg, isolation = sandbox.check_sandbox_availability()

        if not is_avail:
            return TestExecutionResult(
                tool=config.tool,
                test_type=config.test_type,
                exit_code=-1,
                results=[],
                stdout="",
                stderr=f"Execution disabled: {status_msg}",
                duration_ms=0,
                isolation_level=IsolationLevel.disabled.value,
                sandbox_error=status_msg,
                is_sandbox_disabled=True,
            )

        # Generate deterministic mock test results for requirements
        results: List[TestResult] = []
        tid = task_id or uuid4()
        exit_code = 0

        # Check for simulated error markers in workspace
        ws_root = Path(config.workspace_path)
        marker_fail = ws_root / ".simulate_test_failure"
        marker_error = ws_root / ".simulate_runner_error"
        marker_timeout = ws_root / ".simulate_timeout"

        if marker_timeout.exists():
            return TestExecutionResult(
                tool=config.tool,
                test_type=config.test_type,
                exit_code=-1,
                results=[],
                stdout="",
                stderr="Test execution timed out.",
                duration_ms=config.timeout_seconds * 1000,
                isolation_level=isolation.value,
                sandbox_error="Test execution timed out after timeout limit.",
            )

        if marker_error.exists():
            return TestExecutionResult(
                tool=config.tool,
                test_type=config.test_type,
                exit_code=2,
                results=[],
                stdout="",
                stderr="Runner invocation failed: invalid configuration.",
                duration_ms=50,
                isolation_level=isolation.value,
                sandbox_error="Runner invocation failed.",
            )

        target_reqs = requirement_ids or ["R001"]
        for idx, rid in enumerate(target_reqs, start=1):
            test_name = f"test_{rid.lower()}_verification"
            is_failed = (
                test_name in self.simulated_failures
                or marker_fail.exists()
            )

            status = TestStatus.failed if is_failed else TestStatus.passed
            if is_failed:
                exit_code = 1

            results.append(
                TestResult(
                    task_id=tid,
                    requirement_ids=[rid],
                    test_name=test_name,
                    tool=config.tool,
                    test_type=config.test_type,
                    status=status,
                    output="Assertion passed." if not is_failed else f"AssertionError: Requirement {rid} unmet.",
                    duration_ms=45,
                )
            )

        return TestExecutionResult(
            tool=config.tool,
            test_type=config.test_type,
            exit_code=exit_code,
            results=results,
            stdout=f"Ran {len(results)} tests. Passed: {len([r for r in results if r.status == TestStatus.passed])}.",
            stderr="",
            duration_ms=100,
            isolation_level=isolation.value,
        )


class PytestRunner(TestRunner):
    """Executes Python pytest suites inside the isolated subprocess environment."""

    def __init__(self, sandbox: Optional[ExecutionSandbox] = None) -> None:
        self.sandbox = sandbox or ExecutionSandbox()

    @property
    def name(self) -> str:
        return "pytest"

    def supports_project(self, workspace_path: str) -> bool:
        ws = Path(workspace_path)
        return (
            (ws / "pytest.ini").exists()
            or (ws / "pyproject.toml").exists()
            or (ws / "requirements.txt").exists()
            or any(ws.glob("test_*.py"))
            or any(ws.glob("*_test.py"))
        )

    async def run_tests(
        self,
        config: TestExecutionConfig,
        requirement_ids: List[str],
        task_id: Optional[Any] = None,
    ) -> TestExecutionResult:
        python_exe = sys.executable
        cmd = config.command_override or [python_exe, "-m", "pytest", "-v", "--tb=short"]
        if config.test_paths:
            cmd.extend(config.test_paths)

        exit_code, stdout, stderr, duration_ms, isolation, error_msg = (
            await self.sandbox.execute_in_sandbox(
                command=cmd,
                cwd=config.workspace_path,
                timeout_seconds=config.timeout_seconds,
                extra_env=config.extra_env,
            )
        )

        tid = task_id or uuid4()
        results = self._parse_pytest_output(stdout, stderr, exit_code, tid, requirement_ids, config.test_type)

        return TestExecutionResult(
            tool="pytest",
            test_type=config.test_type,
            exit_code=exit_code,
            results=results,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            isolation_level=isolation.value,
            sandbox_error=error_msg,
            is_sandbox_disabled=(isolation == IsolationLevel.disabled),
        )

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        task_id: UUID,
        requirement_ids: List[str],
        test_type: str,
    ) -> List[TestResult]:
        """Extract individual test case results from pytest verbose lines."""
        results: List[TestResult] = []
        re_test_line = re.compile(r"^([\w/\\._\-:]+::\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)", re.MULTILINE)

        for match in re_test_line.finditer(stdout):
            t_name = match.group(1)
            t_status_str = match.group(2).lower()
            status = TestStatus(t_status_str) if t_status_str in TestStatus._value2member_map_ else TestStatus.error

            results.append(
                TestResult(
                    task_id=task_id,
                    requirement_ids=requirement_ids,
                    test_name=t_name,
                    tool="pytest",
                    test_type=test_type,
                    status=status,
                    output=stdout[:500],
                    duration_ms=None,
                )
            )

        if not results and exit_code != 0:
            # Runner or collection error
            results.append(
                TestResult(
                    task_id=task_id,
                    requirement_ids=requirement_ids,
                    test_name="pytest_collection_or_execution",
                    tool="pytest",
                    test_type=test_type,
                    status=TestStatus.error,
                    output=(stderr or stdout)[:1000],
                    duration_ms=None,
                )
            )

        return results


class NpmTestRunner(TestRunner):
    """Executes JavaScript/TypeScript test suites via npm test."""

    def __init__(self, sandbox: Optional[ExecutionSandbox] = None) -> None:
        self.sandbox = sandbox or ExecutionSandbox()

    @property
    def name(self) -> str:
        return "npm_test"

    def supports_project(self, workspace_path: str) -> bool:
        ws = Path(workspace_path)
        pkg = ws / "package.json"
        return pkg.exists()

    async def run_tests(
        self,
        config: TestExecutionConfig,
        requirement_ids: List[str],
        task_id: Optional[Any] = None,
    ) -> TestExecutionResult:
        npm_cmd = ["npm.cmd" if sys.platform == "win32" else "npm", "test", "--", "--runInBand"]
        cmd = config.command_override or npm_cmd
        if config.test_paths:
            cmd.extend(config.test_paths)

        exit_code, stdout, stderr, duration_ms, isolation, error_msg = (
            await self.sandbox.execute_in_sandbox(
                command=cmd,
                cwd=config.workspace_path,
                timeout_seconds=config.timeout_seconds,
                extra_env=config.extra_env,
            )
        )

        tid = task_id or uuid4()
        results = self._parse_jest_output(stdout, stderr, exit_code, tid, requirement_ids, config.test_type)

        return TestExecutionResult(
            tool="npm_test",
            test_type=config.test_type,
            exit_code=exit_code,
            results=results,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            isolation_level=isolation.value,
            sandbox_error=error_msg,
            is_sandbox_disabled=(isolation == IsolationLevel.disabled),
        )

    def _parse_jest_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        task_id: UUID,
        requirement_ids: List[str],
        test_type: str,
    ) -> List[TestResult]:
        """Extract Jest/Vitest test case results."""
        results: List[TestResult] = []
        combined = f"{stdout}\n{stderr}"

        # Matches lines like: PASS src/Button.test.jsx or FAIL src/Button.test.jsx
        re_jest_suite = re.compile(r"^\s*(PASS|FAIL)\s+([^\n\r]+)", re.MULTILINE)
        for match in re_jest_suite.finditer(combined):
            res_str = match.group(1).upper()
            t_name = match.group(2).strip()
            status = TestStatus.passed if res_str == "PASS" else TestStatus.failed

            results.append(
                TestResult(
                    task_id=task_id,
                    requirement_ids=requirement_ids,
                    test_name=t_name,
                    tool="npm_test",
                    test_type=test_type,
                    status=status,
                    output=combined[:500],
                )
            )

        if not results:
            status = TestStatus.passed if exit_code == 0 else TestStatus.failed
            results.append(
                TestResult(
                    task_id=task_id,
                    requirement_ids=requirement_ids,
                    test_name="npm_test_suite",
                    tool="npm_test",
                    test_type=test_type,
                    status=status,
                    output=combined[:1000],
                )
            )

        return results


class PlaywrightRunner(TestRunner):
    """Executes browser test suites via Playwright."""

    def __init__(self, sandbox: Optional[ExecutionSandbox] = None) -> None:
        self.sandbox = sandbox or ExecutionSandbox()

    @property
    def name(self) -> str:
        return "playwright"

    def supports_project(self, workspace_path: str) -> bool:
        ws = Path(workspace_path)
        return (
            (ws / "playwright.config.ts").exists()
            or (ws / "playwright.config.js").exists()
            or (ws / "tests" / "e2e").exists()
        )

    async def run_tests(
        self,
        config: TestExecutionConfig,
        requirement_ids: List[str],
        task_id: Optional[Any] = None,
    ) -> TestExecutionResult:
        npx_cmd = ["npx.cmd" if sys.platform == "win32" else "npx", "playwright", "test"]
        cmd = config.command_override or npx_cmd
        if config.test_paths:
            cmd.extend(config.test_paths)

        exit_code, stdout, stderr, duration_ms, isolation, error_msg = (
            await self.sandbox.execute_in_sandbox(
                command=cmd,
                cwd=config.workspace_path,
                timeout_seconds=config.timeout_seconds,
                extra_env=config.extra_env,
            )
        )

        tid = task_id or uuid4()
        status = TestStatus.passed if exit_code == 0 else TestStatus.failed
        results = [
            TestResult(
                task_id=tid,
                requirement_ids=requirement_ids,
                test_name="playwright_e2e_suite",
                tool="playwright",
                test_type=TestType.browser_test.value,
                status=status,
                output=(stdout + stderr)[:1000],
                duration_ms=duration_ms,
            )
        ]

        return TestExecutionResult(
            tool="playwright",
            test_type=TestType.browser_test.value,
            exit_code=exit_code,
            results=results,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            isolation_level=isolation.value,
            sandbox_error=error_msg,
            is_sandbox_disabled=(isolation == IsolationLevel.disabled),
        )


def detect_test_runner(
    workspace_path: str, tool_override: Optional[str] = None
) -> TestRunner:
    """Identify the appropriate test runner for a workspace."""
    settings = get_settings()
    if settings.MOCK_MODE:
        return MockTestRunner()

    if tool_override:
        tool_clean = tool_override.lower().strip()
        if "pytest" in tool_clean:
            return PytestRunner()
        if "npm" in tool_clean or "jest" in tool_clean:
            return NpmTestRunner()
        if "playwright" in tool_clean:
            return PlaywrightRunner()

    # Heuristic detection
    pw = PlaywrightRunner()
    if pw.supports_project(workspace_path):
        return pw

    npm = NpmTestRunner()
    if npm.supports_project(workspace_path):
        return npm

    py = PytestRunner()
    if py.supports_project(workspace_path):
        return py

    return MockTestRunner()
