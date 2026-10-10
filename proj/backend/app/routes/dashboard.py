"""Dashboard summary route - the main endpoint the future React
dashboard will call. Pure composition of existing services."""

from fastapi import APIRouter

from backend.app.schemas.dashboard import DashboardSummaryResponse
from backend.app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse,
            summary="Combined energy + machine + top-recommendations snapshot")
def get_dashboard_summary():
    return dashboard_service.get_summary()
