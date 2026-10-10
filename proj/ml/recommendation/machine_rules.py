"""Machine-side recommendation rules (sections 8, 10, 16, 17, 18).

Consumes Part 7 (machine_health) and Part 8 (anomaly) outputs directly
- never retrains, never imports Part 7/8's training code, only their
predict.py / anomaly.py inference functions and metadata.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.machine_health.preprocess import SENSOR_METADATA
from ml.recommendation.config import (
    LOW_CONFIDENCE_THRESHOLD,
    MACHINE_PRIORITY_BANDS,
    PERSISTENCE_MODERATE_COUNT,
    PERSISTENCE_STRONG_COUNT,
    PERSISTENCE_WINDOW,
    load_anomaly_meta,
    load_machine_health_meta,
)
from ml.recommendation.schemas import CATEGORIES, Evidence, Recommendation, escalate, max_priority

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANOMALY_SCORES_CSV = PROJECT_ROOT / "data" / "processed" / "hydraulic" / "hydraulic_anomaly_scores.csv"

# Sensor-name prefix -> physical quantity, reused directly from Part 7's
# own documented sensor metadata (SENSOR_METADATA[name]["quantity"]) so
# inspection-area wording always matches the project's own terminology,
# never an invented category.
_QUANTITY_TO_INSPECTION_AREA = {
    "Pressure": "hydraulic pressure lines and pump",
    "Motor power": "motor and drive system",
    "Volume flow": "flow path, pump and valve operation",
    "Temperature": "cooling system and thermal load",
    "Vibration": "mechanical condition (bearings, alignment, mounting)",
    "Cooling efficiency (virtual)": "cooling system and coolant flow",
    "Cooling power (virtual)": "cooling system and coolant flow",
    "Efficiency factor": "overall system efficiency and calibration",
}


def health_severity_rank(predicted_condition: int, classes: list[int]) -> float:
    """0.0 = worst class in `classes`, 1.0 = best class. Purely positional
    - reads the actual class list from Part 7 metadata rather than
    hardcoding which numeric value means "healthy"."""
    ordered = sorted(classes)
    position = ordered.index(predicted_condition)
    return position / (len(ordered) - 1) if len(ordered) > 1 else 1.0


def anomaly_points(status: str) -> int:
    return {"NORMAL": 0, "WARNING": 1, "ANOMALY": 2}.get(status, 0)


def severity_points(rank: float) -> int:
    """rank 1.0 (healthiest) -> 0 points; rank 0.0 (worst) -> 2 points."""
    return round((1.0 - rank) * 2)


def get_persistence_count(cycle_index: int, window: int = PERSISTENCE_WINDOW) -> tuple[int, int]:
    """How many of the `window` most recent STABLE cycles at or before
    `cycle_index` (by actual cycle_index order, from Part 8's real saved
    scores) were WARNING or ANOMALY. Uses real historical data - this
    is only computed if that data is available; returns (0, 0) if not
    (graceful degradation, section 23 TEST 8).
    """
    if not ANOMALY_SCORES_CSV.exists():
        return 0, 0

    scores = pd.read_csv(ANOMALY_SCORES_CSV).sort_values("cycle_index")

    # Guard against a cycle_index outside the real dataset's actual range
    # (e.g. a synthetic/test sentinel value) silently matching via "<=" -
    # this bit us once during testing (see tests.py fixtures), so it is
    # now an explicit, documented check rather than a silent footgun.
    max_real_index = int(scores["cycle_index"].max())
    if cycle_index > max_real_index:
        return 0, 0

    recent = scores[scores["cycle_index"] <= cycle_index].tail(window)
    if recent.empty:
        return 0, 0

    flagged = (recent["anomaly_status"] != "NORMAL").sum()
    return int(flagged), int(len(recent))


def priority_from_points(total_points: int) -> str:
    for lo, hi, priority in MACHINE_PRIORITY_BANDS:
        if lo <= total_points <= hi:
            return priority
    return "LOW"  # defensive fallback, should not be reached given the table above


def inspection_areas_from_deviations(top_deviations: list[dict]) -> list[str]:
    """Map each deviating feature's sensor prefix to its documented
    physical quantity, then to a suggested inspection area, deduplicated
    and order-preserving (largest |z| first, since top_deviations is
    already sorted that way by Part 8)."""
    areas = []
    for dev in top_deviations:
        feature_name = dev["feature"]
        sensor_prefix = feature_name.split("_")[0]
        quantity = SENSOR_METADATA.get(sensor_prefix, {}).get("quantity")
        area = _QUANTITY_TO_INSPECTION_AREA.get(quantity)
        if area and area not in areas:
            areas.append(area)
    return areas


def build_machine_recommendation(
    health_result: dict,
    anomaly_result: dict,
    cycle_index: int | None = None,
    rec_index: int = 0,
) -> Recommendation | None:
    """Build ONE consolidated machine-side recommendation from a single
    cycle's Part 7 + Part 8 outputs, or None if nothing warrants one
    (Case E / TEST 1: normal condition -> no recommendation object at
    all, handled by the caller falling back to CONTINUE_MONITORING).

    health_result: one row's worth of Part 7 predict_from_sensors()
        output, as a dict - {"predicted_condition", "confidence",
        "predicted_condition_meaning", "class_probabilities", ...}.
        May be None if Part 7 output is unavailable (TEST 8).
    anomaly_result: Part 8 detect_anomaly() output dict - {"anomaly_score",
        "status", "top_deviations", "reference_condition", ...}. May be
        None if Part 8 output is unavailable (TEST 8).
    """
    health_meta = load_machine_health_meta()
    anomaly_meta = load_anomaly_meta()

    # --- graceful degradation (TEST 8: missing optional signal) --------
    status = anomaly_result["status"] if anomaly_result else "NORMAL"
    a_points = anomaly_points(status)

    if health_result is not None:
        rank = health_severity_rank(health_result["predicted_condition"], health_meta["classes"])
        s_points = severity_points(rank)
        confidence = health_result["confidence"]
        low_confidence = confidence < LOW_CONFIDENCE_THRESHOLD
    else:
        rank, s_points, confidence, low_confidence = 1.0, 0, None, False

    persistence_flagged, persistence_window_actual = (
        get_persistence_count(cycle_index) if cycle_index is not None else (0, 0)
    )
    if persistence_flagged >= PERSISTENCE_STRONG_COUNT:
        p_points = 2
    elif persistence_flagged >= PERSISTENCE_MODERATE_COUNT:
        p_points = 1
    else:
        p_points = 0

    total_points = a_points + s_points + p_points
    priority = priority_from_points(total_points)

    # Case B: uncertain classification caps CRITICAL down to HIGH -
    # "do not force a diagnosis" when the classifier itself is unsure.
    if priority == "CRITICAL" and low_confidence:
        priority = "HIGH"

    if priority == "NO_ACTION":
        return None  # Case E - nothing to report for this cycle

    # --- evidence -----------------------------------------------------
    evidence = []
    if anomaly_result:
        evidence.append(Evidence(
            signal="anomaly_score",
            observation=f"status={status}",
            severity={"NORMAL": "low", "WARNING": "moderate", "ANOMALY": "high"}[status],
            source=anomaly_meta["model_type"],
        ))
        for dev in anomaly_result.get("top_deviations", [])[:3]:
            evidence.append(Evidence(
                signal=dev["feature"],
                observation=f"z={dev['z_score']:+.2f} vs reference",
                severity="high" if abs(dev["z_score"]) >= 3 else "moderate",
                source=anomaly_meta["model_type"],
            ))
    if health_result is not None:
        evidence.append(Evidence(
            signal="cooler_condition",
            observation=health_result["predicted_condition_meaning"],
            severity="high" if rank <= 0.34 else ("moderate" if rank < 1.0 else "low"),
            source=health_meta["model_type"],
        ))
        if low_confidence:
            evidence.append(Evidence(
                signal="classification_confidence",
                observation=f"confidence={confidence:.2f} (below {LOW_CONFIDENCE_THRESHOLD} threshold)",
                severity="moderate",
                source=health_meta["model_type"],
            ))
    if persistence_flagged >= PERSISTENCE_MODERATE_COUNT:
        evidence.append(Evidence(
            signal="anomaly_persistence",
            observation=f"{persistence_flagged}/{persistence_window_actual} recent cycles flagged",
            severity="high" if persistence_flagged >= PERSISTENCE_STRONG_COUNT else "moderate",
            source="hydraulic_anomaly_scores_history",
        ))

    # --- category, title, action, reason -------------------------------
    areas = inspection_areas_from_deviations(anomaly_result.get("top_deviations", [])) if anomaly_result else []

    if status == "ANOMALY" and rank <= 0.34:
        category = "MACHINE_INSPECTION"
        title = "Degraded machine condition with abnormal sensor behaviour"
        reason = ("Known degraded machine condition is accompanied by abnormal sensor "
                   "behaviour relative to the learned reference population.")
    elif status == "ANOMALY" and (health_result is None or low_confidence or rank >= 1.0):
        category = "MACHINE_INSPECTION"
        title = "Abnormal sensor behaviour with uncertain condition classification"
        reason = ("Abnormal sensor behaviour was detected, but the machine-condition "
                   "classification does not clearly corroborate degradation "
                   "(low confidence or a healthy predicted class). Further diagnosis required.")
    elif status == "WARNING" or p_points > 0:
        category = "PREVENTIVE_MAINTENANCE"
        title = "Borderline sensor deviation detected"
        reason = "Sensor behaviour is at the edge of the reference range and/or has recurred across recent cycles."
    else:
        category = "MACHINE_INSPECTION"
        title = "Degraded machine condition"
        reason = f"Machine-condition classification indicates: {health_result['predicted_condition_meaning']}."

    if areas:
        action = "Inspect " + "; ".join(areas) + "."
    elif category == "PREVENTIVE_MAINTENANCE":
        action = "Schedule a preventive check during the next maintenance window."
    else:
        action = "Inspect machine condition and relevant sensor trends."

    # --- confidence (RULE confidence, not statistical probability) ------
    n_evidence = len(evidence)
    rule_confidence = min(1.0, 0.3 + 0.15 * n_evidence)
    confidence_basis = (
        "Rule confidence: proportion of maximum supporting evidence strength "
        f"present ({n_evidence} evidence item(s)). NOT a statistical probability "
        "that this recommendation is correct."
    )

    limitations = [
        "Predicted condition and anomaly status are statistical associations "
        "learned from a controlled experimental dataset, not confirmed physical diagnoses.",
        "This is decision support only and does not replace qualified maintenance inspection.",
    ]
    if health_result is None:
        limitations.append("Machine-health classification output was unavailable for this cycle.")
    if anomaly_result is None:
        limitations.append("Anomaly detection output was unavailable for this cycle.")

    import datetime as _dt
    return Recommendation(
        recommendation_id=f"REC-MACHINE-{cycle_index if cycle_index is not None else 'NA'}-{rec_index}",
        category=category,
        priority=priority,
        title=title,
        action=action,
        reason=reason,
        evidence=evidence,
        confidence=rule_confidence,
        confidence_basis=confidence_basis,
        machine_id="hydraulic_test_rig",
        cycle_index=cycle_index,
        energy_datetime=None,
        source_models=[m for m in [
            health_meta["model_type"] if health_result is not None else None,
            anomaly_meta["model_type"] if anomaly_result is not None else None,
        ] if m],
        limitations=limitations,
        generated_at=_dt.datetime.now().isoformat(timespec="seconds"),
    )
