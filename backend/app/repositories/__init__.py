"""Data persistence and repository interfaces for HandoffIQ."""

from app.repositories.base import TaskRepository
from app.repositories.in_memory import InMemoryTaskRepository, get_task_repository

__all__ = [
    "TaskRepository",
    "InMemoryTaskRepository",
    "get_task_repository",
]
