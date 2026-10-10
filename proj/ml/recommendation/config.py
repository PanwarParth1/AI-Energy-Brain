"""Configuration for the Recommendation Engine.

Two kinds of config live here:
  1. Thresholds READ from Part 7/8 model metadata (never copied by
     hand) - so if Part 8 is retrained with different thresholds,
     Part 9 picks up the change automatically instead of silently
     going stale.
  2. Energy-deviation thresholds, DERIVED once from the real Tetouan
     dataset's actual deviation-from-recent-pattern distribution
     (percentiles), not chosen arbitrarily - see build_energy_thresholds().

Both are written to reports/recommendations/recommendation_rules.json
by build_full_config() so the exact numbers used are inspectable.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports" / "recommendations"

MACHINE_HEALTH_META = MODELS_DIR / "machine_health_classifier.meta.json"
ANOMALY_META = MODELS_DIR / "machine_anomaly_detector.meta.json"
ENERGY_META = MODELS_DIR / "energy_forecaster.meta.json"

# Percentiles used to derive ENERGY thresholds from the real historical
# deviation distribution (mirrors Part 8's own WARNING/ANOMALY percentile
# methodology, applied here to energy deviation instead of anomaly score).
ENERGY_ELEVATED_PERCENTILE = 90.0
ENERGY_HIGH_PERCENTILE = 98.0

# Rolling window (in 10-minute steps) used as the "recent reference
# pattern" for energy deviation - 144 steps = 24 hours, matching the
# rolling_mean_144 feature already used in Part 6.
ENERGY_ROLLING_WINDOW = 144

# How many of the most recent stable cycles (by cycle_index) to look
# back over when checking anomaly persistence (section 18). Documented,
# not tuned to produce a desired result.
PERSISTENCE_WINDOW = 10
PERSISTENCE_MODERATE_COUNT = 2   # >= this many WARNING/ANOMALY in window -> moderate persistence
PERSISTENCE_STRONG_COUNT = 5     # >= this many -> strong persistence

# Machine-side point-based priority table (section 17). Documented,
# fixed, not fit to produce a desired demo outcome.
#   anomaly_points:   NORMAL=0, WARNING=1, ANOMALY=2
#   severity_points:  derived from health rank, 0 (healthiest) to 2 (worst)
#   persistence_points: 0 / 1 / 2, from PERSISTENCE_* counts above
#   total = anomaly_points + severity_points + persistence_points  (max 6)
MACHINE_PRIORITY_BANDS = [
    (0, 0, "NO_ACTION"),      # total == 0
    (1, 2, "LOW"),
    (3, 4, "MEDIUM"),
    (5, 5, "HIGH"),
    (6, 6, "CRITICAL"),
]
# If the health classifier's confidence is below this, CRITICAL is
# capped down to HIGH - "do not force a diagnosis" (Part 7/9 Case B).
LOW_CONFIDENCE_THRESHOLD = 0.6


def load_machine_health_meta() -> dict:
    with open(MACHINE_HEALTH_META) as f:
        return json.load(f)


def load_anomaly_meta() -> dict:
    with open(ANOMALY_META) as f:
        return json.load(f)


def load_energy_meta() -> dict:
    with open(ENERGY_META) as f:
        return json.load(f)


def build_energy_thresholds(processed_energy_csv: Path | None = None) -> dict:
    """Derive ENERGY_ELEVATED / ENERGY_HIGH deviation thresholds from the
    REAL historical Tetouan series - percentiles of
    (actual - trailing_144_mean) / trailing_144_mean, computed with a
    strictly backward-looking rolling window (shift(1) before rolling,
    same leakage-safety pattern as Part 6).
    """
    processed_energy_csv = processed_energy_csv or (
        PROJECT_ROOT / "data" / "processed" / "tetouan_energy_processed.csv"
    )
    df = pd.read_csv(processed_energy_csv, parse_dates=["datetime"]).sort_values("datetime")

    target = df["total_power_consumption"]
    trailing_mean = target.shift(1).rolling(ENERGY_ROLLING_WINDOW).mean()
    deviation_pct = ((target - trailing_mean) / trailing_mean * 100).dropna()

    elevated = float(np.percentile(deviation_pct, ENERGY_ELEVATED_PERCENTILE))
    high = float(np.percentile(deviation_pct, ENERGY_HIGH_PERCENTILE))

    return {
        "rolling_window_steps": ENERGY_ROLLING_WINDOW,
        "elevated_percentile": ENERGY_ELEVATED_PERCENTILE,
        "high_percentile": ENERGY_HIGH_PERCENTILE,
        "elevated_deviation_pct_threshold": elevated,
        "high_deviation_pct_threshold": high,
        "n_observations_used": int(len(deviation_pct)),
        "methodology": (
            "Percentiles of (actual - trailing 24h mean) / trailing 24h mean "
            "over the full real Tetouan history, computed with a strictly "
            "backward-looking rolling window (no future data)."
        ),
    }


def build_full_config(save: bool = True) -> dict:
    """Assemble and (optionally) save the complete, inspectable rule
    configuration - the actual numbers Part 9 uses, sourced from real
    model metadata and real historical data, not hand-copied constants.
    """
    health_meta = load_machine_health_meta()
    anomaly_meta = load_anomaly_meta()
    energy_thresholds = build_energy_thresholds()

    config = {
        "machine_health": {
            "target": health_meta["target"],
            "classes": health_meta["classes"],  # e.g. [3, 20, 100]
            "class_names": health_meta["class_names"],
            "model_type": health_meta["model_type"],
        },
        "machine_anomaly": {
            "warning_threshold": anomaly_meta["warning_threshold"],
            "anomaly_threshold": anomaly_meta["anomaly_threshold"],
            "reference_condition": anomaly_meta["reference_condition"],
            "model_type": anomaly_meta["model_type"],
        },
        "energy": energy_thresholds,
        "persistence": {
            "window": PERSISTENCE_WINDOW,
            "moderate_count": PERSISTENCE_MODERATE_COUNT,
            "strong_count": PERSISTENCE_STRONG_COUNT,
        },
        "machine_priority_bands": MACHINE_PRIORITY_BANDS,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
    }

    if save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(REPORTS_DIR / "recommendation_rules.json", "w") as f:
            json.dump(config, f, indent=2, default=str)

    return config


if __name__ == "__main__":
    cfg = build_full_config()
    print(json.dumps(cfg, indent=2, default=str))
