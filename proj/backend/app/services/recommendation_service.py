"""Recommendation service: thin wrapper over ml.recommendation.engine -
no rule logic is reimplemented here, only conversion of Part 9's
dataclasses into plain dicts for the Pydantic response models.
"""

from __future__ import annotations

from backend.app.core.errors import bad_request
from backend.app.services import machine_service
from ml.recommendation.energy_rules import get_recent_energy_observation
from ml.recommendation.engine import generate_recommendations
from ml.recommendation.predict import PROCESSED_ENERGY_CSV
from ml.recommendation.schemas import Recommendation


def _to_dict(rec: Recommendation) -> dict:
    return rec.to_dict()


def generate(cycle_index: int | None, include_energy: bool) -> dict:
    """Generate recommendations for one real cycle (Part 7 + Part 8
    outputs, sliced/recomputed via machine_service - not duplicated
    here), optionally paired with a real energy observation.
    """
    health_result = None
    anomaly_result = None

    if cycle_index is not None:
        machine_service.validate_cycle_index(cycle_index)
        health_result = machine_service.get_health_result_dict(cycle_index)
        anomaly_result = machine_service.get_anomaly_result_dict(cycle_index)

    energy_observation = get_recent_energy_observation(PROCESSED_ENERGY_CSV) if include_energy else None

    recs = generate_recommendations(
        health_result=health_result,
        anomaly_result=anomaly_result,
        cycle_index=cycle_index,
        energy_observation=energy_observation,
    )
    return {"count": len(recs), "recommendations": [_to_dict(r) for r in recs]}


def get_latest() -> dict:
    """GET-friendly default: recommendations for the most recent real
    cycle, machine track only (no energy pairing, since GET has no
    request body - matches section 14's GET /api/recommendations)."""
    latest_index = machine_service._latest_cycle_index()
    return generate(cycle_index=latest_index, include_energy=False)
