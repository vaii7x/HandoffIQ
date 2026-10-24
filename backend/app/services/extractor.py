"""Requirement extractor interface and deterministic mock implementation."""

from abc import ABC, abstractmethod
import re
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.requirement import RequirementPriority


class RequirementCandidate(BaseModel):
    """Candidate requirement identified from the user's initial prompt."""

    original_text: str = Field(..., min_length=1, description="Original requirement wording")
    description: str = Field(default="", description="Detailed context or acceptance criteria")
    priority: RequirementPriority = Field(
        default=RequirementPriority.medium,
        description="Assigned requirement priority"
    )
    related_files: List[str] = Field(default_factory=list, description="Anticipated related files")
    related_test_ids: List[str] = Field(default_factory=list, description="Target test identifiers")


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
    """Deterministic, rule-based mock extractor for demonstration and testing.
    
    This implementation does not call any AI models or Gemini APIs.
    """

    @property
    def extractor_name(self) -> str:
        return "mock"

    async def extract(self, task_id: UUID, original_request: str) -> List[RequirementCandidate]:
        # Special hook to simulate extraction failure in tests
        if "__FORCE_EXTRACTION_FAILURE__" in original_request:
            raise RuntimeError("Simulated requirement extraction failure for testing.")

        req_clean = original_request.strip()
        lower_req = req_clean.lower()
        candidates: List[RequirementCandidate] = []

        # 1. Core Feature Candidate
        candidates.append(
            RequirementCandidate(
                original_text=f"Core capability: {req_clean}",
                description="Implement the primary functional requirements described in the user request.",
                priority=RequirementPriority.critical,
                related_files=["src/App.tsx", "backend/app/main.py"],
                related_test_ids=["TEST-CORE-001"],
            )
        )

        # 2. Authentication / Login detection
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

        # 3. Responsive UI detection
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

        # 4. Theme / Dark Mode detection
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

        # 5. Data Tracking / Persistence detection
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


def get_requirement_extractor() -> RequirementExtractor:
    """Dependency provider returning the configured requirement extractor."""
    # When AI implementation is ready, can switch based on settings.MOCK_MODE
    return MockRequirementExtractor()
