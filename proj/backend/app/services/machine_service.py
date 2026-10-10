"""Machine service: thin orchestration over ml.machine_health.* - no
feature extraction, classification, or anomaly-scoring logic is
reimplemented here.

Caches raw sensors + full-dataset health/anomaly passes at first access
so repeated requests slice an in-memory DataFrame instead of reloading
~540MB of raw sensor files or rescoring 2205 cycles per request
(section 19/23).
"""

from __future__ import annotations

import threading

from backend.app.core.config import settings
from backend.app.core.errors import bad_request, not_found
from ml.machine_health.anomaly import detect_anomaly
from ml.machine_health.predict import predict_from_sensors
from ml.machine_health.preprocess import load_all_sensors, load_profile

_lock = threading.RLock()  # concurrent first requests must not each reload ~540MB of sensors
_cache: dict = {"sensors": None, "health_df": None, "n_cycles": None, "anomaly": {}, "scored_df": None}


def _get_sensors():
    with _lock:
        if _cache["sensors"] is None:
            _cache["sensors"] = load_all_sensors()
            _cache["n_cycles"] = len(load_profile())
        return _cache["sensors"]


def _get_health_df():
    """Full-dataset Part 7 predictions, computed once and cached."""
    with _lock:
        if _cache["health_df"] is None:
            sensors = _get_sensors()
            _cache["health_df"] = predict_from_sensors(sensors)
        return _cache["health_df"]


def get_scored_anomaly_df():
    """Full-dataset Part 8 scores, computed once and cached (the data is
    static, so the result never changes between requests)."""
    with _lock:
        if _cache["scored_df"] is None:
            from ml.machine_health.anomaly import score_cycles
            _cache["scored_df"] = score_cycles(_get_sensors())
        return _cache["scored_df"]


def _cached_detect_anomaly(cycle_index: int) -> dict:
    """Memoised Part 8 detect_anomaly() per cycle. Same function, same
    output - just not recomputed over all 2205 cycles on every request."""
    with _lock:
        store = _cache["anomaly"]
        if cycle_index not in store:
            store[cycle_index] = detect_anomaly(_get_sensors(), cycle_position=cycle_index, top_n=5)
        return store[cycle_index]


def warm_up() -> None:
    """Pre-fill the caches at server start so the first dashboard load
    during a demo is fast. Uses the same functions as the request path."""
    _get_health_df()
    get_scored_anomaly_df()
    _cached_detect_anomaly(_latest_cycle_index())


def _n_cycles() -> int:
    _get_sensors()
    return _cache["n_cycles"]


def validate_machine_id(machine_id: str) -> None:
    if machine_id != settings.MACHINE_ID:
        raise not_found(
            f"Machine '{machine_id}' was not found. This project represents a "
            f"single dataset/test rig: '{settings.MACHINE_ID}'."
        )


def validate_cycle_index(cycle_index: int) -> None:
    n = _n_cycles()
    if cycle_index < 0 or cycle_index >= n:
        raise not_found(f"Cycle {cycle_index} was not found. Valid range: 0-{n - 1}.")


def get_machine_list() -> dict:
    n = _n_cycles()
    return {
        "machines": [{
            "machine_id": settings.MACHINE_ID,
            "name": settings.MACHINE_NAME,
            "source": settings.HYDRAULIC_DATASET_NAME,
            "dataset_type": "controlled experimental test-rig data - not a live industrial facility",
            "n_cycles_available": n,
        }]
    }


def _latest_cycle_index() -> int:
    return _n_cycles() - 1


def get_health(machine_id: str, cycle_index: int | None) -> dict:
    validate_machine_id(machine_id)
    if cycle_index is None:
        cycle_index = _latest_cycle_index()
    validate_cycle_index(cycle_index)

    health_df = _get_health_df()
    row = health_df.iloc[cycle_index]
    from ml.machine_health.predict import load_model
    _, meta = load_model()

    return {
        "machine_id": machine_id,
        "cycle_index": cycle_index,
        "predicted_condition": int(row["predicted_condition"]),
        "predicted_condition_meaning": row["predicted_condition_meaning"],
        "confidence": float(row["confidence"]),
        "class_probabilities": row["class_probabilities"],
        "model_type": meta["model_type"],
        "dataset": settings.HYDRAULIC_DATASET_NAME,
        "limitations": [
            "This is a controlled experimental test-rig dataset, not naturally "
            "occurring factory failure data.",
            "Predicted condition is a statistical classification, not a "
            "confirmed physical diagnosis.",
        ],
    }


def get_anomaly(machine_id: str, cycle_index: int | None) -> dict:
    validate_machine_id(machine_id)
    if cycle_index is None:
        cycle_index = _latest_cycle_index()
    validate_cycle_index(cycle_index)

    result = _cached_detect_anomaly(cycle_index)

    return {
        "machine_id": machine_id,
        "cycle_index": cycle_index,
        "anomaly_score": result["anomaly_score"],
        "status": result["status"],
        "top_deviations": result["top_deviations"],
        "reference_condition": result["reference_condition"],
        "reference_condition_meaning": result["reference_condition_meaning"],
        "note": result["note"],
    }


def get_health_result_dict(cycle_index: int) -> dict:
    """Raw dict form used by recommendation_service - avoids re-running
    Part 7 by slicing the already-cached full-dataset predictions."""
    return _get_health_df().iloc[cycle_index].to_dict()


def get_anomaly_result_dict(cycle_index: int) -> dict:
    """Raw dict form used by recommendation_service - calls Part 8's
    own detect_anomaly() directly (not duplicated here)."""
    return _cached_detect_anomaly(cycle_index)
