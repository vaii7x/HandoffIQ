"""Safe workspace scanner enforcing directory containment, path traversal checks, and security exclusions."""

import os
from pathlib import Path
import re
from typing import List, Optional, Set, Tuple

from app.core.config import get_settings
from app.core.errors import (
    OversizedFileError,
    PathTraversalError,
    WorkspaceNotFoundError,
    WorkspaceSecurityError,
)

# Standard directory exclusions
DEFAULT_EXCLUDED_DIRS: Set[str] = {
    "node_modules",
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    "out",
    "coverage",
    ".cache",
    "__pycache__",
    ".turbo",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
}

# Secret and sensitive credential file patterns
SECRET_FILE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^.*\.(pem|key|pfx|p12|pkcs12)$", re.IGNORECASE),
    re.compile(r"^id_(rsa|ed25519|dsa|ecdsa)(\..+)?$", re.IGNORECASE),
    re.compile(r"^(credentials|service-account.*|client_secret.*)\.json$", re.IGNORECASE),
    re.compile(r"^.*(secret|token|password|credential).*\.(json|txt|ya?ml|key)$", re.IGNORECASE),
]

# Supported eligible source code extensions
DEFAULT_ALLOWED_EXTENSIONS: Set[str] = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
}

# Test file naming patterns
TEST_PATTERNS = [
    re.compile(r"^.*(\.test|\.spec)\.(js|jsx|ts|tsx)$", re.IGNORECASE),
    re.compile(r"^test[_\-].*\.(js|jsx|ts|tsx)$", re.IGNORECASE),
    re.compile(r"^.*[_\-]test\.(js|jsx|ts|tsx)$", re.IGNORECASE),
]


class SafeWorkspaceScanner:
    """Provides validated and secure traversal of local project workspaces."""

    def __init__(
        self,
        workspace_path: str,
        max_file_size_bytes: Optional[int] = None,
        allowed_extensions: Optional[Set[str]] = None,
        excluded_dirs: Optional[Set[str]] = None,
    ) -> None:
        self.raw_workspace_path = workspace_path
        settings = get_settings()
        self.max_file_size_bytes = (
            max_file_size_bytes
            if max_file_size_bytes is not None
            else settings.DEFAULT_MAX_FILE_SIZE_BYTES
        )
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS
        self.excluded_dirs = excluded_dirs or DEFAULT_EXCLUDED_DIRS
        self.workspace_root = self._validate_workspace_root(workspace_path)

    def _validate_workspace_root(self, path_str: str) -> Path:
        """Ensure workspace exists, is a directory, and resolve to absolute canonical path."""
        if not path_str or not path_str.strip():
            raise WorkspaceNotFoundError(path_str or "<empty>")

        raw_path = Path(path_str)
        if not raw_path.exists() or not raw_path.is_dir():
            raise WorkspaceNotFoundError(str(raw_path))

        return raw_path.resolve()

    def resolve_safe_path(self, relative_or_absolute_subpath: str) -> Path:
        """Resolve a subpath, verifying it strictly resides inside the workspace root without escape.

        Raises:
            PathTraversalError: If the path escapes the workspace root.
            WorkspaceSecurityError: If the path references a prohibited secret or credential file.
        """
        clean_input = relative_or_absolute_subpath.strip()

        # Disallow obvious upward relative components before resolving
        parts = Path(clean_input).parts
        if ".." in parts:
            raise PathTraversalError(clean_input, str(self.workspace_root))

        candidate = (self.workspace_root / clean_input).resolve()

        # Verify canonical containment (prevent symlink escapes)
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError:
            raise PathTraversalError(clean_input, str(self.workspace_root))

        # Check for forbidden secret files
        if self.is_secret_file(candidate.name):
            raise WorkspaceSecurityError(
                f"Access to credential or secret file '{candidate.name}' is prohibited.",
                details={"file": candidate.name},
            )

        return candidate

    @staticmethod
    def is_secret_file(file_name: str) -> bool:
        """Check if a file matches known credentials, secrets, or environment files."""
        return any(pattern.match(file_name) for pattern in SECRET_FILE_PATTERNS)

    def is_test_file(self, relative_path: str) -> bool:
        """Determine whether a file is a test suite by path conventions."""
        posix_path = relative_path.replace("\\", "/").lower()
        parts = posix_path.split("/")
        file_name = parts[-1]

        # In a test directory?
        test_dir_names = {"__tests__", "tests", "test", "spec", "specs"}
        if any(part in test_dir_names for part in parts[:-1]):
            return True

        # Matches test file name pattern?
        return any(pattern.match(file_name) for pattern in TEST_PATTERNS)

    def scan_workspace(self) -> Tuple[List[Path], int, int]:
        """Scan workspace for all eligible source files.

        Returns:
            Tuple containing:
            - List of safe, eligible Path objects
            - Count of excluded/skipped files (secrets, unallowed extensions, ignored dirs)
            - Count of oversized files skipped
        """
        eligible_paths: List[Path] = []
        excluded_count = 0
        oversized_count = 0

        for root, dirs, files in os.walk(self.workspace_root, followlinks=False):
            # Prune excluded directories in-place to avoid descending into them
            dirs[:] = [
                d
                for d in dirs
                if d not in self.excluded_dirs and not d.startswith(".")
            ]

            current_dir_path = Path(root)

            for file_name in files:
                file_path = current_dir_path / file_name

                # Filter out symlinks that point outside workspace
                try:
                    resolved_file = file_path.resolve()
                    resolved_file.relative_to(self.workspace_root)
                except (ValueError, OSError):
                    excluded_count += 1
                    continue

                # Filter out secrets
                if self.is_secret_file(file_name):
                    excluded_count += 1
                    continue

                # Filter by permitted extensions
                extension = file_path.suffix.lower()
                if extension not in self.allowed_extensions:
                    excluded_count += 1
                    continue

                # Check file size without loading full content into memory
                try:
                    stat = file_path.stat()
                    if stat.st_size > self.max_file_size_bytes:
                        oversized_count += 1
                        continue
                except OSError:
                    excluded_count += 1
                    continue

                eligible_paths.append(file_path)

        # Deterministic sorting by relative POSIX path
        eligible_paths.sort(
            key=lambda p: str(p.relative_to(self.workspace_root)).replace("\\", "/")
        )
        return eligible_paths, excluded_count, oversized_count

    def read_safe_file(self, relative_path: str) -> str:
        """Safely read content of an indexed file with size limits."""
        target_path = self.resolve_safe_path(relative_path)

        if not target_path.exists() or not target_path.is_file():
            raise WorkspaceNotFoundError(f"File not found: '{relative_path}'")

        stat = target_path.stat()
        if stat.st_size > self.max_file_size_bytes:
            raise OversizedFileError(
                relative_path, stat.st_size, self.max_file_size_bytes
            )

        try:
            return target_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise WorkspaceSecurityError(
                f"Failed to read file '{relative_path}': {str(exc)}",
                details={"file": relative_path},
            )
