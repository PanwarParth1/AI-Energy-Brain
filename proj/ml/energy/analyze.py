"""Development EDA / data-quality report for the Tetouan energy dataset.

This is a diagnostic script for the development team, not the final UI.
It reads the already-processed data produced by preprocess.py, prints a
plain-text report, and saves a handful of PNG plots for a quick visual
sanity check. No modelling happens here.

Run preprocess.py first if data/processed/tetouan_energy_processed.csv
does not exist yet - this script will tell you to if it's missing.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display available in this environment
import matplotlib.pyplot as plt
import pandas as pd

from ml.energy.preprocess import PROCESSED_DIR, PROCESSED_FILENAME, ZONE_COLUMNS

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports" / "energy_eda"


def load_processed() -> pd.DataFrame:
    path = PROCESSED_DIR / PROCESSED_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at '{path}'. Run "
            "`python ml/energy/preprocess.py` first."
        )
    df = pd.read_csv(path, parse_dates=["datetime"])
    return df


def summary_report(df: pd.DataFrame) -> dict:
    """Descriptive statistics computed from the actual processed data."""
    return {
        "n_rows": len(df),
        "date_range": [str(df["datetime"].min()), str(df["datetime"].max())],
        "missing_values_total": int(df.isna().sum().sum()),
        "zone_descriptive_stats": df[ZONE_COLUMNS + ["total_power_consumption"]]
        .describe()
        .to_dict(),
        "weekday_vs_weekend_mean_total": df.groupby("is_weekend")["total_power_consumption"]
        .mean()
        .to_dict(),
        "hourly_mean_total": df.groupby("hour")["total_power_consumption"].mean().to_dict(),
    }


def make_plots(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    # 1. Consumption over time (all three zones)
    fig, ax = plt.subplots(figsize=(11, 4))
    daily = df.set_index("datetime")[ZONE_COLUMNS].resample("D").mean()
    daily.plot(ax=ax)
    ax.set_title("Daily mean power consumption by zone (2017)")
    ax.set_ylabel("Power consumption")
    fig.tight_layout()
    p = out_dir / "01_consumption_over_time.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    # 2. Consumption distribution
    fig, ax = plt.subplots(figsize=(8, 4))
    df[ZONE_COLUMNS].plot(kind="hist", bins=60, alpha=0.6, ax=ax)
    ax.set_title("Distribution of power consumption by zone")
    fig.tight_layout()
    p = out_dir / "02_consumption_distribution.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    # 3. Zone comparison (boxplot)
    fig, ax = plt.subplots(figsize=(6, 5))
    df[ZONE_COLUMNS].plot(kind="box", ax=ax)
    ax.set_title("Zone comparison")
    fig.tight_layout()
    p = out_dir / "03_zone_comparison.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    # 4. Hourly consumption pattern
    fig, ax = plt.subplots(figsize=(8, 4))
    df.groupby("hour")["total_power_consumption"].mean().plot(kind="bar", ax=ax)
    ax.set_title("Mean total consumption by hour of day")
    ax.set_xlabel("Hour")
    fig.tight_layout()
    p = out_dir / "04_hourly_pattern.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    # 5. Weekday vs weekend
    fig, ax = plt.subplots(figsize=(5, 4))
    df.groupby("is_weekend")["total_power_consumption"].mean().rename(
        index={0: "Weekday", 1: "Weekend"}
    ).plot(kind="bar", ax=ax, color=["#4C72B0", "#DD8452"])
    ax.set_title("Weekday vs weekend mean total consumption")
    fig.tight_layout()
    p = out_dir / "05_weekday_vs_weekend.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    return saved


if __name__ == "__main__":
    df = load_processed()
    report = summary_report(df)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "summary.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    plot_paths = make_plots(df, REPORTS_DIR)

    print("=== Energy EDA Report ===")
    print(f"Rows analysed:  {report['n_rows']}")
    print(f"Date range:     {report['date_range'][0]} -> {report['date_range'][1]}")
    print(f"Missing values: {report['missing_values_total']}")
    print()
    print("Weekday vs weekend mean total consumption:")
    for k, v in report["weekday_vs_weekend_mean_total"].items():
        label = "Weekend" if k == 1 else "Weekday"
        print(f"  {label}: {v:.1f}")
    print()
    print(f"Summary JSON saved: {report_path}")
    print("Plots saved:")
    for p in plot_paths:
        print(f"  {p}")
