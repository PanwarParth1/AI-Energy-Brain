"""Inference for the saved machine-health (cooler condition) classifier.

This is the only place that loads models/machine_health_classifier.joblib
for prediction. The FastAPI backend (Part 11) will import from here.

Output is deliberately NOT a single invented "health score out of 100".
Per the Part 7 spec, this exposes:
  - predicted_condition (the raw label value, e.g. 3/20/100)
  - predicted_condition_meaning (the documented UCI meaning)
  - confidence (the model's own predicted probability for that class)
  - class_probabilities (full distribution across all classes)
A dashboard-facing normalized health score can be designed later with
its own defensible methodology - it is not fabricated here.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.machine_health.features import build_feature_table, get_feature_columns
from ml.machine_health.preprocess import LABEL_MEANINGS, SENSOR_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "machine_health_classifier.joblib"
META_PATH = PROJECT_ROOT / "models" / "machine_health_classifier.meta.json"

# Simple in-module cache (added in Part 10 for the FastAPI backend - see
# ml/energy/predict.py for the same pattern and its rationale).
_model_cache: dict = {"model": None, "meta": None}


def clear_model_cache() -> None:
    _model_cache["model"] = None
    _model_cache["meta"] = None


def load_model():
    """Load the trained model and its metadata together (cached after
    the first call within this process).

    Raises FileNotFoundError if train.py (Part 7) has not been run yet.
    """
    if _model_cache["model"] is not None:
        return _model_cache["model"], _model_cache["meta"]

    if not MODEL_PATH.exists() or not META_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at '{MODEL_PATH}'. Run "
            "`python ml/machine_health/train.py` first."
        )
    model = joblib.load(MODEL_PATH)
    with open(META_PATH) as f:
        meta = json.load(f)

    if meta["feature_columns"] != get_feature_columns():
        raise ValueError(
            "Saved model's feature list does not match the current "
            "features.py definition. Retrain with "
            "`python ml/machine_health/train.py` before predicting."
        )
    _model_cache["model"] = model
    _model_cache["meta"] = meta
    return model, meta


def predict_from_sensors(sensors: dict[str, np.ndarray]) -> pd.DataFrame:
    """Predict cooler condition for one or more cycles.

    `sensors` must be {sensor_name: (n_cycles, n_samples) array} for ALL
    17 sensors named in preprocess.SENSOR_NAMES - e.g. the output of
    preprocess.load_all_sensors(), or an equivalently-shaped dict built
    from new sensor readings.

    Returns one row per cycle with predicted_condition, its documented
    meaning, the model's confidence, and the full class-probability
    distribution.
    """
    model, meta = load_model()
    missing = set(SENSOR_NAMES) - set(sensors)
    if missing:
        raise ValueError(f"Missing sensor data for: {sorted(missing)}")

    features = build_feature_table(sensors)
    feature_cols = meta["feature_columns"]
    X = features[feature_cols]

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    classes = model.classes_

    meanings = LABEL_MEANINGS[meta["target"]]
    rows = []
    for i, pred in enumerate(predictions):
        class_probs = {str(c): float(probabilities[i][j]) for j, c in enumerate(classes)}
        confidence = float(probabilities[i][list(classes).index(pred)])
        rows.append({
            "cycle_index": i,
            "predicted_condition": int(pred),
            "predicted_condition_meaning": meanings.get(int(pred), "unknown"),
            "confidence": confidence,
            "class_probabilities": class_probs,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Smoke test: load real raw sensor data, predict, and spot-check a
    # few cycles against their known profile.txt labels. This is a
    # sanity check, not a formal evaluation (evaluate.py / train.py's
    # test-set metrics are the formal numbers).
    from ml.machine_health.preprocess import load_all_sensors, load_profile

    sensors = load_all_sensors()
    profile = load_profile()

    preds = predict_from_sensors(sensors)
    preds["actual_condition"] = profile["cooler_condition"].values
    preds["actual_stable_flag"] = profile["stable_flag"].values

    print(f"Loaded model and generated {len(preds)} predictions.")
    print("\nSample (5 stable cycles, one per condition where possible):")
    sample = preds[preds["actual_stable_flag"] == 0].groupby("actual_condition").head(2)
    print(sample[["cycle_index", "predicted_condition", "confidence", "actual_condition"]].to_string(index=False))

    match_rate = (preds.loc[preds["actual_stable_flag"] == 0, "predicted_condition"]
                  == preds.loc[preds["actual_stable_flag"] == 0, "actual_condition"]).mean()
    print(f"\nMatch rate against known labels, stable cycles "
          f"(includes cycles the model was trained on - not a test metric): {match_rate:.4f}")
