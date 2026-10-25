"""Project indexing service that scans safe workspaces and builds deterministic relationship graphs."""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.models.context_map import (
    FileRelationship,
    IndexedFile,
    ParsedSymbol,
    ProjectIndex,
)
from app.services.context_map.parsers import (
    detect_language,
    parse_css_symbols,
    parse_html_symbols,
    parse_js_ts_symbols,
    parse_json_symbols,
)
from app.services.context_map.scanner import SafeWorkspaceScanner


class ProjectIndexerService:
    """Indexes source files in an explicitly configured workspace, extracting symbols and relations."""

    def __init__(self) -> None:
        # Cache for recent indexes: workspace_path -> ProjectIndex
        self._index_cache: Dict[str, ProjectIndex] = {}

    def index_workspace(
        self,
        workspace_path: str,
        max_file_size_bytes: Optional[int] = None,
        force_refresh: bool = False,
    ) -> ProjectIndex:
        """Scan and index an explicitly configured workspace.

        Args:
            workspace_path: Path to the root directory to index.
            max_file_size_bytes: Optional file size limit in bytes.
            force_refresh: When True, bypasses cache and re-indexes.

        Returns:
            ProjectIndex containing all indexed files, symbols, relationships, and stats.
        """
        scanner = SafeWorkspaceScanner(
            workspace_path=workspace_path,
            max_file_size_bytes=max_file_size_bytes,
        )
        canonical_workspace = str(scanner.workspace_root)

        if not force_refresh and canonical_workspace in self._index_cache:
            return self._index_cache[canonical_workspace]

        eligible_paths, excluded_count, oversized_count = scanner.scan_workspace()

        indexed_files: List[IndexedFile] = []
        test_files: List[str] = []
        total_size = 0
        total_lines = 0

        # Map relative path -> IndexedFile for relationship resolution
        file_map: Dict[str, IndexedFile] = {}

        for path in eligible_paths:
            rel_path = str(path.relative_to(scanner.workspace_root)).replace("\\", "/")
            ext = path.suffix.lower()
            lang = detect_language(ext)

            content = scanner.read_safe_file(rel_path)
            size_bytes = len(content.encode("utf-8"))
            lines = content.splitlines()
            line_count = len(lines)
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            is_test = scanner.is_test_file(rel_path)
            if is_test:
                test_files.append(rel_path)

            symbols: List[ParsedSymbol] = []
            imports: List[str] = []
            exports: List[str] = []
            parsing_method = "regex_heuristic"

            if lang in {"javascript", "typescript", "react_jsx", "react_tsx"}:
                symbols, imports, exports = parse_js_ts_symbols(content, ext)
            elif lang == "css":
                symbols, imports = parse_css_symbols(content)
            elif lang == "html":
                symbols, imports = parse_html_symbols(content)
            elif lang == "json":
                symbols, imports = parse_json_symbols(content)
                parsing_method = "json_parser"

            indexed_file = IndexedFile(
                relative_path=rel_path,
                extension=ext,
                language=lang,
                size_bytes=size_bytes,
                line_count=line_count,
                is_test=is_test,
                symbols=symbols,
                imports=imports,
                exports=exports,
                content_hash=content_hash,
                parsing_method=parsing_method,
            )

            indexed_files.append(indexed_file)
            file_map[rel_path] = indexed_file
            total_size += size_bytes
            total_lines += line_count

        # Build relationships between files
        relationships = self._resolve_relationships(scanner.workspace_root, indexed_files, file_map)

        project_index = ProjectIndex(
            workspace_path=canonical_workspace,
            total_files=len(indexed_files),
            total_size_bytes=total_size,
            total_lines=total_lines,
            files=indexed_files,
            relationships=relationships,
            test_files=test_files,
            excluded_files_count=excluded_count,
            oversized_files_count=oversized_count,
        )

        self._index_cache[canonical_workspace] = project_index
        return project_index

    def get_cached_index(self, workspace_path: str) -> Optional[ProjectIndex]:
        """Retrieve previously cached index for workspace path if exists."""
        resolved = str(Path(workspace_path).resolve())
        return self._index_cache.get(resolved)

    def _resolve_relationships(
        self,
        workspace_root: Path,
        indexed_files: List[IndexedFile],
        file_map: Dict[str, IndexedFile],
    ) -> List[FileRelationship]:
        """Resolve imports and test-target associations between indexed files."""
        relationships: List[FileRelationship] = []
        all_relative_paths: Set[str] = set(file_map.keys())

        # Candidate extensions when resolving extensionless imports (e.g. `import './Button'`)
        candidate_exts = [".js", ".jsx", ".ts", ".tsx", ".css", ".json", "/index.js", "/index.jsx", "/index.ts", "/index.tsx"]

        for source in indexed_files:
            source_posix = source.relative_path
            source_parent = Path(source_posix).parent

            # 1. Resolve relative imports
            for raw_imp in source.imports:
                if not raw_imp.startswith("."):
                    continue

                # Attempt exact resolution
                target_cand = (source_parent / raw_imp).as_posix().lstrip("./")
                resolved_target: Optional[str] = None

                if target_cand in all_relative_paths:
                    resolved_target = target_cand
                else:
                    for ext in candidate_exts:
                        with_ext = f"{target_cand}{ext}"
                        if with_ext in all_relative_paths:
                            resolved_target = with_ext
                            break

                if resolved_target:
                    rel_type = "css_reference" if resolved_target.endswith(".css") else "import"
                    relationships.append(
                        FileRelationship(
                            source_file=source_posix,
                            target_file=resolved_target,
                            relationship_type=rel_type,
                            raw_reference=raw_imp,
                        )
                    )

            # 2. Test associations
            if source.is_test:
                # Look for matching source file (e.g. Button.test.jsx -> Button.jsx)
                base_name = Path(source_posix).stem
                # Strip .test or .spec
                base_stem = base_name.replace(".test", "").replace(".spec", "").replace("test_", "").replace("test-", "")
                
                # Check candidate matches in same dir or parent dir
                for cand_file in all_relative_paths:
                    if cand_file == source_posix or file_map[cand_file].is_test:
                        continue
                    cand_stem = Path(cand_file).stem
                    if cand_stem == base_stem:
                        relationships.append(
                            FileRelationship(
                                source_file=source_posix,
                                target_file=cand_file,
                                relationship_type="test_target",
                                raw_reference=f"test suite for {cand_file}",
                            )
                        )
                        break

        return relationships


# Global singleton instance
_indexer_instance: Optional[ProjectIndexerService] = None


def get_project_indexer() -> ProjectIndexerService:
    """Retrieve global ProjectIndexerService instance."""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = ProjectIndexerService()
    return _indexer_instance
