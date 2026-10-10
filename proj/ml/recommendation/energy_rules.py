"""Energy-side recommendation rules (section 9).

Uses Part 6's own predict.py output (actual/predicted) plus a
backward-looking rolling comparison against recent history - no new
model, no fabricated "energy anomaly" signal (Part 6 does not include
one; this module does not pretend otherwise).
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd

from ml.recommendation.config import build_energy_thresholds, load_energy_meta
from ml.recommendation.schemas import Evidence, Recommendation


def compute_energy_deviation(actual: float, trailing_mean: float) -> float:
    """Percent deviation of `actual` from the trailing reference mean.
    Positive = above recent pattern, negative = below."""
    if trailing_mean == 0:
        return 0.0
    return (actual - trailing_mean) / trailing_mean * 100.0


def classify_energy_deviation(deviation_pct: float, thresholds: dict) -> str:
    if deviation_pct >= thresholds["high_deviation_pct_threshold"]:
        return "highly_elevated"
    if deviation_pct >= thresholds["elevated_deviation_pct_threshold"]:
        return "elevated"
    return "typical"


def build_energy_recommendation(
    datetime_value,
    actual: float,
    trailing_mean: float,
    rec_index: int = 0,
) -> Recommendation | None:
    """One recommendation from a single real energy observation compared
    against its own trailing 24h reference mean. Returns None for
    "typical" behaviour (Case E equivalent for the energy track).
    """
    thresholds = build_energy_thresholds()
    energy_meta = load_energy_meta()

    deviation_pct = compute_energy_deviation(actual, trailing_mean)
    status = classify_energy_deviation(deviation_pct, thresholds)

    if status == "typical":
        return None

    evidence = [
        Evidence(
            signal="total_power_consumption",
            observation=f"{deviation_pct:+.1f}% vs trailing 24h mean",
            severity="high" if status == "highly_elevated" else "moderate",
            source=energy_meta["model_type"],
        )
    ]

    if status == "highly_elevated":
        priority = "HIGH"
        category = "ENERGY_OPTIMIZATION"
        title = "Energy demand substantially above recent pattern"
        action = "Review the current/upcoming high-demand period and operating schedule for avoidable load."
        reason = (f"Consumption is {deviation_pct:+.1f}% above the trailing 24-hour reference mean, "
                   f"above the {thresholds['high_deviation_pct_threshold']:.1f}% historical "
                   f"{thresholds['high_percentile']:.0f}th-percentile threshold.")
    else:
        priority = "MEDIUM"
        category = "ENERGY_MONITORING"
        title = "Elevated energy demand vs recent pattern"
        action = "Review upcoming high-load period and operating schedule."
        reason = (f"Consumption is {deviation_pct:+.1f}% above the trailing 24-hour reference mean, "
                   f"above the {thresholds['elevated_deviation_pct_threshold']:.1f}% historical "
                   f"{thresholds['elevated_percentile']:.0f}th-percentile threshold.")

    rule_confidence = 0.5 if status == "elevated" else 0.7
    confidence_basis = (
        "Rule confidence based on how far the observed deviation exceeds its "
        "historical percentile threshold. NOT a statistical probability that "
        "this recommendation is correct."
    )

    limitations = [
        "This dataset is public city-level power consumption, not industrial "
        "machine energy data - this recommendation concerns aggregate demand, "
        "not a specific machine's efficiency.",
        "Elevated demand is a pattern deviation, not confirmed avoidable waste.",
    ]

    return Recommendation(
        recommendation_id=f"REC-ENERGY-{rec_index}",
        category=category,
        priority=priority,
        title=title,
        action=action,
        reason=reason,
        evidence=evidence,
        confidence=rule_confidence,
        confidence_basis=confidence_basis,
        machine_id="tetouan_city_energy_zone_aggregate",
        cycle_index=None,
        energy_datetime=str(datetime_value),
        source_models=[energy_meta["model_type"]],
        limitations=limitations,
        generated_at=_dt.datetime.now().isoformat(timespec="seconds"),
    )


def get_recent_energy_observation(processed_csv, at_datetime=None) -> dict:
    """Pull one real observation (its own value + trailing 24h mean)
    from the real processed Tetouan data - either the latest available
    row, or the row at/just after `at_datetime` if given.
    """
    df = pd.read_csv(processed_csv, parse_dates=["datetime"]).sort_values("datetime").reset_index(drop=True)
    df["trailing_mean_144"] = df["total_power_consumption"].shift(1).rolling(144).mean()
    df = df.dropna(subset=["trailing_mean_144"])

    if at_datetime is not None:
        row = df[df["datetime"] >= pd.Timestamp(at_datetime)].iloc[0]
    else:
        row = df.iloc[-1]

    return {
        "datetime": row["datetime"],
        "actual": float(row["total_power_consumption"]),
        "trailing_mean": float(row["trailing_mean_144"]),
    }
