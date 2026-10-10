"""System health route.

Kept in its own router so main.py stays a thin assembly file and future
routers (/energy, /machines, ...) can plug in the same way.
"""

from fastapi import APIRouter

from backend.app.core.config import settings
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Liveness check used by the frontend to show connection status."""
    return HealthResponse(status="ok", service=settings.APP_NAME)
