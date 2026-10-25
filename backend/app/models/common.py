"""Common base classes, utilities, and serialization helpers for Pydantic models."""

from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, ConfigDict


def utcnow() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class HandoffIQBaseModel(BaseModel):
    """Base Pydantic model for HandoffIQ domain entities."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )
