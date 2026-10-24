"""Workspace-backed ContextMap service integrating indexing and retrieval into the multi-agent pipeline."""

from typing import Any, Dict, Optional
from app.models.context_map import ContextPackage
from app.repositories.base import TaskRepository
from app.services.agents.base import ContextMapInput, ContextMapOutput, ContextMapService
from app.services.context_map.indexer import ProjectIndexerService, get_project_indexer
from app.services.context_map.retriever import ContextRetrieverService


class WorkspaceContextMapService(ContextMapService):
    """ContextMap service implementing ContextMapService interface using real static indexing."""

    def __init__(
        self,
        task_repo: TaskRepository,
        indexer: Optional[ProjectIndexerService] = None,
        default_workspace_path: Optional[str] = None,
    ) -> None:
        self.task_repo = task_repo
        self.indexer = indexer or get_project_indexer()
        self.default_workspace_path = default_workspace_path

    @property
    def name(self) -> str:
        return "workspace_context_mapper"

    async def create_context_map(self, input_data: ContextMapInput) -> ContextMapOutput:
        """Create structured ContextMapOutput by indexing workspace and retrieving relevant context."""
        workspace_path = (
            input_data.validated_handoff.payload.get("workspace_path")
            or self.default_workspace_path
        )

        req_ids = [r.id for r in input_data.requirements]

        if not workspace_path:
            # Fallback if no workspace directory was specified in handoff
            req_mappings: Dict[str, Any] = {}
            for req in input_data.requirements:
                req_mappings[req.id] = {
                    "description": req.description,
                    "target_files": [f"src/features/{req.id.lower()}.ts"],
                    "constraints": req.tags,
                }
            return ContextMapOutput(
                global_context={
                    "mode": "heuristic_fallback",
                    "note": "No workspace_path specified in handoff payload",
                },
                requirement_mappings=req_mappings,
            )

        # Index workspace
        project_index = self.indexer.index_workspace(workspace_path=workspace_path)

        # Retrieve relevant context
        retriever = ContextRetrieverService(task_repo=self.task_repo)
        package: ContextPackage = await retriever.retrieve_context(
            task_id=input_data.task_id,
            project_index=project_index,
            requirement_ids=req_ids,
        )

        # Structure into ContextMapOutput format
        req_mappings = {}
        for req in input_data.requirements:
            # Filter matched files for this requirement
            matched_for_req = [
                f.relative_path
                for f in package.matched_files
                if any(
                    req.id in reason
                    or (req.description and req.description.lower() in reason.lower())
                    for reason in f.match_reasons
                )
            ]
            if not matched_for_req and package.matched_files:
                # Include top file if none specifically isolated
                matched_for_req = [package.matched_files[0].relative_path]

            req_mappings[req.id] = {
                "description": req.description,
                "target_files": matched_for_req,
                "associated_tests": [
                    t for t in package.related_tests
                ],
                "priority": req.priority,
            }

        global_context = {
            "workspace_path": project_index.workspace_path,
            "total_files": project_index.total_files,
            "matched_files": [f.relative_path for f in package.matched_files],
            "related_tests": package.related_tests,
            "token_accounting": package.token_accounting.model_dump(),
            "limitations_notice": project_index.limitations_notice,
        }

        return ContextMapOutput(
            global_context=global_context,
            requirement_mappings=req_mappings,
        )
