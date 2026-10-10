"""Energy API schemas (sections 5-8). Field names/units are chosen to
stay honest about what the Tetouan dataset actually is - a public
city-level power-consumption dataset, never described as factory or
machine energy data.
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.schemas.common import ModelInfo


class EnergySummaryResponse(BaseModel):
    current_power: float
    current_power_timestamp: str
    recent_average_power: float
    recent_average_window: str
    forecast_power: float
    forecast_timestamp: str
    forecast_horizon: str
    dataset: str
    unit: str
    limitations: list[str]


class EnergyHistoryPoint(BaseModel):
    timestamp: str
    total_power_consumption: float
    zone_1_power_consumption: float
    zone_2_power_consumption: float
    zone_3_power_consumption: float


class EnergyHistoryResponse(BaseModel):
    dataset: str
    unit: str
    count: int
    records: list[EnergyHistoryPoint]


class EnergyForecastPoint(BaseModel):
    timestamp: str
    value: float


class EnergyForecastResponse(BaseModel):
    target: str
    unit: str
    horizon_steps: int
    step_size: str
    predictions: list[EnergyForecastPoint]
    model: ModelInfo
    limitations: list[str]


# --- Part 14: Energy + Production What-If -----------------------------
# Manual scenario inputs only - the Tetouan dataset has no production
# data, and the Part 6 Random Forest forecaster is not used or modified
# here. This is pure arithmetic + classification over user-provided
# numbers, clearly marked as a simulation throughout.

class EnergyScenarioRequest(BaseModel):
    baseline_production: float
    baseline_energy: float
    scenario_production: float
    scenario_energy: float


class EnergyScenarioPoint(BaseModel):
    production: float
    energy: float
    energy_intensity: float


class EnergyScenarioChanges(BaseModel):
    production_percent: float
    energy_percent: float
    energy_intensity_percent: float


class EnergyScenarioResponse(BaseModel):
    simulation: bool
    baseline: EnergyScenarioPoint
    scenario: EnergyScenarioPoint
    changes: EnergyScenarioChanges
    status: str  # "NORMAL" | "WARNING"
    classification: str  # "PROPORTIONAL" | "ENERGY_EFFICIENCY_WARNING"
    explanation: str
    threshold_percent: float
    threshold_note: str
    note: str
