"""Machine Health data pipeline: loads and inspects the raw UCI
Condition Monitoring of Hydraulic Systems dataset.

This is a controlled, experimental hydraulic test-rig dataset (ZeMA
gGmbH). It is NOT naturally occurring factory failure data - it is
used here to demonstrate the Machine Health Intelligence pipeline.
See data/raw/hydraulic/description.txt for the original UCI
documentation (verified against the actual files below, not assumed).

This module only loads and inspects raw data. Feature extraction lives
in features.py; nothing here fits or trains anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "hydraulic"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "hydraulic"

PROFILE_FILENAME = "profile.txt"

# Sensor metadata, VERIFIED against the actual files (see inspect_data
# output) rather than assumed from the UCI documentation alone. Column
# counts match exactly what each .txt file actually contains.
#   name -> (physical quantity, unit, sampling rate Hz, expected n_columns)
SENSOR_METADATA: dict[str, dict] = {
    "PS1": {"quantity": "Pressure", "unit": "bar", "hz": 100, "n_cols": 6000},
    "PS2": {"quantity": "Pressure", "unit": "bar", "hz": 100, "n_cols": 6000},
    "PS3": {"quantity": "Pressure", "unit": "bar", "hz": 100, "n_cols": 6000},
    "PS4": {"quantity": "Pressure", "unit": "bar", "hz": 100, "n_cols": 6000},
    "PS5": {"quantity": "Pressure", "unit": "bar", "hz": 100, "n_cols": 6000},
    "PS6": {"quantity": "Pressure", "unit": "bar", "hz": 100, "n_cols": 6000},
    "EPS1": {"quantity": "Motor power", "unit": "W", "hz": 100, "n_cols": 6000},
    "FS1": {"quantity": "Volume flow", "unit": "l/min", "hz": 10, "n_cols": 600},
    "FS2": {"quantity": "Volume flow", "unit": "l/min", "hz": 10, "n_cols": 600},
    "TS1": {"quantity": "Temperature", "unit": "degC", "hz": 1, "n_cols": 60},
    "TS2": {"quantity": "Temperature", "unit": "degC", "hz": 1, "n_cols": 60},
    "TS3": {"quantity": "Temperature", "unit": "degC", "hz": 1, "n_cols": 60},
    "TS4": {"quantity": "Temperature", "unit": "degC", "hz": 1, "n_cols": 60},
    "VS1": {"quantity": "Vibration", "unit": "mm/s", "hz": 1, "n_cols": 60},
    "CE": {"quantity": "Cooling efficiency (virtual)", "unit": "%", "hz": 1, "n_cols": 60},
    "CP": {"quantity": "Cooling power (virtual)", "unit": "kW", "hz": 1, "n_cols": 60},
    "SE": {"quantity": "Efficiency factor", "unit": "%", "hz": 1, "n_cols": 60},
}
SENSOR_NAMES = list(SENSOR_METADATA.keys())

EXPECTED_N_CYCLES = 2205

# profile.txt column order, as documented in description.txt and
# verified against the actual file's value ranges below.
PROFILE_COLUMNS = [
    "cooler_condition",
    "valve_condition",
    "pump_leakage",
    "accumulator_pressure",
    "stable_flag",
]

# Documented meaning of each profile.txt value, taken directly from
# description.txt - not invented.
LABEL_MEANINGS = {
    "cooler_condition": {3: "close to total failure", 20: "reduced efficiency", 100: "full efficiency"},
    "valve_condition": {100: "optimal switching behavior", 90: "small lag", 80: "severe lag", 73: "close to total failure"},
    "pump_leakage": {0: "no leakage", 1: "weak leakage", 2: "severe leakage"},
    "accumulator_pressure": {130: "optimal pressure", 115: "slightly reduced pressure", 100: "severely reduced pressure", 90: "close to total failure"},
    "stable_flag": {0: "conditions were stable", 1: "static conditions might not have been reached yet"},
}


@dataclass
class DatasetInspectionReport:
    n_cycles_per_file: dict[str, int]
    n_columns_per_file: dict[str, int]
    columns_match_expected: dict[str, bool]
    missing_values_per_file: dict[str, int]
    profile_label_counts: dict[str, dict]
    profile_duplicate_rows: int
    sensor_duplicate_rows: dict[str, int]


def load_profile(path: Path | None = None) -> pd.DataFrame:
    """Load profile.txt (the cycle-wise condition labels)."""
    path = path or (RAW_DIR / PROFILE_FILENAME)
    if not path.exists():
        raise FileNotFoundError(
            f"profile.txt not found at '{path}'. Place the UCI Condition "
            f"Monitoring of Hydraulic Systems files in {RAW_DIR}"
        )
    df = pd.read_csv(path, sep="\t", header=None, names=PROFILE_COLUMNS)
    df.insert(0, "cycle_index", np.arange(len(df)))
    return df


def load_sensor(name: str, raw_dir: Path | None = None) -> np.ndarray:
    """Load one raw sensor file as a (n_cycles, n_samples) matrix."""
    raw_dir = raw_dir or RAW_DIR
    path = raw_dir / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Sensor file not found: '{path}'")
    return np.loadtxt(path, delimiter="\t")


def load_all_sensors(raw_dir: Path | None = None) -> dict[str, np.ndarray]:
    raw_dir = raw_dir or RAW_DIR
    return {name: load_sensor(name, raw_dir) for name in SENSOR_NAMES}


def inspect_data(raw_dir: Path | None = None) -> DatasetInspectionReport:
    """Factual structural report of the raw dataset. Run BEFORE any
    feature extraction or modelling decision - see Part 7 requirement
    to understand the actual data before choosing a target.
    """
    raw_dir = raw_dir or RAW_DIR
    profile = load_profile(raw_dir / PROFILE_FILENAME if False else None)  # uses RAW_DIR default
    sensors = load_all_sensors(raw_dir)

    n_cycles_per_file = {"profile": len(profile)}
    n_columns_per_file = {"profile": len(PROFILE_COLUMNS)}
    columns_match = {}
    missing_per_file = {"profile": int(profile[PROFILE_COLUMNS].isna().sum().sum())}
    sensor_dup_rows = {}

    for name, arr in sensors.items():
        n_cycles_per_file[name] = arr.shape[0]
        n_columns_per_file[name] = arr.shape[1]
        expected_cols = SENSOR_METADATA[name]["n_cols"]
        columns_match[name] = arr.shape[1] == expected_cols
        missing_per_file[name] = int(np.isnan(arr).sum())
        sensor_dup_rows[name] = int(pd.DataFrame(arr).duplicated().sum())

    label_counts = {
        col: profile[col].value_counts().sort_index().to_dict() for col in PROFILE_COLUMNS
    }

    return DatasetInspectionReport(
        n_cycles_per_file=n_cycles_per_file,
        n_columns_per_file=n_columns_per_file,
        columns_match_expected=columns_match,
        missing_values_per_file=missing_per_file,
        profile_label_counts=label_counts,
        profile_duplicate_rows=int(profile[PROFILE_COLUMNS].duplicated().sum()),
        sensor_duplicate_rows=sensor_dup_rows,
    )


def find_condition_blocks(profile: pd.DataFrame, label_col: str) -> list[tuple[int, int, int]]:
    """Find contiguous runs of identical label value in cycle order.

    Returns a list of (start_index, end_index_exclusive, label_value).
    This is how the leakage risk described in the README is actually
    measured, not assumed: the hydraulic dataset changes one physical
    condition at a time and runs many consecutive cycles per setting,
    so labels form large contiguous blocks rather than being scattered.
    """
    values = profile[label_col].values
    blocks = []
    start = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i] != values[start]:
            blocks.append((start, i, values[start]))
            start = i
    return blocks


if __name__ == "__main__":
    report = inspect_data()
    print("=== Machine Health Dataset Inspection (Part 7) ===\n")
    print("Rows (cycles) per file:")
    for name, n in report.n_cycles_per_file.items():
        print(f"  {name}: {n}")
    print("\nColumns per file (matches documented sampling rate?):")
    for name, n in report.n_columns_per_file.items():
        match = report.columns_match_expected.get(name, "n/a")
        print(f"  {name}: {n} columns  (matches expected: {match})")
    print("\nMissing values per file:")
    for name, n in report.missing_values_per_file.items():
        print(f"  {name}: {n}")
    print(f"\nProfile.txt duplicate LABEL rows: {report.profile_duplicate_rows} "
          f"(expected - many cycles share the same condition setting; "
          f"this is not a data-quality problem, see README)")
    print("\nDuplicate raw sensor rows (byte-identical cycles) per sensor:")
    for name, n in report.sensor_duplicate_rows.items():
        print(f"  {name}: {n}")
    print("\nLabel value counts:")
    for col, counts in report.profile_label_counts.items():
        print(f"  {col}: {counts}")


def block_chronological_split(
    profile: pd.DataFrame,
    label_col: str,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> pd.Series:
    """Split strategy for this dataset - NOT a random/stratified split.

    WHY: investigation (see README "Machine Health" section, and
    find_condition_blocks()) found that cooler_condition forms exactly
    THREE large contiguous blocks of consecutive cycles (sizes 732,
    732, 741) - the test rig was set to one condition and run for
    hundreds of cycles before being changed. Consecutive cycles within
    a block are repeated experiments under an unchanged physical
    setting, so a naive random/stratified split risks putting
    near-duplicate neighbouring cycles into both train and test,
    inflating test performance the way it would for the near-duplicate
    energy readings discussed in the Part 5/6 leakage notes.

    This function instead splits EACH label block chronologically into
    70/15/15 (same idea as the energy time-series split), so:
      - every class is represented in every split (blocks = classes),
      - no shuffling occurs,
      - train/validation/test cycles for a given class come from
        different, non-overlapping TIME REGIONS of that class's block,
        which is the closest thing this dataset has to "the future"
        the model will need to generalise to.

    Returns a pandas Series of {"train","validation","test"} aligned to
    profile's row order.
    """
    assignment = pd.Series(index=profile.index, dtype=object)
    blocks = find_condition_blocks(profile.reset_index(drop=True), label_col)

    for start, end, _label_value in blocks:
        block_size = end - start
        train_end = start + int(block_size * train_frac)
        val_end = train_end + int(block_size * val_frac)

        assignment.iloc[start:train_end] = "train"
        assignment.iloc[train_end:val_end] = "validation"
        assignment.iloc[val_end:end] = "test"

    return assignment


def simple_chronological_split(
    df: pd.DataFrame,
    order_col: str = "cycle_index",
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> pd.Series:
    """Chronological 70/15/15 split by row position, after sorting by
    `order_col`. No shuffling. Used by the Part 8 anomaly module for
    the reference population, which (unlike the full cooler_condition
    blocks) is a single, mostly-contiguous run of cycles - see
    train_anomaly.py for the contiguity check that justifies this.

    Returns a Series of {"train","validation","test"} aligned to df's
    ORIGINAL row order (not the sorted order used internally).
    """
    order = df[order_col].argsort().values  # positions that would sort df
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    labels = np.empty(n, dtype=object)
    labels[order[:train_end]] = "train"
    labels[order[train_end:val_end]] = "validation"
    labels[order[val_end:]] = "test"

    return pd.Series(labels, index=df.index)


def grouped_chronological_split(
    df: pd.DataFrame,
    group_cols: list[str],
    order_col: str = "cycle_index",
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> pd.Series:
    """Chronological 70/15/15 split applied WITHIN each contiguous
    (group_cols) block, then combined.

    WHY THIS EXISTS: a naive simple_chronological_split() on the Part 8
    reference population (cooler_condition==100) was tried first and
    found to be badly confounded - accumulator_pressure (an unrelated
    fault dimension that also varies within the reference population)
    happened to change roughly halfway through the block, so a plain
    "first 70% / next 15% / last 15%" split put ALL accumulator_pressure=90
    ("close to total failure") reference cycles in the test set and NONE
    in train. The anomaly detector had never seen that condition during
    training and flagged nearly all of test as ANOMALY - not because the
    model found something genuinely unusual, but because the split
    itself created an artificial train/test mismatch.

    This function fixes that by finding every contiguous block of
    identical (group_cols) combination and splitting 70/15/15 WITHIN
    each block before combining, so every combination present in the
    data contributes to train, validation AND test in the same
    proportion it appears overall - while still never shuffling and
    still keeping each split's cycles chronologically after the
    previous split's, within their own block.
    """
    working = df.reset_index(drop=True)
    key = working[group_cols].astype(str).agg("_".join, axis=1)
    order_vals = working[order_col].values

    # sort by order_col to find true contiguous runs
    sort_idx = np.argsort(order_vals)
    sorted_key = key.values[sort_idx]

    labels = np.empty(len(working), dtype=object)

    start = 0
    n = len(sorted_key)
    for i in range(1, n + 1):
        if i == n or sorted_key[i] != sorted_key[start]:
            block_positions = sort_idx[start:i]  # original-frame positions, in chronological order
            block_size = len(block_positions)
            train_end = int(block_size * train_frac)
            val_end = train_end + int(block_size * val_frac)
            labels[block_positions[:train_end]] = "train"
            labels[block_positions[train_end:val_end]] = "validation"
            labels[block_positions[val_end:]] = "test"
            start = i

    return pd.Series(labels, index=df.index)
