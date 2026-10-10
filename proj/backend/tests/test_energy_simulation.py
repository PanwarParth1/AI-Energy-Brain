"""Tests for the Part 14 Energy + Production What-If endpoint.
Same plain-assertion pattern as the project's other test files.
"""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

PASSED = []
FAILED = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        PASSED.append(name)
    else:
        FAILED.append(f"{name}: {detail}")


def sim(bp, be, sp, se):
    r = client.post("/api/energy/simulate", json={
        "baseline_production": bp, "baseline_energy": be,
        "scenario_production": sp, "scenario_energy": se,
    })
    return r


def test_1_identical_is_normal():
    r = sim(1000, 10000, 1000, 10000)
    d = r.json()
    check("T1_200", r.status_code == 200, r.status_code)
    check("T1_status_normal", d["status"] == "NORMAL", d["status"])
    check("T1_intensity_change_zero", d["changes"]["energy_intensity_percent"] == 0.0)


def test_2_proportional_increase():
    r = sim(1000, 10000, 1500, 15000)
    d = r.json()
    check("T2_200", r.status_code == 200)
    check("T2_production_change_50", d["changes"]["production_percent"] == 50.0)
    check("T2_energy_change_50", d["changes"]["energy_percent"] == 50.0)
    check("T2_intensity_unchanged", d["changes"]["energy_intensity_percent"] == 0.0)
    check("T2_baseline_intensity_10", d["baseline"]["energy_intensity"] == 10.0)
    check("T2_scenario_intensity_10", d["scenario"]["energy_intensity"] == 10.0)
    check("T2_classification_proportional", d["classification"] == "PROPORTIONAL")


def test_3_disproportionate_energy_warns():
    r = sim(1000, 10000, 1200, 15000)
    d = r.json()
    check("T3_200", r.status_code == 200)
    check("T3_production_change_20", d["changes"]["production_percent"] == 20.0)
    check("T3_energy_change_50", d["changes"]["energy_percent"] == 50.0)
    check("T3_baseline_intensity_10", d["baseline"]["energy_intensity"] == 10.0)
    check("T3_scenario_intensity_12_5", d["scenario"]["energy_intensity"] == 12.5)
    check("T3_status_warning", d["status"] == "WARNING", d["status"])
    check("T3_classification_warning", d["classification"] == "ENERGY_EFFICIENCY_WARNING")


def test_4_production_up_energy_down_no_false_warning():
    r = sim(1000, 10000, 1200, 9500)
    d = r.json()
    check("T4_200", r.status_code == 200)
    check("T4_intensity_improves", d["scenario"]["energy_intensity"] < d["baseline"]["energy_intensity"])
    check("T4_status_normal_not_warning", d["status"] == "NORMAL", d["status"])
    check("T4_classification_not_warning", d["classification"] != "ENERGY_EFFICIENCY_WARNING")


def test_5_invalid_inputs_rejected():
    for label, (bp, be, sp, se) in {
        "zero_baseline_production": (0, 10000, 1000, 10000),
        "negative_baseline_production": (-100, 10000, 1000, 10000),
        "zero_scenario_production": (1000, 10000, 0, 10000),
        "negative_baseline_energy": (1000, -500, 1000, 10000),
        "negative_scenario_energy": (1000, 10000, 1000, -500),
        "zero_baseline_energy": (1000, 0, 1200, 15000),  # Part 16: previously a 500 (ZeroDivisionError)
    }.items():
        r = sim(bp, be, sp, se)
        check(f"T5_{label}_rejected", r.status_code == 400, r.status_code)
        check(f"T5_{label}_error_shape", "error" in r.json())


def test_zero_scenario_energy_is_valid_not_a_crash():
    r = sim(1000, 10000, 1000, 0)
    check("zero_scenario_energy_200", r.status_code == 200, r.status_code)
    check("zero_scenario_energy_normal", r.json()["status"] == "NORMAL")


def test_threshold_is_in_response_not_hidden():
    r = sim(1000, 10000, 1200, 15000)
    d = r.json()
    check("threshold_percent_present", "threshold_percent" in d)
    check("threshold_note_present", "threshold_note" in d and "PROTOTYPE" in d["threshold_note"].upper())


def test_simulation_flag_and_note():
    r = sim(1000, 10000, 1000, 10000)
    d = r.json()
    check("simulation_flag_true", d["simulation"] is True)
    check("note_present", len(d["note"]) > 0)


def run_all():
    for fn in [test_1_identical_is_normal, test_2_proportional_increase, test_3_disproportionate_energy_warns,
               test_4_production_up_energy_down_no_false_warning, test_5_invalid_inputs_rejected,
               test_threshold_is_in_response_not_hidden, test_simulation_flag_and_note]:
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
