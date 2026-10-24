"""Execution security manager enforcing sanitized environments, timeouts, and artifact directory bounds."""

import asyncio
import os
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.errors import PathTraversalError, WorkspaceSecurityError
from app.services.test_runner.base import IsolationLevel

# Environment variables safe for inheriting into execution subprocesses
SAFE_ENV_PASSTHROUGH = {
    "PATH",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "COMMONPROGRAMFILES",
    "COMSPEC",
    "PATHEXT",
    "LANG",
    "LC_ALL",
    "PYTHONPATH",
    "NODE_PATH",
}

# Forbidden keywords in subprocess environments
FORBIDDEN_ENV_KEYWORDS = (
    "KEY",
    "SECRET",
    "TOKEN",
    "PASS",
    "AUTH",
    "CREDENTIAL",
    "SUPABASE",
    "GEMINI",
    "PRIVATE",
    "DOCKER",
)


class ExecutionSandbox:
    """Manages process containment, secret isolation, and timeout boundaries for test execution."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def check_sandbox_availability(self) -> Tuple[bool, str, IsolationLevel]:
        """Verify whether an appropriate sandbox environment is available.

        Returns:
            Tuple of (is_available, status_message, isolation_level).
        """
        if not self.settings.TEST_EXECUTION_ENABLED:
            return (
                False,
                "Test execution sandbox is disabled by system configuration.",
                IsolationLevel.disabled,
            )

        if self.settings.MOCK_MODE:
            return (
                True,
                "Operating in mock sandbox environment for development.",
                IsolationLevel.mock_sandbox,
            )

        # Process-level restricted sandbox
        return (
            True,
            (
                "Process-level restriction active. Sanitized environment, bounded timeouts, "
                "and path confinement applied. Note: Does not provide container/hypervisor-grade isolation."
            ),
            IsolationLevel.process_restricted,
        )

    def sanitize_environment(
        self,
        workspace_path: str,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Construct a minimal, sanitized environment stripping all backend credentials and Docker sockets."""
        sanitized: Dict[str, str] = {}

        # 1. Selectively pass through only non-sensitive standard system variables
        for key, val in os.environ.items():
            key_upper = key.upper()
            if key_upper in SAFE_ENV_PASSTHROUGH:
                # Extra check: avoid passing if contains credential keywords
                if not any(k in key_upper for k in FORBIDDEN_ENV_KEYWORDS):
                    sanitized[key] = val

        # 2. Bound temp and artifact directories to workspace
        artifacts_dir = Path(workspace_path) / ".handoffiq" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(workspace_path) / ".handoffiq" / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        sanitized["TMP"] = str(temp_dir)
        sanitized["TEMP"] = str(temp_dir)
        sanitized["HANDOFFIQ_ARTIFACT_DIR"] = str(artifacts_dir)
        sanitized["PYTHONUNBUFFERED"] = "1"
        sanitized["CI"] = "true"

        # Explicitly disable external package installations and network access where supported
        sanitized["PIP_NO_INDEX"] = "true"
        sanitized["npm_config_offline"] = "true"

        # 3. Apply safe extra environment variables, verifying no secrets
        if extra_env:
            for k, v in extra_env.items():
                k_upper = k.upper()
                if any(forbidden in k_upper for forbidden in FORBIDDEN_ENV_KEYWORDS):
                    continue
                sanitized[k] = v

        return sanitized

    def validate_artifact_path(self, workspace_path: str, target_rel_or_abs: str) -> Path:
        """Verify that any created or requested artifact strictly resides within the allowed directory."""
        ws_root = Path(workspace_path).resolve()
        candidate = (ws_root / target_rel_or_abs).resolve()

        if ".." in Path(target_rel_or_abs).parts:
            raise PathTraversalError(target_rel_or_abs, str(ws_root))

        try:
            candidate.relative_to(ws_root)
        except ValueError:
            raise PathTraversalError(target_rel_or_abs, str(ws_root))

        return candidate

    async def execute_in_sandbox(
        self,
        command: List[str],
        cwd: str,
        timeout_seconds: Optional[int] = None,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str, int, IsolationLevel, Optional[str]]:
        """Execute a test command in the isolated subprocess environment.

        Returns:
            Tuple of (exit_code, stdout, stderr, duration_ms, isolation_level, error_message).
        """
        is_avail, status_msg, isolation = self.check_sandbox_availability()
        if not is_avail:
            return (
                -1,
                "",
                "",
                0,
                IsolationLevel.disabled,
                f"Execution disabled: {status_msg}",
            )

        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self.settings.TEST_EXECUTION_TIMEOUT_SECONDS
        )

        canonical_cwd = str(Path(cwd).resolve())
        env = self.sanitize_environment(canonical_cwd, extra_env=extra_env)

        start_time = time.perf_counter()
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=canonical_cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=float(timeout)
                )
                exit_code = process.returncode or 0
                error_msg = None
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                exit_code = -1
                stdout_bytes = b""
                stderr_bytes = f"Command timed out after {timeout} seconds.".encode("utf-8")
                error_msg = f"Test execution timed out after {timeout} seconds."

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            return exit_code, stdout, stderr, duration_ms, isolation, error_msg

        except FileNotFoundError as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return (
                -1,
                "",
                str(exc),
                duration_ms,
                isolation,
                f"Test command executable not found: {command[0]}",
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return (
                -1,
                "",
                str(exc),
                duration_ms,
                isolation,
                f"Sandbox execution error: {str(exc)}",
            )
