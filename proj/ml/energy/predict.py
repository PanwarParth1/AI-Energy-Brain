"""Inference for the saved energy forecaster.

This is the ONLY place that loads models/energy_forecaster.joblib for
prediction. The FastAPI backend (Part 11) will import functions from
here rather than touching joblib or feature engineering directly.

Two prediction modes are provided:

1. predict_on_processed(df) - verified one-step-ahead prediction on
   REAL historical data (used by evaluate.py, and by the backend when
   showing "what the model would have forecast" for known history).

2. predict_future(history_df, n_steps) - genuine forecasting into
   timestamps with no real target yet. This REQUIRES an explicit,
   documented assumption (see the function docstring) because no
   dataset can supply real future weather or real future consumption
   to lag from. The assumption is stated in the return value, not
   hidden.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import json
import pandas as pd

from ml.energy.features import (
    TARGET_COL,
    WEATHER_COLUMNS,
    WEATHER_LAG,
    build_feature_target_matrix,
    create_forecasting_features,
    get_feature_columns,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "energy_forecaster.joblib"
META_PATH = PROJECT_ROOT / "models" / "energy_forecaster.meta.json"

# Simple in-module cache (added in Part 10 for the FastAPI backend, which
# would otherwise reload this joblib file from disk on every API request -
# same pattern applied to ml/machine_health/predict.py and anomaly.py).
_model_cache: dict = {"model": None, "meta": None}


def clear_model_cache() -> None:
    """Force the next load_model() call to re-read from disk (e.g. after
    retraining within the same process)."""
    _model_cache["model"] = None
    _model_cache["meta"] = None


def load_model():
    """Load the trained model and its metadata together (cached after
    the first call within this process).

    Raises FileNotFoundError with an actionable message if train.py
    (Part 6) has not been run yet - never falls back to a fake model.
    """
    if _model_cache["model"] is not None:
        return _model_cache["model"], _model_cache["meta"]

    if not MODEL_PATH.exists() or not META_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at '{MODEL_PATH}'. Run "
            "`python ml/energy/train.py` first."
        )
    model = joblib.load(MODEL_PATH)
    with open(META_PATH) as f:
        meta = json.load(f)

    if meta["feature_columns"] != get_feature_columns():
        # Guards against silently serving stale predictions if features.py
        # is changed after the model was trained but before retraining.
        raise ValueError(
            "Saved model's feature list does not match the current "
            "features.py definition. Retrain the model with "
            "`python ml/energy/train.py` before predicting."
        )
    _model_cache["model"] = model
    _model_cache["meta"] = meta
    return model, meta


def predict_on_processed(df: pd.DataFrame) -> pd.DataFrame:
    """One-step-ahead prediction on a dataframe shaped like the Part 5
    processed output (must be chronologically sorted and contain the
    same raw columns Part 5 produces).

    This is the "verified" prediction path: every row's target is
    already known in the input, which is what lets evaluate.py score
    the model honestly. It does not assume anything about the future.
    """
    model, meta = load_model()
    featured = create_forecasting_features(df.sort_values("datetime").reset_index(drop=True))
    X, y, dt = build_feature_target_matrix(featured, drop_incomplete=True)

    predictions = model.predict(X)
    return pd.DataFrame(
        {
            "datetime": dt,
            "actual": y,
            "predicted": predictions,
        }
    )


def predict_future(history_df: pd.DataFrame, n_steps: int = 6) -> pd.DataFrame:
    """Recursive multi-step forecast beyond the end of known data.

    LIMITATION (documented, not hidden):
    Genuine future weather observations do not exist. Each forecasted
    step's weather-lag features are held at the LAST OBSERVED weather
    reading (a persistence assumption on weather, not a real forecast).
    Target lag/rolling features, however, are updated recursively using
    the model's own previous predictions, which is the standard and
    honest way to extend a one-step model forward.

    Because errors compound with each recursive step, accuracy degrades
    the further out n_steps goes. This function is for short-horizon
    "next few readings" use (n_steps small, e.g. up to ~6 = 1 hour) -
    it is not a substitute for a dedicated multi-step model.
    """
    model, meta = load_model()
    history = history_df.sort_values("datetime").reset_index(drop=True).copy()

    if len(history) < 145:  # needs at least lag_144 of real history
        raise ValueError(
            "predict_future needs at least 145 rows (24h+10min) of real "
            "history to compute lag_144 for the first forecasted step."
        )

    last_known_weather = history.iloc[-1][WEATHER_COLUMNS]
    last_timestamp = history["datetime"].iloc[-1]

    forecasts = []
    working_history = history.copy()

    for step in range(1, n_steps + 1):
        next_timestamp = last_timestamp + pd.Timedelta(minutes=10 * step)

        # Calendar features for a future timestamp are exactly computable -
        # no assumption needed, the clock is deterministic. Computed here
        # directly (mirrors preprocess.create_time_features) because that
        # function also expects zone columns we don't have for a future row.
        next_row = {
            "datetime": next_timestamp,
            TARGET_COL: None,  # unknown - this is what we are predicting
            "hour": next_timestamp.hour,
            "minute": next_timestamp.minute,
            "day_of_week": next_timestamp.dayofweek,
            "day_of_month": next_timestamp.day,
            "month": next_timestamp.month,
            "day_of_year": next_timestamp.dayofyear,
            "is_weekend": int(next_timestamp.dayofweek in (5, 6)),
        }
        for col in WEATHER_COLUMNS:
            # Documented assumption: future weather = last observed weather.
            next_row[col] = last_known_weather[col]

        temp_df = pd.concat([working_history, pd.DataFrame([next_row])], ignore_index=True)
        featured = create_forecasting_features(temp_df)
        feature_cols = get_feature_columns()
        last_feature_row = featured.iloc[[-1]][feature_cols]

        if last_feature_row.isna().any(axis=None):
            raise ValueError(
                f"Insufficient history to build features for step {step}."
            )

        pred = float(model.predict(last_feature_row)[0])
        forecasts.append({"datetime": next_timestamp, "predicted": pred})

        # Feed the prediction back in as if it were observed, so the
        # NEXT step's lag/rolling features can be computed. This is the
        # recursive part of "recursive multi-step forecasting".
        next_row[TARGET_COL] = pred
        working_history = pd.concat([working_history, pd.DataFrame([next_row])], ignore_index=True)

    result = pd.DataFrame(forecasts)
    result.attrs["assumption"] = (
        "Future weather held constant at the last observed reading; "
        "target values beyond step 1 are recursive predictions, not "
        "real measurements."
    )
    return result


if __name__ == "__main__":
    # Small smoke test using the real test split, so this file can be
    # run standalone to sanity-check that a saved model loads correctly.
    from ml.energy.train import load_full_processed
    from ml.energy.preprocess import create_time_split

    full_df = load_full_processed()
    _, _, test_df = create_time_split(full_df)

    preds = predict_on_processed(load_full_processed())
    test_preds = preds[preds["datetime"] >= test_df["datetime"].min()]
    print(f"Loaded model and generated {len(test_preds)} test-set predictions.")
    print(test_preds.head())
