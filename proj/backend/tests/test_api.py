"""Backend API tests (section 26) using FastAPI's TestClient against
REAL project data - no mocking of ML functions. Uses plain assertions
(no pytest dependency, matching ml/recommendation/tests.py's approach)
so this can run with just `python backend/tests/test_api.py`.
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


# 1. GET /api/health -------------------------------------------------------
def test_health():
    r = client.get("/api/health")
    check("health_status_200", r.status_code == 200, r.status_code)
    check("health_body", r.json() == {"status": "ok", "service": "AI Energy Brain API"}, r.json())


# 2. energy summary ----------------------------------------------------------
def test_energy_summary():
    r = client.get("/api/energy/summary")
    check("energy_summary_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("energy_summary_has_current_power", "current_power" in body)
    check("energy_summary_dataset_is_tetouan", "Tetouan" in body["dataset"], body.get("dataset"))
    check("energy_summary_no_fabricated_cost_field", "cost" not in body and "savings" not in body)


# 3. energy history ------------------------------------------------------------
def test_energy_history():
    r = client.get("/api/energy/history?limit=5")
    check("energy_history_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("energy_history_count_5", body["count"] == 5, body["count"])
    check("energy_history_chronological",
          all(body["records"][i]["timestamp"] <= body["records"][i + 1]["timestamp"]
              for i in range(len(body["records"]) - 1)))

    r_over = client.get(f"/api/energy/history?limit=99999")
    check("energy_history_limit_capped", r_over.status_code == 422, r_over.status_code)


# 4. energy forecast -------------------------------------------------------------
def test_energy_forecast():
    r = client.get("/api/energy/forecast?horizon=3")
    check("energy_forecast_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("energy_forecast_3_points", len(body["predictions"]) == 3, len(body["predictions"]))
    check("energy_forecast_has_limitations", len(body["limitations"]) > 0)

    r_bad = client.get("/api/energy/forecast?horizon=0")
    check("energy_forecast_rejects_zero_horizon", r_bad.status_code == 422, r_bad.status_code)


# 5. machine listing -----------------------------------------------------------
def test_machine_listing():
    r = client.get("/api/machines")
    check("machines_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("machines_exactly_one", len(body["machines"]) == 1, len(body["machines"]))
    check("machines_id_correct", body["machines"][0]["machine_id"] == "hydraulic_test_rig")


# 6. valid machine analysis -----------------------------------------------------
def test_machine_analyze_valid():
    r = client.post("/api/machines/analyze", json={"cycle_index": 301})
    check("analyze_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("analyze_has_health", "predicted_condition" in body["health"])
    check("analyze_has_anomaly", "status" in body["anomaly"])
    check("analyze_has_recommendations", isinstance(body["recommendations"], list))
    check("analyze_cycle_301_is_degraded", body["health"]["predicted_condition"] == 3,
          body["health"]["predicted_condition"])


# 7. invalid cycle index --------------------------------------------------------
def test_invalid_cycle_index():
    r = client.get("/api/machines/hydraulic_test_rig/health?cycle_index=99999")
    check("invalid_cycle_404", r.status_code == 404, r.status_code)
    check("invalid_cycle_error_shape", "error" in r.json() and "code" in r.json()["error"])

    r2 = client.post("/api/machines/analyze", json={"cycle_index": -1})
    check("negative_cycle_404", r2.status_code == 404, r2.status_code)


# 8. anomaly endpoint ------------------------------------------------------------
def test_anomaly_endpoint():
    r = client.get("/api/machines/hydraulic_test_rig/anomaly?cycle_index=301")
    check("anomaly_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("anomaly_has_status", body["status"] in ("NORMAL", "WARNING", "ANOMALY"), body["status"])
    check("anomaly_no_fabricated_failure_probability", "failure_probability" not in body)
    check("anomaly_cycle_301_is_anomaly", body["status"] == "ANOMALY", body["status"])


# 9. recommendation endpoint -----------------------------------------------------
def test_recommendation_endpoint():
    r = client.get("/api/recommendations")
    check("recommendations_get_200", r.status_code == 200, r.status_code)

    r2 = client.post("/api/recommendations/generate", json={"cycle_index": 301, "include_energy": False})
    check("recommendations_post_200", r2.status_code == 200, r2.status_code)
    body = r2.json()
    check("recommendations_have_priority", all("priority" in rec for rec in body["recommendations"]))
    check("recommendations_have_evidence", all("evidence" in rec for rec in body["recommendations"]))


# 10. dashboard summary -----------------------------------------------------------
def test_dashboard_summary():
    r = client.get("/api/dashboard/summary")
    check("dashboard_200", r.status_code == 200, r.status_code)
    body = r.json()
    check("dashboard_has_energy", "energy" in body)
    check("dashboard_has_machines", "machines" in body)
    check("dashboard_machine_total_is_2205",
          body["machines"]["status_counts"]["total"] == 2205,
          body["machines"]["status_counts"]["total"])
    check("dashboard_no_fabricated_fleet_size",
          body["machines"]["status_counts"]["total"] != 50)  # sanity: not a made-up fleet number


# 11. invalid machine ID -----------------------------------------------------------
def test_invalid_machine_id():
    r = client.get("/api/machines/factory_line_7/health")
    check("invalid_machine_404", r.status_code == 404, r.status_code)
    check("invalid_machine_error_shape", "error" in r.json())


# 12. CORS behaviour -----------------------------------------------------------------
def test_cors():
    r = client.options("/api/health", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
    })
    check("cors_allowed_origin_200", r.status_code == 200, r.status_code)
    check("cors_allowed_origin_header",
          r.headers.get("access-control-allow-origin") == "http://localhost:5173")

    r2 = client.options("/api/health", headers={
        "Origin": "http://evil.com", "Access-Control-Request-Method": "GET",
    })
    check("cors_rejects_unknown_origin", r2.headers.get("access-control-allow-origin") is None)


def run_all():
    for fn in [test_health, test_energy_summary, test_energy_history, test_energy_forecast,
               test_machine_listing, test_machine_analyze_valid, test_invalid_cycle_index,
               test_anomaly_endpoint, test_recommendation_endpoint, test_dashboard_summary,
               test_invalid_machine_id, test_cors]:
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
