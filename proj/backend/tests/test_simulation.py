"""API-level tests for the What-If Simulation endpoints (Part 12).
Same plain-assertion pattern as backend/tests/test_api.py.
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


def test_simulatable_sensors():
    r = client.get("/api/machines/simulate/sensors")
    check("sim_sensors_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("sim_sensors_excludes_virtual", set(body["excluded_virtual_sensors"]) == {"CE", "CP", "SE"})
    check("sim_sensors_14_physical", len(body["sensors"]) == 14, len(body["sensors"]))


def test_valid_simulation():
    r = client.post("/api/machines/simulate", json={
        "machine_id": "hydraulic_test_rig",
        "baseline_cycle_index": 1714,
        "perturbations": [{"sensor": "VS1", "mode": "multiply", "value": 5.0}],
    })
    check("sim_valid_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("sim_has_baseline_and_simulated", "baseline" in body and "simulated" in body)
    check("sim_flag_true", body["simulation"] is True)
    check("sim_scenario_type", body["scenario_type"] == "what_if")
    check("sim_changes_recorded", "VS1" in body["changes"])


def test_baseline_matches_real_endpoints():
    """Cross-check against the REAL, non-simulated endpoints for the
    same cycle with EMPTY perturbations - must match exactly."""
    cycle = 301
    real_health = client.get(f"/api/machines/hydraulic_test_rig/health?cycle_index={cycle}").json()
    real_anomaly = client.get(f"/api/machines/hydraulic_test_rig/anomaly?cycle_index={cycle}").json()

    r = client.post("/api/machines/simulate", json={
        "machine_id": "hydraulic_test_rig", "baseline_cycle_index": cycle, "perturbations": [],
    })
    sim_baseline = r.json()["baseline"]

    check("sim_baseline_condition_matches_real_api",
          sim_baseline["health"]["predicted_condition"] == real_health["predicted_condition"])
    check("sim_baseline_anomaly_status_matches_real_api",
          sim_baseline["anomaly"]["status"] == real_anomaly["status"])
    check("sim_baseline_anomaly_score_matches_real_api",
          abs(sim_baseline["anomaly"]["anomaly_score"] - real_anomaly["anomaly_score"]) < 1e-9)


def test_invalid_sensor_400():
    r = client.post("/api/machines/simulate", json={
        "machine_id": "hydraulic_test_rig", "baseline_cycle_index": 301,
        "perturbations": [{"sensor": "CE", "mode": "offset", "value": 1.0}],
    })
    check("sim_invalid_sensor_400", r.status_code == 400, r.status_code)
    check("sim_invalid_sensor_error_shape", "error" in r.json())


def test_invalid_cycle_404():
    r = client.post("/api/machines/simulate", json={
        "machine_id": "hydraulic_test_rig", "baseline_cycle_index": 999999,
        "perturbations": [{"sensor": "PS1", "mode": "multiply", "value": 2.0}],
    })
    check("sim_invalid_cycle_404", r.status_code == 404, r.status_code)


def test_invalid_mode_422():
    r = client.post("/api/machines/simulate", json={
        "machine_id": "hydraulic_test_rig", "baseline_cycle_index": 301,
        "perturbations": [{"sensor": "PS1", "mode": "scale", "value": 2.0}],
    })
    check("sim_invalid_mode_422", r.status_code == 422, r.status_code)


def test_invalid_machine_id():
    r = client.post("/api/machines/simulate", json={
        "machine_id": "some_other_rig", "baseline_cycle_index": 301,
        "perturbations": [{"sensor": "PS1", "mode": "multiply", "value": 2.0}],
    })
    check("sim_invalid_machine_404", r.status_code == 404, r.status_code)


def test_raw_data_untouched_after_api_calls():
    """The API calls above perturbed PS1/VS1/CE heavily - confirm the
    cached in-memory sensor matrices are still pristine afterward."""
    from backend.app.services import machine_service
    sensors = machine_service._get_sensors()
    from ml.machine_health.preprocess import load_sensor
    fresh_ps1_row = load_sensor("PS1")[301]
    check("raw_data_untouched_after_simulation_calls",
          (sensors["PS1"][301] == fresh_ps1_row).all())


def run_all():
    for fn in [test_simulatable_sensors, test_valid_simulation, test_baseline_matches_real_endpoints,
               test_invalid_sensor_400, test_invalid_cycle_404, test_invalid_mode_422,
               test_invalid_machine_id, test_raw_data_untouched_after_api_calls]:
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
