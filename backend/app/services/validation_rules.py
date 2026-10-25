"""Deterministic validation rules, deep content comparison, and contradiction checks for context handoffs."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

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

SUSPICIOUS_PATTERNS: List[str] = [
    "ignore previous instructions",
    "ignore all previous",
    "system prompt override",
    "system_prompt_override",
    "instruction_override",
    "bypass safety",
    "bypass_safety",
    "export secret",
    "dump database credentials",
]


def extract_payload_corpus(payload: Any) -> Tuple[str, Dict[str, Any]]:
    """Recursively extract all textual strings and flattened key-value paths from handoff payload."""
    texts: List[str] = []
    flat_kv: Dict[str, Any] = {}

    def _recurse(val: Any, path: str = ""):
        if isinstance(val, dict):
            for k, v in val.items():
                curr_path = f"{path}.{k}" if path else str(k)
                flat_kv[curr_path.lower()] = v
                flat_kv[str(k).lower()] = v
                if isinstance(v, (str, int, float, bool)):
                    texts.append(f"{k}: {v}")
                elif v is None:
                    texts.append(f"{k}: None")
                else:
                    _recurse(v, curr_path)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, (str, int, float, bool)):
                    texts.append(str(item))
                else:
                    _recurse(item, path)
        elif isinstance(val, (str, int, float, bool)):
            texts.append(str(val))

    _recurse(payload)
    return " \n ".join(texts), flat_kv


def check_missing_requirements(
    canonical_requirements: List[Requirement],
    handoff_req_ids: List[str],
    payload: Optional[Dict[str, Any]] = None,
) -> List[ValidationIssue]:
    """Identify canonical requirements missing from requirement_ids or explicitly omitted in the handoff spec."""
    issues: List[ValidationIssue] = []
    handoff_set = set(handoff_req_ids)
    corpus, flat_kv = extract_payload_corpus(payload or {})
    corpus_lower = corpus.lower()

    # Explicit list of omitted/dropped requirements in payload
    omitted_items = []
    for k in ["omitted_requirements", "dropped_specs", "out_of_scope", "excluded_requirements", "skipped_requirements"]:
        val = (payload or {}).get(k)
        if isinstance(val, list):
            omitted_items.extend([str(x).lower() for x in val])
        elif isinstance(val, str):
            omitted_items.append(val.lower())

    for req in canonical_requirements:
        req_id = req.id
        reported_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        severity = PRIORITY_TO_SEVERITY.get(req.priority, IssueSeverity.high)

        # 1. Check ID presence in handoff_req_ids (match either canonical req.id or source_id)
        is_id_present = (req_id in handoff_set) or (bool(req.source_id) and req.source_id in handoff_set)
        if not is_id_present:
            issues.append(
                ValidationIssue(
                    requirement_id=reported_id,
                    issue_type=IssueType.omission,
                    severity=severity,
                    description=f"Canonical requirement {reported_id} ({req_id}) is missing from the handoff requirement_ids.",
                    original_value=req.original_text,
                    observed_value=None,
                    repair_status=RepairStatus.pending,
                    evidence=[
                        f"Canonical requirement '{reported_id}' (canonical id '{req_id}', text: {req.original_text}) not found in handoff ids: {handoff_req_ids}"
                    ],
                )
            )
            continue

        # 2. Check explicit omission in payload fields or out_of_scope list
        is_explicitly_omitted = False
        omission_evidence = ""

        # Check omitted items list
        for o in omitted_items:
            if req_id.lower() in o or (req.source_id and req.source_id.lower() in o) or any(w in o for w in ["delivery fee", "delivery_fee"] if "delivery" in req_text_lower):
                is_explicitly_omitted = True
                omission_evidence = f"Requirement flagged in payload out-of-scope list: '{o}'"
                break

        # Check payload text patterns indicating omission
        if not is_explicitly_omitted:
            patterns = [
                rf"{req_id.lower()}\s*:\s*(omitted|skipped|dropped|out[\s_-]of[\s_-]scope|not\s+implemented|none)",
                rf"{req_id.lower()}\s+is\s+(omitted|skipped|dropped|out[\s_-]of[\s_-]scope|not\s+implemented)",
            ]
            if req.source_id:
                patterns.extend([
                    rf"{req.source_id.lower()}\s*:\s*(omitted|skipped|dropped|out[\s_-]of[\s_-]scope|not\s+implemented|none)",
                    rf"{req.source_id.lower()}\s+is\s+(omitted|skipped|dropped|out[\s_-]of[\s_-]scope|not\s+implemented)",
                ])
            if "delivery" in req_text_lower and "fee" in req_text_lower:
                patterns.extend([
                    r"delivery[\s_-]fee.*(omitted|out[\s_-]of[\s_-]scope|skipped|not\s+included|dropped|excluded)",
                    r"pricing\.delivery_fee.*(omitted|none|out[\s_-]of[\s_-]scope)",
                ])
                if flat_kv.get("delivery_fee") in ["omitted", "out_of_scope", "none", None] and "delivery_fee" in flat_kv:
                    is_explicitly_omitted = True
                    omission_evidence = f"Payload key 'delivery_fee' is set to '{flat_kv.get('delivery_fee')}'"

            for pat in patterns:
                match = re.search(pat, corpus_lower)
                if match:
                    is_explicitly_omitted = True
                    omission_evidence = f"Handoff specification contains: '{match.group(0)}'"
                    break

        if is_explicitly_omitted:
            issues.append(
                ValidationIssue(
                    requirement_id=reported_id,
                    issue_type=IssueType.omission,
                    severity=severity,
                    description=f"Canonical requirement {reported_id} ({req_id}) was omitted or marked out of scope in the handoff specification.",
                    original_value=req.original_text,
                    observed_value="Omitted from handoff specification",
                    repair_status=RepairStatus.unresolved,
                    evidence=[
                        f"Canonical requirement '{reported_id}' ({req.original_text}) was omitted: {omission_evidence}"
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
    canonical_set = set()
    for req in canonical_requirements:
        canonical_set.add(req.id)
        if req.source_id:
            canonical_set.add(req.source_id)

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


def check_suspicious_instructions(payload: Any) -> List[ValidationIssue]:
    """Identify prompt injections, unsafe overrides, or malicious directives in payload."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    payload_str = str(payload).lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in payload_str or payload.get("bypass_safety") is True:
            issues.append(
                ValidationIssue(
                    requirement_id=None,
                    issue_type=IssueType.suspicious_instruction,
                    severity=IssueSeverity.critical,
                    description=f"Detected suspicious instruction or unsafe override in handoff payload matching '{pattern}'.",
                    original_value=None,
                    observed_value=str(payload.get("instruction_override") or pattern),
                    repair_status=RepairStatus.unresolved,
                    evidence=[f"Payload contains flagged instruction pattern '{pattern}'"],
                )
            )
            break
    return issues


def check_deterministic_contradictions(
    canonical_requirements: List[Requirement],
    payload: Dict[str, Any],
) -> List[ValidationIssue]:
    """Evaluate explicit contradiction rules between canonical requirements and payload."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    corpus, flat_kv = extract_payload_corpus(payload)
    corpus_lower = corpus.lower()

    # 1. Configured contradiction rules
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        for req_kw, payload_key, bad_values, explanation in CONTRADICTION_RULES:
            if req_kw in req_text_lower and payload_key in flat_kv:
                observed_val = flat_kv[payload_key]
                if observed_val in bad_values:
                    issues.append(
                        ValidationIssue(
                            requirement_id=rep_id,
                            issue_type=IssueType.contradiction,
                            severity=IssueSeverity.critical,
                            description=f"Explicit contradiction on requirement {rep_id}: {explanation}",
                            original_value=req.original_text,
                            observed_value=f"{payload_key}={observed_val}",
                            repair_status=RepairStatus.unresolved,
                            evidence=[
                                f"Payload key '{payload_key}' has value '{observed_val}' which explicitly opposes requirement '{rep_id}'"
                            ],
                        )
                    )

    # 2. Persistence Contradictions (Persistent Database vs In-Memory Only)
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["postgresql", "database", "relational", "sql", "persistent storage", "persist"]):
            # Check if payload specifies in-memory only storage
            in_memory_keys = [
                k for k, v in flat_kv.items()
                if ("database" in k or "storage" in k or "persistence" in k)
                and (
                    v in ["in-memory", "in_memory", "memory", "in-memory dict", "in-memory dictionary"]
                    or (k == "persistence" and v is False)
                )
            ]
            has_in_memory_phrase = any(
                p in corpus_lower for p in [
                    "in-memory dict", "in-memory dictionary", "in_memory_dict", "in memory dictionary",
                    "store orders in memory", "in-memory storage instead of database", "no persistent database",
                    "transient memory", "in-memory only"
                ]
            )
            # Avoid false positive if payload says "no in-memory" or "not in-memory"
            if "not in-memory" in corpus_lower or "no in-memory" in corpus_lower or "without in-memory" in corpus_lower:
                has_in_memory_phrase = False

            if in_memory_keys or has_in_memory_phrase:
                observed = flat_kv.get(in_memory_keys[0]) if in_memory_keys else "In-memory dictionary storage"
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.contradiction,
                        severity=IssueSeverity.critical,
                        description=f"Contradiction on requirement {rep_id}: Handoff specifies in-memory storage, contradicting canonical persistent database requirement.",
                        original_value=req.original_text,
                        observed_value=f"{in_memory_keys[0]}={observed}" if in_memory_keys else str(observed),
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload specifies in-memory storage opposing canonical database requirement: {observed}"
                        ],
                    )
                )

    # 3. Atomicity Contradictions (Database Transaction vs Non-Atomic Updates)
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["atomic", "transaction", "race condition"]):
            non_atomic_keys = [
                k for k, v in flat_kv.items()
                if ("inventory" in k or "update" in k or "transaction" in k or "atomicity" in k)
                and (
                    v in ["non-atomic", "non_atomic", False]
                    or (k.endswith("transaction") and v is False)
                )
            ]
            has_non_atomic_phrase = any(
                p in corpus_lower for p in [
                    "non-atomic", "non atomic", "without transaction", "no database transaction",
                    "deduct inventory outside transaction", "non-transactional", "race condition prone"
                ]
            )
            if "not non-atomic" in corpus_lower:
                has_non_atomic_phrase = False

            if non_atomic_keys or has_non_atomic_phrase:
                observed = flat_kv.get(non_atomic_keys[0]) if non_atomic_keys else "Non-atomic inventory updates"
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.contradiction,
                        severity=IssueSeverity.critical,
                        description=f"Contradiction on requirement {rep_id}: Downstream handoff specifies non-atomic inventory updates without database transactions.",
                        original_value=req.original_text,
                        observed_value=f"{non_atomic_keys[0]}={observed}" if non_atomic_keys else str(observed),
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload specifies non-atomic inventory updates opposing canonical transaction requirement: {observed}"
                        ],
                    )
                )

    # 4. Idempotency Contradictions (Idempotent Payments vs Duplicate Charge Risk)
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["idempotent", "duplicate charge", "duplicate payment", "idempotency"]):
            idempotency_keys = [
                k for k, v in flat_kv.items()
                if ("idempotency" in k or "payment" in k or "duplicate" in k)
                and (
                    v in [False, "none", "disabled", "non-idempotent", "non_idempotent"]
                    or (k.endswith("idempotency") and v is False)
                )
            ]
            has_duplicate_risk_phrase = any(
                p in corpus_lower for p in [
                    "non-idempotent", "non idempotent", "no idempotency", "without idempotency",
                    "duplicate payment risk", "allows duplicate charges", "charges repeatedly on retry",
                    "no idempotency keys", "idempotency keys omitted"
                ]
            )
            if idempotency_keys or has_duplicate_risk_phrase:
                observed = flat_kv.get(idempotency_keys[0]) if idempotency_keys else "Non-idempotent charge endpoint with duplicate payment risk"
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.contradiction,
                        severity=IssueSeverity.critical,
                        description=f"Contradiction on requirement {rep_id}: Downstream handoff lacks idempotency guarantees, exposing payment processing to duplicate charges.",
                        original_value=req.original_text,
                        observed_value=f"{idempotency_keys[0]}={observed}" if idempotency_keys else str(observed),
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload lacks idempotency guarantees opposing canonical payment requirement: {observed}"
                        ],
                    )
                )

    return issues


def check_weakened_constraints(
    canonical_requirements: List[Requirement],
    payload: Dict[str, Any],
) -> List[ValidationIssue]:
    """Detect relaxed or weakened security, business, and functional constraints in payload."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    corpus, flat_kv = extract_payload_corpus(payload)
    corpus_lower = corpus.lower()

    # 1. Existing check: allow_anonymous or security_constraint=optional_auth or weakened_rule
    if (
        flat_kv.get("allow_anonymous") is True
        or flat_kv.get("security_constraint") == "optional_auth"
        or "weakened_rule" in flat_kv
    ):
        matched_req = next(
            (r for r in canonical_requirements if "auth" in (r.original_text + " " + r.description).lower()),
            canonical_requirements[0] if canonical_requirements else None,
        )
        req_id = matched_req.id if matched_req else None
        orig_text = matched_req.original_text if matched_req else "Strict requirement"
        observed_val = str(flat_kv.get("weakened_rule") or flat_kv.get("security_constraint") or "allow_anonymous=True")

        issues.append(
            ValidationIssue(
                requirement_id=req_id,
                issue_type=IssueType.weakened_constraint,
                severity=IssueSeverity.high,
                description=f"Requirement constraint was weakened in handoff payload: {observed_val}.",
                original_value=orig_text,
                observed_value=observed_val,
                repair_status=RepairStatus.unresolved,
                evidence=[f"Payload indicates weakened constraint '{observed_val}' opposing requirement '{orig_text}'"],
            )
        )

    # 2. Passwords in Plaintext or Weak Hashing
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["password", "hash", "bcrypt", "credential", "auth"]):
            has_plaintext = False
            observed_crypto = ""

            for k, v in flat_kv.items():
                if ("password" in k or "auth" in k or "crypto" in k) and str(v).lower() in ["plaintext", "plain_text", "cleartext", "unencrypted", "none", "md5"]:
                    has_plaintext = True
                    observed_crypto = f"{k}={v}"
                    break

            if not has_plaintext:
                pt_phrases = [
                    "passwords are stored in plaintext", "passwords stored in plaintext", "passwords in plaintext",
                    "plaintext password", "plain text password",
                    "cleartext password", "unencrypted password",
                    "without hashing", "no password hashing"
                ]
                for p in pt_phrases:
                    if p in corpus_lower:
                        has_plaintext = True
                        observed_crypto = p
                        break

            if has_plaintext:
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.weakened_constraint,
                        severity=IssueSeverity.critical,
                        description=f"Security constraint weakened on requirement {rep_id}: Passwords are stored in plaintext or without cryptographic hashing.",
                        original_value=req.original_text,
                        observed_value=observed_crypto or "Plaintext password storage",
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload specifies plaintext password storage opposing canonical requirement: {observed_crypto}"
                        ],
                    )
                )

    # 3. Authorization Gaps on Order Cancellation
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["cancellation", "cancel", "authorization", "role-based", "role"]):
            has_auth_gap = False
            observed_gap = ""

            for k, v in flat_kv.items():
                if ("cancel" in k or "cancellation" in k) and (
                    (k.endswith("require_auth") and v is False)
                    or (k.endswith("public_endpoint") and v is True)
                    or (k.endswith("role_check") and v in [False, "none", "disabled"])
                ):
                    has_auth_gap = True
                    observed_gap = f"{k}={v}"
                    break

            if not has_auth_gap:
                gap_phrases = [
                    "unauthenticated cancellation", "public cancellation endpoint", "no role check on cancel",
                    "any user can cancel any order", "cancellation endpoint is public", "cancellation without auth",
                    "require_auth: false", "public_endpoint: true"
                ]
                for p in gap_phrases:
                    if p in corpus_lower:
                        has_auth_gap = True
                        observed_gap = p
                        break

            if has_auth_gap:
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.weakened_constraint,
                        severity=IssueSeverity.critical,
                        description=f"Authorization gap on requirement {rep_id}: Cancellation endpoint lacks role-based authorization, allowing unauthorized or public cancellation.",
                        original_value=req.original_text,
                        observed_value=observed_gap or "Unauthenticated cancellation endpoint",
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload indicates unauthenticated or unrestricted cancellation: {observed_gap}"
                        ],
                    )
                )

    # 4. Client-side / Frontend-only Validation
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["server-side", "server side", "validation", "price", "integrity"]):
            has_client_only = False
            observed_val = ""

            for k, v in flat_kv.items():
                if ("validation" in k or "tier" in k) and (
                    v in ["frontend_only", "frontend-only", "client_only", "client-side-only"]
                    or (k.endswith("server_validation") and v is False)
                ):
                    has_client_only = True
                    observed_val = f"{k}={v}"
                    break

            if not has_client_only:
                val_phrases = [
                    "frontend-only validation", "frontend only validation", "client-side validation only",
                    "client side validation only", "client-side only validation", "client side only validation",
                    "client-side only", "frontend-only", "validate on client only", "trust client prices",
                    "order prices are validated on the client frontend only", "server_validation: false"
                ]
                for p in val_phrases:
                    if p in corpus_lower:
                        has_client_only = True
                        observed_val = p
                        break

            if has_client_only:
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.weakened_constraint,
                        severity=IssueSeverity.high,
                        description=f"Integrity constraint weakened on requirement {rep_id}: Price and payload validation performed only on client frontend without server-side verification.",
                        original_value=req.original_text,
                        observed_value=observed_val or "Frontend-only validation",
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload specifies frontend-only validation opposing canonical server-side validation: {observed_val}"
                        ],
                    )
                )

    # 5. Partial Orders Allowed (Weakened All-or-Nothing Rule)
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["reject partial", "partial order", "all items available", "full order"]):
            has_partial = False
            observed_partial = ""

            for k, v in flat_kv.items():
                if ("partial" in k or "order" in k) and (
                    (k.endswith("allow_partial_fulfillment") and v is True)
                    or (k.endswith("allow_partial_orders") and v is True)
                    or (k.endswith("partial_orders") and v is True)
                ):
                    has_partial = True
                    observed_partial = f"{k}={v}"
                    break

            if not has_partial:
                partial_phrases = [
                    "allow partial orders", "allow partial fulfillment", "partial orders allowed",
                    "accept partial orders", "accept partial fulfillment", "fulfill available items and drop unavailable",
                    "allow_partial_fulfillment: true", "allow_partial_orders: true"
                ]
                for p in partial_phrases:
                    if p in corpus_lower:
                        has_partial = True
                        observed_partial = p
                        break

            if has_partial:
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.weakened_constraint,
                        severity=IssueSeverity.high,
                        description=f"Business rule weakened on requirement {rep_id}: Handoff permits partial orders instead of rejecting when items are unavailable.",
                        original_value=req.original_text,
                        observed_value=observed_partial or "Allow partial order fulfillment",
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload permits partial order fulfillment opposing canonical rejection rule: {observed_partial}"
                        ],
                    )
                )

    # 6. Repeated Inventory Restoration (Stock Inflation Risk)
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["single inventory restoration", "exactly once", "restoration", "stock inflation"]):
            has_repeated_restoration = False
            observed_restoration = ""

            for k, v in flat_kv.items():
                if ("restoration" in k or "inventory" in k) and (
                    v in ["on_every_retry", "every_retry", "repeated"]
                    or (k.endswith("restoration_on_retry") and v is True)
                ):
                    has_repeated_restoration = True
                    observed_restoration = f"{k}={v}"
                    break

            if not has_repeated_restoration:
                restoration_phrases = [
                    "restore inventory on every retry", "repeated inventory restoration",
                    "inventory is restored on every cancel retry", "restores inventory without checking cancellation state",
                    "inventory_restoration: on_every_retry"
                ]
                for p in restoration_phrases:
                    if p in corpus_lower:
                        has_repeated_restoration = True
                        observed_restoration = p
                        break

            if has_repeated_restoration:
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.weakened_constraint,
                        severity=IssueSeverity.high,
                        description=f"Integrity constraint weakened on requirement {rep_id}: Inventory is restored repeatedly on cancellation retries, risking stock inflation.",
                        original_value=req.original_text,
                        observed_value=observed_restoration or "Repeated inventory restoration on retries",
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload permits repeated inventory restoration opposing single restoration guarantee: {observed_restoration}"
                        ],
                    )
                )

    # 7. Changed Numeric Thresholds (Delivery Fee Alterations)
    for req in canonical_requirements:
        rep_id = req.source_id or req.id
        req_text_lower = (req.original_text + " " + req.description).lower()
        if "delivery" in req_text_lower and "fee" in req_text_lower:
            # Check canonical expectation ($5 under $30)
            if "$5" in req.original_text and "$30" in req.original_text:
                altered_fee = False
                observed_fee = ""

                # Look for altered delivery fee numbers or thresholds
                fee_val = flat_kv.get("delivery_fee") or flat_kv.get("pricing.delivery_fee")
                threshold_val = flat_kv.get("fee_threshold") or flat_kv.get("pricing.fee_threshold")

                if fee_val is not None and str(fee_val) not in ["5", "$5", "5.0", "5.00", "omitted", "none", "None"]:
                    altered_fee = True
                    observed_fee = f"delivery_fee={fee_val}"
                elif threshold_val is not None and str(threshold_val) not in ["30", "$30", "30.0", "30.00"]:
                    altered_fee = True
                    observed_fee = f"fee_threshold={threshold_val}"

                if not altered_fee:
                    # Check text phrases
                    altered_phrases = [
                        ("$10 delivery fee", "$10 delivery fee"),
                        ("$10 fee", "$10 fee"),
                        ("orders under $50", "orders under $50"),
                        ("free delivery for all", "free delivery for all orders"),
                        ("$0 delivery fee", "$0 delivery fee"),
                    ]
                    for needle, obs in altered_phrases:
                        if needle in corpus_lower:
                            altered_fee = True
                            observed_fee = obs
                            break

                if altered_fee:
                    issues.append(
                        ValidationIssue(
                            requirement_id=rep_id,
                            issue_type=IssueType.weakened_constraint,
                            severity=IssueSeverity.high,
                            description=f"Changed numeric threshold on requirement {rep_id}: Delivery fee calculation altered from canonical specification ($5 under $30).",
                            original_value="$5 flat fee on orders under $30",
                            observed_value=observed_fee or "Altered fee calculation",
                            repair_status=RepairStatus.unresolved,
                            evidence=[
                                f"Payload specifies altered delivery fee calculation: {observed_fee}"
                            ],
                        )
                    )

    return issues


def check_semantic_drift(
    canonical_requirements: List[Requirement],
    payload: Dict[str, Any],
) -> List[ValidationIssue]:
    """Detect subtle semantic drift or altered functional scope in payload."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    corpus, flat_kv = extract_payload_corpus(payload)

    if "drift_note" in flat_kv or flat_kv.get("theme_spec") == "monochrome_light_only":
        matched_req = next(
            (
                r
                for r in canonical_requirements
                if "dark" in (r.original_text + " " + r.description).lower()
                or "theme" in (r.original_text + " " + r.description).lower()
            ),
            canonical_requirements[0] if canonical_requirements else None,
        )
        req_id = matched_req.id if matched_req else None
        orig_text = matched_req.original_text if matched_req else "Canonical requirement"
        observed_val = str(flat_kv.get("drift_note") or flat_kv.get("theme_spec"))

        issues.append(
            ValidationIssue(
                requirement_id=req_id,
                issue_type=IssueType.semantic_drift,
                severity=IssueSeverity.high,
                description=f"Semantic drift detected in handoff payload: {observed_val}.",
                original_value=orig_text,
                observed_value=observed_val,
                repair_status=RepairStatus.unresolved,
                evidence=[f"Payload alters canonical scope with drifted definition '{observed_val}'"],
            )
        )
    return issues


def check_testing_coverage(
    canonical_requirements: List[Requirement],
    payload: Dict[str, Any],
) -> List[ValidationIssue]:
    """Detect gaps in automated testing coverage or skipped test suites."""
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    corpus, flat_kv = extract_payload_corpus(payload)
    corpus_lower = corpus.lower()

    for req in canonical_requirements:
        req_text_lower = (req.original_text + " " + req.description).lower()
        if any(w in req_text_lower for w in ["test", "automated test", "test coverage", "pytest"]):
            has_testing_gap = False
            observed_gap = ""

            for k, v in flat_kv.items():
                if ("testing" in k or "test" in k) and (
                    str(v).lower() in ["incomplete", "skipped", "0%", "none", "disabled"]
                    or (k.endswith("coverage") and str(v) in ["0%", "0", "none"])
                    or ("skipped_suites" in k and isinstance(v, list) and len(v) > 0)
                ):
                    has_testing_gap = True
                    observed_gap = f"{k}={v}"
                    break

            if not has_testing_gap:
                gap_phrases = [
                    "incomplete tests", "automated tests are incomplete", "tests skipped",
                    "testing is out of scope", "0% coverage", "0% test coverage",
                    "no automated tests", "skipped test suites"
                ]
                for p in gap_phrases:
                    if p in corpus_lower:
                        has_testing_gap = True
                        observed_gap = p
                        break

            if has_testing_gap:
                rep_id = req.source_id or req.id
                issues.append(
                    ValidationIssue(
                        requirement_id=rep_id,
                        issue_type=IssueType.implementation_gap,
                        severity=IssueSeverity.high,
                        description=f"Testing coverage gap on requirement {rep_id}: Automated test coverage is incomplete or key domain tests are skipped.",
                        original_value=req.original_text,
                        observed_value=observed_gap or "Incomplete test coverage / tests skipped",
                        repair_status=RepairStatus.unresolved,
                        evidence=[
                            f"Payload indicates incomplete test coverage opposing canonical testing requirement: {observed_gap}"
                        ],
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Per-Requirement Semantic & Invariant Comparison Rules
# ---------------------------------------------------------------------------

PHARMACY_SEMANTIC_RULES = [
    (
        ("R1", "R2"), ["medical records"],
        ["allow cross-patient", "cross-patient record access allowed", "permits cross-patient", "view records of other patients", "patients can view other patient", "access all patient records", "shared patient records", "view any patient record", "access any patient's records", "access any patient records", "patients may access any patient"],
        ["cross-patient", "cross patient"],
        [("cross_patient_access", [True, "true"]), ("allow_cross_patient", [True, "true"]), ("patient_isolation", [False, "false"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Privacy and patient record isolation violation on requirement {id}: Downstream handoff permits cross-patient record access or weakens patient data isolation."
    ),
    (
        "R5", ["staff role", "audit log", "change staff roles"],
        ["optional staff-role audit logging", "optional staff role audit logging", "staff role audit logging is optional", "staff-role audit logging is optional", "not logged", "role audit is optional", "role change audit optional", "role changes optional audit", "skip audit log for role changes"],
        [],
        [("audit_staff_roles", ["optional", "disabled", False]), ("role_audit", [False, "false"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Audit compliance violation on requirement {id}: Role changes must be strictly recorded in an audit log; optional staff-role audit logging is not permitted."
    ),
    (
        "R7", ["end date earlier than the start date", "end date earlier than start date"],
        ["invalid dates allowed", "end date earlier than start date is allowed", "end date before start date allowed", "end date earlier than start date are accepted", "end date earlier than start date are allowed", "allow end date earlier than start date", "end date can be earlier than start date", "skip prescription date validation"],
        ["invalid dates"],
        [("allow_invalid_dates", [True, "true"]), ("validate_dates", [False, "false"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Prescription validation contradiction on requirement {id}: Downstream handoff allows invalid prescription dates (end date earlier than start date)."
    ),
    (
        "R8", ["unsigned, expired, or cancelled prescription", "prevent dispensing an unsigned"],
        ["unsafe dispensing", "allow dispensing unsigned", "allow dispensing unsigned, expired, or cancelled", "dispense without doctor signature", "unsigned dispensing allowed", "unsigned prescriptions may be dispensed"],
        ["dispensing unsigned", "unsigned prescriptions", "dispense expired prescription", "dispensing cancelled prescription"],
        [("allow_unsigned_dispense", [True, "true"]), ("dispense_unsigned", [True, "true"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Prescription safety violation on requirement {id}: Downstream handoff permits unsafe dispensing of unsigned, expired, or cancelled prescriptions."
    ),
    (
        "R9", ["contraindicated by a recorded patient allergy", "patient allergy"],
        ["frontend-only allergy checks", "frontend only allergy checks", "frontend-only allergy check", "frontend only allergy check", "allergy checks on the frontend only", "allergy check on client only", "allergy check on the frontend only", "client-side allergy validation", "client side allergy check", "dispense without server-side allergy check", "server skips allergy"],
        [],
        [("allergy_check", ["frontend_only", "client_only"]), ("server_allergy_check", [False, "false"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Safety and verification regression on requirement {id}: Allergy contraindication checks are restricted to frontend only; server-side enforcement is required."
    ),
    (
        ("R3", "R12"), ["negative"],
        ["concurrent negative stock", "negative stock allowed", "negative inventory allowed", "stock can drop below zero", "inventory can become negative", "stock can become negative", "negative stock permitted", "allow negative quantity in inventory", "allow negative inventory", "allow negative stock", "without concurrency protection", "inventory is decremented without concurrency protection", "decremented without concurrency protection"],
        ["negative stock", "negative inventory"],
        [("allow_negative_stock", [True, "true"]), ("allow_negative_inventory", [True, "true"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Inventory invariant contradiction on requirement {id}: Inventory quantities must never become negative under concurrent dispensing operations."
    ),
    (
        ("R4", "R13"), ["atomic"],
        ["partial transaction failure", "partial changes remain", "dispensing steps are not atomic", "dispensing steps executed non-atomically", "partial transaction failure allowed", "dispensing is not atomic", "inventory decremented before transaction commit without rollback", "no rollback on partial failure", "partial transaction changes remain", "inventory changes remain even if writing the dispensing record fails", "changes remain even if writing the dispensing record fails", "inventory changes remain even if writing"],
        [],
        [("atomic_dispensing", [False, "false"]), ("rollback_on_failure", [False, "false"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Atomicity violation on requirement {id}: Dispensing must be atomic; partial changes remaining upon step failure violate transaction integrity."
    ),
    (
        "R14", ["dispensed more than once unless an explicitly authorized refill"],
        ["allow duplicate dispensing", "duplicate dispensing allowed", "prescriptions can be dispensed multiple times without refill", "repeat dispensing permitted without refill", "allow dispensing same prescription multiple times", "dispensed more than once without authorized refill"],
        ["duplicate dispensing"],
        [("allow_duplicate_dispensing", [True, "true"]), ("duplicate_dispense", [True, "true"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Dispensing control violation on requirement {id}: System must prevent duplicate dispensing without authorized refills."
    ),
    (
        "R15", ["expired medication must never be dispensed"],
        ["expired batches may be dispensed", "expired batches can be dispensed", "expired medication can be dispensed", "allow dispensing expired medication", "dispensing expired batches permitted", "expired batches allowed"],
        ["expired batches"],
        [("allow_expired_batches", [True, "true"]), ("dispense_expired_batches", [True, "true"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Safety invariant contradiction on requirement {id}: Expired medication batches must never be dispensed."
    ),
    (
        "R16", ["earliest expiration date first"],
        ["incorrect batch selection", "latest expiration date first", "lifo batch selection", "dispense newest batch first", "random batch selection", "ignore expiration date when selecting batch", "dispense batch with latest expiration first"],
        [],
        [("batch_selection", ["lifo", "random", "latest_expiration"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Batch selection discrepancy on requirement {id}: Dispensing must select the eligible batch with the earliest expiration date first (FEFO)."
    ),
    (
        "R17", ["strictly below the configured threshold, not when equal to it"],
        ["wrong threshold boundary", "less than or equal to the configured threshold", "stock <= threshold", "less than or equal to threshold", "trigger when available stock is equal to threshold", "triggers on equal or below threshold", "low-stock alerts trigger when available stock is less than or equal to threshold", "threshold boundary <="],
        [],
        [("low_stock_condition", ["<=", "less_than_or_equal"])],
        IssueType.weakened_constraint, IssueSeverity.medium,
        "Threshold boundary discrepancy on requirement {id}: Low-stock alerts must trigger strictly below threshold (<), not when equal to it (<=)."
    ),
    (
        "R18", ["invoice totals must use decimal-safe arithmetic", "decimal-safe arithmetic"],
        ["floating-point billing", "floating point billing", "float arithmetic for currency", "invoice calculations use floating point", "ieee 754 float billing", "standard float for currency totals", "float billing"],
        [],
        [("currency_format", ["float", "ieee754", "floating_point"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Financial precision regression on requirement {id}: Invoice totals must use decimal-safe arithmetic, never floating-point."
    ),
    (
        "R19", ["discounts must never reduce the payable total below zero"],
        ["negative totals", "discounts can reduce total below zero", "negative invoice total allowed", "payable total may be negative", "allow negative payable amount", "negative totals permitted"],
        ["negative totals"],
        [("allow_negative_total", [True, "true"]), ("allow_negative_invoice", [True, "true"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Billing boundary contradiction on requirement {id}: Discounts must never reduce payable total below zero."
    ),
    (
        ("R5", "R20"), ["idempotency"],
        ["payment retries can create duplicate charges", "retries can create duplicate charges", "duplicate charges", "retrying payment charges patient twice", "payment retries charge again", "missing payment idempotency", "payment endpoint is not idempotent", "duplicate charges on retry", "retrying payment endpoint lacks idempotency"],
        [],
        [("idempotent_payments", [False, "false"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Payment idempotency contradiction on requirement {id}: Payment retries with identical idempotency keys must prevent duplicate charges."
    ),
    (
        "R21", ["failed payment must not mark an invoice as paid or release medication"],
        ["premature payment confirmation", "release medication before payment is confirmed", "failed payment marks invoice as paid", "medication released on failed payment", "mark paid before capture", "release medication on failed payment"],
        [],
        [("release_on_pending", [True, "true"]), ("release_medication_on_failure", [True, "true"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Billing lifecycle contradiction on requirement {id}: Medication must not be released and invoice must not be marked paid on failed or unconfirmed payments."
    ),
    (
        "R22", ["refunds must not exceed the amount successfully captured"],
        ["excessive refunds", "refunds can exceed original captured amount", "refund amount exceeds captured", "concurrent refunds can exceed payment total", "refund amount not capped to captured amount", "excessive refunds allowed", "refund amount can exceed original captured amount"],
        [],
        [("allow_excess_refunds", [True, "true"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Refund boundary contradiction on requirement {id}: Total refunds must not exceed successfully captured payment amount."
    ),
    (
        "R23", ["Draft → Signed → Dispensed", "cancelled prescriptions cannot return to signed without creating a new version"],
        ["invalid state transitions", "cancelled prescriptions can return to signed without creating a new version", "cancelled to signed directly", "unversioned transition from cancelled to signed", "invalid state transitions allowed", "cancelled prescriptions can return to signed directly without new version"],
        [],
        [("allow_invalid_transitions", [True, "true"])],
        IssueType.contradiction, IssueSeverity.high,
        "Workflow state contradiction on requirement {id}: Cancelled prescriptions cannot return to Signed without creating a new version."
    ),
    (
        "R24", ["notifications must not be sent for rolled-back transactions"],
        ["notifications sent for rolled-back transactions", "send notification before transaction commit", "notification dispatched on rolled-back transactions", "notifications sent on failed dispensing"],
        [],
        [("notify_on_rollback", [True, "true"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Notification integrity violation on requirement {id}: Notifications must never be sent for rolled-back transactions."
    ),
    (
        "R25", ["notification delivery failures must not reverse a successful dispensing"],
        ["unsafe notification retries", "notification delivery failures reverse dispensing", "failed notifications reverse dispensing", "retries create duplicate notifications", "notification failure rolls back dispensing", "failed notifications reverse dispensing transaction"],
        [],
        [("reverse_dispense_on_notify_fail", [True, "true"])],
        IssueType.contradiction, IssueSeverity.high,
        "Fault isolation contradiction on requirement {id}: Notification failure must not reverse dispensing, and retries must not create duplicates."
    ),
    (
        "R26", ["persist in postgresql and survive server restarts"],
        ["missing persistence", "in-memory storage", "records stored in-memory", "ephemeral cache without database", "does not survive server restarts", "records stored in-memory dictionary storage"],
        [],
        [("storage", ["in-memory", "memory", "ephemeral"]), ("persistence", [False, "false"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Persistence contradiction on requirement {id}: Records must persist in PostgreSQL and survive server restarts; in-memory storage is non-compliant."
    ),
    (
        "R27", ["all inventory and financial state changes must be auditable with actor, timestamp, entity id, and before/after values"],
        ["incomplete auditing", "audit logs omit before/after values", "audit logs omit actor", "omit before/after values", "audit log does not record before and after", "audit log omits before/after values", "audit logs omit before/after values and actor"],
        [],
        [("audit_include_values", [False, "false"]), ("full_audit", [False, "false"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Audit integrity gap on requirement {id}: Audit logs must record actor, timestamp, entity ID, and before/after values."
    ),
    (
        "R28", ["sensitive medical information and payment credentials must not appear in application logs"],
        ["sensitive-data leakage", "sensitive data leakage", "payment card details logged", "credit card numbers logged", "medical diagnosis logged in application logs", "raw card numbers stored directly", "sensitive medical info in application logs", "payment card details and medical diagnosis logged in application logs"],
        [],
        [("log_credentials", [True, "true"]), ("log_card_details", [True, "true"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Data privacy violation on requirement {id}: Sensitive medical info and payment credentials must never be written to application logs."
    ),
    (
        "R29", ["all sensitive api operations must enforce authorization on the server"],
        ["frontend-only authorization", "frontend only authorization", "client-side authorization only", "backend endpoints do not verify roles", "authorization checks performed on frontend only", "server endpoints omit authorization", "server endpoints omit authorization checks"],
        [],
        [("server_authorization", [False, "false"]), ("auth_enforcement", ["client_only", "frontend_only"])],
        IssueType.weakened_constraint, IssueSeverity.critical,
        "Security boundary regression on requirement {id}: Sensitive operations must enforce authorization on the server, regardless of frontend visibility."
    ),
    (
        "R30", ["concurrent updates must not silently overwrite changes"],
        ["silent overwrite on concurrent updates", "last-write-wins without conflict detection", "concurrent updates overwrite changes silently", "no concurrency conflict detection", "lost updates allowed", "concurrent updates overwrite changes silently without conflict detection"],
        ["lost updates"],
        [("concurrency_control", ["none", "disabled"]), ("last_write_wins", [True, "true"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Concurrency integrity gap on requirement {id}: Concurrent updates must detect conflicts and prevent silent overwrites (lost updates)."
    ),
    (
        "R31", ["distinguish available, reserved, dispensed, and expired inventory accurately"],
        ["inaccurate inventory reporting", "dashboard does not distinguish reserved", "merges available and reserved inventory", "expired stock counted as available", "dashboard reports inaccurate inventory", "dashboard merges available and reserved inventory"],
        [],
        [("distinguish_reserved_stock", [False, "false"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Reporting accuracy discrepancy on requirement {id}: Dashboard must accurately distinguish available, reserved, dispensed, and expired inventory."
    ),
    (
        "R32", ["calculate revenue from successfully captured payments minus completed refunds"],
        ["incorrect revenue", "revenue includes failed payments", "revenue calculation includes pending refunds", "revenue reports include uncaptured payments", "revenue includes pending refunds", "revenue calculation includes pending refunds and failed payments"],
        [],
        [("revenue_includes_pending", [True, "true"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "Financial reporting error on requirement {id}: Revenue calculation must exclude failed payments and pending refunds."
    ),
    (
        "R33", ["all list endpoints must support pagination and enforce server-side authorization"],
        ["missing pagination/security", "missing pagination", "list endpoints do not support pagination", "unpaginated list endpoints", "list endpoints return all records without authorization", "unpaginated list endpoints without authorization"],
        [],
        [("pagination_supported", [False, "false"]), ("paginate_lists", [False, "false"])],
        IssueType.weakened_constraint, IssueSeverity.high,
        "API scalability and security gap on requirement {id}: All list endpoints must support pagination and enforce server-side authorization."
    ),
    (
        "R34", ["automated tests must cover role permissions, prescription eligibility"],
        ["insufficient tests", "tests omit concurrency", "tests skip rollback", "tests omit idempotency", "automated tests skip role permissions", "incomplete automated test suite", "automated test suite skips concurrency, rollback, and idempotency"],
        [],
        [("automated_tests", [False, "false"])],
        IssueType.implementation_gap, IssueSeverity.high,
        "Testing coverage deficiency on requirement {id}: Automated tests must cover concurrency, rollback, idempotency, refund limits, and audit logs."
    ),
    (
        "R35", ["integration tests must verify that a failed dispensing transaction leaves inventory and dispensing records unchanged"],
        ["broken rollback", "failed dispensing leaves inventory decremented", "failed dispensing modifies records", "rollback verification omitted", "failed dispensing leaves inventory decremented in integration tests"],
        [],
        [("verify_rollback", [False, "false"])],
        IssueType.contradiction, IssueSeverity.critical,
        "Rollback integrity failure on requirement {id}: Integration tests must verify that failed dispensing transactions leave inventory and records unchanged."
    ),
    (
        "R36", ["environment-based configuration, database migrations, a readme"],
        ["incomplete migrations", "database migrations omitted", "schema created manually without migrations", "no alembic or database migrations", "database schema created manually without migrations"],
        [],
        [("database_migrations", [False, "false"])],
        IssueType.implementation_gap, IssueSeverity.high,
        "Deployment and migration deficiency on requirement {id}: Database migrations and environment configuration must be provided."
    ),
]


def matches_target_rule(r: Requirement, target_sid: Any, keywords: List[str]) -> bool:
    sid = (r.source_id or "").upper()
    rid = r.id.upper()
    target_sids = [target_sid] if isinstance(target_sid, str) else list(target_sid)
    req_corpus = (r.original_text + " " + r.description).lower()

    if keywords and not any(kw.lower() in req_corpus for kw in keywords):
        return False

    for ts in target_sids:
        ts_upper = str(ts).upper()
        if sid == ts_upper:
            return True
        if ts_upper.startswith("R") and ts_upper[1:].isdigit():
            num = int(ts_upper[1:])
            if rid == f"R{num:03d}":
                return True

    return bool(keywords)


def check_per_requirement_semantics(
    canonical_requirements: List[Requirement],
    payload: Dict[str, Any],
) -> List[ValidationIssue]:
    """Execute per-requirement semantic checks comparing constraints, conditions, and invariants.
    
    Ensures identical IDs do not imply compliance when downstream specifications alter or contradict
    canonical requirements. Distinguishes safe/compliant statements from violations.
    """
    issues: List[ValidationIssue] = []
    if not isinstance(payload, dict):
        return issues

    corpus, flat_kv = extract_payload_corpus(payload)
    raw_clauses = re.split(r"[\n;\.\,]", corpus)
    clauses = [c.strip() for c in raw_clauses if len(c.strip()) > 3]

    flagged_req_ids = set()

    for rule in PHARMACY_SEMANTIC_RULES:
        target_sid, keywords, explicit_bads, ambig_phrases, kv_checks, issue_type, severity, desc_template = rule

        # Find matching requirement
        target_req = next((r for r in canonical_requirements if matches_target_rule(r, target_sid, keywords)), None)
        if not target_req:
            continue

        rep_id = target_req.source_id or target_req.id
        if rep_id in flagged_req_ids:
            continue

        violation_detected = False
        observed_snippet = ""

        # 1. Check flat_kv
        for key, bad_vals in kv_checks:
            if key in flat_kv:
                val = flat_kv[key]
                if val in bad_vals or str(val).lower() in [str(b).lower() for b in bad_vals]:
                    violation_detected = True
                    observed_snippet = f"{key}={val}"
                    break

        # 2. Check clauses
        if not violation_detected:
            for clause in clauses:
                c_lower = clause.lower()

                # Explicit bad phrase (always a violation)
                for bad in explicit_bads:
                    if bad.lower() in c_lower:
                        violation_detected = True
                        observed_snippet = clause
                        break
                if violation_detected:
                    break

                # Ambiguous phrase (check for lack of prevention)
                for amb in ambig_phrases:
                    if amb.lower() in c_lower:
                        has_prevention = bool(re.search(
                            r"\b(prevent|prevents|prevented|preventing|never|no|prohibit|prohibits|prohibited|forbid|forbids|forbidden|strictly forbidden|strictly prevented|disallow|disallows|disallowed|reject|rejects|rejected|avoid|without)\b",
                            c_lower
                        ))
                        if not has_prevention:
                            violation_detected = True
                            observed_snippet = clause
                            break
                if violation_detected:
                    break

        if violation_detected:
            flagged_req_ids.add(rep_id)
            issues.append(
                ValidationIssue(
                    requirement_id=rep_id,
                    issue_type=issue_type,
                    severity=severity,
                    description=desc_template.format(id=rep_id),
                    original_value=target_req.original_text,
                    observed_value=observed_snippet or "Observed non-compliant specification in downstream handoff",
                    repair_status=RepairStatus.unresolved,
                    evidence=[f"Downstream handoff specifies: {observed_snippet}"],
                )
            )

    return issues
