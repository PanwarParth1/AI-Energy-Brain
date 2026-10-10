"""Metric calculation and evaluation-plot generation for the energy
forecaster.

Kept separate from train.py so the same metric function is used both
during model selection (on validation) and for the final reported
numbers (on test) - one implementation, no risk of the two diverging.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports" / "energy_forecasting"


def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """MAE, RMSE and R2 - the standard regression trio.

    MAE  (Mean Absolute Error): average absolute size of the error, in
         the same units as the target (power consumption). Easy to
         interpret directly: "predictions are off by this much on average".
    RMSE (Root Mean Squared Error): like MAE but squares errors before
         averaging, so large errors are penalised more heavily than
         small ones. Same units as the target.
    R2   (coefficient of determination): the fraction of the target's
         variance the model explains, from -inf to 1.0. 1.0 is a perfect
         fit; 0.0 means "no better than always predicting the mean".
         This is NOT the same thing as classification accuracy and is
         never reported as a percentage-correct figure.
    """
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def make_evaluation_plots(
    datetime_index: pd.Series,
    y_true: pd.Series,
    y_pred: np.ndarray,
    out_dir: Path | None = None,
) -> list[Path]:
    """Actual-vs-predicted, residuals-over-time, and scatter plots on
    whichever set is passed in (this project uses TEST for the final
    reported plots, per Part 6's requirement).
    """
    out_dir = out_dir or REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    residuals = y_true.values - y_pred

    # 1. Actual vs predicted over time
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(datetime_index, y_true.values, label="Actual", linewidth=1)
    ax.plot(datetime_index, y_pred, label="Predicted", linewidth=1, alpha=0.8)
    ax.set_title("Actual vs predicted total power consumption (test set)")
    ax.set_xlabel("Datetime")
    ax.set_ylabel("Total power consumption (sum of Zone 1-3 readings)")
    ax.legend()
    fig.tight_layout()
    p = out_dir / "actual_vs_predicted.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    # 2. Residuals over time
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.plot(datetime_index, residuals, linewidth=0.8, color="#C44E52")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Prediction error (actual - predicted) over time")
    ax.set_xlabel("Datetime")
    ax.set_ylabel("Residual")
    fig.tight_layout()
    p = out_dir / "residuals_over_time.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    # 3. Actual vs predicted scatter
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(y_true.values, y_pred, s=4, alpha=0.3)
    lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    ax.plot(lims, lims, color="black", linewidth=1, linestyle="--", label="Perfect prediction")
    ax.set_xlabel("Actual total power consumption")
    ax.set_ylabel("Predicted total power consumption")
    ax.set_title("Actual vs predicted (test set)")
    ax.legend()
    fig.tight_layout()
    p = out_dir / "actual_vs_predicted_scatter.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    saved.append(p)

    return saved


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
