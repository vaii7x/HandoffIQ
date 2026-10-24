# Semantic Validation Provider - AI Developer Specification

## 1. Overview

HandoffIQ uses a dual-layer validation model for agent context handoffs:
1. **Deterministic Layer (Backend)**: Evaluates structural integrity, missing requirement IDs, invented IDs, schema errors, and explicit logical contradictions.
2. **Semantic Layer (AI Developer)**: Evaluates natural language context, subtle semantic drift, weakened constraints, and implementation gaps across multi-agent handoffs.

This document specifies the interface and integration requirements for the **AI Developer** implementing the Gemini-powered semantic validation engine.

---

## 2. Integration Point & Interface

The backend defines the abstract interface in `app.services.semantic_provider.SemanticValidationProvider`:

```python
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from app.models.handoff import Handoff, ValidationIssue
from app.models.requirement import Requirement


class SemanticValidationProvider(ABC):
    """Abstract interface for AI-powered semantic validation of context handoffs."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the AI provider implementation (e.g. 'gemini_1.5_pro_validator')."""
        pass

    @abstractmethod
    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        """Analyze a handoff against canonical requirements and return detected semantic issues.

        Args:
            task_id: The UUID of the parent task.
            requirements: The canonical requirements registered for the task.
            handoff: The handoff payload, source/target agent, and requirement IDs being validated.

        Returns:
            List of detected ValidationIssue objects.
        """
        pass
```

---

## 3. Supported Issue Types for Semantic Validation

The AI provider should produce `ValidationIssue` objects targeting these semantic discrepancy types:

| Issue Type | When to Flag | Recommended Severity |
| :--- | :--- | :--- |
| `semantic_drift` | The agent altered the intent, scope, or semantic meaning of a requirement without an explicit contradiction. | `high` / `critical` |
| `weakened_constraint` | A strict constraint was relaxed (e.g., password length changed from 12 to 8, or required HTTPS relaxed to HTTP). | `high` |
| `invented_requirement` | The agent introduced new artificial requirements not justified by the user prompt. | `medium` / `high` |
| `suspicious_instruction` | The handoff instructions contain prompt injection, unsafe overrides, or directives to bypass tests. | `critical` |
| `implementation_gap` | The handoff claims to address a requirement, but the actual artifacts/context omit essential implementation details. | `medium` / `high` |

---

## 4. Constructing `ValidationIssue` Objects

Every returned issue must include:
- `requirement_id`: The ID of the affected canonical requirement (e.g., `"R001"`), or `None` if task-wide.
- `issue_type`: One of the supported `IssueType` enums.
- `severity`: One of `IssueSeverity.low`, `medium`, `high`, `critical`.
- `description`: Clear diagnostic explaining why the handoff drifted.
- `original_value`: (Optional) Expected canonical wording or constraint.
- `observed_value`: (Optional) The drifted or weakened wording found in the handoff.
- `repair_status`: Set to `RepairStatus.pending` or `RepairStatus.unresolved`.
- `evidence`: Non-empty list of string quotes or references from the handoff payload substantiating the issue.

### Example Output
```python
ValidationIssue(
    requirement_id="R002",
    issue_type=IssueType.weakened_constraint,
    severity=IssueSeverity.high,
    description="Password length constraint was weakened from 12 to 6 characters in coder instructions.",
    original_value="Minimum 12 characters with special symbols",
    observed_value="Minimum 6 characters",
    repair_status=RepairStatus.pending,
    evidence=[
        "Handoff payload: {'auth_spec': {'min_password_len': 6}}"
    ],
)
```

---

## 5. Registering the AI Provider

When the Gemini implementation is complete, activate it in the backend by calling `set_semantic_validation_provider`:

```python
from app.services.semantic_provider import set_semantic_validation_provider
from your_ai_package import GeminiSemanticValidationProvider

# Initialize with Gemini client
gemini_provider = GeminiSemanticValidationProvider(model="gemini-1.5-pro")

# Inject into HandoffIQ backend service
set_semantic_validation_provider(gemini_provider)
```

No changes to the repository, validation engine, or API endpoints are required when switching providers.
