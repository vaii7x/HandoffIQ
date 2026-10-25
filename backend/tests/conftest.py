"""Pytest fixtures and environment configuration for HandoffIQ."""

import sys
import asyncio
import os
import pytest
from app.core.config import get_settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Ensure automated unit tests execute with deterministic in-memory fixtures without polluting remote databases."""
    monkeypatch.setenv("MOCK_MODE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

