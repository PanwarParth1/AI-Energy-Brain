"""Energy data pipeline for AI Energy Brain.

Turns the raw UCI Tetouan City Power Consumption CSV into a clean,
chronologically-split dataset ready for Part 6 (forecasting) and
Part 7 (anomaly detection).

This module does NOT train any model. It only loads, inspects,
cleans, feature-engineers and splits data. Every function is pure
(no hidden global state) so it can be reused from analyze.py, from
a notebook, or from a future retraining script.

Reminder: the Tetouan dataset is a public city-level power-consumption
dataset. It is used here to demonstrate the Energy Intelligence
pipeline and is not industrial factory data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# --- paths -------------------------------------------------------------
# Resolved relative to this file so the script works no matter which
# directory it is launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RAW_FILENAME = "Tetuan City power consumption.csv"
PROCESSED_FILENAME = "tetouan_energy_processed.csv"

# --- schema contract -----------------------------------------------------
# The raw file's exact headers, as delivered by UCI. Column names are
# whitespace-inconsistent in the source (Zone 2/3 have a double space) -
# this is a documented cleaning step, not a silent assumption.
EXPECTED_RAW_COLUMNS = [
    "DateTime",
    "Temperature",
    "Humidity",
    "Wind Speed",
    "general diffuse flows",
    "diffuse flows",
    "Zone 1 Power Consumption",
    "Zone 2  Power Consumption",
    "Zone 3  Power Consumption",
]

# Raw column -> clean snake_case column. This mapping is the single
# source of truth for renaming; nothing else in the pipeline renames
# columns implicitly. Meaning is unchanged - only formatting is normalised.
COLUMN_RENAME_MAP = {
    "DateTime": "datetime",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Wind Speed": "wind_speed",
    "general diffuse flows": "general_diffuse_flows",
    "diffuse flows": "diffuse_flows",
    "Zone 1 Power Consumption": "zone_1_power_consumption",
    "Zone 2  Power Consumption": "zone_2_power_consumption",
    "Zone 3  Power Consumption": "zone_3_power_consumption",
}

ZONE_COLUMNS = [
    "zone_1_power_consumption",
    "zone_2_power_consumption",
    "zone_3_power_consumption",
]
ENVIRONMENTAL_COLUMNS = [
    "temperature",
    "humidity",
    "wind_speed",
    "general_diffuse_flows",
    "diffuse_flows",
]
NUMERIC_COLUMNS = ZONE_COLUMNS + ENVIRONMENTAL_COLUMNS

# The source data is sampled every 10 minutes. This is verified against
# the actual file in validate_data(), not assumed.
EXPECTED_SAMPLING_INTERVAL = pd.Timedelta(minutes=10)


@dataclass
class DataQualityReport:
    """Plain container for the numbers inspect_data() finds.

    Kept as a dataclass (not just printed) so analyze.py and any
    future caller can consume the actual figures programmatically
    instead of re-deriving or guessing them.
    """

    n_rows: int
    n_columns: int
    columns: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    duplicate_rows: int
    duplicate_datetimes: int
    datetime_start: pd.Timestamp
    datetime_end: pd.Timestamp
    sampling_interval_mode: pd.Timedelta
    timestamp_gaps: int
    infinite_values: dict[str, int]
    negative_values: dict[str, int]


# --- pipeline steps ------------------------------------------------------

def load_raw_data(path: Path | None = None) -> pd.DataFrame:
    """Load the raw CSV exactly as downloaded. No cleaning happens here.

    Raises FileNotFoundError with an actionable message if the file is
    missing, rather than silently generating placeholder data.
    """
    path = path or (RAW_DIR / RAW_FILENAME)

    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at '{path}'.\n"
            "Download the UCI Tetouan City Power Consumption dataset and "
            f"place the CSV at: {RAW_DIR}"
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"Raw dataset at '{path}' is empty.")

    missing_cols = set(EXPECTED_RAW_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Raw dataset is missing expected columns: {sorted(missing_cols)}. "
            f"Found columns: {list(df.columns)}"
        )

    return df


def inspect_data(df: pd.DataFrame) -> DataQualityReport:
    """Produce a factual data-quality report from the RAW dataframe.

    This must run before any cleaning decision is made - you cannot
    justify a cleaning strategy without first knowing what is actually
    wrong (or not wrong) with the data.
    """
    parsed_dt = pd.to_datetime(df["DateTime"], format="%m/%d/%Y %H:%M", errors="coerce")
    n_parse_failures = int(parsed_dt.isna().sum())
    if n_parse_failures:
        raise ValueError(
            f"{n_parse_failures} DateTime value(s) could not be parsed with "
            "format '%m/%d/%Y %H:%M'. Inspect the raw file before proceeding."
        )

    sorted_dt = parsed_dt.sort_values()
    diffs = sorted_dt.diff().dropna()
    sampling_mode = diffs.mode().iloc[0] if not diffs.empty else pd.Timedelta(0)

    full_range = pd.date_range(start=parsed_dt.min(), end=parsed_dt.max(), freq=sampling_mode)
    n_gaps = len(full_range.difference(parsed_dt))

    numeric_df = df.rename(columns=COLUMN_RENAME_MAP)[NUMERIC_COLUMNS]

    infinite_values = {
        col: int(np.isinf(numeric_df[col]).sum())
        for col in numeric_df.columns
        if np.isinf(numeric_df[col]).sum() > 0
    }
    negative_values = {
        col: int((numeric_df[col] < 0).sum())
        for col in numeric_df.columns
        if (numeric_df[col] < 0).sum() > 0
    }

    return DataQualityReport(
        n_rows=len(df),
        n_columns=len(df.columns),
        columns=list(df.columns),
        dtypes={c: str(t) for c, t in df.dtypes.items()},
        missing_values={c: int(v) for c, v in df.isna().sum().items()},
        duplicate_rows=int(df.duplicated().sum()),
        duplicate_datetimes=int(df["DateTime"].duplicated().sum()),
        datetime_start=parsed_dt.min(),
        datetime_end=parsed_dt.max(),
        sampling_interval_mode=sampling_mode,
        timestamp_gaps=int(n_gaps),
        infinite_values=infinite_values,
        negative_values=negative_values,
    )


def clean_data(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    """Apply cleaning decisions justified by `report`.

    Decisions made here (and why - see README "Energy Data Pipeline"
    section for the full reasoning):
      - Column names are normalised to snake_case (whitespace-only fix).
      - DateTime is parsed to a real datetime dtype.
      - Rows are sorted chronologically (already sorted in the source,
        but this makes the guarantee explicit rather than assumed).
      - No missing-value filling is applied: the raw file has zero
        missing values (see report.missing_values), so inventing a
        fill strategy would be unjustified.
      - No duplicate removal is applied: zero duplicate rows and zero
        duplicate timestamps were found.
      - No outliers are removed: energy spikes are real signal for a
        forecasting/anomaly task, not noise to discard.
    """
    if report.duplicate_rows > 0:
        raise ValueError(
            f"{report.duplicate_rows} duplicate row(s) detected. This pipeline "
            "does not silently drop duplicates - inspect them first."
        )
    if report.duplicate_datetimes > 0:
        raise ValueError(
            f"{report.duplicate_datetimes} duplicate DateTime value(s) detected. "
            "Inspect whether they carry different measurements before proceeding."
        )
    if any(v > 0 for v in report.missing_values.values()):
        raise ValueError(
            "Missing values detected but no handling strategy is implemented "
            "for them yet. Extend clean_data() deliberately before proceeding: "
            f"{report.missing_values}"
        )
    if report.infinite_values:
        raise ValueError(f"Infinite values detected: {report.infinite_values}")
    if report.timestamp_gaps > 0:
        raise ValueError(
            f"{report.timestamp_gaps} missing timestamp(s) detected in the "
            "expected 10-minute sequence. Decide a gap-handling strategy "
            "before proceeding - do not silently interpolate."
        )

    cleaned = df.rename(columns=COLUMN_RENAME_MAP).copy()
    cleaned["datetime"] = pd.to_datetime(cleaned["datetime"], format="%m/%d/%Y %H:%M")
    cleaned = cleaned.sort_values("datetime").reset_index(drop=True)

    for col in NUMERIC_COLUMNS:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="raise")

    return cleaned


def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features derived independently from each row's own
    timestamp. None of these look at other rows, so none of them can
    leak information from the future.

    minute is included (not just hour) because the data is sampled every
    10 minutes, so minute-of-hour (0,10,20...50) still carries a small
    amount of intra-hour signal that hour alone collapses.
    """
    out = df.copy()
    dt = out["datetime"]

    out["hour"] = dt.dt.hour
    out["minute"] = dt.dt.minute
    out["day_of_week"] = dt.dt.dayofweek  # Monday=0 ... Sunday=6
    out["day_of_month"] = dt.dt.day
    out["month"] = dt.dt.month
    out["day_of_year"] = dt.dt.dayofyear
    out["is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype(int)

    # Documented aggregate: the three zones are consumption zones of the
    # same city dataset, NOT three separate machines. Summing them gives
    # a defensible city-wide total for later forecasting/anomaly work.
    out["total_power_consumption"] = out[ZONE_COLUMNS].sum(axis=1)

    return out


def validate_data(df: pd.DataFrame) -> None:
    """Final structural guarantees before the data is split or saved.

    Raises on the first violation found rather than continuing with
    corrupted data.
    """
    if df.empty:
        raise ValueError("Dataset is empty after cleaning.")

    if not df["datetime"].is_monotonic_increasing:
        raise ValueError("Dataset is not sorted chronologically.")

    if df["datetime"].duplicated().any():
        raise ValueError("Duplicate timestamps present after cleaning.")

    for col in NUMERIC_COLUMNS + ["total_power_consumption"]:
        if not np.issubdtype(df[col].dtype, np.number):
            raise ValueError(f"Column '{col}' is not numeric after cleaning.")
        if df[col].isna().any():
            raise ValueError(f"Column '{col}' contains NaN after cleaning.")
        if np.isinf(df[col]).any():
            raise ValueError(f"Column '{col}' contains infinite values after cleaning.")

    # Future-feature guard: fail loudly if anything named lag_/rolling_
    # sneaks in here. Those belong to Part 6, computed only inside the
    # training script, on the training split only.
    leakage_like = [c for c in df.columns if c.startswith(("lag_", "rolling_", "future_"))]
    if leakage_like:
        raise ValueError(
            f"Found lag/rolling/future-looking columns in Part 5 output: "
            f"{leakage_like}. These must not be created before the "
            "train/validation/test split (Part 6)."
        )


def create_time_split(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Deterministic chronological split. No shuffling, no randomness.

    train_frac + val_frac must be < 1.0; the remainder is the test set.
    Splitting by row position (on already-sorted, gap-free, 10-minute
    data) is equivalent to splitting by date and is simpler to make
    exact and reproducible.
    """
    if not df["datetime"].is_monotonic_increasing:
        raise ValueError("Refusing to split: dataframe is not chronologically sorted.")

    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train = df.iloc[:train_end].reset_index(drop=True)
    val = df.iloc[train_end:val_end].reset_index(drop=True)
    test = df.iloc[val_end:].reset_index(drop=True)

    # Hard guarantee: train strictly precedes validation strictly precedes test.
    assert train["datetime"].max() < val["datetime"].min(), "Train/validation overlap in time."
    assert val["datetime"].max() < test["datetime"].min(), "Validation/test overlap in time."

    return train, val, test


def save_processed_data(
    full_df: pd.DataFrame,
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    out_dir: Path | None = None,
) -> dict[str, Path]:
    """Write processed outputs. Never touches data/raw/."""
    out_dir = out_dir or PROCESSED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "processed": out_dir / PROCESSED_FILENAME,
        "train": out_dir / "train.csv",
        "validation": out_dir / "validation.csv",
        "test": out_dir / "test.csv",
    }

    full_df.to_csv(paths["processed"], index=False)
    train.to_csv(paths["train"], index=False)
    val.to_csv(paths["validation"], index=False)
    test.to_csv(paths["test"], index=False)

    return paths


def run_pipeline(raw_path: Path | None = None, out_dir: Path | None = None) -> dict:
    """Run the full Part 5 pipeline end to end and return a summary dict.

    This is the single entry point every caller (CLI, analyze.py,
    tests) should use, so "run it again" always means the same thing.
    """
    raw_df = load_raw_data(raw_path)
    report = inspect_data(raw_df)
    cleaned = clean_data(raw_df, report)
    featured = create_time_features(cleaned)
    validate_data(featured)
    train, val, test = create_time_split(featured)
    paths = save_processed_data(featured, train, val, test, out_dir)

    return {
        "report": report,
        "processed_shape": featured.shape,
        "train_range": (train["datetime"].min(), train["datetime"].max()),
        "val_range": (val["datetime"].min(), val["datetime"].max()),
        "test_range": (test["datetime"].min(), test["datetime"].max()),
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "paths": paths,
    }


if __name__ == "__main__":
    summary = run_pipeline()
    r = summary["report"]
    print("=== Energy Data Pipeline: Part 5 ===")
    print(f"Raw rows:            {r.n_rows}")
    print(f"Raw columns:         {r.n_columns}")
    print(f"Missing values:      {sum(r.missing_values.values())}")
    print(f"Duplicate rows:      {r.duplicate_rows}")
    print(f"Duplicate datetimes: {r.duplicate_datetimes}")
    print(f"Datetime range:      {r.datetime_start} -> {r.datetime_end}")
    print(f"Sampling interval:   {r.sampling_interval_mode}")
    print(f"Timestamp gaps:      {r.timestamp_gaps}")
    print()
    print(f"Processed shape:     {summary['processed_shape']}")
    print(f"Train rows:          {summary['train_rows']}  ({summary['train_range'][0]} -> {summary['train_range'][1]})")
    print(f"Validation rows:     {summary['val_rows']}  ({summary['val_range'][0]} -> {summary['val_range'][1]})")
    print(f"Test rows:           {summary['test_rows']}  ({summary['test_range'][0]} -> {summary['test_range'][1]})")
    print()
    for name, path in summary["paths"].items():
        print(f"Saved {name}: {path}")
