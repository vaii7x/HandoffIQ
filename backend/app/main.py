"""FastAPI main application entrypoint for HandoffIQ."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.api.routes import health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers


def create_application() -> FastAPI:
    """Initialize and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="Multi-agent AI reliability and context handoff orchestration platform.",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    allowed_origins = [settings.FRONTEND_ORIGIN]
    # In development, also accept localhost variants if different
    if not settings.is_production:
        for extra in ["http://localhost:3000", "http://127.0.0.1:3000"]:
            if extra not in allowed_origins:
                allowed_origins.append(extra)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Mount health endpoint at root level (/health)
    app.include_router(health.router)

    # Mount versioned/prefixed application API (/api)
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_application()
