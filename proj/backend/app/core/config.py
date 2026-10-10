"""Central configuration for the AI Energy Brain backend.

Every tunable value (app name, allowed origins, and later the model
thresholds) lives here so it is changed in ONE place instead of being
scattered through route files.
"""

import os
from pathlib import Path


class Settings:
    # --- application identity ---
    APP_NAME: str = "AI Energy Brain API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = (
        "Industrial intelligence API combining energy forecasting and "
        "machine-health monitoring. ML models are not implemented yet."
    )

    # --- CORS ---
    # The local Vite dev server is always allowed. For a deployment, set the
    # ALLOWED_ORIGINS environment variable to the deployed frontend URL(s),
    # comma-separated (e.g. "https://my-app.onrender.com"). Never use "*",
    # which would let any website call this API.
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *[
            o.strip().rstrip("/")
            for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
            if o.strip()
        ],
    ]

    # --- project paths ---
    # config.py -> core -> app -> backend -> PROJECT ROOT
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = BASE_DIR / "models"
    REPORTS_DIR: Path = BASE_DIR / "reports"

    # --- dataset identity (used across energy/machine endpoints) ---
    ENERGY_DATASET_NAME: str = "UCI Tetouan City Power Consumption"
    ENERGY_UNIT: str = "kilowatts (summed across Zone 1-3 readings)"
    HYDRAULIC_DATASET_NAME: str = "UCI Condition Monitoring of Hydraulic Systems"
    MACHINE_ID: str = "hydraulic_test_rig"
    MACHINE_NAME: str = "Hydraulic Test Rig"

    # --- pagination / request limits ---
    ENERGY_HISTORY_DEFAULT_LIMIT: int = 100
    ENERGY_HISTORY_MAX_LIMIT: int = 1000
    ENERGY_FORECAST_DEFAULT_HORIZON: int = 6
    ENERGY_FORECAST_MAX_HORIZON: int = 36  # 6 hours at 10-min steps; see Part 6/9 accuracy-decay note

    # Part 14: energy-intensity what-if classification. A PROTOTYPE/DEMO
    # threshold only - not an industry standard, not derived from any
    # dataset (there is no production data to derive it from). If the
    # simulated energy intensity (energy/production) rises by more than
    # this percentage versus baseline, the scenario is classified as an
    # energy efficiency warning rather than normal/proportional.
    ENERGY_INTENSITY_WARNING_THRESHOLD_PERCENT: float = 5.0


settings = Settings()
