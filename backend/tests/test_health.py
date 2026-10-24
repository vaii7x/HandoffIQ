"""Tests for application startup, health endpoints, and OpenAPI generation."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a FastAPI test client."""
    return TestClient(app)


def test_app_startup_and_openapi_generation(client: TestClient) -> None:
    """Verify application boots and generates OpenAPI specification."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "HandoffIQ"
    assert "/health" in data["paths"]
    assert "/api/health" in data["paths"]


def test_health_endpoint_root(client: TestClient) -> None:
    """Verify GET /health returns valid JSON with required health status and mock mode."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "HandoffIQ"
    assert "app_env" in data
    assert "mock_mode" in data
    assert isinstance(data["mock_mode"], bool)
    assert "timestamp" in data


def test_health_endpoint_prefixed(client: TestClient) -> None:
    """Verify GET /api/health also returns valid JSON under API prefix."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mock_mode"] is True or data["mock_mode"] is False


def test_no_secrets_exposed_in_health_response(client: TestClient) -> None:
    """Verify that credentials and secrets are never exposed in health checks."""
    response = client.get("/health")
    content = response.text.lower()
    forbidden_terms = ["placeholder-gemini-key", "service-role", "placeholder-service-role-key"]
    for term in forbidden_terms:
        assert term not in content, f"Secret term '{term}' leaked in health endpoint response!"


def test_settings_secrets_masked() -> None:
    """Verify SecretStr prevents accidental credential leakage in string conversions."""
    settings = get_settings()
    # str representation of SecretStr must be masked
    assert str(settings.SUPABASE_SERVICE_ROLE_KEY) == "**********"
    assert str(settings.GEMINI_API_KEY) == "**********"
    # Secret values can only be accessed via explicit method
    assert settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value() is not None
    assert settings.GEMINI_API_KEY.get_secret_value() is not None


def test_cors_headers(client: TestClient) -> None:
    """Verify CORS preflight handles allowed frontend origin."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
