"""Cycle-level feature extraction for the hydraulic sensor data.

Each raw sensor file is a (n_cycles, n_samples) matrix - one 60-second
load cycle per row. This module reduces each cycle's raw samples to a
small set of summary statistics, so a classical (non-deep-learning)
classifier can work with one flat feature vector per cycle instead of
a raw time-series matrix.

Sensors sample at different rates (1Hz/10Hz/100Hz - see preprocess.py's
SENSOR_METADATA), but because every sensor is aligned to the SAME
60-second cycle boundaries, extracting the same statistics independently
from each sensor's own samples handles the multi-rate issue without any
resampling: no sensor's raw samples are ever stretched, shrunk, or
mixed with another sensor's.

Feature set (documented, not exhaustive):
  mean, std, min, max, range, rms, slope
    - mean/std/min/max/range: standard summary of the cycle's level and
      spread - meaningful for every physical quantity in this dataset
      (pressure, temperature, flow, power, efficiency).
    - rms (root-mean-square): captures signal "energy", useful
      especially for power/vibration-like channels.
    - slope: linear trend across the 60-second cycle (computed with a
      closed-form least-squares slope, vectorized across all cycles at
      once). A cycle where pressure is still falling at the end differs
      physically from one that has settled, even if mean/std look similar.
  kurtosis (VS1 - vibration - only)
    - excess kurtosis, a standard vibration-analysis statistic that
      captures "peakedness"/impulsiveness in a signal, which mean/std
      do not. Not applied to every sensor because it is specifically a
      vibration-diagnostics feature, not a generic one.

median/quantiles were evaluated and left out: for these smooth,
near-periodic industrial signals they were highly correlated with
mean/std and did not add distinct information, so including them would
only have inflated the feature count without a clear benefit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.machine_health.preprocess import SENSOR_METADATA, SENSOR_NAMES

GENERIC_STATS = ["mean", "std", "min", "max", "range", "rms", "slope"]
VIBRATION_SENSOR = "VS1"
VIBRATION_EXTRA_STATS = ["kurtosis"]


def _vectorized_slope(matrix: np.ndarray) -> np.ndarray:
    """Closed-form least-squares slope of each row against sample index.

    Equivalent to np.polyfit(x, row, 1)[0] for every row, but computed
    in one vectorized pass instead of a per-row Python loop - the
    100 Hz sensors have 6000 samples x 2205 cycles, so a loop-based
    implementation would be needlessly slow.
    """
    n = matrix.shape[1]
    x = np.arange(n, dtype=np.float64)
    x_centered = x - x.mean()
    denom = np.sum(x_centered**2)
    y_centered = matrix - matrix.mean(axis=1, keepdims=True)
    numer = y_centered @ x_centered
    return numer / denom


def _excess_kurtosis(matrix: np.ndarray) -> np.ndarray:
    """Excess kurtosis per row (0 for a normal distribution), computed
    manually with numpy to avoid adding scipy as an explicit project
    dependency (it is already present transitively via scikit-learn,
    but this keeps the import surface honest).
    """
    mean = matrix.mean(axis=1, keepdims=True)
    std = matrix.std(axis=1, keepdims=True)
    std_safe = np.where(std == 0, 1.0, std)  # avoid divide-by-zero on flat cycles
    fourth_moment = np.mean(((matrix - mean) / std_safe) ** 4, axis=1)
    return fourth_moment - 3.0


def extract_sensor_features(matrix: np.ndarray, sensor_name: str) -> pd.DataFrame:
    """Extract the documented statistics for one sensor's (n_cycles,
    n_samples) matrix. Returns a dataframe with one row per cycle and
    columns named '<sensor>_<stat>'.
    """
    mean = matrix.mean(axis=1)
    std = matrix.std(axis=1)
    mn = matrix.min(axis=1)
    mx = matrix.max(axis=1)
    rng = mx - mn
    rms = np.sqrt(np.mean(matrix**2, axis=1))
    slope = _vectorized_slope(matrix)

    data = {
        f"{sensor_name}_mean": mean,
        f"{sensor_name}_std": std,
        f"{sensor_name}_min": mn,
        f"{sensor_name}_max": mx,
        f"{sensor_name}_range": rng,
        f"{sensor_name}_rms": rms,
        f"{sensor_name}_slope": slope,
    }

    if sensor_name == VIBRATION_SENSOR:
        data[f"{sensor_name}_kurtosis"] = _excess_kurtosis(matrix)

    return pd.DataFrame(data)


def build_feature_table(sensors: dict[str, np.ndarray]) -> pd.DataFrame:
    """Combine per-sensor features into one cycle-level feature table.

    `sensors` must be {sensor_name: (n_cycles, n_samples) array}, as
    returned by preprocess.load_all_sensors(). Column order is fixed
    (sorted sensor name order) so train.py and predict.py always agree.
    """
    missing = set(SENSOR_NAMES) - set(sensors)
    if missing:
        raise ValueError(f"Missing sensor data for: {sorted(missing)}")

    frames = [extract_sensor_features(sensors[name], name) for name in SENSOR_NAMES]
    table = pd.concat(frames, axis=1)

    if table.isna().any().any():
        bad_cols = table.columns[table.isna().any()].tolist()
        raise ValueError(f"NaN produced during feature extraction in columns: {bad_cols}")
    if np.isinf(table.to_numpy()).any():
        raise ValueError("Infinite value produced during feature extraction.")

    return table


def get_feature_columns() -> list[str]:
    """Exact, ordered feature column list - used by both train.py and
    predict.py so they can never drift apart."""
    cols = []
    for name in SENSOR_NAMES:
        for stat in GENERIC_STATS:
            cols.append(f"{name}_{stat}")
        if name == VIBRATION_SENSOR:
            for stat in VIBRATION_EXTRA_STATS:
                cols.append(f"{name}_{stat}")
    return cols
