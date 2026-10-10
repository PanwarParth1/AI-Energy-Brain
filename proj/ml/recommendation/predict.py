"""Convenience entry points for generating recommendations from REAL
project data, mirroring the predict.py pattern used in ml/energy and
ml/machine_health.
"""

from __future__ import annotations

from pathlib import Path

from ml.energy.predict import predict_on_processed
from ml.energy.train import load_full_processed
from ml.machine_health.anomaly import detect_anomaly
from ml.machine_health.predict import predict_from_sensors
from ml.machine_health.preprocess import load_all_sensors
from ml.recommendation.energy_rules import get_recent_energy_observation
from ml.recommendation.engine import generate_recommendations
from ml.recommendation.schemas import Recommendation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_ENERGY_CSV = PROJECT_ROOT / "data" / "processed" / "tetouan_energy_processed.csv"


def recommend_for_machine_cycle(cycle_index: int, include_energy: bool = False) -> list[Recommendation]:
    """Generate recommendations for ONE real hydraulic cycle, using
    actual Part 7 + Part 8 outputs for that cycle. Optionally attaches
    one real (but unrelated - see engine.py's cross-track note) energy
    observation to demonstrate cross-track logic.
    """
    sensors = load_all_sensors()

    health_df = predict_from_sensors(sensors)
    health_result = health_df.iloc[cycle_index].to_dict()

    anomaly_result = detect_anomaly(sensors, cycle_position=cycle_index, top_n=5)

    energy_observation = get_recent_energy_observation(PROCESSED_ENERGY_CSV) if include_energy else None

    return generate_recommendations(
        health_result=health_result,
        anomaly_result=anomaly_result,
        cycle_index=cycle_index,
        energy_observation=energy_observation,
    )


def recommend_for_energy_only(at_datetime=None) -> list[Recommendation]:
    """Generate recommendations from the energy track alone, using a
    real observation from the processed Tetouan data."""
    energy_observation = get_recent_energy_observation(PROCESSED_ENERGY_CSV, at_datetime=at_datetime)
    return generate_recommendations(energy_observation=energy_observation)


if __name__ == "__main__":
    print("=== Recommendation Engine: real-data smoke test ===\n")

    print("--- Cycle 1675 (reference, cooler=100, expected mostly quiet) ---")
    for r in recommend_for_machine_cycle(1675):
        print(f"[{r.priority}] {r.category}: {r.title}")

    print("\n--- Cycle 211 (degraded cooler=3, expect inspection) ---")
    for r in recommend_for_machine_cycle(211):
        print(f"[{r.priority}] {r.category}: {r.title}")

    print("\n--- Energy-only, latest real observation ---")
    for r in recommend_for_energy_only():
        print(f"[{r.priority}] {r.category}: {r.title}")
