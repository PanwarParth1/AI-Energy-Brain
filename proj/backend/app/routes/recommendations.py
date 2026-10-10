"""Recommendation Engine routes - thin wrappers over recommendation_service,
which itself only calls Part 9's generate_recommendations()."""

from fastapi import APIRouter

from backend.app.schemas.recommendation import RecommendationGenerateRequest, RecommendationsResponse
from backend.app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationsResponse,
            summary="Recommendations for the most recent real cycle")
def get_recommendations():
    return recommendation_service.get_latest()


@router.post("/generate", response_model=RecommendationsResponse,
             summary="Generate recommendations for a specific cycle, optionally with a real energy observation")
def generate_recommendations(payload: RecommendationGenerateRequest):
    """cycle_index=None with include_energy=False returns the
    deterministic CONTINUE_MONITORING default (Part 9's Case E)."""
    return recommendation_service.generate(
        cycle_index=payload.cycle_index, include_energy=payload.include_energy
    )
