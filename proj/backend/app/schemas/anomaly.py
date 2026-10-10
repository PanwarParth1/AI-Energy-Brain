"""Machine Anomaly API schemas (section 13).

Mirrors ml.machine_health.anomaly.detect_anomaly()'s actual output -
does not add a fabricated "failure probability" field.
"""

from __future__ import annotations

from pydantic import BaseModel


class DeviationItem(BaseModel):
    feature: str
    z_score: float
    raw_value: float
    reference_mean: float
    explanation: str


class AnomalyResponse(BaseModel):
    machine_id: str
    cycle_index: int
    anomaly_score: float
    status: str  # NORMAL | WARNING | ANOMALY
    top_deviations: list[DeviationItem]
    reference_condition: dict
    reference_condition_meaning: str
    note: str
