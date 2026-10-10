"""Deterministic tests for the What-If Simulation foundation (Part 12).

Plain assertions (no pytest dependency), matching the pattern used by
ml/recommendation/tests.py and backend/tests/test_api.py. Runs against
REAL raw sensor data - no synthetic fixtures for the ML-facing tests,
since the whole point of this module is that it goes through the real
pipeline.
"""

from __future__ import annotations

import sys

import numpy as np

from ml.machine_health.anomaly import detect_anomaly
from ml.machine_health.predict import predict_from_sensors
from ml.machine_health.preprocess import SENSOR_NAMES, load_all_sensors
from ml.machine_health.simulate import (
    PERTURBABLE_SENSORS,
    Perturbation,
    SimulationValidationError,
    analyze_simulated_machine,
    apply_perturbations,
    extract_baseline_cycle,
)

PASSED = []
FAILED = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        PASSED.append(name)
    else:
        FAILED.append(f"{name}: {detail}")


_sensors_cache = None


def get_sensors():
    global _sensors_cache
    if _sensors_cache is None:
        _sensors_cache = load_all_sensors()
    return _sensors_cache


# --- TEST 1: load a valid baseline cycle -----------------------------------
def test_1_baseline_load():
    sensors = get_sensors()
    cycle = extract_baseline_cycle(sensors, 301)
    check("TEST1_all_sensors_present", set(cycle.keys()) == set(SENSOR_NAMES))
    check("TEST1_ps1_matches_real_row", np.array_equal(cycle["PS1"], sensors["PS1"][301]))


# --- TEST 2: multiply perturbation -----------------------------------------
def test_2_multiply():
    sensors = get_sensors()
    baseline = extract_baseline_cycle(sensors, 301)
    simulated = apply_perturbations(baseline, [Perturbation("VS1", "multiply", 2.0)])
    check("TEST2_multiply_correct", np.allclose(simulated["VS1"], baseline["VS1"] * 2.0))


# --- TEST 3: offset perturbation --------------------------------------------
def test_3_offset():
    sensors = get_sensors()
    baseline = extract_baseline_cycle(sensors, 301)
    simulated = apply_perturbations(baseline, [Perturbation("TS2", "offset", 5.0)])
    check("TEST3_offset_correct", np.allclose(simulated["TS2"], baseline["TS2"] + 5.0))


# --- TEST 4: original sensor data remains unchanged -------------------------
def test_4_immutability():
    sensors = get_sensors()
    original = sensors["PS1"][301].copy()
    baseline = extract_baseline_cycle(sensors, 301)
    _ = apply_perturbations(baseline, [Perturbation("PS1", "multiply", 10.0), Perturbation("TS1", "offset", 50.0)])
    check("TEST4_full_dataset_unchanged", np.array_equal(sensors["PS1"][301], original))
    check("TEST4_extracted_baseline_unchanged", np.array_equal(baseline["PS1"], original))


# --- TEST 5: invalid sensor name rejected -----------------------------------
def test_5_invalid_sensor():
    for bad in ["CE", "CP", "SE", "NOT_A_SENSOR"]:
        try:
            Perturbation(bad, "offset", 1.0).validate()
            check(f"TEST5_rejects_{bad}", False, "did not raise")
        except SimulationValidationError:
            check(f"TEST5_rejects_{bad}", True)


# --- TEST 6: invalid perturbation mode rejected -----------------------------
def test_6_invalid_mode():
    try:
        Perturbation("PS1", "scale", 2.0).validate()
        check("TEST6_rejects_bad_mode", False, "did not raise")
    except SimulationValidationError:
        check("TEST6_rejects_bad_mode", True)


# --- TEST 7: NaN/infinite values rejected -----------------------------------
def test_7_nan_inf():
    for bad_val in [float("nan"), float("inf"), float("-inf")]:
        try:
            Perturbation("PS1", "offset", bad_val).validate()
            check(f"TEST7_rejects_{bad_val}", False, "did not raise")
        except SimulationValidationError:
            check(f"TEST7_rejects_{bad_val}", True)
    try:
        Perturbation("PS1", "multiply", 0.0).validate()
        check("TEST7_rejects_multiply_zero", False, "did not raise")
    except SimulationValidationError:
        check("TEST7_rejects_multiply_zero", True)
    try:
        Perturbation("PS1", "multiply", -2.0).validate()
        check("TEST7_rejects_multiply_negative", False, "did not raise")
    except SimulationValidationError:
        check("TEST7_rejects_multiply_negative", True)


# --- TEST 8: sensor shape remains unchanged ---------------------------------
def test_8_shape_preserved():
    sensors = get_sensors()
    baseline = extract_baseline_cycle(sensors, 301)
    simulated = apply_perturbations(baseline, [Perturbation("PS1", "multiply", 3.0), Perturbation("TS1", "offset", 5.0)])
    for name in SENSOR_NAMES:
        check(f"TEST8_shape_{name}", simulated[name].shape == baseline[name].shape,
              f"{simulated[name].shape} != {baseline[name].shape}")


# --- TEST 9: feature extraction works on simulated data ---------------------
def test_9_feature_extraction():
    sensors = get_sensors()
    result = analyze_simulated_machine(sensors, 301, [Perturbation("VS1", "multiply", 2.0)])
    check("TEST9_health_present", "predicted_condition" in result["simulated"]["health"])
    check("TEST9_anomaly_present", "anomaly_score" in result["simulated"]["anomaly"])


# --- TEST 10: existing Part 7 model receives simulated features ------------
def test_10_part7_integration():
    sensors = get_sensors()
    result = analyze_simulated_machine(sensors, 1714, [Perturbation("VS1", "multiply", 5.0)])
    h = result["simulated"]["health"]
    check("TEST10_valid_condition", h["predicted_condition"] in (3, 20, 100), h["predicted_condition"])
    check("TEST10_confidence_in_range", 0.0 <= h["confidence"] <= 1.0)


# --- TEST 11: existing Part 8 anomaly pipeline receives simulated features -
def test_11_part8_integration():
    sensors = get_sensors()
    result = analyze_simulated_machine(sensors, 1714, [Perturbation("VS1", "multiply", 5.0)])
    a = result["simulated"]["anomaly"]
    check("TEST11_valid_status", a["status"] in ("NORMAL", "WARNING", "ANOMALY"), a["status"])
    check("TEST11_score_is_float", isinstance(a["anomaly_score"], float))
    check("TEST11_deviations_present", isinstance(a["top_deviations"], list))
    # Real, model-driven change (not hardcoded): a healthy reference cycle
    # (1714) with vibration multiplied x5 should score MORE abnormal than
    # its own untouched baseline - this is the actual IsolationForest
    # scoring the perturbed cycle, not an if/else rule.
    check("TEST11_score_increased_with_perturbation",
          result["simulated"]["anomaly"]["anomaly_score"] > result["baseline"]["anomaly"]["anomaly_score"],
          f"{result['simulated']['anomaly']['anomaly_score']} vs {result['baseline']['anomaly']['anomaly_score']}")


# --- TEST 12: baseline prediction identical to the normal pipeline ---------
def test_12_baseline_matches_real_pipeline():
    sensors = get_sensors()
    cycle_index = 301
    real_health = predict_from_sensors(sensors).iloc[cycle_index].to_dict()
    real_anomaly = detect_anomaly(sensors, cycle_position=cycle_index, top_n=5)

    result = analyze_simulated_machine(sensors, cycle_index, [Perturbation("VS1", "multiply", 2.0)])
    sim_baseline_health = result["baseline"]["health"]
    sim_baseline_anomaly = result["baseline"]["anomaly"]

    check("TEST12_condition_matches", sim_baseline_health["predicted_condition"] == real_health["predicted_condition"])
    check("TEST12_confidence_matches", abs(sim_baseline_health["confidence"] - real_health["confidence"]) < 1e-9)
    check("TEST12_anomaly_score_matches", abs(sim_baseline_anomaly["anomaly_score"] - real_anomaly["anomaly_score"]) < 1e-9)
    check("TEST12_anomaly_status_matches", sim_baseline_anomaly["status"] == real_anomaly["status"])


# --- duplicate-sensor validation (extra, beyond the spec's 13) -------------
def test_extra_duplicate_sensor_rejected():
    sensors = get_sensors()
    try:
        analyze_simulated_machine(sensors, 301, [
            Perturbation("PS1", "multiply", 2.0),
            Perturbation("PS1", "offset", 5.0),
        ])
        check("TESTX_rejects_duplicate_sensor", False, "did not raise")
    except SimulationValidationError:
        check("TESTX_rejects_duplicate_sensor", True)


# --- out-of-range cycle index -----------------------------------------------
def test_extra_invalid_cycle_index():
    sensors = get_sensors()
    try:
        analyze_simulated_machine(sensors, 999999, [Perturbation("PS1", "multiply", 2.0)])
        check("TESTX_rejects_bad_cycle_index", False, "did not raise")
    except SimulationValidationError:
        check("TESTX_rejects_bad_cycle_index", True)


def run_all():
    for fn in [test_1_baseline_load, test_2_multiply, test_3_offset, test_4_immutability,
               test_5_invalid_sensor, test_6_invalid_mode, test_7_nan_inf, test_8_shape_preserved,
               test_9_feature_extraction, test_10_part7_integration, test_11_part8_integration,
               test_12_baseline_matches_real_pipeline, test_extra_duplicate_sensor_rejected,
               test_extra_invalid_cycle_index]:
        fn()

    print(f"PASSED: {len(PASSED)}")
    for name in PASSED:
        print(f"  ok  {name}")
    print(f"\nFAILED: {len(FAILED)}")
    for name in FAILED:
        print(f"  FAIL  {name}")

    return len(FAILED) == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
