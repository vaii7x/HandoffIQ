"""Deterministic validation rules and contradiction checks for context handoffs."""

from typing import Any, Dict, List, Optional, Tuple
from app.models.handoff import IssueSeverity, IssueType, RepairStatus, ValidationIssue
from app.models.requirement import Requirement, RequirementPriority


# Mapping of requirement priorities to omission issue severity
PRIORITY_TO_SEVERITY: Dict[RequirementPriority, IssueSeverity] = {
    RequirementPriority.critical: IssueSeverity.critical,
    RequirementPriority.high: IssueSeverity.high,
    RequirementPriority.medium: IssueSeverity.medium,
    RequirementPriority.low: IssueSeverity.low,
}

# Configured explicit contradiction rules
# (canonical_keyword, payload_key, contradicting_values, explanation)
CONTRADICTION_RULES: List[Tuple[str, str, List[Any], str]] = [
    (
        "auth",
        "auth_enabled",
        [False, "false", "disabled", "none"],
        "Payload explicitly disables authentication while canonical requirement mandates auth.",
    ),
    (
        "auth",
        "skip_auth",
        [True, "true"],
        "Payload explicitly skips authentication while canonical requirement mandates auth.",
    ),
    (
        "dark theme",
        "dark_mode",
        [False, "false", "disabled", "light_only"],
        "Payload disables dark mode while canonical requirement mandates dark theme support.",
    ),
    (
        "dark theme",
        "theme",
        ["light_only", "light-only", "disabled"],
        "Payload restricts theme to light only while canonical requirement mandates dark theme support.",
    ),
    (
        "responsive",
        "responsive_layout",
        [False, "false", "disabled", "desktop_only"],
        "Payload disables responsive layout while canonical requirement mandates responsive support.",
    ),
]


def check_missing_requirements(
    canonical_requirements: List[Requirement],
    handoff_req_ids: List[str],
) -> List[ValidationIssue]:
    """Identify canonical requirements that are missing from the handoff."""
    issues: List[ValidationIssue] = []
    handoff_set = set(handoff_req_ids)

    for req in canonical_requirements:
        if req.id not in handoff_set:
            severity = PRIORITY_TO_SEVERITY.get(req.priority, IssueSeverity.high)
            issues.append(
                ValidationIssue(
                    requirement_id=req.id,
                    issue_type=IssueType.omission,
                    severity=severity,
                    description=f"Canonical requirement {req.id} is missing from the handoff requirement_ids.",
                    original_value=req.original_text,
                    observed_value=None,
                    repair_status=RepairStatus.pending,
                    evidence=[
                        f"Canonical requirement '{req.id}' ({req.original_text}) not found in handoff ids: {handoff_req_ids}"
                    ],
                )
            )
    return issues


def check_unknown_requirements(
    canonical_requirements: List[Requirement],
    handoff_req_ids: List[str],
) -> List[ValidationIssue]:
    """Identify requirement IDs in the handoff that do not exist in canonical task records."""
    issues: List[ValidationIssue] = []
    canonical_set = {req.id for req in canonical_requirements}

    for req_id in handoff_req_ids:
        if req_id not in canonical_set:
            issues.append(
                ValidationIssue(
                    requirement_id=req_id,
                    issue_type=IssueType.invented_requirement,
                    severity=IssueSeverity.high,
                    description=f"Requirement ID '{req_id}' is not a registered canonical requirement for this task.",
                    original_value=None,
                    observed_value=req_id,
                    repair_status=RepairStatus.unresolved,
                    evidence=[
                        f"Invented or unrecognized ID '{req_id}' present in handoff requirement_ids"
                    ],
                )
            )
    return issues


def check_payload_structure(payload: Any) -> List[ValidationIssue]:
    """Verify handoff payload is a non-empty structured JSON object."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        issues.append(
            ValidationIssue(
                requirement_id=None,
                issue_type=IssueType.schema_error,
                severity=IssueSeverity.critical,
                description=f"Handoff payload must be a JSON dictionary, got {type(payload).__name__}.",
                original_value="dict",
                observed_value=type(payload).__name__,
                repair_status=RepairStatus.unresolved,
                evidence=[f"Payload type is {type(payload).__name__}"],
            )
        )
    elif len(payload) == 0:
        issues.append(
            ValidationIssue(
                requirement_id=None,
                issue_type=IssueType.schema_error,
                severity=IssueSeverity.medium,
                description="Handoff payload is empty dictionary; expected structured context or instructions.",
                original_value="non-empty dict",
                observed_value="empty dict",
                repair_status=RepairStatus.unresolved,
                evidence=["Payload dictionary contains zero keys"],
            )
        )
    return issues


def check_deterministic_contradictions(
    canonical_requirements: List[Requirement],
    payload: Dict[str, Any],
) -> List[ValidationIssue]:
    """Evaluate configured deterministic contradiction rules between canonical requirements and payload."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    for req in canonical_requirements:
        req_text_lower = (req.original_text + " " + req.description).lower()

        for req_kw, payload_key, bad_values, explanation in CONTRADICTION_RULES:
            if req_kw in req_text_lower and payload_key in payload:
                observed_val = payload[payload_key]
                if observed_val in bad_values:
                    issues.append(
                        ValidationIssue(
                            requirement_id=req.id,
                            issue_type=IssueType.contradiction,
                            severity=IssueSeverity.critical,
                            description=f"Explicit contradiction on requirement {req.id}: {explanation}",
                            original_value=req.original_text,
                            observed_value=f"{payload_key}={observed_val}",
                            repair_status=RepairStatus.unresolved,
                            evidence=[
                                f"Payload key '{payload_key}' has value '{observed_val}' which explicitly opposes requirement '{req.id}'"
                            ],
                        )
                    )

    return issues
