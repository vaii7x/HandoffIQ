"""Handoff validation service managing requirement fidelity, issue tracking, and safe repair."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.errors import TaskNotFoundError
from app.models.event import WorkflowEvent
from app.models.handoff import (
    Handoff,
    HandoffStatus,
    IssueSeverity,
    IssueType,
    RepairStatus,
    ValidationIssue,
)
from app.models.requirement import Requirement
from app.repositories.base import TaskRepository
from app.repositories.handoff_repository import HandoffRepository, get_handoff_repository
from app.services.task_service import get_task_repository
from app.services.semantic_provider import (
    SemanticValidationProvider,
    get_semantic_validation_provider,
)
from app.services.validation_rules import (
    check_deterministic_contradictions,
    check_missing_requirements,
    check_payload_structure,
    check_per_requirement_semantics,
    check_semantic_drift,
    check_suspicious_instructions,
    check_testing_coverage,
    check_unknown_requirements,
    check_weakened_constraints,
)

logger = logging.getLogger(__name__)


def is_unrequested_ui_constraint(issue: ValidationIssue, task_request: str) -> bool:
    """Check if an issue refers to an unrequested UI requirement on a non-UI task."""
    lower_req = task_request.lower()
    user_wanted_ui = any(w in lower_req for w in ["ui", "frontend", "gui", "interface", "web", "react", "view"])
    if user_wanted_ui:
        return False
    desc_lower = (issue.description + " " + " ".join(issue.evidence) + " " + str(issue.observed_value or "")).lower()
    return any(w in desc_lower for w in ["ui layer", "ui-layer", "uimodule", "graphical ui", "user interface layer"])


def is_blocking_issue(issue: ValidationIssue, task_request: str = "") -> bool:
    """Determine whether an unresolved issue must block progression to coding."""
    if issue.repair_status == RepairStatus.repaired:
        return False

    # Critical issues, suspicious instructions, explicit contradictions, schema errors, or un-repaired omissions are always blocking
    if issue.severity == IssueSeverity.critical:
        return True
    if issue.issue_type in [IssueType.suspicious_instruction, IssueType.contradiction, IssueType.schema_error]:
        return True
    if issue.issue_type == IssueType.omission:
        return True

    # High severity violations of user-mandated requirements are blocking
    if issue.severity == IssueSeverity.high:
        if is_unrequested_ui_constraint(issue, task_request):
            return False
        return True

    # Check weakened security/auth constraints
    if issue.issue_type == IssueType.weakened_constraint:
        desc_lower = (issue.description + " " + " ".join(issue.evidence)).lower()
        if any(w in desc_lower for w in ["auth", "security", "token", "credential", "bypass", "anonymous", "permission", "password"]):
            return True

    # Medium or low severity implementation choices or advisory notes do not block progression
    return False


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

        # 1. Deterministic check: missing required requirement IDs or explicit omissions
        issues.extend(
            check_missing_requirements(
                canonical_requirements=canonical_requirements,
                handoff_req_ids=handoff.requirement_ids,
                payload=handoff.payload,
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

        # 4. Deterministic check: explicit contradictions (persistence, atomicity, idempotency, etc.)
        issues.extend(
            check_deterministic_contradictions(
                canonical_requirements=canonical_requirements,
                payload=handoff.payload,
            )
        )

        # 5. Deterministic check: suspicious instructions / unsafe overrides
        issues.extend(check_suspicious_instructions(handoff.payload))

        # 6. Deterministic check: weakened constraints (passwords, validation, partial orders, authorization)
        issues.extend(check_weakened_constraints(canonical_requirements, handoff.payload))

        # 7. Deterministic check: subtle semantic drift
        issues.extend(check_semantic_drift(canonical_requirements, handoff.payload))

        # 8. Deterministic check: testing coverage gaps
        issues.extend(check_testing_coverage(canonical_requirements, handoff.payload))

        # 8b. Per-requirement semantic comparison (invariants, security guarantees, boundaries)
        issues.extend(check_per_requirement_semantics(canonical_requirements, handoff.payload))

        # 9. Injected semantic provider check (AI semantic analysis)
        try:
            semantic_issues = await self.semantic_provider.analyze(
                task_id=task_id,
                requirements=canonical_requirements,
                handoff=handoff,
            )
            issues.extend(semantic_issues)
        except Exception as exc:
            logger.error("Semantic analysis provider error: %s", exc)
            # Never silently mark compliant; record provider error as an unresolved issue requiring review
            issues.append(
                ValidationIssue(
                    requirement_id=None,
                    issue_type=IssueType.implementation_gap,
                    severity=IssueSeverity.medium,
                    description=f"Semantic compliance uncertain: Provider '{self.semantic_provider.provider_name}' error ({str(exc)}). Manual review required.",
                    original_value="Verified canonical compliance",
                    observed_value="Uncertain / provider error",
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
        for r in canonical_reqs:
            if r.source_id:
                canonical_map[r.source_id] = r

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
        repaired_issues: List[ValidationIssue] = []

        # 5. Safe repair of recoverable omissions and unrequested implementation constraints
        if auto_repair and initial_issues:
            current_req_ids = list(handoff.requirement_ids)
            updated_payload = dict(handoff.payload)

            for issue in initial_issues:
                # Check if this omission is an explicit payload omission (cannot be repaired automatically)
                is_explicit_payload_omission = (
                    issue.observed_value == "Omitted from handoff specification"
                    or any("omitted from handoff specification" in str(e).lower() or "out-of-scope list" in str(e).lower() for e in issue.evidence)
                )

                # 5a. Recoverable omissions (missing ID only, not explicitly dropped in downstream specification)
                if issue.issue_type == IssueType.omission and issue.requirement_id in canonical_map:
                    if is_explicit_payload_omission:
                        # Cannot safely auto-repair when downstream spec intentionally dropped it
                        continue

                    if issue.requirement_id not in current_req_ids:
                        current_req_ids.append(issue.requirement_id)
                        was_repaired = True
                        repaired_issue = issue.model_copy(
                            update={"repair_status": RepairStatus.repaired}
                        )
                        repaired_issues.append(repaired_issue)
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

                # 5b. Unrequested UI layer constraints on non-UI tasks (e.g. calculator division by zero)
                elif is_unrequested_ui_constraint(issue, task.original_request):
                    was_repaired = True
                    updated_payload["error_handling_guidance"] = (
                        "Exceptions and errors (e.g. division by zero) must raise standard exceptions "
                        "(e.g. ValueError or ZeroDivisionError) or return descriptive error messages in the core module. "
                        "An unrequested graphical UI is not required."
                    )
                    repaired_issue = issue.model_copy(
                        update={
                            "repair_status": RepairStatus.repaired,
                            "description": (
                                f"Repaired: Reconciled error-handling constraint on {issue.requirement_id or 'core logic'} "
                                "to canonical specification (handled via ValueError/core error message without requiring an unrequested graphical UI)."
                            ),
                            "evidence": list(issue.evidence) + ["Handoff payload reconciled to align with canonical non-UI specification."],
                        }
                    )
                    repaired_issues.append(repaired_issue)
                    await self.task_repo.add_event(
                        WorkflowEvent(
                            task_id=task_id,
                            event_type="handoff_repaired",
                            stage="validation",
                            message=f"Reconciled unrequested UI-layer constraint on {issue.requirement_id or 'error handling'} to canonical specification.",
                            metadata={
                                "handoff_id": str(handoff.id),
                                "requirement_id": issue.requirement_id,
                                "source_agent": source_agent,
                                "target_agent": target_agent,
                                "resolution": "reconciled_to_canonical",
                            },
                        )
                    )

            if was_repaired:
                current_req_ids.sort()
                handoff = handoff.model_copy(
                    update={
                        "requirement_ids": current_req_ids,
                        "payload": updated_payload,
                    }
                )

        # 6. Revalidation: If repair was performed, re-validate handoff
        if was_repaired:
            revalidated_issues = await self.run_validation_checks(task_id, canonical_reqs, handoff)
            repaired_issue_ids = {r.id for r in repaired_issues}
            repaired_req_ids = {r.requirement_id for r in repaired_issues if r.requirement_id}

            active_unresolved = []
            for iss in revalidated_issues:
                # If this issue was repaired as an unrequested UI constraint, do not re-flag
                if is_unrequested_ui_constraint(iss, task.original_request):
                    continue
                # If an omission was repaired, BUT revalidation still finds an explicit payload omission, keep it unresolved
                is_repaired_req = iss.requirement_id in repaired_req_ids or (
                    iss.requirement_id in canonical_map
                    and (
                        canonical_map[iss.requirement_id].id in repaired_req_ids
                        or canonical_map[iss.requirement_id].source_id in repaired_req_ids
                    )
                )
                if is_repaired_req and iss.issue_type == IssueType.omission:
                    if iss.observed_value == "Omitted from handoff specification":
                        active_unresolved.append(iss)
                    continue
                if iss.id in repaired_issue_ids:
                    continue
                active_unresolved.append(iss)

            final_issues = repaired_issues + active_unresolved
        else:
            final_issues = initial_issues

        # Ensure every issue has a concrete status (repaired or unresolved)
        final_issues = [
            iss.model_copy(update={"repair_status": RepairStatus.unresolved})
            if iss.repair_status != RepairStatus.repaired
            else iss
            for iss in final_issues
        ]

        # 7. Compute final handoff status using blocking classification
        blocking_unresolved = [
            iss for iss in final_issues
            if iss.repair_status != RepairStatus.repaired and is_blocking_issue(iss, task.original_request)
        ]

        review_required_issues = [
            iss for iss in final_issues
            if iss.repair_status != RepairStatus.repaired and (
                iss.issue_type == IssueType.implementation_gap
                or "uncertain" in iss.description.lower()
                or "review required" in iss.description.lower()
                or "manual review" in iss.description.lower()
            )
        ]

        if blocking_unresolved:
            final_status = HandoffStatus.blocked
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' blocked due to {len(blocking_unresolved)} blocking issues."
            event_type = "handoff_blocked"
        elif review_required_issues:
            final_status = HandoffStatus.review_required
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' requires review due to {len(review_required_issues)} uncertain specifications."
            event_type = "handoff_review_required"
        elif was_repaired:
            final_status = HandoffStatus.repaired
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' validated after automated specification repair."
            event_type = "handoff_validated"
        else:
            final_status = HandoffStatus.validated
            log_msg = f"Handoff from '{source_agent}' to '{target_agent}' validated with zero blocking issues."
            event_type = "handoff_validated"

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
