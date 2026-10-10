"""Deterministic unit/integration tests for the Recommendation Engine.

No new test-framework dependency (pytest is not in requirements.txt) -
plain functions + assert, run via `python ml/recommendation/tests.py`.

Section 23's TEST 1-8, using SYNTHETIC fixture inputs shaped exactly
like the real predict_from_sensors()/detect_anomaly() outputs. These
fixtures are clearly labelled as test fixtures and are NEVER written
into any model report - they exist only to exercise rule-engine
branches deterministically and fast, independent of which real cycles
happen to be available.
"""

from __future__ import annotations

from ml.recommendation.engine import generate_recommendations
from ml.recommendation.schemas import PRIORITY_RANK

PASSED = []
FAILED = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        PASSED.append(name)
    else:
        FAILED.append(f"{name}: {detail}")


# --- fixture builders (synthetic, clearly labelled) -----------------------

def fixture_health(predicted_condition=100, confidence=0.99, meaning="full efficiency"):
    return {
        "predicted_condition": predicted_condition,
        "predicted_condition_meaning": meaning,
        "confidence": confidence,
        "class_probabilities": {"3": 0.0, "20": 0.0, "100": confidence},
    }


def fixture_anomaly(status="NORMAL", score=0.4, deviations=None):
    return {
        "anomaly_score": score,
        "status": status,
        "top_deviations": deviations or [],
        "reference_condition": {"cooler_condition": 100},
        "reference_condition_meaning": "full efficiency",
        "note": "test fixture",
    }


def fixture_deviation(feature="TS1_mean", z=4.0):
    return {"feature": feature, "z_score": z, "raw_value": 0.0, "reference_mean": 0.0,
            "explanation": f"{feature} deviates (test fixture)"}


# --- TEST 1: normal machine -> no unnecessary maintenance recommendation --
def test_1_normal_machine():
    recs = generate_recommendations(
        health_result=fixture_health(100, 0.99, "full efficiency"),
        anomaly_result=fixture_anomaly("NORMAL", 0.4),
        cycle_index=None,
    )
    check("TEST1_single_rec", len(recs) == 1, f"got {len(recs)}")
    check("TEST1_is_continue_monitoring", recs[0].category == "CONTINUE_MONITORING", recs[0].category)


# --- TEST 2: high anomaly -> inspection recommendation ---------------------
def test_2_high_anomaly():
    recs = generate_recommendations(
        health_result=fixture_health(100, 0.95, "full efficiency"),
        anomaly_result=fixture_anomaly("ANOMALY", 0.9, [fixture_deviation("TS1_mean", 4.0)]),
        cycle_index=None,
    )
    check("TEST2_has_rec", len(recs) >= 1)
    check("TEST2_is_inspection", any(r.category == "MACHINE_INSPECTION" for r in recs),
          [r.category for r in recs])


# --- TEST 3: high anomaly + degraded health -> higher priority -------------
def test_3_anomaly_plus_degraded():
    recs_mild = generate_recommendations(
        health_result=fixture_health(100, 0.95, "full efficiency"),
        anomaly_result=fixture_anomaly("WARNING", 0.6, [fixture_deviation("TS1_mean", 2.0)]),
        cycle_index=None,
    )
    recs_severe = generate_recommendations(
        health_result=fixture_health(3, 0.95, "close to total failure"),
        anomaly_result=fixture_anomaly("ANOMALY", 0.9, [fixture_deviation("TS1_mean", 4.0)]),
        cycle_index=None,
    )
    mild_priority = max(PRIORITY_RANK[r.priority] for r in recs_mild)
    severe_priority = max(PRIORITY_RANK[r.priority] for r in recs_severe)
    check("TEST3_severe_outranks_mild", severe_priority > mild_priority,
          f"mild={mild_priority} severe={severe_priority}")


# --- TEST 4: temperature + vibration deviation -> consolidated rec --------
def test_4_consolidated_mechanical():
    recs = generate_recommendations(
        health_result=fixture_health(20, 0.9, "reduced efficiency"),
        anomaly_result=fixture_anomaly("ANOMALY", 0.85, [
            fixture_deviation("TS1_mean", 4.0),
            fixture_deviation("TS2_mean", 3.8),
            fixture_deviation("VS1_std", 3.5),
        ]),
        cycle_index=None,
    )
    machine_recs = [r for r in recs if r.category == "MACHINE_INSPECTION"]
    check("TEST4_single_consolidated_rec", len(machine_recs) == 1, f"got {len(machine_recs)}")
    check("TEST4_mentions_both_areas",
          "cooling" in machine_recs[0].action.lower() and "mechanical" in machine_recs[0].action.lower(),
          machine_recs[0].action)


# --- TEST 5: elevated energy forecast only -> energy recommendation -------
def test_5_energy_only():
    recs = generate_recommendations(
        energy_observation={"datetime": "2017-07-15 14:00:00", "actual": 100000, "trailing_mean": 60000},
    )
    check("TEST5_has_energy_rec", any(r.category in ("ENERGY_MONITORING", "ENERGY_OPTIMIZATION") for r in recs),
          [r.category for r in recs])


# --- TEST 6: energy + machine anomaly -> combined recommendation ----------
def test_6_combined():
    recs = generate_recommendations(
        health_result=fixture_health(3, 0.95, "close to total failure"),
        anomaly_result=fixture_anomaly("ANOMALY", 0.9, [fixture_deviation("TS1_mean", 4.0)]),
        cycle_index=None,
        energy_observation={"datetime": "2017-07-15 14:00:00", "actual": 100000, "trailing_mean": 60000},
    )
    check("TEST6_has_cross_track_rec", any(r.recommendation_id.startswith("REC-CROSS") for r in recs),
          [r.recommendation_id for r in recs])


# --- TEST 7: multiple overlapping signals -> duplicate suppression --------
def test_7_duplicate_suppression():
    recs = generate_recommendations(
        health_result=fixture_health(3, 0.95, "close to total failure"),
        anomaly_result=fixture_anomaly("ANOMALY", 0.9, [
            fixture_deviation("TS1_mean", 5.0),
            fixture_deviation("TS2_mean", 4.9),
            fixture_deviation("TS3_mean", 4.8),
            fixture_deviation("TS4_mean", 4.7),
            fixture_deviation("VS1_std", 4.6),
        ]),
        cycle_index=None,
    )
    machine_recs = [r for r in recs if r.category == "MACHINE_INSPECTION"]
    check("TEST7_one_rec_not_five", len(machine_recs) == 1, f"got {len(machine_recs)}")
    check("TEST7_multiple_evidence_items", len(machine_recs[0].evidence) >= 3,
          len(machine_recs[0].evidence))


# --- TEST 8: missing optional signal -> graceful degradation --------------
def test_8_missing_signal():
    # anomaly result missing entirely
    recs_a = generate_recommendations(health_result=fixture_health(3, 0.95, "close to total failure"))
    check("TEST8a_no_crash_missing_anomaly", len(recs_a) >= 1)

    # health result missing entirely
    recs_b = generate_recommendations(anomaly_result=fixture_anomaly("ANOMALY", 0.9, [fixture_deviation()]))
    check("TEST8b_no_crash_missing_health", len(recs_b) >= 1)

    # both missing, no energy either -> should degrade to CONTINUE_MONITORING, not crash
    recs_c = generate_recommendations()
    check("TEST8c_no_crash_nothing_given", len(recs_c) == 1 and recs_c[0].category == "CONTINUE_MONITORING",
          [r.category for r in recs_c])


def run_all():
    for fn in [test_1_normal_machine, test_2_high_anomaly, test_3_anomaly_plus_degraded,
               test_4_consolidated_mechanical, test_5_energy_only, test_6_combined,
               test_7_duplicate_suppression, test_8_missing_signal]:
        fn()

    print(f"PASSED: {len(PASSED)}")
    for name in PASSED:
        print(f"  ok  {name}")
    print(f"\nFAILED: {len(FAILED)}")
    for name in FAILED:
        print(f"  FAIL  {name}")

    return len(FAILED) == 0


if __name__ == "__main__":
    import sys
    success = run_all()
    sys.exit(0 if success else 1)
