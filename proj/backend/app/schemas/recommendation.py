"""Recommendation API schemas (section 14).

Mirrors ml.recommendation.schemas.Recommendation field-for-field so
the API never re-derives or renames what Part 9 already produces.
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.schemas.anomaly import DeviationItem  # noqa: F401 (kept for symmetry, not reused directly)


class EvidenceItem(BaseModel):
    signal: str
    observation: str
    severity: str
    source: str


class RecommendationItem(BaseModel):
    recommendation_id: str
    category: str
    priority: str
    title: str
    action: str
    reason: str
    evidence: list[EvidenceItem]
    confidence: float
    confidence_basis: str
    machine_id: str
    cycle_index: int | None
    energy_datetime: str | None
    source_models: list[str]
    limitations: list[str]
    generated_at: str


class RecommendationsResponse(BaseModel):
    count: int
    recommendations: list[RecommendationItem]


class RecommendationGenerateRequest(BaseModel):
    cycle_index: int | None = None
    include_energy: bool = False
