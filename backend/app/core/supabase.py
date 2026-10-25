"""Supabase client initialization and configuration validation."""

from typing import Optional
from supabase import Client, create_client

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError

_supabase_client: Optional[Client] = None


def validate_supabase_config(settings: Settings) -> None:
    """Validate that valid Supabase credentials are provided when MOCK_MODE is disabled."""
    if settings.MOCK_MODE:
        return

    url = settings.SUPABASE_URL.strip() if settings.SUPABASE_URL else ""
    key = (
        settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value().strip()
        if settings.SUPABASE_SERVICE_ROLE_KEY
        else ""
    )

    if (
        not url
        or "placeholder" in url.lower()
        or not key
        or "placeholder" in key.lower()
    ):
        raise ConfigurationError(
            "Supabase configuration is invalid or missing. "
            "Valid SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are strictly required when MOCK_MODE is disabled."
        )


def get_supabase_client() -> Client:
    """Return initialized Supabase client using the backend service role key.

    Fails explicitly with ConfigurationError if MOCK_MODE is false and credentials
    are missing or placeholders.
    """
    global _supabase_client
    settings = get_settings()
    validate_supabase_config(settings)

    if _supabase_client is None:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
        _supabase_client = create_client(url, key)

    return _supabase_client


def set_supabase_client(client: Optional[Client]) -> None:
    """Configure or inject a custom or mocked Supabase client for testing."""
    global _supabase_client
    _supabase_client = client
