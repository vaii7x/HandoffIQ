"""Central API router assembling all sub-routes."""

from fastapi import APIRouter
from app.api.routes import context_map, experiments, handoffs, health, tasks, workflow

api_router = APIRouter()

# Register route modules
api_router.include_router(health.router)
api_router.include_router(tasks.router)
api_router.include_router(handoffs.router)
api_router.include_router(workflow.router)
api_router.include_router(context_map.router)
api_router.include_router(experiments.router)
