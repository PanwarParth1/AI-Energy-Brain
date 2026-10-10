"""What-If Simulation API schemas (Part 12).

Mirrors ml.machine_health.simulate's real output field-for-field -
nothing here is a new/invented shape.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.anomaly import DeviationItem
from backend.app.schemas.recommendation import RecommendationItem


class PerturbationInput(BaseModel):
    sensor: str = Field(..., description="One of the 14 physical sensors - see GET /machines/simulate/sensors.")
    mode: Literal["multiply", "offset"]
    value: float


class SimulateRequest(BaseModel):
    machine_id: str
    baseline_cycle_index: int
    perturbations: list[PerturbationInput] = Field(default_factory=list)


class SimHealth(BaseModel):
    predicted_condition: int
    predicted_condition_meaning: str
    confidence: float
    class_probabilities: dict[str, float]


class SimAnomaly(BaseModel):
    anomaly_score: float
    status: str
    top_deviations: list[DeviationItem]
    reference_condition: dict
    reference_condition_meaning: str
    note: str


class SimScenarioResult(BaseModel):
    health: SimHealth
    anomaly: SimAnomaly


class SensorChange(BaseModel):
    mode: str
    value: float
    unit: str
    baseline_mean: float
    simulated_mean: float


class SimulateResponse(BaseModel):
    simulation: bool
    scenario_type: str
    machine_id: str
    baseline_cycle_index: int
    baseline: SimScenarioResult
    simulated: SimScenarioResult
    changes: dict[str, SensorChange]
    note: str
    # Part 18 (optional, additive): recommendations from the existing Part 9 engine,
    # computed from the SIMULATED outputs. None + recommendations_error if the engine failed.
    recommendations: list[RecommendationItem] | None = None
    recommendations_error: str | None = None
    recommendation_note: str | None = None


class SimulatableSensorsResponse(BaseModel):
    sensors: list[str]
    excluded_virtual_sensors: list[str]
    valid_modes: list[str]
    note: str
