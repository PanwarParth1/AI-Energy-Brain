"""Energy Intelligence routes - thin wrappers over energy_service."""

from fastapi import APIRouter, Query

from backend.app.core.config import settings
from backend.app.schemas.energy import (
    EnergyForecastResponse,
    EnergyHistoryResponse,
    EnergyScenarioRequest,
    EnergyScenarioResponse,
    EnergySummaryResponse,
)
from backend.app.services import energy_service

router = APIRouter(prefix="/energy", tags=["energy"])


@router.get("/summary", response_model=EnergySummaryResponse,
            summary="Current, recent-average, and next-step forecast power for the Tetouan dataset")
def get_summary():
    """Dashboard-level energy snapshot: the dataset's latest real
    reading, its trailing-24h average, and the model's one-step-ahead
    forecast. This is a public city-level power dataset, not
    industrial machine energy data."""
    return energy_service.get_summary()


@router.get("/history", response_model=EnergyHistoryResponse,
            summary="Chronological historical power-consumption records")
def get_history(
    limit: int = Query(settings.ENERGY_HISTORY_DEFAULT_LIMIT, ge=1, le=settings.ENERGY_HISTORY_MAX_LIMIT,
                        description=f"Max {settings.ENERGY_HISTORY_MAX_LIMIT} records."),
    start: str | None = Query(None, description="ISO datetime lower bound, e.g. 2017-06-01T00:00:00"),
    end: str | None = Query(None, description="ISO datetime upper bound"),
):
    """Returns the most recent `limit` records within the optional
    [start, end] window, oldest-to-newest."""
    return energy_service.get_history(limit=limit, start=start, end=end)


@router.get("/forecast", response_model=EnergyForecastResponse,
            summary="Multi-step energy forecast (recursive, short-horizon)")
def get_forecast(
    horizon: int = Query(settings.ENERGY_FORECAST_DEFAULT_HORIZON, ge=1,
                          le=settings.ENERGY_FORECAST_MAX_HORIZON,
                          description=f"Steps of 10 minutes each, max {settings.ENERGY_FORECAST_MAX_HORIZON}."),
):
    """Calls Part 6's own predict_future() - no forecasting logic is
    reimplemented here. See response `limitations` for the future-weather
    and error-compounding caveats that apply beyond a few steps."""
    return energy_service.get_forecast(horizon=horizon)


@router.post("/simulate", response_model=EnergyScenarioResponse,
             summary="Energy + Production what-if: compare energy intensity between a baseline and a manual scenario")
def simulate_energy_production(payload: EnergyScenarioRequest):
    """Part 14: manual production + energy what-if. Does NOT call or
    modify the Part 6 Random Forest forecaster - the Tetouan dataset has
    no production data, so this is pure arithmetic over user-provided
    numbers, classified against a documented prototype threshold.
    See response `note` and `threshold_note`."""
    return energy_service.run_energy_production_scenario(
        baseline_production=payload.baseline_production,
        baseline_energy=payload.baseline_energy,
        scenario_production=payload.scenario_production,
        scenario_energy=payload.scenario_energy,
    )
