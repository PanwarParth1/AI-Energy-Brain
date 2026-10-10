"""Alert API schema (section 15).

Alerts are a VIEW over existing anomaly/recommendation outputs, not a
second alert-generation system - see backend/app/services/alert_service.py.
"""

from __future__ import annotations

from pydantic import BaseModel


class AlertItem(BaseModel):
    alert_id: str
    severity: str  # WARNING | ANOMALY | HIGH | CRITICAL (source-status-dependent)
    category: str  # "machine_anomaly" | "recommendation"
    title: str
    machine_id: str
    cycle_index: int | None
    source: str


class AlertsResponse(BaseModel):
    count: int
    alerts: list[AlertItem]
