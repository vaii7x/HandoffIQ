"""FastAPI router for HandoffIQ Presentation-Ready Demo Mode."""

from typing import List
from fastapi import APIRouter, Query

from app.models.demo import (
    DemoHandoffItem,
    DemoRepairItem,
    DemoRequirement,
    DemoRevalidationResponse,
    DemoValidationResponse,
    OracleCheck,
)
from app.services.demo_service import (
    DEMO_BROKEN_HANDOFF,
    DEMO_REPAIRS,
    DEMO_REQUIREMENTS,
    revalidate_demo_handoff,
    run_oracle_checks,
    validate_demo_handoff,
)

router = APIRouter()


@router.get("/requirements", response_model=List[DemoRequirement])
async def get_demo_requirements() -> List[DemoRequirement]:
    """Return the authoritative 6 canonical requirements for the pharmacy demo."""
    return DEMO_REQUIREMENTS


@router.get("/broken-handoff", response_model=List[DemoHandoffItem])
async def get_demo_broken_handoff() -> List[DemoHandoffItem]:
    """Return the deliberately broken downstream handoff fixture (5 defects + 1 preserved)."""
    return DEMO_BROKEN_HANDOFF


@router.post("/validate", response_model=DemoValidationResponse)
async def run_demo_validation() -> DemoValidationResponse:
    """Execute the real validator against the broken handoff fixture and compare with oracle."""
    return validate_demo_handoff()


@router.get("/repairs", response_model=List[DemoRepairItem])
async def get_demo_repairs() -> List[DemoRepairItem]:
    """Return the 5 unambiguous repairs restoring canonical specifications with diffs."""
    return DEMO_REPAIRS


@router.post("/revalidate", response_model=DemoRevalidationResponse)
async def run_demo_revalidation() -> DemoRevalidationResponse:
    """Execute revalidation across both the real validator and independent demo oracle."""
    return revalidate_demo_handoff()


@router.get("/oracle", response_model=List[OracleCheck])
async def get_demo_oracle_checks(
    phase: str = Query(default="broken_inspection", description="'broken_inspection' or 'revalidation'")
) -> List[OracleCheck]:
    """Run independent deterministic oracle assertions for the given demo phase."""
    if phase == "revalidation":
        # Build repaired items map
        repair_map = {rep.requirement_id: rep.repaired_text for rep in DEMO_REPAIRS}
        repaired_items: List[DemoHandoffItem] = []
        for item in DEMO_BROKEN_HANDOFF:
            if item.requirement_id in repair_map:
                repaired_items.append(
                    DemoHandoffItem(
                        id=item.id,
                        requirement_id=item.requirement_id,
                        defect_id=item.defect_id,
                        status="repaired",
                        received_text=repair_map[item.requirement_id],
                        original_text=item.original_text,
                    )
                )
            else:
                repaired_items.append(item)
        return run_oracle_checks(repaired_items, phase="revalidation")
    else:
        return run_oracle_checks(DEMO_BROKEN_HANDOFF, phase="broken_inspection")
