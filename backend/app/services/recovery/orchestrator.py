"""Bounded recovery orchestrator executing repair loops, patch application, and regression checks."""

from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import PathTraversalError, WorkspaceSecurityError
from app.models.artifact import CodeArtifact
from app.models.event import WorkflowEvent
from app.models.recovery import RecoveryAttempt, RecoveryStatus
from app.models.requirement import Requirement
from app.models.test_result import TestResult, TestStatus
from app.repositories.base import TaskRepository
from app.services.recovery.repair_service import (
    AIRepairService,
    RepairInput,
    get_repair_service,
)
from app.services.test_runner.base import TestExecutionConfig, TestRunner
from app.services.test_runner.runners import detect_test_runner


class BoundedRecoveryOrchestrator:
    """Coordinates automated repair attempts, isolated retesting, and regression tracking."""

    def __init__(
        self,
        task_repo: TaskRepository,
        repair_service: Optional[AIRepairService] = None,
        test_runner: Optional[TestRunner] = None,
        max_attempts: Optional[int] = None,
    ) -> None:
        self.task_repo = task_repo
        self.repair_service = repair_service or get_repair_service()
        self.test_runner = test_runner
        settings = get_settings()
        self.max_attempts = (
            max_attempts
            if max_attempts is not None
            else settings.MAX_RECOVERY_ATTEMPTS
        )

    async def coordinate_recovery(
        self,
        task_id: UUID,
        workspace_path: str,
        initial_test_results: List[TestResult],
        requirements: List[Requirement],
        test_config: Optional[TestExecutionConfig] = None,
    ) -> List[RecoveryAttempt]:
        """Execute bounded recovery cycles until tests pass or max attempts are reached.

        Returns:
            List of all RecoveryAttempt records recorded during this orchestration.
        """
        attempts_log: List[RecoveryAttempt] = []

        # 1. Identify initial failing tests
        failed_tests = [
            t for t in initial_test_results if t.status in {TestStatus.failed, TestStatus.error}
        ]
        if not failed_tests:
            return attempts_log

        # 2. Track baseline passed tests for regression detection
        passed_test_names: Set[str] = {
            t.test_name for t in initial_test_results if t.status == TestStatus.passed
        }

        ws_root = Path(workspace_path).resolve()
        runner = self.test_runner or detect_test_runner(workspace_path)
        config = test_config or TestExecutionConfig(workspace_path=workspace_path)

        current_failed_tests = failed_tests
        latest_results = initial_test_results

        for attempt_num in range(1, self.max_attempts + 1):
            # Record initial attempt record
            failure_summary = (
                f"Attempt {attempt_num}: {len(current_failed_tests)} test(s) failed: "
                f"{', '.join(t.test_name for t in current_failed_tests[:3])}"
            )

            # Map failed tests to requirement IDs
            failed_req_ids = sorted(
                list(
                    {
                        rid
                        for t in current_failed_tests
                        for rid in t.requirement_ids
                    }
                )
            )
            if not failed_req_ids:
                failed_req_ids = [r.id for r in requirements]

            attempt_record = RecoveryAttempt(
                task_id=task_id,
                requirement_ids=failed_req_ids,
                failure_summary=failure_summary,
                repair_summary="Generating repair patch...",
                status=RecoveryStatus.running,
                attempt_number=attempt_num,
                test_result_ids=[str(t.id) for t in current_failed_tests],
            )
            attempt_record = await self.task_repo.add_recovery_attempt(task_id, attempt_record)

            # Call injected AI repair service
            repair_input = RepairInput(
                task_id=task_id,
                workspace_path=str(ws_root),
                failed_tests=current_failed_tests,
                requirements=requirements,
                attempt_number=attempt_num,
                previous_attempts=attempts_log,
            )
            repair_output = await self.repair_service.generate_repair(repair_input)

            # Apply corrections ONLY to task workspace
            applied_artifacts: List[CodeArtifact] = []
            for art in repair_output.artifacts:
                safe_target = self._apply_patch_safely(ws_root, art)
                stored_art = await self.task_repo.add_artifact(task_id, art)
                applied_artifacts.append(stored_art)

            # Rerun relevant tests
            exec_result = await runner.run_tests(
                config=config,
                requirement_ids=failed_req_ids,
                task_id=task_id,
            )

            # Persist fresh test results
            for tr in exec_result.results:
                await self.task_repo.add_test_result(task_id, tr)

            latest_results = exec_result.results

            # Check for regressions: previously passed test that now failed
            regressions: List[str] = []
            for tr in latest_results:
                if tr.test_name in passed_test_names and tr.status in {TestStatus.failed, TestStatus.error}:
                    regressions.append(tr.test_name)

            # Determine remaining unresolved failures
            current_failed_tests = [
                t for t in latest_results if t.status in {TestStatus.failed, TestStatus.error}
            ]

            if not current_failed_tests and not regressions:
                # Succeeded!
                attempt_record = attempt_record.model_copy(
                    update={
                        "status": RecoveryStatus.succeeded,
                        "repair_summary": repair_output.repair_summary,
                        "unresolved_failures": [],
                        "regressions": [],
                    }
                )
                await self.task_repo.update_recovery_attempt(attempt_record)
                attempts_log.append(attempt_record)

                await self.task_repo.add_event(
                    WorkflowEvent(
                        task_id=task_id,
                        event_type="recovery_succeeded",
                        stage="recovery_decision",
                        message=f"Recovery attempt {attempt_num} succeeded. All tests passing.",
                        metadata={"attempt_number": attempt_num, "applied_patches": len(applied_artifacts)},
                    )
                )
                break
            else:
                # Still failing or regressed
                unresolved = [t.test_name for t in current_failed_tests]
                attempt_record = attempt_record.model_copy(
                    update={
                        "status": RecoveryStatus.failed,
                        "repair_summary": repair_output.repair_summary,
                        "unresolved_failures": unresolved,
                        "regressions": regressions,
                    }
                )
                await self.task_repo.update_recovery_attempt(attempt_record)
                attempts_log.append(attempt_record)

                await self.task_repo.add_event(
                    WorkflowEvent(
                        task_id=task_id,
                        event_type="recovery_attempt_failed",
                        stage="recovery_decision",
                        message=f"Recovery attempt {attempt_num} failed with {len(unresolved)} unresolved issues.",
                        metadata={
                            "attempt_number": attempt_num,
                            "unresolved_failures": unresolved,
                            "regressions": regressions,
                        },
                    )
                )

        if current_failed_tests:
            await self.task_repo.add_event(
                WorkflowEvent(
                    task_id=task_id,
                    event_type="recovery_limit_reached",
                    stage="recovery_decision",
                    message=f"Reached maximum recovery attempts ({self.max_attempts}) without full resolution.",
                    metadata={"unresolved_count": len(current_failed_tests)},
                )
            )

        return attempts_log

    def _apply_patch_safely(self, ws_root: Path, artifact: CodeArtifact) -> Path:
        """Safely apply a code patch file strictly inside the workspace root."""
        clean_path = artifact.path.strip()

        if ".." in Path(clean_path).parts:
            raise PathTraversalError(clean_path, str(ws_root))

        dest = (ws_root / clean_path).resolve()

        try:
            dest.relative_to(ws_root)
        except ValueError:
            raise PathTraversalError(clean_path, str(ws_root))

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(artifact.content, encoding="utf-8")
        return dest
