"""Machine Sensor Anomaly Detection: unsupervised training (Part 8).

This is a SEPARATE task from Part 7's classifier:
  Part 7 asks: "which known cooler condition does this cycle match?"
  Part 8 asks: "does this cycle's sensor behaviour look unusual
                compared with a learned REFERENCE population?"

Part 8 does not use Part 7's model, predictions, or probabilities as
input anywhere - it goes straight from raw sensors to features to
IsolationForest, exactly like Part 7 does independently for its own
target. The two modules share only feature-extraction code
(features.py) and raw data.

REFERENCE / NORMAL POPULATION: stable cycles with cooler_condition == 100
WHY: description.txt documents cooler_condition=100 as "full efficiency"
- the only one of the four available condition labels with an
unambiguous, documented "optimal" value that also has a usable amount
of data behind it. A stricter reference (all four conditions
simultaneously at their documented optimum) was checked and found to
cover only 21 cycles total (10 stable) - far too few to train and
split into train/validation/test. Restricting to cooler_condition==100
alone (489 stable cycles) is the most defensible reference population
this dataset actually supports.

IMPORTANT SCOPE LIMITATION (documented, not hidden): valve_condition,
pump_leakage and accumulator_pressure are NOT controlled within this
reference population - they vary freely across the 489 reference
cycles, exactly as they do in the full dataset. This detector therefore
learns "what full-cooler-efficiency sensor behaviour looks like across
the range of other conditions this rig was run at", not "what a
universally fault-free machine looks like". See README Part 8 section
and the Limitations in the final report for what this means in
practice.

Run with: python ml/machine_health/train_anomaly.py
"""

from __future__ import annotations

import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.machine_health.anomaly_evaluate import (
    save_anomaly_timeline_plot,
    save_score_by_condition_plot,
    save_score_distribution_plot,
    save_sensor_comparison_plot,
)
from ml.machine_health.evaluate import save_json
from ml.machine_health.features import build_feature_table, get_feature_columns
from ml.machine_health.preprocess import (
    LABEL_MEANINGS,
    PROFILE_COLUMNS,
    grouped_chronological_split,
    load_all_sensors,
    load_profile,
    simple_chronological_split,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports" / "machine_anomaly"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "hydraulic"

MODEL_PATH = MODELS_DIR / "machine_anomaly_detector.joblib"
META_PATH = MODELS_DIR / "machine_anomaly_detector.meta.json"

REFERENCE_COL = "cooler_condition"
REFERENCE_VALUE = 100
RANDOM_STATE = 42

# Thresholds are DERIVED from the validation reference score
# distribution below (percentiles), not hardcoded - these constants
# only name which percentiles to use, and are documented here for
# transparency.
WARNING_PERCENTILE = 95.0
ANOMALY_PERCENTILE = 99.0


def project_anomaly_score(iso_forest: IsolationForest, X_scaled: np.ndarray) -> np.ndarray:
    """Project-level anomaly score: HIGHER = MORE ABNORMAL.

    sklearn's IsolationForest.score_samples() returns the OPPOSITE
    convention (higher = more normal, i.e. less isolated). We negate
    it here, once, in this single function, so every caller in the
    project uses the same, clearly-documented direction. This is not
    a probability of anything - it is a relative isolation measure.
    """
    return -iso_forest.score_samples(X_scaled)


def status_from_score(score: np.ndarray, warning_threshold: float, anomaly_threshold: float) -> np.ndarray:
    status = np.full(score.shape, "NORMAL", dtype=object)
    status[score >= warning_threshold] = "WARNING"
    status[score >= anomaly_threshold] = "ANOMALY"
    return status


def run_training() -> dict:
    # --- 1. Load + build features (reused from Part 7, not duplicated) -
    profile = load_profile()
    sensors = load_all_sensors()
    features = build_feature_table(sensors)
    feature_cols = get_feature_columns()

    # --- 2. Leakage audit: no profile column may enter X ----------------
    overlap = set(features.columns) & set(PROFILE_COLUMNS)
    if overlap:
        raise AssertionError(f"Target leakage: profile columns found in features: {overlap}")

    combined = pd.concat([profile.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    stable = combined[combined["stable_flag"] == 0].reset_index(drop=True)

    # --- 3. Define reference population ----------------------------------
    is_reference = stable[REFERENCE_COL] == REFERENCE_VALUE
    reference = stable[is_reference].reset_index(drop=True)
    non_reference = stable[~is_reference].reset_index(drop=True)  # offline evaluation only

    # Contiguity check (documents WHY a simple chronological split, not
    # block-per-class like Part 7, is appropriate here - the reference
    # is already a single condition value, not multiple blocks).
    idx_sorted = np.sort(reference["cycle_index"].values)
    gaps = np.diff(idx_sorted)
    n_gaps = int((gaps > 1).sum())

    # --- 4. Split the REFERENCE population -------------------------------
    # A naive chronological split (first 70%/next 15%/last 15% by cycle
    # order) was tried first and found to be badly confounded: within
    # this reference population, accumulator_pressure (an unrelated
    # fault dimension that also varies here - see module docstring)
    # changes roughly halfway through, so a plain positional split put
    # ALL accumulator_pressure=90 cycles in test and NONE in train,
    # making test look artificially anomalous. Fixed by splitting
    # WITHIN each contiguous (valve_condition, pump_leakage,
    # accumulator_pressure) sub-block instead, so every combination
    # contributes proportionally to train/validation/test - see
    # preprocess.grouped_chronological_split() for the full explanation.
    split_labels = grouped_chronological_split(
        reference, group_cols=["valve_condition", "pump_leakage", "accumulator_pressure"]
    )
    reference = reference.assign(split=split_labels.values)

    train_df = reference[reference["split"] == "train"].reset_index(drop=True)
    val_df = reference[reference["split"] == "validation"].reset_index(drop=True)
    test_df = reference[reference["split"] == "test"].reset_index(drop=True)

    X_train = train_df[feature_cols]
    X_val = val_df[feature_cols]
    X_test = test_df[feature_cols]
    X_non_reference = non_reference[feature_cols]

    # --- 5. Feature sanity check: drop truly zero-variance features -----
    # (would be uninformative and would break z-score explanations via
    # divide-by-zero). Checked on TRAIN reference only.
    train_std = X_train.std(axis=0)
    zero_var_cols = train_std[train_std == 0].index.tolist()
    if zero_var_cols:
        feature_cols = [c for c in feature_cols if c not in zero_var_cols]
        X_train = X_train[feature_cols]
        X_val = X_val[feature_cols]
        X_test = X_test[feature_cols]
        X_non_reference = X_non_reference[feature_cols]

    # --- 6. Preprocessing + model, fit ONLY on TRAIN reference ----------
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    X_non_ref_scaled = scaler.transform(X_non_reference)

    iso_forest = IsolationForest(
        n_estimators=200,
        max_samples="auto",
        contamination="auto",  # not used for our thresholds - see below
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    iso_forest.fit(X_train_scaled)

    pipeline = Pipeline([("scaler", scaler), ("iso_forest", iso_forest)])

    # --- 7. Anomaly scores (project convention: higher = more abnormal) -
    train_scores = project_anomaly_score(iso_forest, X_train_scaled)
    val_scores = project_anomaly_score(iso_forest, X_val_scaled)
    test_scores = project_anomaly_score(iso_forest, X_test_scaled)
    non_ref_scores = project_anomaly_score(iso_forest, X_non_ref_scaled)

    # --- 8. Threshold methodology: percentiles of VALIDATION REFERENCE --
    # scores. Validation is reference (known-normal) data the model
    # did not train on, so its score distribution is a fair estimate of
    # "how the model scores normal-but-unseen cycles" - the natural
    # basis for a WARNING/ANOMALY cutoff. Test is touched only after
    # these thresholds are locked.
    warning_threshold = float(np.percentile(val_scores, WARNING_PERCENTILE))
    anomaly_threshold = float(np.percentile(val_scores, ANOMALY_PERCENTILE))

    train_status = status_from_score(train_scores, warning_threshold, anomaly_threshold)
    val_status = status_from_score(val_scores, warning_threshold, anomaly_threshold)
    test_status = status_from_score(test_scores, warning_threshold, anomaly_threshold)
    non_ref_status = status_from_score(non_ref_scores, warning_threshold, anomaly_threshold)

    # --- 9. OFFLINE evaluation using labels (analysis only, never train) -
    # Ground truth for this evaluation: TEST reference cycles = known
    # NORMAL (0); non-reference stable cycles (any condition other than
    # cooler_condition==100) = known ABNORMAL (1), because they fall
    # outside the defined reference condition. Predicted abnormal =
    # status != NORMAL (i.e. WARNING or ANOMALY flagged).
    eval_y_true = np.concatenate([np.zeros(len(test_status)), np.ones(len(non_ref_status))])
    eval_pred_flagged = np.concatenate([
        (test_status != "NORMAL").astype(int),
        (non_ref_status != "NORMAL").astype(int),
    ])

    tp = int(((eval_y_true == 1) & (eval_pred_flagged == 1)).sum())
    fp = int(((eval_y_true == 0) & (eval_pred_flagged == 1)).sum())
    fn = int(((eval_y_true == 1) & (eval_pred_flagged == 0)).sum())
    tn = int(((eval_y_true == 0) & (eval_pred_flagged == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn)

    anomaly_metrics = {
        "note": (
            "OFFLINE evaluation only. Ground truth: test reference cycles "
            "(cooler_condition==100) = NORMAL; non-reference stable cycles "
            "(any other cooler_condition) = ABNORMAL. Labels were used only "
            "here, never during IsolationForest training or threshold selection."
        ),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "n_test_reference_cycles": len(test_status),
        "n_non_reference_cycles": len(non_ref_status),
    }

    # --- 10. Score by actual experimental condition (offline analysis) --
    all_stable_scaled = scaler.transform(stable[feature_cols])
    all_stable_scores = project_anomaly_score(iso_forest, all_stable_scaled)
    all_stable_status = status_from_score(all_stable_scores, warning_threshold, anomaly_threshold)
    stable_with_scores = stable.assign(
        anomaly_score=all_stable_scores,
        anomaly_status=all_stable_status,
    )

    score_by_condition = {}
    for col in PROFILE_COLUMNS:
        if col == "stable_flag":
            continue
        score_by_condition[col] = (
            stable_with_scores.groupby(col)["anomaly_score"]
            .agg(["mean", "median", "std", "count"])
            .to_dict(orient="index")
        )

    # --- 11. Most significant feature deviations (reference vs flagged) -
    # Mean z-score (relative to TRAIN reference mean/std) for each
    # feature, comparing ANOMALY-status cycles to the reference train
    # population. This is an explanatory summary, not a causal claim.
    flagged = stable_with_scores[stable_with_scores["anomaly_status"] == "ANOMALY"]
    deviation_summary = {}
    if len(flagged) > 0:
        flagged_scaled = scaler.transform(flagged[feature_cols])  # already z-scored by StandardScaler
        mean_abs_z = np.abs(flagged_scaled).mean(axis=0)
        deviation_summary = dict(
            sorted(zip(feature_cols, mean_abs_z.tolist()), key=lambda kv: kv[1], reverse=True)
        )

    # --- 12. Save model + metadata ---------------------------------------
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    metadata = {
        "model_type": "isolation_forest",
        "reference_condition": {REFERENCE_COL: REFERENCE_VALUE},
        "reference_condition_meaning": LABEL_MEANINGS[REFERENCE_COL][REFERENCE_VALUE],
        "reference_scope_limitation": (
            "Reference is defined only along cooler_condition. "
            "valve_condition, pump_leakage and accumulator_pressure vary "
            "freely within the reference population."
        ),
        "feature_columns": feature_cols,
        "n_features": len(feature_cols),
        "dropped_zero_variance_features": zero_var_cols,
        "n_train_reference": len(X_train),
        "n_validation_reference": len(X_val),
        "n_test_reference": len(X_test),
        "n_non_reference_stable": len(X_non_reference),
        "reference_cycle_index_gaps_gt_1": n_gaps,
        "isolation_forest_params": {
            "n_estimators": 200,
            "max_samples": "auto",
            "contamination": "auto",
            "random_state": RANDOM_STATE,
        },
        "anomaly_score_definition": "-IsolationForest.score_samples(X_scaled); HIGHER = MORE ABNORMAL",
        "threshold_methodology": (
            f"WARNING = {WARNING_PERCENTILE}th percentile, ANOMALY = "
            f"{ANOMALY_PERCENTILE}th percentile of the VALIDATION reference "
            "population's anomaly score distribution. Never computed from test."
        ),
        "warning_threshold": warning_threshold,
        "anomaly_threshold": anomaly_threshold,
        "offline_evaluation_metrics": anomaly_metrics,
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "dataset": "UCI Condition Monitoring of Hydraulic Systems (ZeMA gGmbH)",
        "dataset_type": "controlled experimental test-rig data - NOT naturally occurring factory failures",
        "data_source": "real",
        "notes": (
            "An anomaly score measures how isolated a cycle's sensor "
            "feature vector is relative to the learned reference "
            "population. It is NOT a failure probability and does not "
            "predict when or whether a component will fail."
        ),
    }
    save_json(metadata, META_PATH)

    # --- 13. Reports + plots ----------------------------------------------
    save_json(
        {
            "n_total_cycles": len(profile),
            "n_stable_cycles": len(stable),
            "n_reference_cycles_stable": len(reference),
            "n_non_reference_stable": len(non_reference),
            "reference_condition": {REFERENCE_COL: REFERENCE_VALUE},
        },
        REPORTS_DIR / "dataset_summary.json",
    )
    save_json(
        {"warning_threshold": warning_threshold, "anomaly_threshold": anomaly_threshold,
         "warning_percentile": WARNING_PERCENTILE, "anomaly_percentile": ANOMALY_PERCENTILE},
        REPORTS_DIR / "thresholds.json",
    )
    save_json(anomaly_metrics, REPORTS_DIR / "anomaly_metrics.json")
    save_json(score_by_condition, REPORTS_DIR / "score_by_condition.json")
    save_json(deviation_summary, REPORTS_DIR / "deviation_summary.json")

    dist_path = save_score_distribution_plot(
        train_scores, val_scores, test_scores, non_ref_scores,
        warning_threshold, anomaly_threshold, REPORTS_DIR / "score_distribution.png",
    )
    cond_path = save_score_by_condition_plot(
        stable_with_scores, REFERENCE_COL, REPORTS_DIR / "score_by_condition.png"
    )
    timeline_path = save_anomaly_timeline_plot(
        stable_with_scores, warning_threshold, anomaly_threshold,
        REPORTS_DIR / "anomaly_timeline.png",
    )
    sensor_path = save_sensor_comparison_plot(
        reference[feature_cols], flagged[feature_cols] if len(flagged) else None,
        deviation_summary, REPORTS_DIR / "sensor_comparison.png",
    )

    # --- 14. Save processed anomaly scores (does not overwrite Part 7) --
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_cols = ["cycle_index", REFERENCE_COL, "valve_condition", "pump_leakage",
                "accumulator_pressure", "anomaly_score", "anomaly_status"]
    stable_with_scores[out_cols].to_csv(
        PROCESSED_DIR / "hydraulic_anomaly_scores.csv", index=False
    )

    return {
        "reference_size": len(reference),
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "non_reference_size": len(non_reference),
        "n_gaps": n_gaps,
        "feature_count": len(feature_cols),
        "dropped_zero_variance_features": zero_var_cols,
        "warning_threshold": warning_threshold,
        "anomaly_threshold": anomaly_threshold,
        "train_status_counts": pd.Series(train_status).value_counts().to_dict(),
        "val_status_counts": pd.Series(val_status).value_counts().to_dict(),
        "test_status_counts": pd.Series(test_status).value_counts().to_dict(),
        "non_ref_status_counts": pd.Series(non_ref_status).value_counts().to_dict(),
        "anomaly_metrics": anomaly_metrics,
        "score_by_condition": score_by_condition,
        "deviation_summary": deviation_summary,
        "model_path": MODEL_PATH,
        "meta_path": META_PATH,
        "plots": [dist_path, cond_path, timeline_path, sensor_path],
    }


if __name__ == "__main__":
    result = run_training()

    print("=== Machine Sensor Anomaly Detection: Part 8 ===\n")
    print(f"Reference condition: {REFERENCE_COL} == {REFERENCE_VALUE} "
          f"({LABEL_MEANINGS[REFERENCE_COL][REFERENCE_VALUE]})")
    print(f"Reference population (stable cycles): {result['reference_size']}")
    print(f"  train={result['train_size']}  validation={result['val_size']}  test={result['test_size']}")
    print(f"Non-reference stable cycles (offline eval only): {result['non_reference_size']}")
    print(f"Reference cycle_index gaps > 1: {result['n_gaps']} (small - documents near-contiguity)\n")

    print(f"Feature count: {result['feature_count']}"
          + (f" (dropped zero-variance: {result['dropped_zero_variance_features']})"
             if result["dropped_zero_variance_features"] else ""))

    print(f"\nWARNING threshold (95th pct of validation scores): {result['warning_threshold']:.4f}")
    print(f"ANOMALY threshold (99th pct of validation scores):  {result['anomaly_threshold']:.4f}\n")

    print("Status counts:")
    for name, counts in [
        ("Train (reference)", result["train_status_counts"]),
        ("Validation (reference)", result["val_status_counts"]),
        ("Test (reference, held out)", result["test_status_counts"]),
        ("Non-reference (other conditions)", result["non_ref_status_counts"]),
    ]:
        print(f"  {name}: {counts}")

    m = result["anomaly_metrics"]
    print(f"\n--- Offline evaluation (test reference=NORMAL vs non-reference=ABNORMAL) ---")
    print(f"Accuracy:  {m['accuracy']:.3f}")
    print(f"Precision: {m['precision']:.3f}")
    print(f"Recall:    {m['recall']:.3f}")
    print(f"F1:        {m['f1']:.3f}")
    print(f"TP={m['true_positive']}  FP={m['false_positive']}  "
          f"FN={m['false_negative']}  TN={m['true_negative']}")

    print("\n--- Mean anomaly score by cooler_condition (actual, offline analysis) ---")
    for cond, stats in result["score_by_condition"].get("cooler_condition", {}).items():
        print(f"  cooler_condition={cond}: mean={stats['mean']:.4f} "
              f"median={stats['median']:.4f} n={stats['count']}")

    print("\n--- Top 5 most deviating features (ANOMALY-flagged cycles, mean |z-score|) ---")
    for name, val in list(result["deviation_summary"].items())[:5]:
        print(f"  {name}: {val:.3f}")

    print(f"\nModel saved:    {result['model_path']}")
    print(f"Metadata saved: {result['meta_path']}")
    print("Plots saved:")
    for p in result["plots"]:
        print(f"  {p}")
