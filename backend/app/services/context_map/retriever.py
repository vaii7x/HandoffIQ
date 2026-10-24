"""Context retrieval service matching canonical requirements to indexed source files with deterministic scoring."""

import math
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.models.context_map import (
    ContextFileMatch,
    ContextPackage,
    FileRelationship,
    IndexedFile,
    ParsedSymbol,
    ProjectIndex,
    TokenAccounting,
)
from app.models.requirement import Requirement
from app.repositories.base import TaskRepository
from app.services.context_map.scanner import SafeWorkspaceScanner

# Stop words to filter out when tokenizing requirements
STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "of", "from", "as", "is", "are", "was", "were", "be", "been",
    "must", "should", "shall", "will", "can", "could", "have", "has",
    "that", "this", "it", "not", "when", "then", "if", "all", "any",
}


def tokenize_text(text: str) -> Set[str]:
    """Extract lowercased alphanumeric keywords from text, omitting stop words."""
    words = re.findall(r"[A-Za-z0-9_$]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP_WORDS}


class ContextRetrieverService:
    """Retrieves relevant source files, components, and tests for requirements using deterministic ranking."""

    def __init__(self, task_repo: TaskRepository) -> None:
        self.task_repo = task_repo

    async def retrieve_context(
        self,
        task_id: UUID,
        project_index: ProjectIndex,
        requirement_ids: Optional[List[str]] = None,
        max_files: int = 10,
        baseline_tokens: Optional[int] = None,
    ) -> ContextPackage:
        """Assemble a compact, deterministic context package for a task's requirements.

        Args:
            task_id: UUID of the task.
            project_index: Pre-indexed workspace data.
            requirement_ids: Optional list of requirement IDs to address (defaults to all).
            max_files: Maximum number of matched source files to return in the package.
            baseline_tokens: Optional explicit token baseline for savings measurement.

        Returns:
            ContextPackage with ranked files, symbols, tests, relationships, and token metrics.
        """
        # 1. Fetch canonical requirements
        all_reqs = await self.task_repo.get_requirements(task_id)
        if requirement_ids:
            target_ids = set(requirement_ids)
            canonical_reqs = [r for r in all_reqs if r.id in target_ids]
        else:
            canonical_reqs = all_reqs

        # 2. Extract requirement tokens and symbols
        req_tokens: Set[str] = set()
        req_token_map: Dict[str, Set[str]] = {}
        for req in canonical_reqs:
            tokens = tokenize_text(f"{req.description} {req.original_text}")
            req_tokens.update(tokens)
            req_token_map[req.id] = tokens

        # 3. Score files deterministically
        file_scores: Dict[str, Tuple[float, List[str], List[ParsedSymbol]]] = {}
        scanner = SafeWorkspaceScanner(project_index.workspace_path)

        for indexed_file in project_index.files:
            # Skip test files from primary source matches (they are associated separately)
            if indexed_file.is_test:
                continue

            score = 0.0
            reasons: List[str] = []
            matched_symbols: List[ParsedSymbol] = []

            file_stem = Path(indexed_file.relative_path).stem.lower()
            file_name = Path(indexed_file.relative_path).name.lower()

            # Path / filename match
            for t in req_tokens:
                if t in file_stem or t in file_name:
                    score += 5.0
                    reasons.append(f"Filename matches requirement keyword '{t}'")

            # Symbol match
            for sym in indexed_file.symbols:
                sym_lower = sym.name.lower()
                for t in req_tokens:
                    if t in sym_lower:
                        score += 4.0
                        matched_symbols.append(sym)
                        sym_type_name = sym.symbol_type.value if hasattr(sym.symbol_type, "value") else str(sym.symbol_type)
                        reasons.append(
                            f"Contains {sym_type_name} '{sym.name}' matching '{t}' (line {sym.line_number})"
                        )
                        break

            # Content match if score is low
            if score == 0.0:
                try:
                    content = scanner.read_safe_file(indexed_file.relative_path)
                    content_lower = content.lower()
                    matched_content_tokens = [t for t in req_tokens if t in content_lower]
                    if matched_content_tokens:
                        score += len(matched_content_tokens) * 1.0
                        reasons.append(
                            f"Content contains requirement keywords: {', '.join(matched_content_tokens[:4])}"
                        )
                except Exception:
                    pass

            if score > 0.0:
                file_scores[indexed_file.relative_path] = (score, reasons, matched_symbols)

        # 4. Sort and select top files
        sorted_files = sorted(
            file_scores.items(),
            key=lambda item: (-item[1][0], item[0]),  # score desc, path asc
        )[:max_files]

        # 5. Build context matches and associate tests
        matched_files: List[ContextFileMatch] = []
        related_tests: Set[str] = set()
        matched_paths: Set[str] = {path for path, _ in sorted_files}

        # Build reverse relationship map for tests
        test_map: Dict[str, List[str]] = {}
        for rel in project_index.relationships:
            if rel.relationship_type == "test_target":
                if rel.target_file not in test_map:
                    test_map[rel.target_file] = []
                test_map[rel.target_file].append(rel.source_file)

        for rel_path, (score, reasons, symbols) in sorted_files:
            associated_tests = test_map.get(rel_path, [])
            for t in associated_tests:
                related_tests.add(t)

            # Generate compact snippet / outline
            snippet = self._generate_snippet(scanner, rel_path, symbols)

            matched_files.append(
                ContextFileMatch(
                    relative_path=rel_path,
                    relevance_score=round(score, 2),
                    match_reasons=reasons[:5],
                    relevant_symbols=symbols,
                    is_test=False,
                    associated_tests=associated_tests,
                    content_snippet=snippet,
                )
            )

        # 6. Filter relevant relationships
        all_relevant_paths = matched_paths.union(related_tests)
        relevant_relationships = [
            rel
            for rel in project_index.relationships
            if rel.source_file in all_relevant_paths or rel.target_file in all_relevant_paths
        ]

        # 7. Token and character accounting
        token_accounting = self._calculate_token_accounting(
            matched_files=matched_files,
            canonical_reqs=canonical_reqs,
            project_index=project_index,
            baseline_tokens=baseline_tokens,
        )

        return ContextPackage(
            task_id=task_id,
            requirement_ids=[r.id for r in canonical_reqs],
            canonical_requirements=canonical_reqs,
            matched_files=matched_files,
            related_tests=sorted(list(related_tests)),
            dependency_graph=relevant_relationships,
            token_accounting=token_accounting,
            explanation=(
                f"Selected {len(matched_files)} source files and {len(related_tests)} test files "
                f"matching {len(canonical_reqs)} canonical requirements."
            ),
        )

    def _generate_snippet(
        self, scanner: SafeWorkspaceScanner, rel_path: str, symbols: List[ParsedSymbol]
    ) -> str:
        """Create a compact outline or snippet around matched symbols."""
        try:
            content = scanner.read_safe_file(rel_path)
            lines = content.splitlines()
            if not symbols:
                # First 25 lines as outline
                return "\n".join(lines[:25])

            # Extract lines around key matched symbols
            snippet_lines: List[str] = []
            for sym in symbols[:3]:
                start = max(0, sym.line_number - 1)
                end = min(len(lines), sym.line_number + 8)
                snippet_lines.append(f"// Symbol: {sym.name} (line {sym.line_number})")
                snippet_lines.extend(lines[start:end])
                snippet_lines.append("...")

            return "\n".join(snippet_lines)
        except Exception:
            return ""

    def _calculate_token_accounting(
        self,
        matched_files: List[ContextFileMatch],
        canonical_reqs: List[Requirement],
        project_index: ProjectIndex,
        baseline_tokens: Optional[int] = None,
    ) -> TokenAccounting:
        """Calculate character, byte, and estimated token counts distinguishing estimates from provider tokens."""
        # Calculate size of the assembled package
        req_text_length = sum(len(r.description or "") + len(r.original_text) for r in canonical_reqs)
        snippet_length = sum(len(f.content_snippet or "") for f in matched_files)
        meta_length = sum(len(f.relative_path) + sum(len(r) for r in f.match_reasons) for f in matched_files)

        total_chars = req_text_length + snippet_length + meta_length
        total_bytes = total_chars * 1  # UTF-8 approximation

        # Standard heuristic: ~3.8 characters per token for code & structured text
        estimated_tokens = int(math.ceil(total_chars / 3.8))

        # Project-level baseline
        full_project_tokens: Optional[int] = None
        if project_index.total_size_bytes > 0:
            full_project_tokens = int(math.ceil(project_index.total_size_bytes / 3.8))

        # Token savings computation: ONLY calculate when a baseline is provided or full project is known
        effective_baseline = baseline_tokens if baseline_tokens is not None else full_project_tokens
        savings_percent: Optional[float] = None
        if effective_baseline and effective_baseline > 0:
            savings = max(0, effective_baseline - estimated_tokens)
            savings_percent = round((savings / effective_baseline) * 100.0, 1)

        notes = (
            f"Estimated locally (~3.8 chars/token). "
            f"Packaged {len(matched_files)} files ({estimated_tokens} tokens) "
        )
        if effective_baseline:
            notes += f"vs baseline of {effective_baseline} tokens ({savings_percent}% reduction)."
        else:
            notes += "without comparative baseline."

        return TokenAccounting(
            total_characters=total_chars,
            total_bytes=total_bytes,
            estimated_tokens=estimated_tokens,
            token_count_type="estimated",
            full_project_estimated_tokens=full_project_tokens,
            baseline_tokens=effective_baseline,
            token_savings_percent=savings_percent,
            accounting_notes=notes,
        )
