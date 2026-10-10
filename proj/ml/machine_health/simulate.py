"""Interactive What-If Simulation foundation (Part 12).

CORE IDEA (verified against the actual code before writing this file,
not assumed): every feature in ml/machine_health/features.py is a
PER-CYCLE statistic computed independently along axis=1 of each
sensor's (n_cycles, n_samples) matrix - mean, std, min, max, range,
rms, slope, kurtosis. None of them look across cycles (unlike the
energy module's lag/rolling features). The same is true downstream:
StandardScaler transforms column-wise using its stored training
mean_/scale_, and both the Part 7 classifier and the Part 8
IsolationForest score each row independently.

That means a single synthetic "cycle" - one (1, n_samples) array per
sensor - can be pushed through the EXISTING, UNMODIFIED
build_feature_table() / predict_from_sensors() / detect_anomaly()
functions and get a mathematically correct result. Nothing in
features.py, predict.py, or anomaly.py needed to change for this to
work, and nothing in this file duplicates their logic - it only
constructs the input shape they already expect and calls them as-is.

WHAT THIS FILE DOES:
  real baseline cycle (from the cached raw dataset, copied - never
  the original arrays)
      -> apply user perturbations (multiply / offset) to a COPY
      -> wrap into the (1, n_samples)-per-sensor shape the existing
         pipeline expects
      -> call the EXISTING predict_from_sensors() and detect_anomaly()
         unchanged, once for the untouched baseline and once for the
         perturbed scenario
      -> return both, clearly labelled

This is NOT retraining, NOT a new model, and NOT a physical digital
twin. It is a decision-support "what happens if this sensor reads
differently" tool, and every result is marked accordingly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ml.machine_health.anomaly import detect_anomaly
from ml.machine_health.predict import predict_from_sensors
from ml.machine_health.preprocess import SENSOR_METADATA, SENSOR_NAMES

# --- which sensors a what-if scenario may touch -----------------------
# Deliberately PHYSICAL sensors only, as an EXPLICIT whitelist rather
# than a string-match on SENSOR_METADATA's quantity text. CE and CP are
# both labelled "(virtual)" in the raw UCI documentation - they are
# computed BY the test rig's own software from other measurements, not
# independent physical inputs a real operator could set. SE ("Efficiency
# factor") is NOT explicitly labelled "(virtual)" in that same
# documentation (verified against data/raw/hydraulic/description.txt),
# but an earlier version of this list included it anyway on the strength
# of that missing label - a real bug, since efficiency factors are
# generally derived from other measurements just like CE/CP, and the
# project's own project-level instructions explicitly group SE with
# CE/CP as sensors to exclude pending further inspection. An explicit
# whitelist here removes the ambiguity for good: if a future part
# demonstrates SE is genuinely an independent, settable input, this is
# the one place to revisit - not a string match that can silently
# reclassify a sensor based on documentation wording alone.
PERTURBABLE_SENSORS: list[str] = [
    "PS1", "PS2", "PS3", "PS4", "PS5", "PS6",
    "EPS1",
    "FS1", "FS2",
    "TS1", "TS2", "TS3", "TS4",
    "VS1",
]
assert set(PERTURBABLE_SENSORS) <= set(SENSOR_NAMES), "PERTURBABLE_SENSORS must be a subset of known sensors"
assert not set(PERTURBABLE_SENSORS) & {"CE", "CP", "SE"}, "Virtual/derived channels must never be perturbable"

VALID_MODES = ("multiply", "offset")


class SimulationValidationError(ValueError):
    """Raised for any invalid perturbation - caught and translated to a
    clean 400 response by the backend service layer (never surfaced as
    a raw exception)."""


@dataclass(frozen=True)
class Perturbation:
    sensor: str
    mode: str  # "multiply" | "offset"
    value: float

    def validate(self) -> None:
        if self.sensor not in PERTURBABLE_SENSORS:
            raise SimulationValidationError(
                f"'{self.sensor}' is not a valid simulation input. Allowed sensors: "
                f"{PERTURBABLE_SENSORS} (virtual/derived channels CE, CP, SE are excluded)."
            )
        if self.mode not in VALID_MODES:
            raise SimulationValidationError(
                f"mode must be one of {VALID_MODES}, got '{self.mode}'."
            )
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise SimulationValidationError(f"value must be numeric, got {type(self.value).__name__}.")
        if math.isnan(self.value) or math.isinf(self.value):
            raise SimulationValidationError("value must be finite (not NaN/Infinity).")
        if self.mode == "multiply" and self.value <= 0:
            # Zero would collapse the whole cycle to a flat line (std/slope/rms
            # all become 0, destroying the signal); negative would flip sign in
            # a way no physical sensor reading does. Both are rejected rather
            # than silently "handled".
            raise SimulationValidationError(
                "multiply value must be a positive, finite number (0 or negative "
                "would produce a physically meaningless flat or sign-flipped signal)."
            )


def validate_perturbations(perturbations: list[Perturbation]) -> None:
    seen = set()
    for p in perturbations:
        p.validate()
        if p.sensor in seen:
            raise SimulationValidationError(
                f"Sensor '{p.sensor}' appears more than once in the perturbation list - "
                "apply at most one change per sensor per simulation."
            )
        seen.add(p.sensor)


def extract_baseline_cycle(sensors: dict[str, np.ndarray], cycle_index: int) -> dict[str, np.ndarray]:
    """Copy ONE real cycle's raw samples out of the full (n_cycles,
    n_samples) matrices, for every sensor. Returns 1D arrays.

    Uses .copy() explicitly - the returned dict shares no memory with
    the cached `sensors` dict, so nothing downstream can ever mutate
    the real dataset in memory, let alone on disk.
    """
    missing = set(SENSOR_NAMES) - set(sensors)
    if missing:
        raise SimulationValidationError(f"Missing sensor data for: {sorted(missing)}")

    n_cycles = next(iter(sensors.values())).shape[0]
    if cycle_index < 0 or cycle_index >= n_cycles:
        raise SimulationValidationError(f"baseline_cycle_index must be within 0-{n_cycles - 1}.")

    return {name: sensors[name][cycle_index].copy() for name in SENSOR_NAMES}


def apply_perturbations(
    baseline_cycle: dict[str, np.ndarray],
    perturbations: list[Perturbation],
) -> dict[str, np.ndarray]:
    """Return a NEW cycle dict (1D arrays) with the named sensors
    modified. The input `baseline_cycle` is never mutated - every array,
    perturbed or not, is copied into the result.

    Preserves array shape exactly (perturbations are elementwise), so
    downstream feature extraction sees the same sampling structure
    (100 Hz / 10 Hz / 1 Hz) it always does.
    """
    validate_perturbations(perturbations)

    result = {name: arr.copy() for name, arr in baseline_cycle.items()}
    by_sensor = {p.sensor: p for p in perturbations}

    for sensor, p in by_sensor.items():
        arr = result[sensor]
        if p.mode == "multiply":
            new_arr = arr * p.value
        else:  # "offset"
            new_arr = arr + p.value

        if np.isnan(new_arr).any() or np.isinf(new_arr).any():
            raise SimulationValidationError(
                f"Applying {p.mode}={p.value} to '{sensor}' produced NaN/Infinite values."
            )
        if new_arr.shape != arr.shape:
            raise SimulationValidationError(f"Perturbation changed the shape of '{sensor}' - rejected.")

        result[sensor] = new_arr

    return result


def _cycle_to_matrix_dict(cycle: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Wrap each sensor's 1D array into the (1, n_samples) shape that
    build_feature_table()/predict_from_sensors()/detect_anomaly()
    already expect (n_cycles=1). This is the ONLY adapter needed to
    reuse those functions unchanged - see module docstring."""
    return {name: arr.reshape(1, -1) for name, arr in cycle.items()}


def _run_existing_pipeline(cycle: dict[str, np.ndarray]) -> dict:
    """Push one synthetic cycle through the EXISTING, unmodified Part 7
    classifier and Part 8 anomaly detector. Returns their real outputs -
    nothing here is a hardcoded or simulated prediction."""
    matrix_dict = _cycle_to_matrix_dict(cycle)

    health_df = predict_from_sensors(matrix_dict)
    health_row = health_df.iloc[0].to_dict()

    anomaly_result = detect_anomaly(matrix_dict, cycle_position=0, top_n=5)

    return {"health": health_row, "anomaly": anomaly_result}


def _sensor_change_summary(
    baseline_cycle: dict[str, np.ndarray],
    simulated_cycle: dict[str, np.ndarray],
    perturbations: list[Perturbation],
) -> dict:
    """Real before/after summary statistics for each perturbed sensor -
    used for a quick "what actually changed" display. Every number here
    is computed from the actual arrays, not invented."""
    changes = {}
    for p in perturbations:
        base = baseline_cycle[p.sensor]
        sim = simulated_cycle[p.sensor]
        changes[p.sensor] = {
            "mode": p.mode,
            "value": p.value,
            "unit": SENSOR_METADATA[p.sensor]["unit"],
            "baseline_mean": float(base.mean()),
            "simulated_mean": float(sim.mean()),
        }
    return changes


def analyze_simulated_machine(
    sensors: dict[str, np.ndarray],
    baseline_cycle_index: int,
    perturbations: list[Perturbation],
) -> dict:
    """The Part 12 foundation function.

    sensors: the FULL cached {sensor_name: (n_cycles, n_samples)} dict -
        e.g. from preprocess.load_all_sensors() or the backend's cached
        copy. Never modified.
    baseline_cycle_index: a REAL cycle in that dataset to start from.
    perturbations: validated Perturbation objects to apply on top of it.

    Returns baseline and simulated results side by side, both produced
    by the exact same trained models Parts 7/8 already use - no
    retraining, no hardcoded thresholds, no second model.
    """
    baseline_cycle = extract_baseline_cycle(sensors, baseline_cycle_index)
    simulated_cycle = apply_perturbations(baseline_cycle, perturbations)

    baseline_result = _run_existing_pipeline(baseline_cycle)
    simulated_result = _run_existing_pipeline(simulated_cycle)

    return {
        "simulation": True,
        "scenario_type": "what_if",
        "baseline_cycle_index": baseline_cycle_index,
        "baseline": baseline_result,
        "simulated": simulated_result,
        "changes": _sensor_change_summary(baseline_cycle, simulated_cycle, perturbations),
        "note": (
            "This is a what-if simulation using modified sensor inputs, run through "
            "the same trained models as the real dashboard. It is not a real-time "
            "industrial measurement, not a physical digital twin, and a changed "
            "prediction does not guarantee a real-world outcome - or the reverse: "
            "an unchanged prediction does not rule one out."
        ),
    }
