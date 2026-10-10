"""Alerts route - a VIEW over existing anomaly/recommendation outputs
(section 15), not a second alert-generation system."""

from fastapi import APIRouter

from backend.app.schemas.alert import AlertsResponse
from backend.app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertsResponse, summary="Current alerts derived from anomaly + recommendation status")
def get_alerts():
    return alert_service.get_alerts()
