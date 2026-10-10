"""Machine Health: cooler-condition classification training.

Pipeline:
  raw sensor files -> cycle-level features (features.py)
    -> filter to STABLE cycles only (documented decision, see below)
    -> block-chronological split (documented decision, see preprocess.py)
    -> baseline (majority class) + Logistic Regression + Random Forest,
       fit on TRAIN
    -> model selection on VALIDATION
    -> final, one-time evaluation of the selected model on TEST
    -> save model + metadata + reports

PRIMARY TARGET: cooler_condition
WHY: of the four available condition labels (cooler, valve, pump
leakage, accumulator pressure), cooler_condition is the only one with
close to perfectly balanced classes (732 / 732 / 741 cycles across its
3 classes - see reports/machine_health/class_distribution.json for all
four labels' actual counts). The other three labels are meaningfully
imbalanced (e.g. valve_condition's majority class alone is 1125 of
2205 cycles). A balanced target gives a cleaner MVP classification
result that is not dominated by a "predict the majority class" trick,
and cooler efficiency is a directly meaningful, commonly-monitored
machine-health quantity. Separate models for the other three labels,
or a multi-label formulation, are documented as future work rather
than forced into this MVP - see the README's "Limitations".

Run with: python ml/machine_health/train.py
"""

from __future__ import annotations

import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.machine_health.evaluate import (
    compute_classification_metrics,
    save_classification_report,
    save_confusion_matrix_plot,
    save_feature_importance_plot,
    save_json,
)
from ml.machine_health.features import build_feature_table, get_feature_columns
from ml.machine_health.preprocess import (
    LABEL_MEANINGS,
    PROFILE_COLUMNS,
    block_chronological_split,
    inspect_data,
    load_all_sensors,
    load_profile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports" / "machine_health"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "hydraulic"

MODEL_PATH = MODELS_DIR / "machine_health_classifier.joblib"
META_PATH = MODELS_DIR / "machine_health_classifier.meta.json"

TARGET_COL = "cooler_condition"
RANDOM_STATE = 42


def run_training() -> dict:
    # --- 1. Inspect + load -------------------------------------------
    inspection = inspect_data()
    profile = load_profile()
    sensors = load_all_sensors()
    features = build_feature_table(sensors)

    feature_cols = get_feature_columns()
    assert list(features.columns) == feature_cols, "Feature column order mismatch."

    # --- 2. Leakage audit: no profile column may enter X ---------------
    overlap = set(features.columns) & set(PROFILE_COLUMNS)
    if overlap:
        raise AssertionError(f"Target leakage: profile columns found in features: {overlap}")

    # --- 3. Filter to STABLE cycles only --------------------------------
    # DOCUMENTED DECISION: profile.txt's stable_flag marks 756 of 2205
    # cycles as "static conditions might not have been reached yet"
    # (i.e. the rig was still settling after a condition change).
    # Investigation (see README) found these unstable cycles cluster at
    # the START of each condition block (the first ~252 cycles right
    # after each setting change), not scattered randomly. Training on
    # them risks teaching the model transient settling-signatures
    # rather than genuine steady-state condition signatures, and they
    # are not representative of what a deployed system would see most
    # of the time. They are excluded from train/validation/test here;
    # the raw data itself is untouched.
    combined = pd.concat([profile.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    stable = combined[combined["stable_flag"] == 0].reset_index(drop=True)

    # --- 4. Block-chronological split (see preprocess.py for why) ------
    split_labels = block_chronological_split(stable, TARGET_COL)
    stable = stable.assign(split=split_labels.values)

    # Save the processed cycle-level feature table (all cycles' features
    # + profile labels + split assignment) for transparency/reuse -
    # mirrors the energy module's data/processed/ convention. This is a
    # DERIVED file; the raw sensor .txt files remain untouched.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.assign(
        is_stable=(combined["stable_flag"] == 0)
    ).to_csv(PROCESSED_DIR / "hydraulic_cycle_features.csv", index=False)
    stable.to_csv(PROCESSED_DIR / "hydraulic_stable_cycles_split.csv", index=False)

    train_df = stable[stable["split"] == "train"].reset_index(drop=True)
    val_df = stable[stable["split"] == "validation"].reset_index(drop=True)
    test_df = stable[stable["split"] == "test"].reset_index(drop=True)

    X_train, y_train = train_df[feature_cols], train_df[TARGET_COL]
    X_val, y_val = val_df[feature_cols], val_df[TARGET_COL]
    X_test, y_test = test_df[feature_cols], test_df[TARGET_COL]

    class_labels = sorted(stable[TARGET_COL].unique().tolist())
    class_names = [f"{v} ({LABEL_MEANINGS[TARGET_COL][v]})" for v in class_labels]

    # --- 5. Baseline: majority-class DummyClassifier --------------------
    baseline = DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)
    baseline.fit(X_train, y_train)
    baseline_val_metrics = compute_classification_metrics(y_val, baseline.predict(X_val), class_labels)
    baseline_test_metrics = compute_classification_metrics(y_test, baseline.predict(X_test), class_labels)

    # --- 6. Candidate models, fit on TRAIN only -------------------------
    # class_weight="balanced" is used on both: although cooler_condition
    # is close to balanced overall, the block-chronological split can
    # shift proportions slightly within a split - balancing costs
    # nothing when classes are already near-even and protects against
    # any residual imbalance.
    logreg = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
    ])
    logreg.fit(X_train, y_train)

    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    # --- 7. Model selection on VALIDATION only --------------------------
    logreg_val_metrics = compute_classification_metrics(y_val, logreg.predict(X_val), class_labels)
    rf_val_metrics = compute_classification_metrics(y_val, rf.predict(X_val), class_labels)

    candidates = {
        "logistic_regression": (logreg, logreg_val_metrics),
        "random_forest": (rf, rf_val_metrics),
    }
    selected_name = max(candidates, key=lambda name: candidates[name][1]["macro_f1"])
    selected_model, selected_val_metrics = candidates[selected_name]

    # --- 8. ONE-TIME test evaluation of the selected model only --------
    y_test_pred = selected_model.predict(X_test)
    selected_test_metrics = compute_classification_metrics(y_test, y_test_pred, class_labels)

    classification_report_dict = save_classification_report(
        y_test, y_test_pred, class_labels, class_names, REPORTS_DIR / "classification_report.json"
    )
    cm_path = save_confusion_matrix_plot(
        y_test, y_test_pred, class_labels, class_names, REPORTS_DIR / "confusion_matrix.png"
    )

    # --- 9. Feature importance ------------------------------------------
    if selected_name == "random_forest":
        importances = dict(
            sorted(zip(feature_cols, selected_model.feature_importances_.tolist()),
                   key=lambda kv: kv[1], reverse=True)
        )
    else:
        coefs = selected_model.named_steps["model"].coef_  # (n_classes, n_features)
        mean_abs_coef = np.abs(coefs).mean(axis=0)
        importances = dict(
            sorted(zip(feature_cols, mean_abs_coef.tolist()), key=lambda kv: kv[1], reverse=True)
        )
    fi_path = save_feature_importance_plot(importances, REPORTS_DIR / "feature_importance.png")

    # --- 10. Save model + metadata ---------------------------------------
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_model, MODEL_PATH)

    metadata = {
        "model_type": selected_name,
        "target": TARGET_COL,
        "target_meaning": LABEL_MEANINGS[TARGET_COL],
        "classes": class_labels,
        "class_names": class_names,
        "feature_columns": feature_cols,
        "n_features": len(feature_cols),
        "train_rows": len(X_train),
        "validation_rows": len(X_val),
        "test_rows": len(X_test),
        "stable_cycles_used": len(stable),
        "total_cycles_available": len(profile),
        "unstable_cycles_excluded": len(profile) - len(stable),
        "random_state": RANDOM_STATE,
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "validation_metrics": {
            "baseline_majority_class": baseline_val_metrics,
            "logistic_regression": logreg_val_metrics,
            "random_forest": rf_val_metrics,
        },
        "selected_model": selected_name,
        "selection_note": "Selected for this MVP based on validation macro F1.",
        "test_metrics": {
            "baseline_majority_class": baseline_test_metrics,
            "selected_model": selected_test_metrics,
        },
        "feature_importance": importances,
        "data_source": "real",
        "dataset": "UCI Condition Monitoring of Hydraulic Systems (ZeMA gGmbH)",
        "dataset_type": "controlled experimental test-rig data - NOT naturally occurring factory failures",
        "split_strategy": "block-chronological (per-class contiguous blocks split 70/15/15 in cycle order, not random)",
        "notes": (
            "A predicted class or an important feature reflects a learned "
            "statistical association in this experimental dataset. It is "
            "not a confirmed physical root cause and does not guarantee "
            "failure at any specific time."
        ),
    }
    save_json(metadata, META_PATH)

    comparison = {
        "validation": {
            "baseline_majority_class": baseline_val_metrics,
            "logistic_regression": logreg_val_metrics,
            "random_forest": rf_val_metrics,
        },
        "selected_model": selected_name,
        "test": {
            "baseline_majority_class": baseline_test_metrics,
            "selected_model": selected_test_metrics,
        },
    }
    save_json(comparison, REPORTS_DIR / "model_comparison.json")
    save_json(selected_test_metrics, REPORTS_DIR / "test_metrics.json")
    save_json(
        {
            "n_cycles_per_file": inspection.n_cycles_per_file,
            "n_columns_per_file": inspection.n_columns_per_file,
            "profile_label_counts": inspection.profile_label_counts,
        },
        REPORTS_DIR / "dataset_summary.json",
    )
    save_json(
        {col: profile[col].value_counts().sort_index().to_dict() for col in PROFILE_COLUMNS},
        REPORTS_DIR / "class_distribution.json",
    )

    return {
        "inspection": inspection,
        "class_labels": class_labels,
        "class_names": class_names,
        "feature_cols": feature_cols,
        "baseline_val": baseline_val_metrics,
        "baseline_test": baseline_test_metrics,
        "logreg_val": logreg_val_metrics,
        "rf_val": rf_val_metrics,
        "selected_name": selected_name,
        "selected_test": selected_test_metrics,
        "importances": importances,
        "cm_path": cm_path,
        "fi_path": fi_path,
        "model_path": MODEL_PATH,
        "meta_path": META_PATH,
        "stable_cycles_used": len(stable),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
    }


if __name__ == "__main__":
    result = run_training()

    print("=== Machine Health Classification: Part 7 ===\n")
    print(f"Primary target: {TARGET_COL}")
    print(f"Classes: {result['class_names']}\n")
    print(f"Stable cycles used: {result['stable_cycles_used']} of "
          f"{result['inspection'].n_cycles_per_file['profile']} total cycles "
          f"(unstable cycles excluded - see train.py docstring)")
    print(f"Train / Validation / Test rows: {result['train_rows']} / "
          f"{result['val_rows']} / {result['test_rows']}\n")
    print(f"Feature count: {len(result['feature_cols'])}\n")

    print("--- Validation metrics (model selection happens here) ---")
    print(f"{'Model':<22}{'Acc':>8}{'MacroP':>9}{'MacroR':>9}{'MacroF1':>9}{'WeightF1':>10}")
    for name, m in [
        ("Baseline (majority)", result["baseline_val"]),
        ("Logistic Regression", result["logreg_val"]),
        ("Random Forest", result["rf_val"]),
    ]:
        print(f"{name:<22}{m['accuracy']:>8.3f}{m['macro_precision']:>9.3f}"
              f"{m['macro_recall']:>9.3f}{m['macro_f1']:>9.3f}{m['weighted_f1']:>10.3f}")

    print(f"\nSelected model: {result['selected_name']} "
          "(selected for this MVP based on validation macro F1)\n")

    print("--- Final TEST metrics (selected model only, evaluated once) ---")
    t = result["selected_test"]
    b = result["baseline_test"]
    print(f"{'Model':<22}{'Acc':>8}{'MacroP':>9}{'MacroR':>9}{'MacroF1':>9}{'WeightF1':>10}")
    print(f"{'Baseline (majority)':<22}{b['accuracy']:>8.3f}{b['macro_precision']:>9.3f}"
          f"{b['macro_recall']:>9.3f}{b['macro_f1']:>9.3f}{b['weighted_f1']:>10.3f}")
    print(f"{result['selected_name']:<22}{t['accuracy']:>8.3f}{t['macro_precision']:>9.3f}"
          f"{t['macro_recall']:>9.3f}{t['macro_f1']:>9.3f}{t['weighted_f1']:>10.3f}")

    print("\n--- Top 10 most important features ---")
    for name, val in list(result["importances"].items())[:10]:
        print(f"  {name}: {val:.4f}")

    print(f"\nModel saved:    {result['model_path']}")
    print(f"Metadata saved: {result['meta_path']}")
    print(f"Confusion matrix: {result['cm_path']}")
    print(f"Feature importance plot: {result['fi_path']}")
