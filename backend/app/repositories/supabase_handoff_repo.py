"""Supabase implementation of HandoffRepository."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.errors import EntityNotFoundError
from app.core.supabase import get_supabase_client
from app.models.handoff import Handoff, ValidationIssue
from app.repositories.handoff_repository import HandoffRepository
from app.repositories.supabase_task_repo import _handle_db_exception


class SupabaseHandoffRepository(HandoffRepository):
    """PostgreSQL/Supabase backed repository for handoffs and validation issues."""

    def __init__(self, client=None) -> None:
        self._client = client

    @property
    def client(self):
        if self._client is not None:
            return self._client
        return get_supabase_client()

    async def create_handoff(self, handoff: Handoff) -> Handoff:
        handoff_data = {
            "id": str(handoff.id),
            "task_id": str(handoff.task_id),
            "source_agent": handoff.source_agent,
            "target_agent": handoff.target_agent,
            "status": handoff.status.value if hasattr(handoff.status, "value") else str(handoff.status),
            "requirement_ids": handoff.requirement_ids,
            "payload": handoff.payload,
            "created_at": handoff.created_at.isoformat(),
        }
        try:
            # 1. Insert parent handoff
            res = self.client.table("handoffs").insert(handoff_data).execute()
            if not res.data:
                raise Exception("Failed to insert handoff record.")

            # 2. Insert child validation issues if present
            saved_issues: List[ValidationIssue] = []
            if handoff.issues:
                issue_rows = [
                    {
                        "id": issue.id,
                        "handoff_id": str(handoff.id),
                        "requirement_id": issue.requirement_id,
                        "issue_type": issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                        "severity": issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                        "description": issue.description,
                        "original_value": issue.original_value,
                        "observed_value": issue.observed_value,
                        "repair_status": issue.repair_status.value if hasattr(issue.repair_status, "value") else str(issue.repair_status),
                        "evidence": issue.evidence,
                    }
                    for issue in handoff.issues
                ]
                issues_res = self.client.table("validation_issues").insert(issue_rows).execute()
                saved_issues = [ValidationIssue(**row) for row in (issues_res.data or [])]

            saved_handoff = Handoff(**res.data[0])
            return saved_handoff.model_copy(update={"issues": saved_issues})
        except Exception as exc:
            _handle_db_exception(exc, "create_handoff")

    async def get_handoff(self, handoff_id: UUID) -> Optional[Handoff]:
        try:
            res = self.client.table("handoffs").select("*").eq("id", str(handoff_id)).execute()
            if not res.data:
                return None

            issues_res = (
                self.client.table("validation_issues")
                .select("*")
                .eq("handoff_id", str(handoff_id))
                .execute()
            )
            issues = [ValidationIssue(**row) for row in (issues_res.data or [])]
            return Handoff(**res.data[0]).model_copy(update={"issues": issues})
        except Exception as exc:
            _handle_db_exception(exc, f"get_handoff({handoff_id})")

    async def list_handoffs_for_task(self, task_id: UUID) -> List[Handoff]:
        try:
            res = (
                self.client.table("handoffs")
                .select("*")
                .eq("task_id", str(task_id))
                .order("created_at", desc=False)
                .execute()
            )
            if not res.data:
                return []

            handoff_ids = [row["id"] for row in res.data]
            # Fetch all issues for these handoffs
            issues_res = (
                self.client.table("validation_issues")
                .select("*")
                .in_("handoff_id", handoff_ids)
                .execute()
            )
            issues_by_handoff: Dict[str, List[ValidationIssue]] = {}
            for row in (issues_res.data or []):
                hid = row["handoff_id"]
                if hid not in issues_by_handoff:
                    issues_by_handoff[hid] = []
                issues_by_handoff[hid].append(ValidationIssue(**row))

            result: List[Handoff] = []
            for row in res.data:
                h = Handoff(**row)
                h = h.model_copy(update={"issues": issues_by_handoff.get(str(h.id), [])})
                result.append(h)

            return result
        except Exception as exc:
            _handle_db_exception(exc, f"list_handoffs_for_task({task_id})")

    async def update_handoff(self, handoff: Handoff) -> Handoff:
        handoff_data = {
            "status": handoff.status.value if hasattr(handoff.status, "value") else str(handoff.status),
            "requirement_ids": handoff.requirement_ids,
            "payload": handoff.payload,
        }
        try:
            res = (
                self.client.table("handoffs")
                .update(handoff_data)
                .eq("id", str(handoff.id))
                .execute()
            )
            if not res.data:
                raise EntityNotFoundError("Handoff", handoff.id)

            # Refresh issues: delete existing and re-insert updated issues
            self.client.table("validation_issues").delete().eq("handoff_id", str(handoff.id)).execute()
            saved_issues: List[ValidationIssue] = []
            if handoff.issues:
                issue_rows = [
                    {
                        "id": issue.id,
                        "handoff_id": str(handoff.id),
                        "requirement_id": issue.requirement_id,
                        "issue_type": issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                        "severity": issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                        "description": issue.description,
                        "original_value": issue.original_value,
                        "observed_value": issue.observed_value,
                        "repair_status": issue.repair_status.value if hasattr(issue.repair_status, "value") else str(issue.repair_status),
                        "evidence": issue.evidence,
                    }
                    for issue in handoff.issues
                ]
                issues_res = self.client.table("validation_issues").insert(issue_rows).execute()
                saved_issues = [ValidationIssue(**row) for row in (issues_res.data or [])]

            return Handoff(**res.data[0]).model_copy(update={"issues": saved_issues})
        except Exception as exc:
            _handle_db_exception(exc, f"update_handoff({handoff.id})")
