"""Machine Sensor Anomaly Detection: inference (Part 8).

This is the only place that loads models/machine_anomaly_detector.joblib
for prediction. The FastAPI backend (Part 11) will import from here.

Goes straight from raw sensors -> features -> anomaly score, exactly
like train_anomaly.py does. Never touches Part 7's classifier, its
predictions, or its probabilities.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.machine_health.features import build_feature_table, get_feature_columns
from ml.machine_health.preprocess import SENSOR_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "machine_anomaly_detector.joblib"
META_PATH = PROJECT_ROOT / "models" / "machine_anomaly_detector.meta.json"

# Simple in-module cache (added in Part 10 for the FastAPI backend - see
# ml/energy/predict.py for the same pattern and its rationale).
_model_cache: dict = {"pipeline": None, "meta": None}


def clear_model_cache() -> None:
    _model_cache["pipeline"] = None
    _model_cache["meta"] = None


def load_model():
    """Load the trained pipeline (scaler + IsolationForest) and its
    metadata (feature list, thresholds, reference condition). Cached
    after the first call within this process.

    Raises FileNotFoundError if train_anomaly.py has not been run yet.
    """
    if _model_cache["pipeline"] is not None:
        return _model_cache["pipeline"], _model_cache["meta"]

    if not MODEL_PATH.exists() or not META_PATH.exists():
        raise FileNotFoundError(
            f"Trained anomaly model not found at '{MODEL_PATH}'. Run "
            "`python ml/machine_health/train_anomaly.py` first."
        )
    pipeline = joblib.load(MODEL_PATH)
    with open(META_PATH) as f:
        meta = json.load(f)
    _model_cache["pipeline"] = pipeline
    _model_cache["meta"] = meta
    return pipeline, meta


def _project_score(pipeline, X: pd.DataFrame) -> np.ndarray:
    """Same convention as train_anomaly.py: higher = more abnormal."""
    scaler = pipeline.named_steps["scaler"]
    iso = pipeline.named_steps["iso_forest"]
    X_scaled = scaler.transform(X)
    return -iso.score_samples(X_scaled)


def _status(score: np.ndarray, meta: dict) -> np.ndarray:
    warning = meta["warning_threshold"]
    anomaly = meta["anomaly_threshold"]
    status = np.full(score.shape, "NORMAL", dtype=object)
    status[score >= warning] = "WARNING"
    status[score >= anomaly] = "ANOMALY"
    return status


def score_cycles(sensors: dict[str, np.ndarray]) -> pd.DataFrame:
    """Score one or more cycles. `sensors` must be
    {sensor_name: (n_cycles, n_samples) array} for all 17 sensors -
    e.g. preprocess.load_all_sensors(), or equivalently-shaped new data.

    Returns one row per cycle: cycle_index, anomaly_score, status.
    """
    pipeline, meta = load_model()
    missing = set(SENSOR_NAMES) - set(sensors)
    if missing:
        raise ValueError(f"Missing sensor data for: {sorted(missing)}")

    features = build_feature_table(sensors)
    feature_cols = meta["feature_columns"]
    X = features[feature_cols]

    scores = _project_score(pipeline, X)
    status = _status(scores, meta)

    return pd.DataFrame({
        "cycle_index": np.arange(len(scores)),
        "anomaly_score": scores,
        "anomaly_status": status,
    })


def explain_deviations(sensors: dict[str, np.ndarray], cycle_position: int, top_n: int = 5) -> list[dict]:
    """For ONE cycle (by its position in `sensors`), return the top_n
    features with the largest |z-score| relative to the TRAINING
    REFERENCE population's mean/std (captured by the fitted StandardScaler).

    This answers "why was this cycle flagged?" at the feature level -
    it does NOT claim to identify a physical root cause. See
    detect_anomaly()'s docstring for the wording rule this follows.
    """
    pipeline, meta = load_model()
    scaler = pipeline.named_steps["scaler"]
    feature_cols = meta["feature_columns"]

    features = build_feature_table(sensors)
    X = features[feature_cols]
    X_scaled = scaler.transform(X)

    z = X_scaled[cycle_position]
    order = np.argsort(-np.abs(z))[:top_n]

    deviations = []
    for i in order:
        feature_name = feature_cols[i]
        z_score = float(z[i])
        direction = "above" if z_score > 0 else "below"
        deviations.append({
            "feature": feature_name,
            "z_score": z_score,
            "raw_value": float(X.iloc[cycle_position][feature_name]),
            "reference_mean": float(scaler.mean_[i]),
            "explanation": (
                f"{feature_name} is substantially {direction} the reference "
                f"distribution (z={z_score:+.2f})."
            ),
        })
    return deviations


def detect_anomaly(sensors: dict[str, np.ndarray], cycle_position: int = 0, top_n: int = 5) -> dict:
    """Single-cycle convenience wrapper combining score_cycles() and
    explain_deviations() for one cycle, in the shape the eventual
    dashboard/API will want.

    IMPORTANT WORDING: this function's output describes STATISTICAL
    DEVIATION from a learned reference population. It never states or
    implies a confirmed physical fault, a failure probability, or a
    time-to-failure - see train_anomaly.py's module docstring and the
    README's Part 8 section for why.
    """
    _, meta = load_model()
    scored = score_cycles(sensors)
    row = scored.iloc[cycle_position]
    deviations = explain_deviations(sensors, cycle_position, top_n)

    return {
        "anomaly_score": float(row["anomaly_score"]),
        "status": row["anomaly_status"],
        "top_deviations": deviations,
        "reference_condition": meta["reference_condition"],
        "reference_condition_meaning": meta["reference_condition_meaning"],
        "note": (
            "This score reflects statistical deviation from the learned "
            "reference sensor behaviour. It is not a failure probability "
            "and does not identify a confirmed physical cause."
        ),
    }


if __name__ == "__main__":
    # Smoke test: save -> reload -> predict, using real raw sensor data.
    from ml.machine_health.preprocess import load_all_sensors, load_profile

    sensors = load_all_sensors()
    profile = load_profile()

    scored = score_cycles(sensors)
    print(f"Loaded model and scored {len(scored)} cycles.")
    print(scored["anomaly_status"].value_counts())

    # Detailed explanation for one known-reference cycle and one
    # known-off-reference cycle, for a human-readable sanity check.
    ref_idx = profile[(profile["cooler_condition"] == 100) & (profile["stable_flag"] == 0)].index[0]
    off_idx = profile[(profile["cooler_condition"] == 3) & (profile["stable_flag"] == 0)].index[0]

    print(f"\n--- detect_anomaly() on a reference cycle (index {ref_idx}) ---")
    result = detect_anomaly(sensors, cycle_position=ref_idx, top_n=3)
    print(f"status={result['status']}  score={result['anomaly_score']:.4f}")
    for d in result["top_deviations"]:
        print(f"  {d['explanation']}")

    print(f"\n--- detect_anomaly() on an off-reference cycle (index {off_idx}, cooler_condition=3) ---")
    result = detect_anomaly(sensors, cycle_position=off_idx, top_n=3)
    print(f"status={result['status']}  score={result['anomaly_score']:.4f}")
    for d in result["top_deviations"]:
        print(f"  {d['explanation']}")
