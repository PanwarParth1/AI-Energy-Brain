"""Energy forecasting: model training and selection.

Pipeline:
  full processed data -> forecasting features (whole-history, leak-safe)
    -> chronological split (same boundaries as Part 5)
    -> baseline + candidate models fit on TRAIN
    -> model selection on VALIDATION
    -> final, one-time evaluation of the selected model on TEST
    -> save model + metadata

This is a ONE-STEP-AHEAD forecaster: it predicts total_power_consumption
at time t using only information available before t (lagged target,
lagged weather, and deterministic calendar features for t itself).

Run with: python ml/energy/train.py
"""

from __future__ import annotations

import json
import platform
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.energy.evaluate import compute_metrics, make_evaluation_plots, save_json
from ml.energy.features import (
    TARGET_COL,
    build_feature_target_matrix,
    create_forecasting_features,
    get_feature_columns,
)
from ml.energy.preprocess import PROCESSED_DIR, PROCESSED_FILENAME, create_time_split

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports" / "energy_forecasting"

MODEL_PATH = MODELS_DIR / "energy_forecaster.joblib"
META_PATH = MODELS_DIR / "energy_forecaster.meta.json"

RANDOM_STATE = 42


def load_full_processed() -> pd.DataFrame:
    path = PROCESSED_DIR / PROCESSED_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at '{path}'. Run "
            "`python ml/energy/preprocess.py` (Part 5) first."
        )
    df = pd.read_csv(path, parse_dates=["datetime"])
    return df.sort_values("datetime").reset_index(drop=True)


def baseline_predict(X: pd.DataFrame) -> pd.Series:
    """Persistence baseline: predict that consumption stays the same as
    10 minutes ago. This uses the lag_1 feature, which is already the
    previous known value - no separate model object is needed.
    """
    return X["lag_1"]


def run_training() -> dict:
    # --- 1. Build features on the FULL sorted dataset first -----------
    # Section 14 of the spec: if we split into train/val/test BEFORE
    # computing lags, the first ~24 hours of validation and test would
    # lose access to real historical context that genuinely existed
    # (e.g. the first validation row's lag_144 needs a timestamp that
    # falls inside the training period). Computing features on the full
    # series first - then splitting - fixes this while still leaking
    # nothing: every lag/rolling value at row i only ever looks at rows
    # strictly before i, regardless of which split i ends up in.
    full_df = load_full_processed()
    featured = create_forecasting_features(full_df)

    # --- 2. Split using the EXACT same boundaries as Part 5 ------------
    # create_time_split is imported (not reimplemented) so the row-count
    # based 70/15/15 boundaries are guaranteed identical to preprocess.py.
    train_df, val_df, test_df = create_time_split(featured)

    X_train, y_train, dt_train = build_feature_target_matrix(train_df, drop_incomplete=True)
    X_val, y_val, dt_val = build_feature_target_matrix(val_df, drop_incomplete=True)
    X_test, y_test, dt_test = build_feature_target_matrix(test_df, drop_incomplete=True)

    # --- 3. Leakage sanity checks ---------------------------------------
    # Validation/test should need ZERO rows dropped for missing history,
    # because they have full preceding history from earlier splits.
    # Only the very start of TRAIN (first 144 rows, no prior data exists
    # at all) should have lost rows to dropna().
    n_val_dropped = len(val_df) - len(X_val)
    n_test_dropped = len(test_df) - len(X_test)
    if n_val_dropped != 0:
        raise AssertionError(
            f"Expected 0 rows dropped from validation due to missing "
            f"history, but {n_val_dropped} were dropped. This indicates "
            "a bug in feature construction, not a real data gap."
        )
    if n_test_dropped != 0:
        raise AssertionError(
            f"Expected 0 rows dropped from test due to missing history, "
            f"but {n_test_dropped} were dropped."
        )

    feature_cols = get_feature_columns()
    assert list(X_train.columns) == feature_cols == list(X_val.columns) == list(X_test.columns), (
        "Feature column order mismatch between splits - this would silently "
        "corrupt predictions."
    )

    # --- 4. Baseline (persistence) --------------------------------------
    baseline_val_metrics = compute_metrics(y_val, baseline_predict(X_val).values)
    baseline_test_metrics = compute_metrics(y_test, baseline_predict(X_test).values)

    # --- 5. Candidate models, fit on TRAIN only -------------------------
    # Linear Regression is wrapped in a Pipeline with StandardScaler so
    # the scaler is fit ONLY on training data (never on val/test) and
    # travels with the model as one saved object - required by the
    # project's "fit only on train" rule, enforced structurally.
    linreg = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression()),
    ])
    linreg.fit(X_train, y_train)

    # Random Forest needs no scaling. min_samples_leaf=5 is a light
    # regularizer - on 36k+ rows an unconstrained forest can memorise
    # near-duplicate consecutive 10-minute readings without generalising
    # better than a mildly-constrained one.
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    # --- 6. Model selection on VALIDATION only --------------------------
    linreg_val_metrics = compute_metrics(y_val, linreg.predict(X_val))
    rf_val_metrics = compute_metrics(y_val, rf.predict(X_val))

    candidates = {
        "linear_regression": (linreg, linreg_val_metrics),
        "random_forest": (rf, rf_val_metrics),
    }
    # Selection rule: lowest validation RMSE. Ties go to the simpler model.
    selected_name = min(candidates, key=lambda name: candidates[name][1]["rmse"])
    selected_model, selected_val_metrics = candidates[selected_name]

    # --- 7. ONE-TIME test evaluation of the selected model only --------
    # The test set is touched exactly once, after selection is final.
    y_test_pred = selected_model.predict(X_test)
    selected_test_metrics = compute_metrics(y_test, y_test_pred)

    # --- 8. Feature importance ------------------------------------------
    if selected_name == "random_forest":
        importances = dict(
            sorted(
                zip(feature_cols, selected_model.feature_importances_.tolist()),
                key=lambda kv: kv[1],
                reverse=True,
            )
        )
    else:
        # Linear Regression: coefficients are on STANDARDIZED features
        # (StandardScaler was applied), so their magnitudes are directly
        # comparable to each other as a rough importance proxy - unlike
        # raw coefficients on unscaled features, which would not be.
        coefs = selected_model.named_steps["model"].coef_
        importances = dict(
            sorted(zip(feature_cols, coefs.tolist()), key=lambda kv: abs(kv[1]), reverse=True)
        )

    # --- 9. Save model + metadata ---------------------------------------
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_model, MODEL_PATH)

    metadata = {
        "model_type": selected_name,
        "target": TARGET_COL,
        "feature_columns": feature_cols,  # exact order predict.py must use
        "forecast_horizon": "one_step_ahead (10 minutes)",
        "train_rows": len(X_train),
        "validation_rows": len(X_val),
        "test_rows": len(X_test),
        "train_range": [str(dt_train.min()), str(dt_train.max())],
        "validation_range": [str(dt_val.min()), str(dt_val.max())],
        "test_range": [str(dt_test.min()), str(dt_test.max())],
        "random_state": RANDOM_STATE,
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "validation_metrics": {
            "baseline_persistence": baseline_val_metrics,
            "linear_regression": linreg_val_metrics,
            "random_forest": rf_val_metrics,
        },
        "selected_model": selected_name,
        "test_metrics": {
            "baseline_persistence": baseline_test_metrics,
            "selected_model": selected_test_metrics,
        },
        "feature_importance": importances,
        "data_source": "real",
        "dataset": "UCI Tetouan City Power Consumption",
        "notes": (
            "total_power_consumption is the sum of three Tetouan city "
            "consumption zones, not three machines. This model forecasts "
            "aggregate city-level power consumption one 10-minute step "
            "ahead; it does not predict industrial machine behaviour."
        ),
    }
    save_json(metadata, META_PATH)

    # --- 10. Evaluation plots on TEST -----------------------------------
    plot_paths = make_evaluation_plots(dt_test, y_test, y_test_pred, REPORTS_DIR)

    comparison = {
        "validation": {
            "baseline_persistence": baseline_val_metrics,
            "linear_regression": linreg_val_metrics,
            "random_forest": rf_val_metrics,
        },
        "selected_model": selected_name,
        "test": {
            "baseline_persistence": baseline_test_metrics,
            "selected_model": selected_test_metrics,
        },
    }
    save_json(comparison, REPORTS_DIR / "model_comparison.json")
    save_json(selected_test_metrics, REPORTS_DIR / "test_metrics.json")

    return {
        "feature_cols": feature_cols,
        "baseline_val": baseline_val_metrics,
        "baseline_test": baseline_test_metrics,
        "linreg_val": linreg_val_metrics,
        "rf_val": rf_val_metrics,
        "selected_name": selected_name,
        "selected_test": selected_test_metrics,
        "importances": importances,
        "plot_paths": plot_paths,
        "model_path": MODEL_PATH,
        "meta_path": META_PATH,
    }


if __name__ == "__main__":
    result = run_training()

    print("=== Energy Forecasting: Part 6 ===\n")
    print(f"Target: total_power_consumption (sum of Zone 1 + Zone 2 + Zone 3)\n")
    print(f"Feature count: {len(result['feature_cols'])}")
    print(f"Features: {result['feature_cols']}\n")

    print("--- Validation metrics (model selection happens here) ---")
    print(f"{'Model':<22}{'MAE':>12}{'RMSE':>12}{'R2':>10}")
    for name, metrics in [
        ("Baseline (persistence)", result["baseline_val"]),
        ("Linear Regression", result["linreg_val"]),
        ("Random Forest", result["rf_val"]),
    ]:
        print(f"{name:<22}{metrics['mae']:>12.2f}{metrics['rmse']:>12.2f}{metrics['r2']:>10.4f}")

    print(f"\nSelected model: {result['selected_name']} (lowest validation RMSE)\n")

    print("--- Final TEST metrics (selected model only, evaluated once) ---")
    t = result["selected_test"]
    b = result["baseline_test"]
    print(f"{'Model':<22}{'MAE':>12}{'RMSE':>12}{'R2':>10}")
    print(f"{'Baseline (persistence)':<22}{b['mae']:>12.2f}{b['rmse']:>12.2f}{b['r2']:>10.4f}")
    print(f"{result['selected_name']:<22}{t['mae']:>12.2f}{t['rmse']:>12.2f}{t['r2']:>10.4f}")

    print("\n--- Top 5 most important features ---")
    for name, val in list(result["importances"].items())[:5]:
        print(f"  {name}: {val:.4f}")

    print(f"\nModel saved:    {result['model_path']}")
    print(f"Metadata saved: {result['meta_path']}")
    print("Plots saved:")
    for p in result["plot_paths"]:
        print(f"  {p}")
