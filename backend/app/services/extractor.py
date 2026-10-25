"""Requirement extractor interface, deterministic explicit parser, and AI extraction implementations."""

from abc import ABC, abstractmethod
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.requirement import RequirementPriority

logger = logging.getLogger(__name__)


class RequirementCandidate(BaseModel):
    """Candidate requirement identified from the user's initial prompt."""

    original_text: str = Field(..., min_length=1, description="Original requirement wording")
    description: str = Field(default="", description="Detailed context or acceptance criteria")
    priority: RequirementPriority = Field(
        default=RequirementPriority.medium,
        description="Assigned requirement priority"
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Original source identifier such as R1, R2, R12, REQ-1"
    )
    related_files: List[str] = Field(default_factory=list, description="Anticipated related files")
    related_test_ids: List[str] = Field(default_factory=list, description="Target test identifiers")


EXPLICIT_ITEM_RE = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:\[|\()?((?:R|REQ-?|REQ_|REQUIREMENT\s*)?\d+[a-z]?)(?:\]|\))?[\.\:\-\)]\s*(.+)$",
    re.IGNORECASE,
)


def _infer_priority(text: str) -> RequirementPriority:
    """Infer requirement priority from domain keywords."""
    lower = text.lower()
    if any(w in lower for w in ["security", "auth", "login", "password", "persistent", "postgresql", "database", "atomic", "transaction", "critical"]):
        return RequirementPriority.critical
    if any(w in lower for w in ["validation", "due date", "character", "length", "filter", "status", "dashboard", "test", "idempotency", "ownership"]):
        return RequirementPriority.high
    return RequirementPriority.medium


def _infer_related_files(text: str) -> List[str]:
    """Infer predicted relevant source files based on requirement scope."""
    lower = text.lower()
    files: List[str] = []
    if any(w in lower for w in ["auth", "login", "password", "ownership", "student"]):
        files.extend(["src/components/Login.tsx", "backend/app/core/security.py"])
    if any(w in lower for w in ["task", "title", "due date", "validation", "status"]):
        files.extend(["src/models/task.ts", "backend/app/models/task.py"])
    if any(w in lower for w in ["persistent", "postgresql", "database", "store"]):
        files.extend(["backend/app/repositories/base.py", "backend/app/db.py"])
    if any(w in lower for w in ["dashboard", "count", "filter"]):
        files.extend(["src/components/Dashboard.tsx", "src/components/TaskList.tsx"])
    if any(w in lower for w in ["idempotency", "duplicate"]):
        files.extend(["backend/app/middleware/idempotency.py"])
    if any(w in lower for w in ["test", "automated test"]):
        files.extend(["backend/tests/test_tasks.py", "tests/integration.test.ts"])
    if not files:
        files = ["src/App.tsx", "backend/app/main.py"]
    return sorted(list(set(files)))


def parse_explicit_requirements(original_request: str) -> List[RequirementCandidate]:
    """Parse explicitly numbered source requirements (e.g. R1..R12, 1..N, REQ-1..N).

    Preserves:
    - Every explicitly numbered requirement as a separate, distinct canonical record.
    - Full original source IDs (e.g. R1..R12).
    - Verbatim constraints, thresholds, conditions, and expected behavior.
    """
    lines = original_request.strip().split("\n")
    items: List[Dict[str, Any]] = []
    current_item: Optional[Dict[str, Any]] = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        match = EXPLICIT_ITEM_RE.match(line)
        if match:
            if current_item:
                items.append(current_item)

            raw_id = match.group(1).strip()
            # Normalize source identifier: preserve original identifier (e.g. "1" -> "1", "r1" -> "R1", "req-1" -> "REQ-1")
            norm_id = re.sub(r"\s+", "", raw_id.upper())

            current_item = {
                "source_id": norm_id,
                "text_parts": [match.group(2).strip()],
            }
        else:
            # Continuation line for the current item if indented or explanatory
            if current_item:
                current_item["text_parts"].append(line)

    if current_item:
        items.append(current_item)

    if not items:
        return []

    candidates: List[RequirementCandidate] = []
    for item in items:
        full_text = " ".join(item["text_parts"]).strip()
        sid = item["source_id"]
        candidates.append(
            RequirementCandidate(
                original_text=full_text,
                description=f"[Source: {sid}] {full_text}",
                priority=_infer_priority(full_text),
                source_id=sid,
                related_files=_infer_related_files(full_text),
                related_test_ids=[f"TEST-{re.sub(r'[^A-Za-z0-9]', '', sid).upper()}-001"],
            )
        )

    return candidates


class RequirementExtractor(ABC):
    """Abstract interface for extracting canonical requirements from user requests."""

    @property
    @abstractmethod
    def extractor_name(self) -> str:
        """Identifier of the extractor implementation (e.g. 'mock', 'gemini_ai')."""
        pass

    @abstractmethod
    async def extract(self, task_id: UUID, original_request: str) -> List[RequirementCandidate]:
        """Extract requirement candidates from the original request text."""
        pass


class MockRequirementExtractor(RequirementExtractor):
    """Deterministic, rule-based extractor for demonstration, testing, and explicit parsing.

    If the request contains explicitly numbered requirements (e.g. R1..R12 or 1..N),
    it preserves every numbered requirement separately. Otherwise, extracts core domain features.
    """

    @property
    def extractor_name(self) -> str:
        return "mock"

    async def extract(self, task_id: UUID, original_request: str) -> List[RequirementCandidate]:
        # Special hook to simulate extraction failure in tests
        if "__FORCE_EXTRACTION_FAILURE__" in original_request:
            raise RuntimeError("Simulated requirement extraction failure for testing.")

        # 1. First priority: Check for explicitly numbered source requirements
        explicit_candidates = parse_explicit_requirements(original_request)
        if explicit_candidates:
            return explicit_candidates

        # 2. Freeform prose heuristic fallback
        req_clean = original_request.strip()
        lower_req = req_clean.lower()
        candidates: List[RequirementCandidate] = []

        # Core Feature Candidate
        candidates.append(
            RequirementCandidate(
                original_text=f"Core capability: {req_clean}",
                description="Implement the primary functional requirements described in the user request.",
                priority=RequirementPriority.critical,
                related_files=["src/App.tsx", "backend/app/main.py"],
                related_test_ids=["TEST-CORE-001"],
            )
        )

        # Authentication / Login detection
        if any(w in lower_req for w in ["login", "auth", "authentication", "sign in", "user session"]):
            candidates.append(
                RequirementCandidate(
                    original_text="User authentication and secure session management.",
                    description="Provide user login, logout, and protected route access with credential validation.",
                    priority=RequirementPriority.high,
                    related_files=["src/components/Login.tsx", "backend/app/core/security.py"],
                    related_test_ids=["TEST-AUTH-001"],
                )
            )

        # Responsive UI detection
        if any(w in lower_req for w in ["responsive", "mobile", "tablet", "layout"]):
            candidates.append(
                RequirementCandidate(
                    original_text="Responsive layout adaptive across mobile and desktop viewports.",
                    description="Ensure views render correctly and adaptively across small and large screen dimensions.",
                    priority=RequirementPriority.medium,
                    related_files=["src/styles/responsive.css", "src/components/Layout.tsx"],
                    related_test_ids=["TEST-UI-001"],
                )
            )

        # Theme / Dark Mode detection
        if any(w in lower_req for w in ["dark theme", "dark mode", "theme", "styling"]):
            candidates.append(
                RequirementCandidate(
                    original_text="Dark theme support with persistent user preference.",
                    description="Provide accessible dark theme toggle and synchronize with browser/system color scheme.",
                    priority=RequirementPriority.low,
                    related_files=["src/theme/themeProvider.tsx", "src/styles/theme.css"],
                    related_test_ids=["TEST-THEME-001"],
                )
            )

        # Data Tracking / Persistence detection
        if any(w in lower_req for w in ["tracker", "store", "save", "crud", "database"]):
            candidates.append(
                RequirementCandidate(
                    original_text="Persistent state management and data storage.",
                    description="Persist user transactions and operational data across browser sessions.",
                    priority=RequirementPriority.high,
                    related_files=["src/services/storage.ts", "backend/app/repositories/base.py"],
                    related_test_ids=["TEST-DATA-001"],
                )
            )

        return candidates


class GeminiRequirementExtractor(RequirementExtractor):
    """AI-powered requirement extractor using Google Gemini Gen AI SDK."""

    def __init__(self, api_key: str, model_name: str = "gemini-flash-lite-latest"):
        self.api_key = api_key
        self.model_name = model_name

    @property
    def extractor_name(self) -> str:
        return f"gemini_ai ({self.model_name})"

    async def extract(self, task_id: UUID, original_request: str) -> List[RequirementCandidate]:
        # 1. If explicit numbered requirements exist in the prompt, parse them directly
        # to guarantee 100% fidelity without LLM loss or unwanted grouping
        explicit_candidates = parse_explicit_requirements(original_request)
        if explicit_candidates:
            return explicit_candidates

        # 2. For unstructured natural language requests, use Gemini with strict atomic extraction
        from google import genai
        from google.genai import types

        prompt = f"""You are an expert software architect analyzing user requirements.
Analyze the following user goal:
\"\"\"{original_request.strip()}\"\"\"

CRITICAL EXTRACTION INSTRUCTIONS:
1. Extract ALL distinct, atomic, verifiable software requirements.
2. Do NOT merge requirements merely because they concern the same feature. For example, authentication and task ownership must be independent verifiable requirements.
3. Preserve every constraint, threshold, and condition from the original text verbatim.
4. If the user provided numbered requirements, preserve every single numbered requirement as its own item with "source_id" set to the original identifier.

Return a valid JSON array of objects with the following keys:
- "original_text": Verbatim requirement statement and constraints (string)
- "description": Detailed acceptance criteria and context (string)
- "priority": one of "critical", "high", "medium", "low"
- "source_id": original source identifier if present (e.g. "R1", "R2") or null
- "related_files": array of predicted relevant file paths
- "related_test_ids": array of test IDs

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
            candidates: List[RequirementCandidate] = []
            for item in data:
                p_val = str(item.get("priority", "medium")).lower()
                priority = RequirementPriority[p_val] if p_val in RequirementPriority.__members__ else RequirementPriority.medium
                text_val = item.get("original_text", "").strip()
                if text_val:
                    sid = item.get("source_id")
                    candidates.append(
                        RequirementCandidate(
                            original_text=text_val,
                            description=item.get("description", f"[Source: {sid}] {text_val}" if sid else text_val),
                            priority=priority,
                            source_id=sid,
                            related_files=item.get("related_files", []),
                            related_test_ids=item.get("related_test_ids", []),
                        )
                    )
            if candidates:
                return candidates
        except Exception as exc:
            logger.warning("Gemini requirement extraction failed, falling back to mock: %s", exc)

        return await MockRequirementExtractor().extract(task_id, original_request)


def get_requirement_extractor() -> RequirementExtractor:
    """Dependency provider returning the configured requirement extractor."""
    from app.core.config import get_settings
    settings = get_settings()
    key = settings.GEMINI_API_KEY.get_secret_value()
    if not settings.MOCK_MODE and key and key != "placeholder-gemini-key":
        return GeminiRequirementExtractor(api_key=key, model_name=settings.GEMINI_MODEL)
    return MockRequirementExtractor()
