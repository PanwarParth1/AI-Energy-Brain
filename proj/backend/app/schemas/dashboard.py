"""Dashboard summary API schema (section 16) - the main endpoint the
future React dashboard will call. Combines already-existing service
outputs; computes nothing new itself.
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.schemas.energy import EnergySummaryResponse
from backend.app.schemas.recommendation import RecommendationItem


class MachineStatusCounts(BaseModel):
    total: int
    normal: int
    warning: int
    anomaly: int


class DashboardMachinesSummary(BaseModel):
    status_counts: MachineStatusCounts
    latest_cycle_index: int
    latest_status: str


class DashboardSummaryResponse(BaseModel):
    energy: EnergySummaryResponse
    machines: DashboardMachinesSummary
    top_recommendations: list[RecommendationItem]
