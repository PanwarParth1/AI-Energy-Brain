"""Part 18: scenario-specific recommendations for the Machine What-If Simulator.

Unlike the older check()-style suites, every test here uses a real `assert`, so a
failure fails pytest. Nothing here hardcodes an expected recommendation for a
particular sensor: scenarios are run through the real Part 7/8 models and the
real Part 9 engine, and the tests assert consistency and behaviour between them.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import simulation_service
from ml.recommendation.engine import generate_recommendations

client = TestClient(app)

URL = "/api/machines/simulate"
MACHINE = "hydraulic_test_rig"
CYCLE = 1714  # real cycle: baseline = full efficiency / NORMAL

# Backward-compatible fields that existed before Part 18 and must still be present.
LEGACY_KEYS = {"simulation", "scenario_type", "machine_id", "baseline_cycle_index",
               "baseline", "simulated", "changes", "note"}
NO_ACTION_CATEGORIES = {"CONTINUE_MONITORING", "NO_ACTION"}


def simulate(perturbations, cycle=CYCLE):
    return client.post(URL, json={
        "machine_id": MACHINE,
        "baseline_cycle_index": cycle,
        "perturbations": perturbations,
    })


def pert(sensor, mode, value):
    return {"sensor": sensor, "mode": mode, "value": value}


# --- 1 / 5: normal scenario, genuinely no action -----------------------------

def test_unchanged_scenario_gets_no_action_recommendation():
    r = simulate([pert("VS1", "multiply", 1.0)])
    assert r.status_code == 200
    body = r.json()
    assert body["recommendations_error"] is None
    assert body["simulated"]["anomaly"]["status"] == "NORMAL"
    recs = body["recommendations"]
    assert recs, "engine must return a state (even 'no action') for a valid scenario"
    assert all(x["category"] in NO_ACTION_CATEGORIES for x in recs)


def test_changing_a_sensor_alone_does_not_force_a_warning():
    """A change that the models do not flag must not produce an escalated recommendation."""
    r = simulate([pert("PS1", "multiply", 1.05)])
    assert r.status_code == 200
    body = r.json()
    assert body["simulated"]["anomaly"]["status"] == "NORMAL"
    assert all(x["category"] in NO_ACTION_CATEGORIES for x in body["recommendations"])


# --- 2 / 3 / 4: abnormal health, anomaly warning, multiple sensors -----------

def test_anomaly_warning_scenario_gets_preventive_maintenance():
    r = simulate([pert("VS1", "multiply", 5.0)])
    body = r.json()
    assert r.status_code == 200
    assert body["simulated"]["anomaly"]["status"] == "WARNING"
    recs = body["recommendations"]
    assert [x["category"] for x in recs] == ["PREVENTIVE_MAINTENANCE"]
    # the action comes from the rule engine's sensor->area mapping for the real deviations
    assert recs[0]["action"].startswith("Inspect")


def test_abnormal_health_and_anomaly_scenario_gets_machine_inspection():
    r = simulate([pert("VS1", "multiply", 5.0), pert("TS2", "offset", 30.0)])
    body = r.json()
    assert r.status_code == 200
    assert body["simulated"]["anomaly"]["status"] == "ANOMALY"
    assert body["simulated"]["health"]["predicted_condition"] != body["baseline"]["health"]["predicted_condition"]
    recs = body["recommendations"]
    assert any(x["category"] == "MACHINE_INSPECTION" for x in recs)
    assert recs[0]["priority"] in {"MEDIUM", "HIGH", "CRITICAL"}


def test_multiple_changed_sensors_are_reflected_in_recommendation_context():
    body = simulate([pert("VS1", "multiply", 5.0), pert("TS2", "offset", 30.0)]).json()
    assert set(body["changes"]) == {"VS1", "TS2"}
    action = body["recommendations"][0]["action"]
    # vibration -> mechanical area, temperature -> cooling/thermal area (engine's own mapping)
    assert "mechanical" in action and "cooling" in action


# --- the recommendation really comes from the SIMULATED outputs + existing engine

def test_recommendations_match_existing_engine_applied_to_simulated_outputs():
    body = simulate([pert("VS1", "multiply", 5.0), pert("TS2", "offset", 30.0)]).json()
    expected = generate_recommendations(
        health_result=body["simulated"]["health"],
        anomaly_result=body["simulated"]["anomaly"],
        cycle_index=None,
    )
    got = body["recommendations"]
    assert [(e.category, e.priority, e.title, e.action) for e in expected] == \
           [(g["category"], g["priority"], g["title"], g["action"]) for g in got]


def test_recommendations_are_not_derived_from_baseline_alone():
    body = simulate([pert("VS1", "multiply", 5.0), pert("TS2", "offset", 30.0)]).json()
    from_baseline = generate_recommendations(
        health_result=body["baseline"]["health"],
        anomaly_result=body["baseline"]["anomaly"],
        cycle_index=None,
    )
    assert from_baseline[0].category in NO_ACTION_CATEGORIES      # baseline is healthy
    assert body["recommendations"][0]["category"] not in NO_ACTION_CATEGORIES  # scenario is not


def test_real_history_persistence_is_not_applied_to_hypothetical_scenario():
    body = simulate([pert("VS1", "multiply", 5.0)]).json()
    for rec in body["recommendations"]:
        assert rec["cycle_index"] is None
        assert all(e["signal"] != "anomaly_persistence" for e in rec["evidence"])
        assert any("what-if scenario" in lim for lim in rec["limitations"])


def test_response_is_honest_about_what_a_recommendation_is():
    note = simulate([pert("VS1", "multiply", 5.0)]).json()["recommendation_note"].lower()
    assert "not a diagnosis" in note
    assert "not a confirmed failure" in note
    assert "do not guarantee" in note


# --- re-running does not leak previous scenarios (backend is stateless) ------

def test_rerun_with_different_scenario_returns_fresh_recommendations():
    first = simulate([pert("VS1", "multiply", 5.0), pert("TS2", "offset", 30.0)]).json()
    second = simulate([pert("VS1", "multiply", 1.0)]).json()
    third = simulate([pert("VS1", "multiply", 5.0), pert("TS2", "offset", 30.0)]).json()
    assert first["recommendations"][0]["category"] == "MACHINE_INSPECTION"
    assert second["recommendations"][0]["category"] in NO_ACTION_CATEGORIES
    assert third["recommendations"][0]["category"] == first["recommendations"][0]["category"]


# --- backward compatibility ----------------------------------------------------

def test_legacy_response_fields_are_still_present():
    body = simulate([pert("VS1", "multiply", 5.0)]).json()
    assert LEGACY_KEYS <= set(body)
    assert body["simulation"] is True and body["scenario_type"] == "what_if"
    assert set(body["baseline"]) == {"health", "anomaly"}
    assert set(body["simulated"]) == {"health", "anomaly"}


def test_recommendation_items_use_the_existing_recommendation_schema():
    rec = simulate([pert("VS1", "multiply", 5.0)]).json()["recommendations"][0]
    expected = {"recommendation_id", "category", "priority", "title", "action", "reason",
                "evidence", "confidence", "confidence_basis", "machine_id", "cycle_index",
                "energy_datetime", "source_models", "limitations", "generated_at"}
    assert set(rec) == expected


# --- 6 / 7: invalid and malformed input ----------------------------------------

@pytest.mark.parametrize("perturbations, status", [
    ([pert("CE", "multiply", 2.0)], 400),              # virtual/derived channel
    ([pert("NOPE", "multiply", 2.0)], 400),            # unknown sensor
    ([pert("VS1", "multiply", 0.0)], 400),             # multiply by zero
    ([pert("VS1", "multiply", -2.0)], 400),            # negative multiplier
    ([pert("VS1", "multiply", 2.0), pert("VS1", "offset", 1.0)], 400),  # duplicate sensor
    ([pert("VS1", "scale", 2.0)], 422),                # invalid mode
    ([{"sensor": "VS1", "mode": "multiply", "value": "abc"}], 422),  # non-numeric value
    ([{"sensor": "VS1"}], 422),                        # incomplete perturbation
])
def test_invalid_perturbations_are_rejected_without_recommendations(perturbations, status):
    r = simulate(perturbations)
    assert r.status_code == status
    assert "recommendations" not in r.json()
    assert "error" in r.json()


def test_unknown_cycle_is_404():
    assert simulate([pert("VS1", "multiply", 2.0)], cycle=99999).status_code == 404


def test_unknown_machine_is_rejected():
    r = client.post(URL, json={"machine_id": "nope", "baseline_cycle_index": 1,
                               "perturbations": [pert("VS1", "multiply", 2.0)]})
    assert r.status_code in (400, 404)


def test_missing_required_fields_are_422():
    assert client.post(URL, json={"machine_id": MACHINE, "perturbations": []}).status_code == 422
    assert client.post(URL, json={}).status_code == 422
    assert client.post(URL, content="not json",
                       headers={"Content-Type": "application/json"}).status_code == 422


# --- 8: recommendation-engine failure ------------------------------------------

def test_engine_failure_keeps_simulation_and_reports_error(monkeypatch):
    def boom(**_kwargs):
        raise RuntimeError("engine exploded")
    monkeypatch.setattr(simulation_service, "generate_recommendations", boom)

    r = simulate([pert("VS1", "multiply", 5.0)])
    assert r.status_code == 200                       # the simulation itself is still valid
    body = r.json()
    assert body["simulated"]["anomaly"]["status"] == "WARNING"
    assert body["recommendations"] is None
    assert body["recommendations_error"] == "Unable to generate recommendations for this scenario."
    assert "engine exploded" not in str(body)         # internals are not leaked to the client


# --- the same endpoint still serves the existing consumers ---------------------

def test_existing_recommendation_endpoints_unaffected():
    assert client.get("/api/recommendations").status_code == 200
    r = client.post("/api/recommendations/generate", json={"cycle_index": CYCLE})
    assert r.status_code == 200 and r.json()["count"] >= 1
