"""Machine / Machine-Health / Anomaly / Analysis routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.app.schemas.anomaly import AnomalyResponse
from backend.app.schemas.machine import MachineHealthResponse, MachineListResponse
from backend.app.schemas.recommendation import RecommendationsResponse
from backend.app.schemas.simulation import SimulatableSensorsResponse, SimulateRequest, SimulateResponse
from backend.app.services import machine_service, recommendation_service, simulation_service

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("", response_model=MachineListResponse,
            summary="List the dataset/test rig this project represents")
def list_machines():
    """Returns ONE entry: the hydraulic test rig this project's data
    comes from. This is not a factory fleet."""
    return machine_service.get_machine_list()


@router.get("/{machine_id}/health", response_model=MachineHealthResponse,
            summary="Part 7 cooler-condition classification for a cycle")
def get_health(
    machine_id: str,
    cycle_index: int | None = Query(None, description="Defaults to the most recent available cycle."),
):
    return machine_service.get_health(machine_id, cycle_index)


@router.get("/{machine_id}/anomaly", response_model=AnomalyResponse,
            summary="Part 8 sensor anomaly score/status for a cycle")
def get_anomaly(
    machine_id: str,
    cycle_index: int | None = Query(None, description="Defaults to the most recent available cycle."),
):
    return machine_service.get_anomaly(machine_id, cycle_index)


class MachineAnalyzeRequest(BaseModel):
    cycle_index: int


class MachineAnalyzeResponse(BaseModel):
    machine: dict
    health: dict
    anomaly: dict
    recommendations: list
    metadata: dict


@router.post("/analyze", response_model=MachineAnalyzeResponse,
             summary="Run Part 7 + Part 8 + Part 9 together for one real cycle")
def analyze_machine(payload: MachineAnalyzeRequest):
    """Orchestrates the existing Part 7/8/9 functions for one cycle -
    health prediction, anomaly detection, and recommendations - and
    returns them together. No ML logic is duplicated here."""
    from backend.app.core.config import settings

    machine_service.validate_cycle_index(payload.cycle_index)
    health = machine_service.get_health(settings.MACHINE_ID, payload.cycle_index)
    anomaly = machine_service.get_anomaly(settings.MACHINE_ID, payload.cycle_index)
    rec_result = recommendation_service.generate(cycle_index=payload.cycle_index, include_energy=False)

    machine_list = machine_service.get_machine_list()["machines"][0]

    return {
        "machine": machine_list,
        "health": health,
        "anomaly": anomaly,
        "recommendations": rec_result["recommendations"],
        "metadata": {
            "cycle_index": payload.cycle_index,
            "source_models": [health["model_type"], "isolation_forest"],
        },
    }


@router.get("/simulate/sensors", response_model=SimulatableSensorsResponse,
            summary="List the sensors and modes a what-if simulation may use")
def get_simulatable_sensors():
    """Foundation info for Part 13's UI: which physical sensors can be
    perturbed, which are excluded and why, and the valid perturbation modes."""
    return simulation_service.get_simulatable_sensors()


@router.post("/simulate", response_model=SimulateResponse,
             summary="What-if simulation: run a modified sensor scenario through the real Part 7/8 models")
def simulate_machine(payload: SimulateRequest):
    """Starts from a REAL baseline cycle, applies the requested
    multiply/offset perturbations to a copy (the original dataset is
    never modified), and runs BOTH the untouched baseline and the
    perturbed scenario through the existing, unmodified Part 7
    classifier and Part 8 anomaly detector.

    This is a what-if decision-support tool, not a live measurement or
    a physical digital twin - see the response's `note` field."""
    perturbations = [p.model_dump() for p in payload.perturbations]
    return simulation_service.run_simulation(
        payload.machine_id, payload.baseline_cycle_index, perturbations
    )
