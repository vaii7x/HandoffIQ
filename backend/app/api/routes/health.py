"""Health check route reporting service status."""

from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from app.core.config import Settings, get_settings
from app.models.common import utcnow

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str = Field(default="healthy", description="Application status indicator")
    app_name: str = Field(description="Configured application name")
    app_env: str = Field(description="Environment mode")
    mock_mode: bool = Field(description="Whether mock mode is active")
    timestamp: datetime = Field(description="Current UTC timestamp")


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Reports the service status and whether mock mode is enabled without leaking secrets.",
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Returns application status and mode."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        mock_mode=settings.MOCK_MODE,
        timestamp=utcnow(),
    )
