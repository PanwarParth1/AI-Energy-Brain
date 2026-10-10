"""Shared forecasting-feature logic for the Energy module.

Both train.py (fitting) and predict.py (inference) import from here so
the exact same feature construction and feature ORDER is guaranteed at
train time and at prediction time. Diverging feature logic between the
two is the single most common way this kind of pipeline silently breaks.

This module builds features only - it never fits a model and never
computes evaluation metrics.
"""

from __future__ import annotations

import pandas as pd

TARGET_COL = "total_power_consumption"

# Zone columns are DELIBERATELY excluded from the feature set.
# total_power_consumption is defined as their exact sum (Part 5), so
# including them as model inputs would let the model "predict" the
# target by simply re-adding its own components - a textbook case of
# target leakage, not a real forecasting signal.
ZONE_COLUMNS = [
    "zone_1_power_consumption",
    "zone_2_power_consumption",
    "zone_3_power_consumption",
]

CALENDAR_FEATURES = [
    "hour",
    "minute",
    "day_of_week",
    "day_of_month",
    "month",
    "day_of_year",
    "is_weekend",
]

# --- target lags -----------------------------------------------------
# 1 step = 10 minutes (the dataset's fixed sampling interval).
# Chosen subset and what each represents in real time:
#   lag_1   -> 10 minutes ago   (immediate persistence / momentum)
#   lag_6   -> 1 hour ago       (short-term trend)
#   lag_36  -> 6 hours ago      (half-day trend)
#   lag_144 -> 24 hours ago     (same time yesterday - daily seasonality)
# Intermediate lags (2, 3, 12, 18, 72...) were evaluated and left out:
# they are highly correlated with their neighbours in a 10-minute series
# and add multicollinearity/noise without a distinct real-world meaning.
TARGET_LAGS = [1, 6, 36, 144]

# --- target rolling statistics ----------------------------------------
# Computed on target.shift(1) so the window ending at t-1 is used to
# describe the state BEFORE t - the current/target value at t is never
# part of its own rolling statistic. This is the leakage-prevention
# mechanism required by the spec.
#   rolling_mean_6   -> mean of the previous 1 hour
#   rolling_mean_144 -> mean of the previous 24 hours
#   rolling_std_6    -> volatility over the previous 1 hour
ROLLING_MEAN_WINDOWS = [6, 144]
ROLLING_STD_WINDOWS = [6]

# --- weather features --------------------------------------------------
# IMPORTANT DESIGN DECISION:
# The raw weather columns (temperature, humidity, ...) are measured AT
# the same timestamp as the target. Using them directly to predict the
# target at that same timestamp implicitly assumes a perfect weather
# forecast, which this project does not have and must not fake. Instead
# we use each weather variable's own lag_1 (the previous, ALREADY
# OBSERVED 10-minute reading) as a feature. This keeps the model
# strictly one-step-ahead-safe with zero assumptions about future
# weather, at the cost of losing a little same-instant predictive power.
WEATHER_COLUMNS = [
    "temperature",
    "humidity",
    "wind_speed",
    "general_diffuse_flows",
    "diffuse_flows",
]
WEATHER_LAG = 1


def create_forecasting_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag/rolling/weather-lag columns to a chronologically sorted,
    already-processed dataframe (the Part 5 output).

    Must be called on the FULL sorted dataset, before any train/val/test
    split - see ml/energy/train.py for why (validation/test rows need
    genuine historical context from the rows immediately before them).

    Returns a new dataframe; the input is not modified. Early rows will
    contain NaN in the new columns because they have no history to look
    back on - callers are responsible for dropping those (see train.py).
    """
    if not df["datetime"].is_monotonic_increasing:
        raise ValueError(
            "create_forecasting_features requires a chronologically sorted "
            "dataframe - sort by 'datetime' before calling this."
        )

    out = df.copy()
    target = out[TARGET_COL]

    for lag in TARGET_LAGS:
        out[f"lag_{lag}"] = target.shift(lag)

    for window in ROLLING_MEAN_WINDOWS:
        out[f"rolling_mean_{window}"] = target.shift(1).rolling(window).mean()

    for window in ROLLING_STD_WINDOWS:
        out[f"rolling_std_{window}"] = target.shift(1).rolling(window).std()

    for col in WEATHER_COLUMNS:
        out[f"{col}_lag_{WEATHER_LAG}"] = out[col].shift(WEATHER_LAG)

    return out


def get_feature_columns() -> list[str]:
    """The exact, ordered list of columns the model is trained and
    queried with. train.py and predict.py both call this instead of
    each hardcoding their own list, so the two can never drift apart.
    """
    lag_cols = [f"lag_{lag}" for lag in TARGET_LAGS]
    rolling_cols = [f"rolling_mean_{w}" for w in ROLLING_MEAN_WINDOWS] + [
        f"rolling_std_{w}" for w in ROLLING_STD_WINDOWS
    ]
    weather_lag_cols = [f"{col}_lag_{WEATHER_LAG}" for col in WEATHER_COLUMNS]
    return CALENDAR_FEATURES + lag_cols + rolling_cols + weather_lag_cols


def build_feature_target_matrix(
    featured_df: pd.DataFrame,
    drop_incomplete: bool = True,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Slice a featured dataframe into (X, y, datetime).

    If drop_incomplete is True, rows with any NaN in the feature columns
    (i.e. rows without enough history) are dropped. This should only
    ever remove rows from the very start of the TRAIN split - see the
    assertion in train.py that verifies validation/test have zero NaN.
    """
    feature_cols = get_feature_columns()
    working = featured_df[feature_cols + [TARGET_COL, "datetime"]].copy()

    if drop_incomplete:
        working = working.dropna(subset=feature_cols + [TARGET_COL])

    X = working[feature_cols].reset_index(drop=True)
    y = working[TARGET_COL].reset_index(drop=True)
    dt = working["datetime"].reset_index(drop=True)
    return X, y, dt
