"""Standardized error classes and FastAPI exception handlers."""

from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class EntityNotFoundError(AppError):
    """Raised when a requested resource is not found."""

    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity": entity_name, "identifier": str(identifier)},
        )


class TaskNotFoundError(AppError):
    """Raised when a requested task does not exist."""

    def __init__(self, message: str = "Task not found", details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            code="TASK_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ExperimentNotFoundError(AppError):
    """Raised when a requested experiment does not exist."""

    def __init__(self, experiment_id: Any) -> None:
        super().__init__(
            message=f"Experiment '{experiment_id}' was not found.",
            code="EXPERIMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"experiment_id": str(experiment_id)},
        )


class InvalidMutationTypeError(AppError):
    """Raised when an unsupported or invalid mutation type is requested."""

    def __init__(self, invalid_types: Any, supported_types: Optional[Any] = None) -> None:
        details = {"invalid_types": invalid_types}
        if supported_types:
            details["supported_types"] = supported_types
        super().__init__(
            message=f"Invalid mutation type(s): {invalid_types}.",
            code="INVALID_MUTATION_TYPE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class TaskAlreadyRunningError(AppError):
    """Raised when an execution run is requested for a task that is already running."""

    def __init__(self, task_id: Any) -> None:
        super().__init__(
            message=f"Task {task_id} is already executing.",
            code="TASK_ALREADY_RUNNING",
            status_code=status.HTTP_409_CONFLICT,
            details={"task_id": str(task_id)},
        )


class ValidationError(AppError):
    """Raised for domain validation failures."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConfigurationError(AppError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class DatabaseError(AppError):
    """Raised when database operations encounter connection errors, timeouts, or constraint violations."""

    def __init__(
        self,
        message: str = "Database operation failed.",
        code: str = "DATABASE_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class WorkspaceNotFoundError(AppError):
    """Raised when a specified workspace directory does not exist or is not a directory."""

    def __init__(self, workspace_path: str) -> None:
        super().__init__(
            message=f"Workspace path '{workspace_path}' does not exist or is not a directory.",
            code="WORKSPACE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"workspace_path": workspace_path},
        )


class PathTraversalError(AppError):
    """Raised when an accessed path attempts directory traversal outside the workspace."""

    def __init__(self, path: str, workspace_root: str) -> None:
        super().__init__(
            message=f"Path '{path}' resolves outside the allowed workspace '{workspace_root}'.",
            code="PATH_TRAVERSAL_DETECTED",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"path": path, "workspace_root": workspace_root},
        )


class WorkspaceSecurityError(AppError):
    """Raised when a file or directory access violates security policies (e.g. secrets, escaping symlinks)."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            code="WORKSPACE_SECURITY_VIOLATION",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class OversizedFileError(AppError):
    """Raised when a file exceeds the maximum permitted indexing size."""

    def __init__(self, file_path: str, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            message=f"File '{file_path}' ({size_bytes} bytes) exceeds maximum index size limit of {max_bytes} bytes.",
            code="OVERSIZED_FILE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"file_path": file_path, "size_bytes": size_bytes, "max_bytes": max_bytes},
        )


class ContextMapError(AppError):
    """Raised when context map indexing or retrieval fails."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            code="CONTEXT_MAP_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform JSON error handlers for the application."""

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        error_payload: dict[str, Any] = {
            "code": exc.code,
            "message": exc.message,
        }
        if exc.details is not None:
            error_payload["details"] = exc.details

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error_payload},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "Input validation failed.",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "details": None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": str(exc) if app.debug else None,
                }
            },
        )
