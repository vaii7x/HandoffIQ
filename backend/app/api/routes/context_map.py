"""API endpoints for ContextMap project indexing, file inspection, and context retrieval."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.errors import EntityNotFoundError, TaskNotFoundError, WorkspaceNotFoundError
from app.models.context_map import (
    ContextPackage,
    FileRelationship,
    IndexedFile,
    ProjectIndex,
)
from app.repositories.base import TaskRepository
from app.repositories.in_memory import get_task_repository
from app.services.task_service import TaskService, get_task_service
from app.services.context_map.indexer import ProjectIndexerService, get_project_indexer
from app.services.context_map.retriever import ContextRetrieverService
from app.services.context_map.scanner import SafeWorkspaceScanner

router = APIRouter(prefix="", tags=["ContextMap"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class WorkspaceIndexRequest(BaseModel):
    """Payload to trigger indexing on a local workspace."""

    workspace_path: str = Field(description="Explicit local path to workspace directory")
    max_file_size_bytes: Optional[int] = Field(
        default=None, description="Override maximum file size threshold in bytes"
    )
    force_refresh: bool = Field(
        default=False, description="Force re-indexing ignoring any cached index"
    )


class WorkspaceIndexResponse(BaseModel):
    """Summary of workspace indexing results."""

    workspace_path: str
    total_files: int
    total_size_bytes: int
    total_lines: int
    files: List[IndexedFile]
    relationships: List[FileRelationship]
    test_files: List[str]
    excluded_files_count: int
    oversized_files_count: int
    limitations_notice: str


class ContextRetrievalRequest(BaseModel):
    """Payload to retrieve relevant context for a task."""

    workspace_path: str = Field(description="Workspace directory to retrieve context from")
    requirement_ids: Optional[List[str]] = Field(
        default=None, description="Subset of requirement IDs to address (default: all)"
    )
    max_files: int = Field(default=10, ge=1, le=50, description="Max files in returned package")
    baseline_tokens: Optional[int] = Field(
        default=None, ge=1, description="Explicit baseline tokens for savings calculation"
    )


class FileContentResponse(BaseModel):
    """Safe retrieval of full file contents."""

    workspace_path: str
    relative_path: str
    size_bytes: int
    line_count: int
    content: str


# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

@router.post(
    "/context-map/index",
    response_model=WorkspaceIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Index a workspace",
)
def index_workspace(
    payload: WorkspaceIndexRequest,
    indexer: ProjectIndexerService = Depends(get_project_indexer),
    task_service: TaskService = Depends(get_task_service),

) -> WorkspaceIndexResponse:
    """Index eligible source files in a local workspace, returning metadata and symbols."""
    project_index = indexer.index_workspace(
        workspace_path=payload.workspace_path,
        max_file_size_bytes=payload.max_file_size_bytes,
        force_refresh=payload.force_refresh,
    )
    return WorkspaceIndexResponse(
        workspace_path=project_index.workspace_path,
        total_files=project_index.total_files,
        total_size_bytes=project_index.total_size_bytes,
        total_lines=project_index.total_lines,
        files=project_index.files,
        relationships=project_index.relationships,
        test_files=project_index.test_files,
        excluded_files_count=project_index.excluded_files_count,
        oversized_files_count=project_index.oversized_files_count,
        limitations_notice=project_index.limitations_notice,
    )


@router.get(
    "/context-map/index",
    response_model=WorkspaceIndexResponse,
    summary="Get cached workspace index",
)
def get_cached_index(
    workspace_path: str = Query(..., description="Workspace directory path"),
    indexer: ProjectIndexerService = Depends(get_project_indexer),
    task_service: TaskService = Depends(get_task_service),

) -> WorkspaceIndexResponse:
    """Retrieve existing cached index for a workspace path."""
    cached = indexer.get_cached_index(workspace_path)
    if not cached:
        raise WorkspaceNotFoundError(
            f"Workspace '{workspace_path}' has not been indexed yet. Call POST /api/context-map/index first."
        )

    return WorkspaceIndexResponse(
        workspace_path=cached.workspace_path,
        total_files=cached.total_files,
        total_size_bytes=cached.total_size_bytes,
        total_lines=cached.total_lines,
        files=cached.files,
        relationships=cached.relationships,
        test_files=cached.test_files,
        excluded_files_count=cached.excluded_files_count,
        oversized_files_count=cached.oversized_files_count,
        limitations_notice=cached.limitations_notice,
    )


@router.get(
    "/context-map/file",
    response_model=FileContentResponse,
    summary="Safely fetch file content",
)
def get_file_content(
    workspace_path: str = Query(..., description="Workspace directory path"),
    relative_path: str = Query(..., description="POSIX relative path within workspace"),
) -> FileContentResponse:
    """Safely fetch file content with path traversal and credential leak prevention."""
    scanner = SafeWorkspaceScanner(workspace_path)
    content = scanner.read_safe_file(relative_path)
    lines = content.splitlines()

    return FileContentResponse(
        workspace_path=str(scanner.workspace_root),
        relative_path=relative_path,
        size_bytes=len(content.encode("utf-8")),
        line_count=len(lines),
        content=content,
    )


@router.post(
    "/tasks/{task_id}/context-map",
    response_model=ContextPackage,
    status_code=status.HTTP_200_OK,
    summary="Retrieve context package for a task",
)
async def retrieve_task_context(
    task_id: str,
    payload: ContextRetrievalRequest,
    task_repo: TaskRepository = Depends(get_task_repository),
    indexer: ProjectIndexerService = Depends(get_project_indexer),
    task_service: TaskService = Depends(get_task_service),

) -> ContextPackage:
    """Retrieve relevant source files, symbols, tests, and token accounting for task requirements."""
    resolved_id = await task_service.resolve_task_id(task_id)
    task = await task_repo.get_task(resolved_id)
    if not task:
        raise TaskNotFoundError(f"Task with ID {resolved_id} not found.")

    # Index workspace (cached or fresh)
    project_index = indexer.index_workspace(
        workspace_path=payload.workspace_path,
        force_refresh=False,
    )

    retriever = ContextRetrieverService(task_repo=task_repo)
    package = await retriever.retrieve_context(
        task_id=resolved_id,
        project_index=project_index,
        requirement_ids=payload.requirement_ids,
        max_files=payload.max_files,
        baseline_tokens=payload.baseline_tokens,
    )

    return package
