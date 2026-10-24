"""Handoff validation service managing requirement fidelity, issue tracking, and safe repair."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.errors import TaskNotFoundError
from app.models.event import WorkflowEvent
from app.models.handoff import (
    Handoff,
    HandoffStatus,
    IssueType,
    RepairStatus,
    ValidationIssue,
)
from app.models.requirement import Requirement
from app.repositories.base import TaskRepository
from app.repositories.handoff_repository import HandoffRepository, get_handoff_repository
from app.repositories.in_memory import get_task_repository
from app.services.semantic_provider import (
    SemanticValidationProvider,
    get_semantic_validation_provider,
)
from app.services.validation_rules import (
    check_deterministic_contradictions,
    check_missing_requirements,
    check_payload_structure,
    check_semantic_drift,
    check_suspicious_instructions,
    check_unknown_requirements,
    check_weakened_constraints,
)

logger = logging.getLogger(__name__)


class HandoffValidationService:
    """Service validating agent handoffs against canonical task requirements."""

    def __init__(
        self,
        task_repository: TaskRepository,
        handoff_repository: HandoffRepository,
        semantic_provider: SemanticValidationProvider,
    ) -> None:
        self.task_repo = task_repository
        self.handoff_repo = handoff_repository
        self.semantic_provider = semantic_provider

    async def run_validation_checks(
        self,
        task_id: UUID,
        canonical_requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        """Execute deterministic checks and semantic analysis provider.

        Security Note: Content in payload is treated as passive data. No instructions
        or executable code are ever parsed or evaluated.
        """
        issues: List[ValidationIssue] = []

        # 1. Deterministic check: missing required requirement IDs (omissions)
        issues.extend(
            check_missing_requirements(
                canonical_requirements=canonical_requirements,
                handoff_req_ids=handoff.requirement_ids,
            )
        )

        # 2. Deterministic check: unknown / invented requirement IDs
        issues.extend(
            check_unknown_requirements(
                canonical_requirements=canonical_requirements,
                handoff_req_ids=handoff.requirement_ids,
            )
        )

        # 3. Deterministic check: payload structure & schema
        issues.extend(check_payload_structure(handoff.payload))

        # 4. Deterministic check: explicit contradictions
        issues.extend(
            check_deterministic_contradictions(
                canonical_requirements=canonical_requirements,
                payload=handoff.payload,
            )
        )

        # 5. Deterministic check: suspicious instructions / unsafe overrides
        issues.extend(check_suspicious_instructions(handoff.payload))

        # 6. Deterministic check: weakened constraints
        issues.extend(check_weakened_constraints(canonical_requirements, handoff.payload))

        # 7. Deterministic check: subtle semantic drift
        issues.extend(check_semantic_drift(canonical_requirements, handoff.payload))

        # 8. Injected semantic provider check (AI semantic drift analysis)
        try:
            semantic_issues = await self.semantic_provider.analyze(
                task_id=task_id,
                requirements=canonical_requirements,
                handoff=handoff,
            )
            issues.extend(semantic_issues)
        except Exception as exc:
            logger.error("Semantic analysis provider error: %s", exc)
            # Record provider error as an issue without failing the entire validation
            issues.append(
                ValidationIssue(
                    requirement_id=None,
                    issue_type=IssueType.schema_error,
                    severity=check_deterministic_contradictions.__annotations__.get("severity", "medium"),
                    description=f"Semantic provider error: {str(exc)}",
                    repair_status=RepairStatus.unresolved,
                    evidence=[f"Provider '{self.semantic_provider.provider_name}' raised: {str(exc)}"],
                )
            )

        return issues

    async def submit_and_validate_handoff(
        self,
        task_id: UUID,
        source_agent: str,
        target_agent: str,
        requirement_ids: List[str],
        payload: Dict[str, Any],
        auto_repair: bool = True,
    ) -> Tuple[Handoff, bool]:
        """Register, validate, and optionally repair an agent context handoff."""
        # 1. Verify task exists
        task = await self.task_repo.get_task(task_id)
        if not task:
            raise TaskNotFoundError()

        # 2. Load canonical requirements for task
        canonical_reqs = await self.task_repo.get_requirements(task_id)
        canonical_map = {r.id: r for r in canonical_reqs}

        # 3. Construct initial Handoff entity
        handoff = Handoff(
            task_id=task_id,
            source_agent=source_agent,
            target_agent=target_agent,
            status=HandoffStatus.pending,
            requirement_ids=list(requirement_ids),
            payload=payload,
            issues=[],
        )

        # 4. Run initial validation pass
        initial_issues = await self.run_validation_checks(task_id, canonical_reqs, handoff)
        was_repaired = False
        repaired_omissions: List[ValidationIssue] = []

        # 5. Safe repair of recoverable omissions
        if auto_repair and initial_issues:
            # Separate recoverable omissions from other issues
            current_req_ids = list(handoff.requirement_ids)
            for issue in initial_issues:
                if issue.issue_type == IssueType.omission and issue.requirement_id in canonical_map:
                    # Restore omitted canonical requirement
                    if issue.requirement_id not in current_req_ids:
                        current_req_ids.append(issue.requirement_id)
                        was_repaired = True

                        # Mark omission issue as repaired
                        repaired_issue = issue.model_copy(
                            update={"repair_status": RepairStatus.repaired}
                        )
                        repaired_omissions.append(repaired_issue)

                        # Record workflow event for safe repair
                        await self.task_repo.add_event(
                            WorkflowEvent(
                                task_id=task_id,
                                event_type="handoff_repaired",
                                stage="validation",
                                message=f"Restored omitted canonical requirement {issue.requirement_id} into handoff.",
                                metadata={
                                    "handoff_id": str(handoff.id),
                                    "requirement_id": issue.requirement_id,
                                    "source_agent": source_agent,
                                    "target_agent": target_agent,
                                },
                            )
                        )

            if was_repaired:
                # Update handoff requirement_ids with restored IDs
                current_req_ids.sort()
                handoff = handoff.model_copy(update={"requirement_ids": current_req_ids})

        # 6. Revalidation: If repair was performed, re-validate handoff
        if was_repaired:
            revalidated_issues = await self.run_validation_checks(task_id, canonical_reqs, handoff)
            # Combine history: retain repaired omission records for audit transparency
            repaired_req_ids = {r.requirement_id for r in repaired_omissions}
            active_unresolved = [
                iss for iss in revalidated_issues if iss.requirement_id not in repaired_req_ids
            ]
            final_issues = repaired_omissions + active_unresolved
        else:
            final_issues = initial_issues

        # 7. Compute final handoff status
        has_unresolved_issues = any(
            iss.repair_status != RepairStatus.repaired for iss in final_issues
        )

        if not final_issues:
            final_status = HandoffStatus.validated
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' validated with zero issues."
            event_type = "handoff_validated"
        elif was_repaired and not has_unresolved_issues:
            final_status = HandoffStatus.repaired
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' validated after automatic omission repair."
            event_type = "handoff_validated"
        else:
            final_status = HandoffStatus.blocked
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' blocked due to {len(final_issues)} issues."
            event_type = "handoff_blocked"

        handoff = handoff.model_copy(
            update={
                "status": final_status,
                "issues": final_issues,
            }
        )

        # 8. Record audit event for validation outcome
        await self.task_repo.add_event(
            WorkflowEvent(
                task_id=task_id,
                event_type=event_type,
                stage="validation",
                message=log_msg,
                metadata={
                    "handoff_id": str(handoff.id),
                    "status": str(final_status),
                    "issues_count": len(final_issues),
                    "was_repaired": was_repaired,
                },
            )
        )

        # 9. Store handoff in repository
        saved_handoff = await self.handoff_repo.create_handoff(handoff)
        return saved_handoff, was_repaired

    async def list_handoffs_for_task(self, task_id: UUID) -> List[Handoff]:
        """List all handoffs recorded for a task."""
        # Ensure task exists
        task = await self.task_repo.get_task(task_id)
        if not task:
            raise TaskNotFoundError()
        return await self.handoff_repo.list_handoffs_for_task(task_id)


def get_handoff_service() -> HandoffValidationService:
    """Dependency provider creating HandoffValidationService with injected repositories and provider."""
    task_repo = get_task_repository()
    handoff_repo = get_handoff_repository()
    semantic_provider = get_semantic_validation_provider()
    return HandoffValidationService(
        task_repository=task_repo,
        handoff_repository=handoff_repo,
        semantic_provider=semantic_provider,
    )
