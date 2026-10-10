"""Metric calculation and evaluation-plot generation for the machine
health classifier.

Separated from train.py for the same reason as the energy module: one
metric implementation used both for model selection (on validation)
and for the final reported numbers (on test).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports" / "machine_health"


def compute_classification_metrics(y_true, y_pred, labels: list) -> dict:
    """Accuracy plus macro/weighted precision, recall and F1.

    Macro: each class contributes equally regardless of how many
    samples it has - this is what catches a model that only does well
    on the majority class.
    Weighted: each class contributes in proportion to its sample count
    - closer to "how well does this do on a random cycle from this data".
    Both are reported because they can tell different stories under
    class imbalance (see profile.txt label counts in the README).
    """
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
    }


def save_classification_report(y_true, y_pred, labels: list, label_names: list, out_path: Path) -> dict:
    report = classification_report(
        y_true, y_pred, labels=labels, target_names=[str(n) for n in label_names],
        output_dict=True, zero_division=0,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    return report


def save_confusion_matrix_plot(y_true, y_pred, labels: list, label_names: list, out_path: Path) -> Path:
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=label_names)
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    disp.plot(ax=ax, cmap="Blues", colorbar=True, values_format="d")
    ax.set_title("Machine Health: Cooler Condition\nConfusion Matrix (test set)", pad=14)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def save_feature_importance_plot(importances: dict, out_path: Path, top_n: int = 20) -> Path:
    items = list(importances.items())[:top_n]
    names = [k for k, _ in items][::-1]
    values = [v for _, v in items][::-1]

    fig, ax = plt.subplots(figsize=(7, 8))
    ax.barh(names, values, color="#4C72B0")
    ax.set_xlabel("Importance (predictive weight in the model - not proof of physical cause)")
    ax.set_title(f"Top {top_n} predictive features - cooler condition")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
