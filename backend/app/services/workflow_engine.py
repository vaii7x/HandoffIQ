"""Workflow execution engine coordinating agent handoffs, stage transitions, and verification."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from app.core.errors import AppError, TaskAlreadyRunningError, TaskNotFoundError
from app.models.agent_run import AgentRun, AgentRunStatus, AgentType
from app.models.event import WorkflowEvent
from app.models.handoff import HandoffStatus
from app.models.requirement import Requirement, RequirementStatus
from app.models.task import Task, TaskStatus
from app.models.test_result import TestStatus
from app.repositories.base import TaskRepository
from app.repositories.in_memory import get_task_repository
from app.services.agents.base import (
    CoderInput,
    CoderService,
    ContextMapInput,
    ContextMapService,
    RecoveryDecisionService,
    RecoveryInput,
    ResearchInput,
    ResearcherService,
    ReviewerInput,
    ReviewerService,
    TesterInput,
    TesterService,
)
from app.services.agents.mock_agents import (
    get_coder_service,
    get_context_map_service,
    get_recovery_decision_service,
    get_researcher_service,
    get_reviewer_service,
    get_tester_service,
)
from app.services.handoff_service import HandoffValidationService, get_handoff_service

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowEngine:
    """Coordinates execution across multi-agent stages, handoffs, and verification."""

    def __init__(
        self,
        task_repository: TaskRepository,
        handoff_service: HandoffValidationService,
        researcher: ResearcherService,
        context_mapper: ContextMapService,
        coder: CoderService,
        reviewer: ReviewerService,
        tester: TesterService,
        recovery_service: RecoveryDecisionService,
    ) -> None:
        self.task_repo = task_repository
        self.handoff_service = handoff_service
        self.researcher = researcher
        self.context_mapper = context_mapper
        self.coder = coder
        self.reviewer = reviewer
        self.tester = tester
        self.recovery_service = recovery_service

    async def execute_workflow(self, task_id: UUID) -> None:
        """Run the end-to-end multi-agent orchestration pipeline for a task."""
        task = await self.task_repo.get_task(task_id)
        if not task:
            raise TaskNotFoundError()

        try:
            # ----------------------------------------------------------------
            # STAGE 1: Research
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="research", progress=15, status=TaskStatus.running)
            research_run = await self._start_agent_run(task_id, AgentType.researcher)

            requirements = await self.task_repo.get_requirements(task_id)
            research_out = await self.researcher.execute(
                ResearchInput(
                    task_id=task_id,
                    original_request=task.original_request,
                    requirements=requirements,
                )
            )
            await self._finish_agent_run(research_run, summary=research_out.summary)

            # ----------------------------------------------------------------
            # STAGE 2: Handoff Validation (Researcher -> Coder)
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="handoff_validation", progress=30)
            handoff, _ = await self.handoff_service.submit_and_validate_handoff(
                task_id=task_id,
                source_agent="researcher",
                target_agent="coder",
                requirement_ids=research_out.requirement_ids,
                payload=research_out.handoff_payload,
                auto_repair=True,
            )

            if handoff.status == HandoffStatus.blocked:
                await self._fail_workflow(
                    task_id,
                    reason=f"Handoff validation blocked with {len(handoff.issues)} unresolved discrepancies.",
                    stage="handoff_validation",
                )
                return

            # ----------------------------------------------------------------
            # STAGE 3: Context Mapping
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="context_mapping", progress=45)
            context_map_out = await self.context_mapper.create_context_map(
                ContextMapInput(
                    task_id=task_id,
                    requirements=requirements,
                    validated_handoff=handoff,
                )
            )
            await self.task_repo.add_event(
                WorkflowEvent(
                    task_id=task_id,
                    event_type="context_mapped",
                    stage="context_mapping",
                    message="ContextMap generated and partitioned for coding phase.",
                    metadata={"requirement_count": len(context_map_out.requirement_mappings)},
                )
            )

            # ----------------------------------------------------------------
            # STAGE 4: Coding
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="coding", progress=60)
            coder_run = await self._start_agent_run(task_id, AgentType.coder)
            coder_out = await self.coder.execute(
                CoderInput(
                    task_id=task_id,
                    requirements=requirements,
                    context_map=context_map_out,
                )
            )
            await self._finish_agent_run(coder_run, summary=coder_out.summary)

            # Mark requirements as implemented
            for req in requirements:
                await self.task_repo.update_requirement(
                    task_id,
                    req.model_copy(update={"status": RequirementStatus.implemented}),
                )

            # ----------------------------------------------------------------
            # STAGE 5: Code Review
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="code_review", progress=75)
            reviewer_run = await self._start_agent_run(task_id, AgentType.reviewer)
            reviewer_out = await self.reviewer.execute(
                ReviewerInput(
                    task_id=task_id,
                    requirements=requirements,
                    artifacts=coder_out.artifacts,
                )
            )
            if reviewer_out.approved:
                await self._finish_agent_run(reviewer_run, summary=reviewer_out.review_notes)
            else:
                await self._finish_agent_run(
                    reviewer_run,
                    summary=reviewer_out.review_notes,
                    status=AgentRunStatus.failed,
                    error="Code review rejected.",
                )

            # ----------------------------------------------------------------
            # STAGE 6: Testing
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="testing", progress=85)
            tester_run = await self._start_agent_run(task_id, AgentType.tester)
            tester_out = await self.tester.execute(
                TesterInput(
                    task_id=task_id,
                    requirements=requirements,
                    artifacts=coder_out.artifacts,
                )
            )
            await self._finish_agent_run(tester_run, summary=tester_out.summary)

            # ----------------------------------------------------------------
            # STAGE 7: Recovery Decision (if review or tests failed)
            # ----------------------------------------------------------------
            if not reviewer_out.approved or not tester_out.all_passed:
                await self._update_task_stage(task_id, stage="recovery_decision", progress=90)
                failed_tests = [t for t in tester_out.test_results if t.status != TestStatus.passed]
                recovery = await self.recovery_service.evaluate(
                    RecoveryInput(
                        task_id=task_id,
                        requirements=requirements,
                        failed_tests=failed_tests,
                        review_issues=reviewer_out.issues,
                        attempt_number=1,
                    )
                )

                await self.task_repo.add_event(
                    WorkflowEvent(
                        task_id=task_id,
                        event_type="recovery_decision",
                        stage="recovery_decision",
                        message=recovery.repair_summary,
                        metadata={"should_retry": recovery.should_retry, "retry_stage": recovery.retry_stage},
                    )
                )

            # ----------------------------------------------------------------
            # STAGE 8: Final Verification & Evidence-Based Requirement Updates
            # ----------------------------------------------------------------
            await self._update_task_stage(task_id, stage="verification", progress=100)

            # Test results lookup by requirement
            tests_by_req: Dict[str, List[TestStatus]] = {}
            for test in tester_out.test_results:
                for rid in test.requirement_ids:
                    if rid not in tests_by_req:
                        tests_by_req[rid] = []
                    tests_by_req[rid].append(test.status)

            all_reqs_verified = True
            for req in requirements:
                req_tests = tests_by_req.get(req.id, [])
                if req_tests and all(st == TestStatus.passed for st in req_tests):
                    # Verified strictly with passing test evidence
                    new_status = RequirementStatus.verified
                    await self.task_repo.update_requirement(
                        task_id,
                        req.model_copy(update={"status": new_status}),
                    )
                    await self.task_repo.add_event(
                        WorkflowEvent(
                            task_id=task_id,
                            event_type="requirement_verified",
                            stage="verification",
                            message=f"Requirement {req.id} verified with passing test evidence.",
                            metadata={"requirement_id": req.id, "test_count": len(req_tests)},
                        )
                    )
                elif any(st in [TestStatus.failed, TestStatus.error] for st in req_tests):
                    new_status = RequirementStatus.failed
                    all_reqs_verified = False
                    await self.task_repo.update_requirement(
                        task_id,
                        req.model_copy(update={"status": new_status}),
                    )
                    await self.task_repo.add_event(
                        WorkflowEvent(
                            task_id=task_id,
                            event_type="requirement_failed",
                            stage="verification",
                            message=f"Requirement {req.id} verification failed.",
                            metadata={"requirement_id": req.id},
                        )
                    )
                else:
                    # No conclusive test evidence; do NOT mark as verified
                    all_reqs_verified = False

            # Update final task status
            final_status = (
                TaskStatus.completed
                if (all_reqs_verified and reviewer_out.approved)
                else TaskStatus.failed
            )

            current_task = await self.task_repo.get_task(task_id)
            if current_task:
                await self.task_repo.update_task(
                    current_task.model_copy(
                        update={
                            "status": final_status,
                            "current_stage": "verification",
                            "progress": 100,
                        }
                    )
                )

            await self.task_repo.add_event(
                WorkflowEvent(
                    task_id=task_id,
                    event_type="workflow_completed" if final_status == TaskStatus.completed else "workflow_failed",
                    stage="verification",
                    message=f"Workflow finished with status '{final_status}'.",
                    metadata={"status": str(final_status), "all_verified": all_reqs_verified},
                )
            )

        except Exception as exc:
            logger.error("Workflow execution failed for task %s: %s", task_id, exc)
            await self._fail_workflow(task_id, reason=str(exc), stage="execution_failure")

    async def _update_task_stage(
        self,
        task_id: UUID,
        stage: str,
        progress: int,
        status: Optional[TaskStatus] = None,
    ) -> None:
        task = await self.task_repo.get_task(task_id)
        if task:
            updates = {"current_stage": stage, "progress": progress}
            if status:
                updates["status"] = status
            await self.task_repo.update_task(task.model_copy(update=updates))
            await self.task_repo.add_event(
                WorkflowEvent(
                    task_id=task_id,
                    event_type="stage_transition",
                    stage=stage,
                    message=f"Advanced to stage '{stage}' (progress: {progress}%).",
                    metadata={"stage": stage, "progress": progress},
                )
            )

    async def _start_agent_run(self, task_id: UUID, agent_type: AgentType) -> AgentRun:
        run = AgentRun(
            task_id=task_id,
            agent_type=agent_type,
            status=AgentRunStatus.running,
            started_at=utcnow(),
        )
        await self.task_repo.add_agent_run(run)
        type_str = str(agent_type.value if hasattr(agent_type, "value") else agent_type)
        await self.task_repo.add_event(
            WorkflowEvent(
                task_id=task_id,
                event_type="agent_run_started",
                stage=type_str,
                message=f"Agent '{type_str}' started phase execution.",
                metadata={"agent_type": type_str, "run_id": str(run.id)},
            )
        )
        return run

    async def _finish_agent_run(
        self,
        run: AgentRun,
        summary: str,
        status: AgentRunStatus = AgentRunStatus.completed,
        error: Optional[str] = None,
    ) -> None:
        updated = run.model_copy(
            update={
                "status": status,
                "completed_at": utcnow(),
                "summary": summary,
                "error": error,
            }
        )
        await self.task_repo.update_agent_run(updated)
        type_str = str(run.agent_type.value if hasattr(run.agent_type, "value") else run.agent_type)
        status_str = str(status.value if hasattr(status, "value") else status)
        is_completed = (status == AgentRunStatus.completed or status_str == "completed")
        await self.task_repo.add_event(
            WorkflowEvent(
                task_id=run.task_id,
                event_type="agent_run_completed" if is_completed else "agent_run_failed",
                stage=type_str,
                message=f"Agent '{type_str}' finished with status '{status_str}'.",
                metadata={"agent_type": type_str, "status": status_str},
            )
        )

    async def _fail_workflow(self, task_id: UUID, reason: str, stage: str) -> None:
        task = await self.task_repo.get_task(task_id)
        if task:
            await self.task_repo.update_task(
                task.model_copy(
                    update={
                        "status": TaskStatus.failed,
                        "current_stage": stage,
                    }
                )
            )
            await self.task_repo.add_event(
                WorkflowEvent(
                    task_id=task_id,
                    event_type="workflow_failed",
                    stage=stage,
                    message=f"Workflow failed at stage '{stage}': {reason}",
                    metadata={"error": reason, "stage": stage},
                )
            )


class TaskExecutionManager:
    """Manages active task runs, prevents duplicate executions, and manages background jobs."""

    def __init__(self, workflow_engine: WorkflowEngine) -> None:
        self.engine = workflow_engine
        self._running_tasks: Set[UUID] = set()
        self._active_jobs: Dict[UUID, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_task_run(self, task_id: UUID) -> Dict[str, Any]:
        """Initiate background workflow execution with duplicate run protection."""
        async with self._lock:
            # Check if task is already running
            if task_id in self._running_tasks:
                raise TaskAlreadyRunningError(task_id)

            task = await self.engine.task_repo.get_task(task_id)
            if not task:
                raise TaskNotFoundError()

            if task.status == TaskStatus.running:
                raise TaskAlreadyRunningError(task_id)

            # Mark task running in registry and persistence
            self._running_tasks.add(task_id)
            await self.engine.task_repo.update_task(
                task.model_copy(
                    update={
                        "status": TaskStatus.running,
                        "current_stage": "research",
                    }
                )
            )

        # Launch background managed job
        job = asyncio.create_task(self._managed_run_wrapper(task_id))
        self._active_jobs[task_id] = job

        return {
            "task_id": task_id,
            "status": "running",
            "current_stage": "research",
            "message": "Workflow started",
        }

    async def _managed_run_wrapper(self, task_id: UUID) -> None:
        """Run wrapper ensuring locks are released and unhandled exceptions persist failure status."""
        try:
            await self.engine.execute_workflow(task_id)
        except Exception as exc:
            logger.error("Unhandled exception in task runner %s: %s", task_id, exc)
            await self.engine._fail_workflow(task_id, reason=str(exc), stage="runner_failure")
        finally:
            async with self._lock:
                self._running_tasks.discard(task_id)
                self._active_jobs.pop(task_id, None)

    async def is_running(self, task_id: UUID) -> bool:
        async with self._lock:
            return task_id in self._running_tasks

    async def wait_for_completion(self, task_id: UUID, timeout: float = 10.0) -> None:
        """Helper for test suites to await background job completion."""
        job = self._active_jobs.get(task_id)
        if job and not job.done():
            await asyncio.wait_for(job, timeout=timeout)


_workflow_engine: Optional[WorkflowEngine] = None
_execution_manager: Optional[TaskExecutionManager] = None


def get_workflow_engine() -> WorkflowEngine:
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine(
            task_repository=get_task_repository(),
            handoff_service=get_handoff_service(),
            researcher=get_researcher_service(),
            context_mapper=get_context_map_service(),
            coder=get_coder_service(),
            reviewer=get_reviewer_service(),
            tester=get_tester_service(),
            recovery_service=get_recovery_decision_service(),
        )
    return _workflow_engine


def get_execution_manager() -> TaskExecutionManager:
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = TaskExecutionManager(get_workflow_engine())
    return _execution_manager
