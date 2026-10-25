"""Semantic validation provider interface and implementations."""

from abc import ABC, abstractmethod
import asyncio
import json
import logging
from typing import List, Optional
from uuid import UUID

from app.models.handoff import Handoff, IssueSeverity, IssueType, RepairStatus, ValidationIssue
from app.models.requirement import Requirement

logger = logging.getLogger(__name__)


class SemanticValidationProvider(ABC):
    """Abstract interface for AI-powered semantic validation of context handoffs.

    The AI developer implements this interface using Gemini or LLM agents to detect
    subtle semantic drift, weakened constraints, and implementation gaps that cannot
    be reliably detected through deterministic schema or keyword checking.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier of the semantic provider implementation."""
        pass

    @abstractmethod
    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        """Analyze a handoff against canonical requirements and return identified semantic issues.

        Args:
            task_id: The UUID of the parent task.
            requirements: The canonical requirements registered for the task.
            handoff: The handoff payload, source/target agent, and requirement IDs being validated.

        Returns:
            List of detected ValidationIssue objects (e.g. semantic_drift, weakened_constraint).
        """
        pass


class NoOpSemanticValidationProvider(SemanticValidationProvider):
    """Default no-op provider returning no semantic issues.

    Active in local development and test environments where deterministic validation
    is evaluated without live AI infrastructure.
    """

    @property
    def provider_name(self) -> str:
        return "noop_semantic_provider"

    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        return []


class UncertainSemanticValidationProvider(SemanticValidationProvider):
    """Semantic provider simulating analysis uncertainty or ambiguous requirements requiring review."""

    def __init__(self, reason: str = "Semantic compliance could not be verified; ambiguous handoff context requires review."):
        self.reason = reason

    @property
    def provider_name(self) -> str:
        return "uncertain_semantic_provider"

    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        matched_req = requirements[0] if requirements else None
        return [
            ValidationIssue(
                requirement_id=matched_req.id if matched_req else None,
                issue_type=IssueType.implementation_gap,
                severity=IssueSeverity.medium,
                description=f"Semantic compliance uncertain: {self.reason}",
                original_value=matched_req.original_text if matched_req else "Verified canonical compliance",
                observed_value="Ambiguous / unverified downstream handoff",
                repair_status=RepairStatus.unresolved,
                evidence=[f"Semantic analyzer flagged uncertainty: {self.reason}"],
            )
        ]


class GeminiSemanticValidationProvider(SemanticValidationProvider):
    """AI-powered semantic validation provider using Google Gemini Gen AI SDK."""

    def __init__(self, api_key: str, model_name: str = "gemini-flash-lite-latest"):
        self.api_key = api_key
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return f"gemini_semantic_analyzer ({self.model_name})"

    async def analyze(
        self,
        task_id: UUID,
        requirements: List[Requirement],
        handoff: Handoff,
    ) -> List[ValidationIssue]:
        from google import genai
        from google.genai import types

        canonical_data = [
            {"id": r.id, "text": r.original_text, "description": r.description}
            for r in requirements
        ]
        handoff_data = {
            "source_agent": handoff.source_agent,
            "target_agent": handoff.target_agent,
            "requirement_ids": handoff.requirement_ids,
            "payload": handoff.payload,
        }

        prompt = f"""You are an AI verification engineer specializing in multi-agent context handoff reliability.
Compare the canonical requirements with the agent handoff context.

Canonical Requirements:
{json.dumps(canonical_data, indent=2)}

Handoff Context:
{json.dumps(handoff_data, indent=2)}

CRITICAL VERIFICATION RULES:
1. Distinguish explicit user-mandated requirements from agent-proposed implementation details.
2. An implementation choice (such as internal module structure, or handling error messages in a CLI vs script vs UI layer) is NOT a discrepancy unless the user explicitly requested or forbade it.
3. For tasks that do NOT request a graphical UI (e.g. calculator, algorithm, CLI tool, library), handling exceptions (such as division by zero) via standard exceptions (e.g. ValueError or ZeroDivisionError) or error messages in code satisfies the requirement. Do NOT invent a UI-layer discrepancy or requirement.
4. Only flag an issue as high or critical severity if it weakens security, skips authentication, introduces data loss, or directly contradicts a canonical requirement.
5. If the handoff is compliant with canonical requirements, return an empty array [].
6. If compliance cannot be established or if downstream specifications are ambiguous, return an issue with issue_type "implementation_gap" and explain why compliance cannot be established. Never silently assume compliance when ambiguous.

Return a valid JSON array of issues (empty array [] if perfectly compliant):
[
  {{
    "requirement_id": "REQ-XXX-XX",
    "issue_type": "semantic_drift" | "weakened_constraint" | "contradiction" | "implementation_gap" | "omission",
    "severity": "critical" | "high" | "medium" | "low",
    "description": "Clear explanation of the discrepancy or uncertainty",
    "original_value": "Expected canonical requirement or constraint",
    "observed_value": "Observed downstream specification or behavior",
    "evidence": ["Exact quote or excerpt demonstrating the issue"]
  }}
]

Return ONLY the raw JSON array.
"""
        def _call_gemini():
            client = genai.Client(api_key=self.api_key)
            return client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

        try:
            response = await asyncio.wait_for(asyncio.to_thread(_call_gemini), timeout=25.0)
            data = json.loads(response.text)
            issues: List[ValidationIssue] = []
            for item in data:
                type_str = item.get("issue_type", "semantic_drift").lower()
                issue_type = IssueType[type_str] if type_str in IssueType.__members__ else IssueType.semantic_drift
                sev_str = item.get("severity", "medium").lower()
                severity = IssueSeverity[sev_str] if sev_str in IssueSeverity.__members__ else IssueSeverity.medium

                issues.append(
                    ValidationIssue(
                        requirement_id=item.get("requirement_id"),
                        issue_type=issue_type,
                        severity=severity,
                        description=item.get("description", "Semantic issue detected by Gemini"),
                        original_value=item.get("original_value"),
                        observed_value=item.get("observed_value"),
                        repair_status=RepairStatus.unresolved,
                        evidence=item.get("evidence", []),
                    )
                )
            return issues
        except Exception as exc:
            logger.warning("Gemini semantic analysis failed or cannot establish compliance: %s", exc)
            # Never silently mark compliant on failure; report as uncertain requiring review
            return [
                ValidationIssue(
                    requirement_id=None,
                    issue_type=IssueType.implementation_gap,
                    severity=IssueSeverity.medium,
                    description=f"Semantic compliance uncertain: Semantic analysis could not complete ({type(exc).__name__}: {str(exc)}). Manual review required.",
                    original_value="Verified canonical compliance",
                    observed_value="Uncertain / analysis failed",
                    repair_status=RepairStatus.unresolved,
                    evidence=[f"Semantic analyzer '{self.provider_name}' encountered: {str(exc)}"],
                )
            ]


_semantic_provider: Optional[SemanticValidationProvider] = None


def get_semantic_validation_provider() -> SemanticValidationProvider:
    """Dependency provider returning the active semantic validation provider."""
    global _semantic_provider
    if _semantic_provider is not None:
        return _semantic_provider

    from app.core.config import get_settings
    settings = get_settings()
    key = settings.GEMINI_API_KEY.get_secret_value()
    if not settings.MOCK_MODE and key and key != "placeholder-gemini-key":
        return GeminiSemanticValidationProvider(api_key=key, model_name=settings.GEMINI_MODEL)
    return NoOpSemanticValidationProvider()


def set_semantic_validation_provider(provider: SemanticValidationProvider) -> None:
    """Configure or inject a custom AI semantic validation provider."""
    global _semantic_provider
    _semantic_provider = provider
