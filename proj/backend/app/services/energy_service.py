"""Energy service: thin orchestration over ml.energy.* - no forecasting
or feature logic is reimplemented here.

Caches the processed Tetouan CSV in memory (module-level singleton) so
repeated requests don't re-read a 52k-row file from disk every time
(section 23 - avoid unnecessary reloads).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.app.core.config import settings
from backend.app.core.errors import bad_request, server_error
from ml.energy.predict import load_model as load_energy_model, predict_future
from ml.energy.preprocess import PROCESSED_DIR, PROCESSED_FILENAME

_ENERGY_META_PATH = settings.MODELS_DIR / "energy_forecaster.meta.json"

_cache: dict = {"df": None, "meta": None}


def _get_processed_df() -> pd.DataFrame:
    if _cache["df"] is None:
        path = PROCESSED_DIR / PROCESSED_FILENAME
        if not path.exists():
            raise server_error(f"Processed energy dataset not found. Run ml/energy/preprocess.py first.")
        df = pd.read_csv(path, parse_dates=["datetime"]).sort_values("datetime").reset_index(drop=True)
        _cache["df"] = df
    return _cache["df"]


def _get_meta() -> dict:
    if _cache["meta"] is None:
        if not _ENERGY_META_PATH.exists():
            raise server_error("Energy forecaster metadata not found. Run ml/energy/train.py first.")
        with open(_ENERGY_META_PATH) as f:
            _cache["meta"] = json.load(f)
    return _cache["meta"]


def get_summary() -> dict:
    df = _get_processed_df()
    meta = _get_meta()

    latest = df.iloc[-1]
    recent_window = df.tail(144)  # 24h at 10-min steps, same window Part 9 uses
    recent_average = float(recent_window["total_power_consumption"].mean())

    forecast_df = predict_future(df, n_steps=1)
    forecast_row = forecast_df.iloc[0]

    return {
        "current_power": float(latest["total_power_consumption"]),
        "current_power_timestamp": str(latest["datetime"]),
        "recent_average_power": recent_average,
        "recent_average_window": "trailing 24 hours (144 x 10-minute steps)",
        "forecast_power": float(forecast_row["predicted"]),
        "forecast_timestamp": str(forecast_row["datetime"]),
        "forecast_horizon": "1 step (10 minutes)",
        "dataset": settings.ENERGY_DATASET_NAME,
        "unit": settings.ENERGY_UNIT,
        "limitations": [
            "This is a public city-level power-consumption dataset, not "
            "industrial machine energy data.",
            "The dataset's last real timestamp is "
            f"{df['datetime'].max()}; forecasts beyond it are model "
            "predictions, not live measurements.",
        ],
    }


def get_history(limit: int, start: str | None, end: str | None) -> dict:
    df = _get_processed_df()

    if start:
        try:
            start_ts = pd.Timestamp(start)
        except ValueError:
            raise bad_request(f"Invalid 'start' datetime: {start}")
        df = df[df["datetime"] >= start_ts]
    if end:
        try:
            end_ts = pd.Timestamp(end)
        except ValueError:
            raise bad_request(f"Invalid 'end' datetime: {end}")
        df = df[df["datetime"] <= end_ts]

    df = df.tail(limit)  # most recent `limit` records within the (optional) window

    records = [
        {
            "timestamp": str(row["datetime"]),
            "total_power_consumption": float(row["total_power_consumption"]),
            "zone_1_power_consumption": float(row["zone_1_power_consumption"]),
            "zone_2_power_consumption": float(row["zone_2_power_consumption"]),
            "zone_3_power_consumption": float(row["zone_3_power_consumption"]),
        }
        for _, row in df.iterrows()
    ]

    return {
        "dataset": settings.ENERGY_DATASET_NAME,
        "unit": settings.ENERGY_UNIT,
        "count": len(records),
        "records": records,
    }


def _percent_change(baseline: float, scenario: float) -> float:
    """Safe percent change; only ever called after baseline has been
    validated non-zero by the caller."""
    return (scenario - baseline) / baseline * 100.0


def run_energy_production_scenario(
    baseline_production: float,
    baseline_energy: float,
    scenario_production: float,
    scenario_energy: float,
) -> dict:
    """Part 14: energy-intensity what-if. Pure arithmetic over
    user-provided numbers - no ML model is called, trained, or modified
    here. The Tetouan dataset has no production data, so this cannot be
    (and does not pretend to be) a real historical comparison.

    energy_intensity = energy / production - a standard industrial
    concept (energy consumed per unit produced), computed here from
    manual scenario inputs, not from any trained model.
    """
    for name, value in [
        ("baseline_production", baseline_production),
        ("scenario_production", scenario_production),
    ]:
        if value is None or value <= 0:
            raise bad_request(f"{name} must be a positive number (got {value}). Production cannot be zero or negative.")
    for name, value in [
        ("baseline_energy", baseline_energy),
        ("scenario_energy", scenario_energy),
    ]:
        if value is None or value < 0:
            raise bad_request(f"{name} must be zero or a positive number (got {value}).")

    if baseline_energy == 0:
        # A zero baseline makes every percent-change comparison undefined
        # (division by zero), so reject it clearly instead of crashing.
        raise bad_request(
            "baseline_energy must be greater than zero - a zero baseline makes the "
            "energy-intensity comparison undefined."
        )

    baseline_intensity = baseline_energy / baseline_production
    scenario_intensity = scenario_energy / scenario_production

    production_change = _percent_change(baseline_production, scenario_production)
    energy_change = _percent_change(baseline_energy, scenario_energy)
    intensity_change = _percent_change(baseline_intensity, scenario_intensity)

    threshold = settings.ENERGY_INTENSITY_WARNING_THRESHOLD_PERCENT
    if intensity_change > threshold:
        status, classification = "WARNING", "ENERGY_EFFICIENCY_WARNING"
        explanation = (
            f"Energy consumption increased faster than production, so energy intensity rose by "
            f"{intensity_change:.1f}% (above the {threshold:.0f}% demo threshold). "
            "This scenario is worth reviewing for avoidable energy use."
        )
    elif intensity_change < -0.01:  # meaningfully negative, not just floating-point noise
        status, classification = "NORMAL", "PROPORTIONAL"
        explanation = (
            f"Energy intensity improved by {abs(intensity_change):.1f}% - production grew faster than "
            "energy consumption in this scenario."
        )
    else:
        status, classification = "NORMAL", "PROPORTIONAL"
        explanation = (
            "Energy consumption changed in proportion to production output - energy intensity is "
            "essentially unchanged."
        )

    return {
        "simulation": True,
        "baseline": {
            "production": baseline_production, "energy": baseline_energy, "energy_intensity": baseline_intensity,
        },
        "scenario": {
            "production": scenario_production, "energy": scenario_energy, "energy_intensity": scenario_intensity,
        },
        "changes": {
            "production_percent": production_change,
            "energy_percent": energy_change,
            "energy_intensity_percent": intensity_change,
        },
        "status": status,
        "classification": classification,
        "explanation": explanation,
        "threshold_percent": threshold,
        "threshold_note": (
            "PROTOTYPE/DEMO threshold for this hackathon project, not an industry standard and not "
            "derived from any dataset - the Tetouan dataset contains no production data."
        ),
        "note": (
            "This is a manual what-if scenario using user-provided production and energy figures. "
            "It does not use or modify the trained energy forecasting model, and does not represent "
            "real historical production data."
        ),
    }


def get_forecast(horizon: int) -> dict:
    if horizon < 1 or horizon > settings.ENERGY_FORECAST_MAX_HORIZON:
        raise bad_request(
            f"horizon must be between 1 and {settings.ENERGY_FORECAST_MAX_HORIZON} "
            f"(10-minute steps); got {horizon}."
        )

    df = _get_processed_df()
    meta = _get_meta()

    forecast_df = predict_future(df, n_steps=horizon)
    predictions = [
        {"timestamp": str(row["datetime"]), "value": float(row["predicted"])}
        for _, row in forecast_df.iterrows()
    ]

    limitations = [
        "One-step-ahead model extended recursively for horizon > 1: "
        "each step feeds the previous step's prediction back in as history.",
        "Future weather is held constant at the last observed reading "
        "(no real future weather exists in this dataset) - see ml/energy/predict.py.",
        "Accuracy degrades with distance from the last real observation; "
        "intended for short horizons (~1 hour / 6 steps).",
    ]

    return {
        "target": meta["target"],
        "unit": settings.ENERGY_UNIT,
        "horizon_steps": horizon,
        "step_size": "10 minutes",
        "predictions": predictions,
        "model": {
            "name": "energy_forecaster",
            "model_type": meta["model_type"],
            "dataset": settings.ENERGY_DATASET_NAME,
        },
        "limitations": limitations,
    }
