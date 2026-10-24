"""Domain models for ContextMap project indexing, symbol extraction, and context retrieval."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import Field

from app.models.common import HandoffIQBaseModel
from app.models.requirement import Requirement


class SymbolType(str, Enum):
    """Types of extracted source code symbols."""

    function = "function"
    component = "component"
    class_def = "class"
    css_selector = "css_selector"
    variable = "variable"
    import_stmt = "import"


class ParsedSymbol(HandoffIQBaseModel):
    """An individual symbol (function, component, class, selector) extracted from a source file."""

    name: str = Field(description="Name or identifier of the symbol")
    symbol_type: SymbolType = Field(description="Classification of the symbol")
    line_number: int = Field(ge=1, description="1-based line number where the symbol definition begins")
    end_line_number: Optional[int] = Field(default=None, ge=1, description="End line number if detected")
    is_exported: bool = Field(default=False, description="Whether the symbol is exported")
    parsing_method: str = Field(
        default="regex_heuristic",
        description="Method used for extraction ('regex_heuristic' vs 'ast_parser')",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FileRelationship(HandoffIQBaseModel):
    """Directed relationship between two files (import, style reference, or test target)."""

    source_file: str = Field(description="Relative path of the source file")
    target_file: str = Field(description="Relative path of the referenced/target file")
    relationship_type: str = Field(
        description="Type of relationship: 'import', 'css_reference', 'test_target'"
    )
    raw_reference: str = Field(description="Raw string specifier as written in the source code")


class IndexedFile(HandoffIQBaseModel):
    """Indexed metadata and extracted symbols for a single eligible workspace file."""

    relative_path: str = Field(description="POSIX-normalized relative path within workspace")
    extension: str = Field(description="File extension including dot, e.g. '.jsx'")
    language: str = Field(description="Detected language (html, css, javascript, typescript, react_jsx, react_tsx, json)")
    size_bytes: int = Field(ge=0, description="File size in bytes")
    line_count: int = Field(ge=0, description="Total lines in the file")
    is_test: bool = Field(default=False, description="Whether the file is categorized as a test")
    symbols: List[ParsedSymbol] = Field(default_factory=list, description="Extracted symbols")
    imports: List[str] = Field(default_factory=list, description="Raw import specifiers")
    exports: List[str] = Field(default_factory=list, description="Exported symbol names or identifiers")
    content_hash: str = Field(description="SHA-256 hash of file content for cache invalidation")
    parsing_method: str = Field(
        default="regex_heuristic",
        description="Method used for extraction ('regex_heuristic' vs 'ast_parser')",
    )


class ProjectIndex(HandoffIQBaseModel):
    """Aggregate index of an analyzed workspace."""

    workspace_path: str = Field(description="Absolute path to workspace directory")
    total_files: int = Field(ge=0, description="Total number of eligible indexed files")
    total_size_bytes: int = Field(ge=0, description="Combined size of all indexed files in bytes")
    total_lines: int = Field(ge=0, description="Total line count across all indexed files")
    files: List[IndexedFile] = Field(default_factory=list, description="List of indexed files")
    relationships: List[FileRelationship] = Field(
        default_factory=list, description="Discovered relationships between source files"
    )
    test_files: List[str] = Field(
        default_factory=list, description="List of relative paths identified as test suites"
    )
    indexed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when index was generated",
    )
    excluded_files_count: int = Field(
        default=0, description="Count of skipped files due to ignore rules or security"
    )
    oversized_files_count: int = Field(
        default=0, description="Count of skipped files exceeding size threshold"
    )
    limitations_notice: str = Field(
        default=(
            "Static regex-based heuristic analysis for HTML, CSS, JS, and React. "
            "Dependency resolution is heuristic and does not execute source code."
        ),
        description="Disclosure of static heuristic analysis boundaries",
    )


class TokenAccounting(HandoffIQBaseModel):
    """Structured token and character metrics distinguishing provider tokens from local estimates."""

    total_characters: int = Field(ge=0, description="Total character count of the context package")
    total_bytes: int = Field(ge=0, description="Total byte size of the context package")
    estimated_tokens: int = Field(
        ge=0, description="Estimated token count using local calculation (~3.8 chars/token for code)"
    )
    token_count_type: str = Field(
        default="estimated",
        description="Source of token count: 'estimated' vs 'provider_reported'",
    )
    full_project_estimated_tokens: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated token count of the entire indexed workspace, if available",
    )
    baseline_tokens: Optional[int] = Field(
        default=None,
        ge=0,
        description="Baseline token count against which savings are measured, if provided",
    )
    token_savings_percent: Optional[float] = Field(
        default=None,
        description="Calculated token reduction percentage relative to baseline or full project (None if no baseline)",
    )
    accounting_notes: str = Field(
        default="Local estimation only (~3.8 characters per token). Provider-reported tokens require live LLM provider.",
        description="Clarification on token counting provenance",
    )


class ContextFileMatch(HandoffIQBaseModel):
    """Source file matched to requirements with relevance scoring and explanation."""

    relative_path: str = Field(description="Relative path of the matched file")
    relevance_score: float = Field(ge=0.0, description="Deterministic relevance score")
    match_reasons: List[str] = Field(
        default_factory=list, description="Deterministic explanations for why this file is included"
    )
    relevant_symbols: List[ParsedSymbol] = Field(
        default_factory=list, description="Specific functions, components, or classes that matched"
    )
    is_test: bool = Field(default=False, description="Whether this file is a test file")
    associated_tests: List[str] = Field(
        default_factory=list, description="Relative paths to corresponding test files"
    )
    content_snippet: Optional[str] = Field(
        default=None, description="Compact outline or extracted lines of relevant symbols"
    )
    line_range: Optional[List[int]] = Field(
        default=None, description="[start_line, end_line] range if a specific section was isolated"
    )


class ContextPackage(HandoffIQBaseModel):
    """Compact context package delivered to agents for a given task and requirements."""

    task_id: UUID = Field(description="Associated task identifier")
    requirement_ids: List[str] = Field(
        default_factory=list, description="Requirement IDs addressed by this context package"
    )
    canonical_requirements: List[Requirement] = Field(
        default_factory=list, description="Canonical requirement definitions with immutable text"
    )
    matched_files: List[ContextFileMatch] = Field(
        default_factory=list, description="Ranked relevant files and extracted snippets"
    )
    related_tests: List[str] = Field(
        default_factory=list, description="All test files identified as relevant to the requirements"
    )
    dependency_graph: List[FileRelationship] = Field(
        default_factory=list, description="Relevant relationships between matched files"
    )
    token_accounting: TokenAccounting = Field(
        description="Character and token accounting metrics"
    )
    explanation: str = Field(description="Summary of why this context package was selected")
