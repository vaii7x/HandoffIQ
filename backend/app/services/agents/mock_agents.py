"""Deterministic mock implementations of agent services and dependency injection registry."""

from typing import List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.core.errors import ConfigurationError
from app.models.artifact import CodeArtifact
from app.models.handoff import IssueSeverity, IssueType, RepairStatus, ValidationIssue
from app.models.test_result import TestResult, TestStatus
from app.services.agents.base import (
    CoderInput,
    CoderOutput,
    CoderService,
    ContextMapInput,
    ContextMapOutput,
    ContextMapService,
    RecoveryDecision,
    RecoveryDecisionService,
    RecoveryInput,
    ResearchInput,
    ResearchOutput,
    ResearcherService,
    ReviewerInput,
    ReviewerOutput,
    ReviewerService,
    TesterInput,
    TesterOutput,
    TesterService,
)


def _assert_mock_mode_enabled(service_name: str) -> None:
    """Ensure mock implementations are never executed when MOCK_MODE is disabled."""
    settings = get_settings()
    if not settings.MOCK_MODE:
        raise ConfigurationError(
            f"Mock {service_name} cannot be used when MOCK_MODE is disabled. "
            f"The AI developer must inject a live {service_name} implementation."
        )


# ============================================================================
# Deterministic Mock Services
# ============================================================================

class MockResearcherService(ResearcherService):
    """Deterministic mock researcher for testing and local execution."""

    @property
    def name(self) -> str:
        return "mock_researcher"

    async def execute(self, input_data: ResearchInput) -> ResearchOutput:
        _assert_mock_mode_enabled("ResearcherService")

        if "__SIMULATE_RESEARCHER_FAILURE__" in input_data.original_request:
            raise RuntimeError("Simulated researcher agent failure.")

        req_ids = [r.id for r in input_data.requirements]
        return ResearchOutput(
            summary=f"Architecture research completed for {len(req_ids)} requirements.",
            handoff_payload={
                "architecture_spec": "spec_v1.md",
                "components": ["CoreModule", "AuthModule", "UIModule"],
                "guidance": "Follow clean hexagonal architecture with strict type safety.",
            },
            requirement_ids=req_ids,
        )


class MockContextMapService(ContextMapService):
    """Deterministic mock context projection service."""

    @property
    def name(self) -> str:
        return "mock_context_mapper"

    async def create_context_map(self, input_data: ContextMapInput) -> ContextMapOutput:
        _assert_mock_mode_enabled("ContextMapService")

        mappings = {}
        for req in input_data.requirements:
            mappings[req.id] = {
                "description": req.description,
                "related_files": req.related_files or ["src/index.ts"],
                "priority": str(req.priority),
            }

        return ContextMapOutput(
            global_context=input_data.validated_handoff.payload,
            requirement_mappings=mappings,
        )


class MockCoderService(CoderService):
    """Deterministic mock coder producing code artifacts matching requirements."""

    @property
    def name(self) -> str:
        return "mock_coder"

    async def execute(self, input_data: CoderInput) -> CoderOutput:
        _assert_mock_mode_enabled("CoderService")

        for req in input_data.requirements:
            if "__SIMULATE_CODER_FAILURE__" in req.original_text:
                raise RuntimeError("Simulated coder agent failure.")

        artifacts: List[CodeArtifact] = []
        for i, req in enumerate(input_data.requirements, 1):
            file_path = req.related_files[0] if req.related_files else f"src/feature_{i}.ts"
            lang = "typescript" if file_path.endswith((".ts", ".tsx")) else "python"
            artifacts.append(
                CodeArtifact(
                    task_id=input_data.task_id,
                    path=file_path,
                    language=lang,
                    content=f"// Implementation for requirement {req.id}\nexport const run_{req.id.lower()} = () => true;\n",
                    requirement_ids=[req.id],
                    version=1,
                )
            )

        return CoderOutput(
            artifacts=artifacts,
            summary=f"Generated {len(artifacts)} code artifacts implementing requirements.",
        )


class MockReviewerService(ReviewerService):
    """Deterministic mock code reviewer checking artifacts against requirements."""

    @property
    def name(self) -> str:
        return "mock_reviewer"

    async def execute(self, input_data: ReviewerInput) -> ReviewerOutput:
        _assert_mock_mode_enabled("ReviewerService")

        for req in input_data.requirements:
            if "__SIMULATE_REVIEW_FAILURE__" in req.original_text:
                return ReviewerOutput(
                    approved=False,
                    issues=[
                        ValidationIssue(
                            requirement_id=req.id,
                            issue_type=IssueType.implementation_gap,
                            severity=IssueSeverity.high,
                            description=f"Code artifact failed review criteria for {req.id}.",
                            repair_status=RepairStatus.unresolved,
                            evidence=["Artifact missing error boundary"],
                        )
                    ],
                    review_notes="Code review rejected due to missing implementation guarantees.",
                )

        return ReviewerOutput(
            approved=True,
            issues=[],
            review_notes="All artifacts reviewed and approved against canonical requirements.",
        )


class MockTesterService(TesterService):
    """Deterministic mock tester producing TestResult verification evidence."""

    @property
    def name(self) -> str:
        return "mock_tester"

    async def execute(self, input_data: TesterInput) -> TesterOutput:
        _assert_mock_mode_enabled("TesterService")

        test_results: List[TestResult] = []
        all_passed = True

        for req in input_data.requirements:
            if "__SIMULATE_TEST_FAILURE__" in req.original_text:
                all_passed = False
                test_results.append(
                    TestResult(
                        task_id=input_data.task_id,
                        requirement_ids=[req.id],
                        test_name=f"test_verification_{req.id.lower()}",
                        tool="pytest",
                        status=TestStatus.failed,
                        output=f"AssertionError: Requirement {req.id} verification assertion failed.",
                        duration_ms=45,
                    )
                )
            else:
                test_results.append(
                    TestResult(
                        task_id=input_data.task_id,
                        requirement_ids=[req.id],
                        test_name=f"test_verification_{req.id.lower()}",
                        tool="pytest",
                        status=TestStatus.passed,
                        output=f"1 passed: Requirement {req.id} verified successfully.",
                        duration_ms=25,
                    )
                )

        return TesterOutput(
            test_results=test_results,
            all_passed=all_passed,
            summary=f"Executed {len(test_results)} verification tests. All passed: {all_passed}.",
        )


class MockRecoveryDecisionService(RecoveryDecisionService):
    """Deterministic mock recovery service evaluating self-healing."""

    @property
    def name(self) -> str:
        return "mock_recovery_decision"

    async def evaluate(self, input_data: RecoveryInput) -> RecoveryDecision:
        _assert_mock_mode_enabled("RecoveryDecisionService")

        # Allow 1 retry attempt upon failure
        if input_data.attempt_number < 2 and (input_data.failed_tests or input_data.review_issues):
            return RecoveryDecision(
                should_retry=True,
                retry_stage="coding",
                repair_summary=f"Automated retry attempt {input_data.attempt_number} addressing {len(input_data.failed_tests)} test failures.",
            )

        return RecoveryDecision(
            should_retry=False,
            retry_stage=None,
            repair_summary="No further recovery attempts authorized.",
        )


# ============================================================================
# Service Injection Registry & Providers
# ============================================================================

_researcher_service: ResearcherService = MockResearcherService()
_context_map_service: ContextMapService = MockContextMapService()
_coder_service: CoderService = MockCoderService()
_reviewer_service: ReviewerService = MockReviewerService()
_tester_service: TesterService = MockTesterService()
_recovery_decision_service: RecoveryDecisionService = MockRecoveryDecisionService()


def get_researcher_service() -> ResearcherService:
    return _researcher_service


def set_researcher_service(service: ResearcherService) -> None:
    global _researcher_service
    _researcher_service = service


def get_context_map_service() -> ContextMapService:
    return _context_map_service


def set_context_map_service(service: ContextMapService) -> None:
    global _context_map_service
    _context_map_service = service


def get_coder_service() -> CoderService:
    return _coder_service


def set_coder_service(service: CoderService) -> None:
    global _coder_service
    _coder_service = service


def get_reviewer_service() -> ReviewerService:
    return _reviewer_service


def set_reviewer_service(service: ReviewerService) -> None:
    global _reviewer_service
    _reviewer_service = service


def get_tester_service() -> TesterService:
    return _tester_service


def set_tester_service(service: TesterService) -> None:
    global _tester_service
    _tester_service = service


def get_recovery_decision_service() -> RecoveryDecisionService:
    return _recovery_decision_service


def set_recovery_decision_service(service: RecoveryDecisionService) -> None:
    global _recovery_decision_service
    _recovery_decision_service = service
