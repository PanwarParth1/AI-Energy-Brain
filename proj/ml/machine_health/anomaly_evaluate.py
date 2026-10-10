"""Plotting helpers for the Part 8 anomaly detection module.

Kept separate from evaluate.py (which handles Part 7's classification
plots) since these are a different kind of report - score
distributions and offline label-based analysis, not classification
metrics.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_score_distribution_plot(
    train_scores, val_scores, test_scores, non_ref_scores,
    warning_threshold: float, anomaly_threshold: float, out_path: Path,
) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    bins = np.linspace(
        min(train_scores.min(), non_ref_scores.min()),
        max(train_scores.max(), non_ref_scores.max()),
        60,
    )
    ax.hist(train_scores, bins=bins, alpha=0.5, label=f"Train reference (n={len(train_scores)})", density=True)
    ax.hist(test_scores, bins=bins, alpha=0.5, label=f"Test reference (n={len(test_scores)})", density=True)
    ax.hist(non_ref_scores, bins=bins, alpha=0.5, label=f"Non-reference (n={len(non_ref_scores)})", density=True)
    ax.axvline(warning_threshold, color="orange", linestyle="--", label=f"WARNING threshold ({warning_threshold:.2f})")
    ax.axvline(anomaly_threshold, color="red", linestyle="--", label=f"ANOMALY threshold ({anomaly_threshold:.2f})")
    ax.set_xlabel("Anomaly score (higher = more abnormal)")
    ax.set_ylabel("Density")
    ax.set_title("Anomaly score distribution: reference vs non-reference cycles")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def save_score_by_condition_plot(stable_with_scores: pd.DataFrame, reference_col: str, out_path: Path) -> Path:
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
    cols = ["cooler_condition", "valve_condition", "pump_leakage", "accumulator_pressure"]
    for ax, col in zip(axes, cols):
        groups = stable_with_scores.groupby(col)["anomaly_score"]
        labels = [str(k) for k in sorted(groups.groups.keys())]
        data = [groups.get_group(k).values for k in sorted(groups.groups.keys())]
        ax.boxplot(data, labels=labels, showfliers=False)
        ax.set_title(col + (" (reference)" if col == reference_col else ""))
        ax.set_xlabel("value")
        if ax is axes[0]:
            ax.set_ylabel("Anomaly score")
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Anomaly score by actual experimental condition (offline analysis)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def save_anomaly_timeline_plot(
    stable_with_scores: pd.DataFrame, warning_threshold: float, anomaly_threshold: float, out_path: Path
) -> Path:
    df = stable_with_scores.sort_values("cycle_index")
    colors = df["anomaly_status"].map({"NORMAL": "#4C72B0", "WARNING": "#DD8452", "ANOMALY": "#C44E52"})

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.scatter(df["cycle_index"], df["anomaly_score"], c=colors, s=6, alpha=0.7)
    ax.axhline(warning_threshold, color="orange", linestyle="--", linewidth=1)
    ax.axhline(anomaly_threshold, color="red", linestyle="--", linewidth=1)
    ax.set_xlabel("Cycle index (experiment order)")
    ax.set_ylabel("Anomaly score")
    ax.set_title("Anomaly status over cycle index (stable cycles; offline, uses labels only for colour)")

    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#4C72B0", label="NORMAL", markersize=6),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#DD8452", label="WARNING", markersize=6),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#C44E52", label="ANOMALY", markersize=6),
    ]
    ax.legend(handles=legend_elems, fontsize=8)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def save_sensor_comparison_plot(
    reference_features: pd.DataFrame,
    flagged_features,
    deviation_summary: dict,
    out_path: Path,
    top_n: int = 8,
) -> Path:
    """Compare reference vs ANOMALY-flagged cycles on the top-deviating
    features (mean value with std error bars). If no cycles were
    flagged ANOMALY, produce a note-only placeholder instead of a
    misleading empty plot.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if flagged_features is None or len(flagged_features) == 0 or not deviation_summary:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.axis("off")
        ax.text(0.5, 0.5, "No cycles reached ANOMALY status - nothing to compare.",
                ha="center", va="center")
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        return out_path

    top_features = list(deviation_summary.keys())[:top_n]
    ref_means = reference_features[top_features].mean()
    ref_stds = reference_features[top_features].std()
    flagged_means = flagged_features[top_features].mean()
    flagged_stds = flagged_features[top_features].std()

    x = np.arange(len(top_features))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, ref_means, width, yerr=ref_stds, label="Reference (normal)", color="#4C72B0", capsize=3)
    ax.bar(x + width / 2, flagged_means, width, yerr=flagged_stds, label="ANOMALY-flagged", color="#C44E52", capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(top_features, rotation=45, ha="right")
    ax.set_ylabel("Raw feature value")
    ax.set_title("Reference vs ANOMALY-flagged cycles: top deviating features")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
