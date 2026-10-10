# AI Energy Brain

Industrial intelligence platform combining **energy intelligence** and
**machine-health intelligence** into a single dashboard.

> **Current status: Part 18 complete (scenario recommendations in the Machine What-If Simulator).**
> Energy forecasting, machine health classification, anomaly detection,
> a rule-based recommendation engine, a FastAPI backend, a React control-
> center dashboard, and Machine / Energy What-If simulators are all
> implemented and tested. It is a prototype built on public datasets - see
> "Current limitations" in section 23.

---

## 1. Project description

AI Energy Brain is a hackathon MVP that aims to help industrial operators
answer two related questions from one interface:

- What is happening with energy consumption, and what demand can be expected?
- Which machines are showing abnormal sensor behaviour and should be inspected?

The system deliberately avoids unsupported claims. It reports *anomalies*,
*risk*, *health scores* and *recommended inspections* - never guaranteed
failures or failure dates.

## 2. Current architecture

```
Datasets  ->  Preprocessing  ->  ML models  ->  Rule engine  ->  FastAPI  ->  React
   (offline, run once)            (artifacts in models/)        (online, during demo)
```

Training never happens inside the API. Models are trained offline by scripts
in `ml/`, saved to `models/`, and only loaded for inference by the backend.

## 3. Technology stack

| Layer    | Tools |
|----------|-------|
| Frontend | React, Vite, Tailwind CSS v4, Recharts |
| Backend  | Python, FastAPI, Uvicorn, Pydantic |
| ML       | NumPy, Pandas, scikit-learn, Joblib |
| Analysis | Matplotlib, Seaborn |
| Database | SQLite (added in a later part) |
| API      | REST / JSON |

## 4. Folder structure

```
AI-ENERGY-BRAIN/
├── backend/
│   ├── app/
│   │   ├── main.py          # app factory, CORS, router mounting
│   │   ├── core/            # configuration and thresholds
│   │   ├── routes/          # API endpoints
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # business logic (later parts)
│   │   └── utils/           # helpers
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # reusable UI pieces
│   │   ├── pages/           # dashboard pages (Part 12)
│   │   ├── charts/          # Recharts wrappers (Part 12)
│   │   ├── services/api.js  # all backend calls
│   │   └── utils/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── ml/
│   ├── common/              # shared preprocessing and split helpers
│   ├── energy/              # energy forecasting + anomaly detection
│   └── machine_health/      # condition classification + sensor anomaly
├── data/
│   ├── raw/                 # original downloaded datasets
│   ├── processed/           # cleaned, feature-engineered data
│   └── sample/              # small samples for quick testing
├── models/                  # trained .joblib artifacts + .meta.json
├── scripts/                 # one-off utility scripts
├── README.md
└── .gitignore
```

## 5. Backend setup (Windows PowerShell)

Run all backend commands **from the project root** (`AI-ENERGY-BRAIN/`).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

If PowerShell blocks the activation script, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 6. Start the backend

```powershell
uvicorn backend.app.main:app --reload
```

The API runs at http://localhost:8000 and interactive docs are at
http://localhost:8000/docs

## 7. Frontend setup

```powershell
cd frontend
copy .env.example .env
npm install
```

## 8. Start the frontend

```powershell
npm run dev
```

The dashboard runs at http://localhost:5173

## 9. Health endpoint

`GET /api/health`

```json
{
  "status": "ok",
  "service": "AI Energy Brain API"
}
```

## 10. Development status

| Part | Module | Status |
|------|--------|--------|
| 1-4  | Project foundation and setup                         | Done |
| 5    | Energy data pipeline                                 | Done |
| 6    | Energy forecasting (Random Forest)                   | Done |
| 7    | Machine health classification (Logistic Regression)  | Done |
| 8    | Machine anomaly detection (Isolation Forest)         | Done |
| 9    | Rule-based recommendation engine                     | Done |
| 10   | FastAPI backend                                      | Done |
| 11   | React dashboard                                      | Done |
| 12   | Machine What-If backend                              | Done |
| 13   | Machine What-If UI                                   | Done |
| 14   | Energy + Production What-If                          | Done |
| 15   | Unified dashboard / control center                   | Done |
| 16   | Final validation & demo readiness                    | Done |
| 18   | Machine What-If recommendation integration           | Done |

## 11. Datasets (used in later parts)

- **Energy:** UCI Tetouan City Power Consumption - a public city-level power
  consumption dataset, used to demonstrate the energy intelligence pipeline.
  It is not a factory dataset.
- **Machine health:** UCI Condition Monitoring of Hydraulic Systems - a
  controlled experimental test-rig dataset, not naturally occurring factory
  failures.

Any simulated element added later will be labelled as simulated in the API
response and in the user interface.

## 12. Energy Data Pipeline (Part 5)

**Dataset name:** UCI Tetouan City Power Consumption Dataset

**Dataset role:** a public, city-level power-consumption dataset used to
demonstrate the Energy Intelligence pipeline. It is **not** direct
industrial factory data, and it is never described as such anywhere in
this project.

**Raw data location:** `data/raw/Tetuan City power consumption.csv`
(52,416 rows, unmodified - the pipeline never writes to this folder).

**Preprocessing command** (from project root, with the backend venv active):

```powershell
python ml/energy/preprocess.py
```

**EDA / data-quality report command:**

```powershell
python ml/energy/analyze.py
```

**Processed data location:** `data/processed/`
- `tetouan_energy_processed.csv` - full cleaned dataset with time features
- `train.csv` / `validation.csv` / `test.csv` - chronological split

**Train/validation/test strategy:** deterministic chronological split,
70% / 15% / 15% by row position (the source data has zero timestamp gaps,
so row-position splitting is equivalent to date splitting). No shuffling.
Train strictly precedes validation strictly precedes test in time -
enforced with an assertion in the pipeline, not just a comment.

**Key data-quality findings (actual, from the raw file):**
- 52,416 rows, 9 raw columns, 0 missing values, 0 duplicate rows, 0
  duplicate timestamps, 0 timestamp gaps, 0 infinite values, 0 negative
  values.
- Sampling interval is a consistent 10 minutes across the entire file.
- Date range: 2017-01-01 00:00 to 2017-12-30 23:50 (the source file does
  not include December 31, 2017 - this is a property of the published
  dataset, not a bug in this pipeline).

**Cleaning decisions:**
- Column names normalised to snake_case (the raw file has inconsistent
  spacing - e.g. a double space in "Zone 2  Power Consumption"). No
  missing-value filling, duplicate removal, or outlier removal was
  applied, because none of those problems exist in the raw data - adding
  handling logic for a problem that isn't present would be unjustified.
- `total_power_consumption` = sum of the three zone columns. This is a
  documented aggregate of consumption **zones**, not a sum across
  separate machines.

**Leakage checks performed:** no scaling/normalisation is fitted in this
part; all time features are computed independently per row from that
row's own timestamp; the split is chronological with an assertion that
train/validation/test do not overlap in time; the pipeline explicitly
rejects any column named `lag_*`, `rolling_*`, or `future_*` if one is
accidentally introduced before the split.

## 13. Energy Forecasting (Part 6)

**Target:** `total_power_consumption` - the sum of the three Tetouan
consumption zones (Zone 1 + Zone 2 + Zone 3). This is a public,
city-level aggregate, not a factory or machine quantity.

**Forecast horizon:** one-step-ahead (predicts the next 10-minute
reading using only information available before that timestamp).

**Feature construction approach:** lag/rolling/weather-lag features are
computed on the FULL chronologically-sorted processed dataset first,
and the dataset is split into train/validation/test AFTER, using the
same 70/15/15 row-position boundaries as Part 5. This lets validation
and test rows use real historical context from the periods immediately
before them (as they genuinely could in production) without ever
looking at a value from their own future. Verified: 0 rows were dropped
from validation or test for missing history; only the first 144 rows of
train were dropped (no history exists before the dataset starts at
all).

**Key design decision - weather features are lagged, not contemporaneous:**
the raw weather columns are measured at the same timestamp as the
target. Using them directly would implicitly assume a perfect weather
forecast, which this project does not have. Instead, each weather
variable's previous (already-observed) reading is used
(`temperature_lag_1`, etc.) - this keeps the one-step forecast honest
with zero assumptions about the future.

**Leakage guard:** the three zone columns are excluded from the feature
set entirely, because `total_power_consumption` is defined as their
exact sum - including them would let the model "predict" the target by
re-adding its own components.

**Commands:**
```powershell
python ml/energy/train.py
python ml/energy/predict.py
```

**Validation metrics (used for model selection):**

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Baseline (persistence) | 796.67 | 1205.32 | 0.9920 |
| Linear Regression | 451.05 | 687.34 | 0.9974 |
| Random Forest | 388.94 | 549.64 | 0.9983 |

**Selected model:** Random Forest (lowest validation RMSE, and it also
had the lowest MAE - a consistent win, not a marginal one).

**Final test metrics (selected model, evaluated once):**

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Baseline (persistence) | 786.35 | 1177.63 | 0.9932 |
| Random Forest | 473.12 | 707.14 | 0.9975 |

**Model file:** `models/energy_forecaster.joblib` +
`models/energy_forecaster.meta.json` (feature list, exact order,
training config, all metrics above).

**Limitation:** `predict.py` also offers `predict_future()` for
multi-step forecasting beyond the end of known data. This recursively
feeds the model's own predictions back in, and holds future weather
constant at the last observed reading (a documented simplifying
assumption, since no real future weather exists in this dataset).
Accuracy degrades the further out this is used - it is intended for a
short horizon (roughly up to 1 hour / 6 steps), not as a substitute for
a dedicated multi-step model.

This module forecasts aggregate city-level power consumption from a
public dataset. It does not predict industrial machine behaviour - that
is the separate Machine Health Intelligence module (Part 8 onward).

## 14. Machine Health: Cooler Condition Classification (Part 7)

**Dataset:** UCI Condition Monitoring of Hydraulic Systems (ZeMA gGmbH).
A **controlled experimental hydraulic test rig** - 2205 sixty-second
load cycles, 17 sensor channels (pressure, motor power, volume flow,
temperature, vibration, and virtual cooling/efficiency channels)
sampled at 100 Hz / 10 Hz / 1 Hz respectively, plus `profile.txt`
labelling each cycle's cooler condition, valve condition, internal
pump leakage, accumulator pressure, and a stability flag. This is
**not** naturally occurring factory failure data.

**Dataset structure (verified against the actual files):**
- All 17 sensor files + `profile.txt` have exactly 2205 rows.
- Column counts per file match the documented sampling rates exactly
  (100 Hz sensors: 6000 columns; 10 Hz: 600; 1 Hz: 60).
- Zero missing values across every file.
- `profile.txt` has 2025 duplicate label *rows* - expected, not a data
  quality issue: many cycles share the same condition setting (see
  block structure below), so their label tuples repeat.
- `PS4` (a pressure channel) has 1237 duplicate raw *rows*, including
  many all-zero cycles - a genuine physical property (PS4's line often
  reads ~0 bar under real operating conditions in this rig), not
  corrupted data. Raw values were not altered.

**Primary target: `cooler_condition`** (3 classes: 3% "close to total
failure", 20% "reduced efficiency", 100% "full efficiency"). Chosen
over the other three available labels (valve condition, pump leakage,
accumulator pressure) because it is the only one with close to
perfectly balanced classes (732 / 732 / 741 cycles); the others are
meaningfully imbalanced (e.g. valve condition's majority class alone
covers 1125 of 2205 cycles). Separate models for the other three
labels are left as documented future work, not forced into this MVP.

**Split strategy - NOT random.** Investigation found `cooler_condition`
forms exactly **three large contiguous blocks** of consecutive cycles
(sizes 732 / 732 / 741 cycles) - the rig was set to one condition and
run for hundreds of cycles before being changed. A naive random or
stratified split risks putting near-duplicate neighbouring cycles from
the same run into both train and test. Instead, each class's block was
split chronologically 70/15/15 (mirroring the energy module's
approach), so every class appears in every split while train,
validation and test cycles for a given class come from different,
non-overlapping time regions of that class's block.

**Stability filtering.** `profile.txt`'s `stable_flag` marks 756 of
2205 cycles as not yet at steady state - investigation showed these
cluster at the *start* of each condition block (the rig settling after
a setting change), not scattered randomly. These 756 cycles were
excluded from train/validation/test (1449 stable cycles used), to
avoid teaching the model transient settling signatures instead of
genuine steady-state condition signatures. Raw data is untouched;
this is a training-set inclusion decision only.

**Feature extraction:** for each of the 17 sensors, 7 generic cycle-level
statistics (mean, std, min, max, range, RMS, slope), computed directly
from that sensor's own raw samples with no resampling across the
different sampling rates. The vibration channel (VS1) additionally
gets excess kurtosis. **120 features total.** The three profile.txt
label columns are never included as features (verified programmatically
in train.py, not just by convention).

**Models evaluated:** majority-class `DummyClassifier` baseline,
Logistic Regression (scaled, `class_weight="balanced"`), Random Forest
(`class_weight="balanced"`).

**Result - both models solve this task essentially perfectly on
validation and test (Logistic Regression selected, tied with Random
Forest, on validation macro F1 = 1.000; test macro F1 = 1.000, exact
diagonal confusion matrix).** This was investigated rather than taken
at face value: it holds even with the two most cooler-related virtual
sensors (CE, CP) removed from the feature set entirely, and Random
Forest's feature importances are spread thin (no single feature above
0.03 of 120). The honest explanation is that this is a **controlled
experiment with three deliberately large, discrete condition settings**
(3% / 20% / 100% efficiency) - changing the cooler setting shifts
temperatures, pressures and flow system-wide, producing large,
consistent, easily-separable differences between classes. **This is
not evidence that a deployed system would achieve this accuracy on
gradual, real-world degradation**, where conditions would drift
continuously and classes would overlap far more - see Limitations.

**Model file:** `models/machine_health_classifier.joblib` +
`models/machine_health_classifier.meta.json`.

**Commands:**
```powershell
python ml/machine_health/preprocess.py
python ml/machine_health/train.py
python ml/machine_health/predict.py
```

**Limitations:**
- This dataset uses three widely-separated, artificial severity
  settings. It does not demonstrate detection of subtle, gradual
  real-world degradation, and near-perfect accuracy here should not be
  read as a general capability claim.
- Only `cooler_condition` is modelled in Part 7. Valve condition,
  pump leakage, and accumulator pressure are documented but not yet
  modelled - a natural next module, either as separate classifiers or
  a multi-label formulation.
- Predictions are a statistical association learned from this
  experimental dataset, not a confirmed physical root cause, and do
  not guarantee failure at any specific time.

## 15. Machine Sensor Anomaly Detection (Part 8)

**Objective:** answer "does this cycle's sensor behaviour look unusual
compared with a learned reference population?" - a separate,
independent question from Part 7's "which known cooler condition does
this match?". Part 8 does not use Part 7's model, predictions, or
probabilities anywhere; it goes straight from raw sensors to features
to `IsolationForest`, verified programmatically (no profile label
column ever enters the feature matrix).

**Reference / normal population: `cooler_condition == 100`** ("full
efficiency", stable cycles only - 489 cycles). Chosen because it is the
only documented value with an unambiguous "optimal" meaning that also
has enough data: a stricter reference requiring all four condition
labels simultaneously optimal was checked and found to cover only 21
cycles (10 stable) - too few to train and split.

**Scope limitation (documented, not hidden):** `valve_condition`,
`pump_leakage` and `accumulator_pressure` are NOT controlled within
this reference population - they vary freely across the 489 reference
cycles. This detector learns "what full-cooler-efficiency sensor
behaviour looks like across the range of other conditions this rig was
run at," not a universally fault-free state.

**Split strategy - a real mid-build correction, documented rather than
hidden.** A first attempt used a plain chronological split (first
70%/next 15%/last 15% of reference cycles by order). This was checked
against the actual label distributions and found to be badly
confounded: `accumulator_pressure` happens to change partway through
the reference population, so the naive split put **100% of
accumulator_pressure=90 cycles in test and none in train** - the model
had never seen that condition, so it flagged nearly all of test as
anomalous for a reason unrelated to genuine abnormality. Fixed by
splitting chronologically **within each contiguous (valve_condition,
pump_leakage, accumulator_pressure) sub-block** instead (48 sub-blocks,
sizes 10-19 cycles each), so every combination present in the data
contributes proportionally to train/validation/test. After the fix,
test-reference status proportions (3 WARNING + 2 ANOMALY out of 98,
≈5%) line up closely with the 95th/99th-percentile thresholds by
design.

**Features:** the same 120 (post zero-variance-drop: 116) cycle-level
features from Part 7's `features.py`, reused rather than re-implemented.
4 features (`PS2_min`, `PS3_min`, `FS1_min`, `SE_min`) were dropped for
having zero variance within the training reference population.

**Model:** `IsolationForest(n_estimators=200, max_samples="auto",
contamination="auto", random_state=42)`, wrapped with a `StandardScaler`
fitted only on the training reference population, in a single saved
`sklearn.Pipeline`.

**Anomaly score:** `-IsolationForest.score_samples(X_scaled)` - **higher
= more abnormal** (the sign is flipped from sklearn's native
convention, done once in code and documented). This is a relative
isolation measure, not a probability of anything.

**Thresholds - derived from data, not arbitrary:** WARNING = 95th
percentile, ANOMALY = 99th percentile of the **validation reference**
population's score distribution (never test). Actual values:
WARNING = 0.5167, ANOMALY = 0.5252.

**Offline evaluation** (labels used only for evaluation, never for
training or threshold selection): test-reference cycles (known
NORMAL) vs. non-reference stable cycles (known off-reference-condition,
960 cycles) →

| Metric | Value |
|---|---|
| Accuracy | 0.995 |
| Precision | 0.995 |
| Recall | 1.000 |
| F1 | 0.997 |

Mean anomaly score by actual `cooler_condition` (offline analysis
only): 100→0.458, 20→0.649, 3→0.670 - monotonically increasing with
documented severity, a sign the score captures real signal.

**Commands:**
```powershell
python ml/machine_health/train_anomaly.py
python ml/machine_health/anomaly.py
```

**Model file:** `models/machine_anomaly_detector.joblib` +
`models/machine_anomaly_detector.meta.json`.

**Limitations:**
- An anomaly score is **not** a failure probability, does not predict
  time-to-failure, and a flagged deviation is not a confirmed physical
  root cause.
- The reference population only controls for cooler condition; a cycle
  could be flagged due to valve/pump/accumulator variation the
  reference already includes some of, or due to a genuinely novel
  condition - the two are not distinguishable from the score alone.
- Some slope-type features have very low variance within the reference
  population, which can produce very large z-scores in
  `explain_deviations()` for modest absolute changes - documented so
  this isn't misread as an extreme deviation in absolute terms.
- Like Part 7, this is a controlled experimental dataset with large,
  deliberate condition steps - real-world gradual degradation would
  likely show far more score overlap between normal and early-stage
  abnormal behaviour than seen here.

## 16. AI Recommendation Engine (Part 9)

**Objective:** convert Parts 6-8's existing model outputs into
structured, explainable, actionable recommendations - "given current
machine and energy signals, what should an operator inspect or
consider doing next?" Purely deterministic Python rule logic - **no
LLM, no external API** - for reproducibility, explainability, and zero
hallucination risk.

**Architecture:**
```
Part 7 (health) + Part 8 (anomaly)  ->  machine_rules.py  ─┐
Part 6 (forecast) vs recent history ->  energy_rules.py   ─┤─> engine.py -> Recommendation[]
                                                             │   (cross-track + dedup)
```
Part 9 never retrains or modifies any Part 6/7/8 model - it only calls
their existing `predict.py`/`anomaly.py` inference functions and reads
their `.meta.json` files.

**Categories:** `MACHINE_INSPECTION`, `PREVENTIVE_MAINTENANCE`,
`ENERGY_MONITORING`, `ENERGY_OPTIMIZATION`, `CONTINUE_MONITORING`,
`NO_ACTION`. **Priorities:** `INFO` < `LOW` < `MEDIUM` < `HIGH` <
`CRITICAL`.

**Priority logic - a transparent point table, not a magic formula:**
`total_points = anomaly_points (0-2, from Part 8 status) + severity_points
(0-2, from Part 7's predicted class rank) + persistence_points (0-2, from
how many of the last 10 real historical stable cycles were flagged)`,
mapped to priority bands documented in `config.py`. A low machine-health
classification confidence (<0.6) caps `CRITICAL` down to `HIGH` -
"do not force a diagnosis" when the classifier itself is uncertain.

**All thresholds are sourced, not hand-copied:** Part 8's WARNING/ANOMALY
thresholds and Part 7's class list are read live from their `.meta.json`
files. Energy deviation thresholds (ELEVATED/HIGH) are derived from the
**real** historical Tetouan deviation-from-24h-mean distribution
(90th/98th percentile: 34.5% / 40.9%), the same percentile methodology
Part 8 already used - not arbitrary numbers. The full resolved
configuration is saved to `reports/recommendations/recommendation_rules.json`.

**Evidence & consolidation:** every recommendation carries a structured
`evidence` list (`signal`, `observation`, `severity`, `source`).
Multiple deviating sensor features are mapped to their **documented
physical quantity** (reusing Part 7's own `SENSOR_METADATA`, e.g.
"Temperature", "Vibration") and consolidated into ONE recommendation
with a deduplicated action ("Inspect cooling system...; mechanical
condition...") instead of one alert per feature.

**Temporal persistence:** genuinely implemented using Part 8's real
saved `hydraulic_anomaly_scores.csv` - looks back over the most recent
10 real stable cycles at or before the target cycle. Verified behaviour:
a cycle at the very start of a newly-degraded block (e.g. cycle 211,
the first stable cycle after a condition change) shows low persistence
(1/1) and scores MEDIUM; the same block 90 cycles later (cycle 300)
shows full persistence (10/10) and escalates to CRITICAL - the
escalation is driven by real recurrence in the data, not staged.

**Cross-track logic - honesty note.** The Tetouan (energy) and hydraulic
(machine) datasets are independent, real, unrelated sources with no
shared timeline or facility. When both a machine and an energy
recommendation reach MEDIUM+ priority together, the engine produces an
additional combined recommendation ("Coinciding abnormal machine and
energy signals warrant investigation... this does not establish that
one caused the other"), and every such recommendation's `limitations`
field explicitly states the two tracks are demonstrated together, not
genuinely correlated in this MVP.

**"Confidence" is rule confidence, not statistical probability** -
every recommendation's `confidence_basis` field states exactly what it
means (proportion of supporting evidence present), so it is never
confused with the underlying model's own probability output.

**Testing:** 8 deterministic unit tests (no pytest dependency - plain
assertions, `python ml/recommendation/tests.py`), all passing. A
genuine bug was found and fixed during testing: an early version's
persistence lookup could accidentally match unrelated real data when
given a large synthetic test `cycle_index` (Python's `<=` comparison
against real data); fixed by isolating unit-test fixtures with
`cycle_index=None` and adding an explicit out-of-range guard in
`get_persistence_count()`.

**Integration testing on real data:** ran real Part 6-8 outputs through
the engine for representative real cycles (a genuine reference/normal
cycle, an early-block low-persistence cycle, a persistent-anomaly
cycle, and a cross-track pairing using a verified real elevated-energy
timestamp) - see `reports/recommendations/recommendation_examples.json`.
All 5 priorities and 4 of 6 categories were exercised by real data
(`PREVENTIVE_MAINTENANCE`/`NO_ACTION` require narrower signal windows
not hit by the specific real cycles sampled, though both are covered by
the unit tests).

**Evaluation methodology:** rule-based systems have no ground-truth
"correct recommendation" dataset, so no accuracy figure is reported.
Evaluated instead via schema validity, determinism (identical input ->
identical output, verified), rule/category/priority coverage, and unit
test pass rate - see `reports/recommendations/recommendation_test_report.json`.

**Commands:**
```powershell
python ml/recommendation/tests.py
python ml/recommendation/evaluate.py
```

**Limitations:**
- The recommendation engine provides AI-assisted decision support and
  does not replace qualified maintenance or engineering inspection.
- Part 7's classifier was trained only on stable cycles; predictions on
  transient/unstable cycles (e.g. cycle 0, still settling after a
  condition change) are less reliable and may disagree with the
  cycle's eventual steady-state label - observed directly in the real
  integration example for `early_anomaly_low_persistence`.
- Machine and energy tracks are demonstrated together but are not from
  a shared real facility or timeline (see cross-track note above).
- "Confidence" is a rule-strength heuristic, not a statistical or
  causal probability.

## 17. FastAPI Backend (Part 10)

**Objective:** expose Parts 6-9's existing functionality as a REST API,
with zero duplicated ML/rule logic - every route calls a thin service
function that calls the actual existing `predict.py`/`anomaly.py`/
`engine.py` functions.

**Architecture:**
```
Route (backend/app/routes/*.py)
    -> Service (backend/app/services/*.py)
        -> existing ml/energy, ml/machine_health, ml/recommendation functions
            -> Pydantic response model -> JSON
```

**Routes created** (all under `/api`, in addition to the existing `/api/health`):

| Method | Path | Backed by |
|---|---|---|
| GET | `/energy/summary` | `ml.energy.predict` |
| GET | `/energy/history` | processed Tetouan CSV (cached) |
| GET | `/energy/forecast` | `ml.energy.predict.predict_future()` |
| GET | `/machines` | dataset identity (one test rig) |
| GET | `/machines/{id}/health` | `ml.machine_health.predict.predict_from_sensors()` |
| GET | `/machines/{id}/anomaly` | `ml.machine_health.anomaly.detect_anomaly()` |
| POST | `/machines/analyze` | Part 7 + Part 8 + Part 9 combined |
| GET | `/recommendations` | `ml.recommendation.engine.generate_recommendations()` (latest cycle) |
| POST | `/recommendations/generate` | same, for a chosen cycle/energy pairing |
| GET | `/alerts` | derived view over anomaly status + HIGH/CRITICAL recommendations |
| GET | `/dashboard/summary` | composition of the above |

**Schemas:** `backend/app/schemas/{energy,machine,anomaly,recommendation,dashboard,alert,common}.py` -
Pydantic models mirroring Parts 6-9's actual field names (e.g.
`total_power_consumption`, `predicted_condition_meaning`,
`confidence_basis`) rather than inventing new ones.

**Services:** `backend/app/services/{energy,machine,recommendation,dashboard,alert}_service.py` -
route handlers are one or two lines each; all real work happens here,
and every service function ultimately calls an existing Part 6-9
function.

**Model-loading strategy:** a small, honest fix was made to the source
of the slowness rather than duplicating logic in the backend. Part
6/7/8's own `load_model()` functions (`ml/energy/predict.py`,
`ml/machine_health/predict.py`, `ml/machine_health/anomaly.py`)
previously re-read their `.joblib`/`.meta.json` files from disk on
*every* call. Added a simple in-module cache (a few lines each,
verified to return byte-identical results via smoke-test comparison
before/after) so the model loads once per process and every caller in
the whole project benefits, not just the API. Raw sensor data (~540MB)
and full-dataset Part 7 predictions are separately cached at the
`machine_service` module level.

**Performance (measured, not estimated):** first request after startup
is slow (~9s: one-time raw-sensor load + full-dataset inference across
2205 cycles); subsequent requests are ~3s for endpoints needing a
per-cycle anomaly *explanation* (`/machines/analyze`,
`/recommendations`, `/dashboard/summary` - `detect_anomaly()` does two
internal feature-extraction passes over the full dataset, a Part 8
characteristic this project did not change) and under 1s for
bulk/cached-only endpoints (`/machines`, `/energy/*`,
`/machines/{id}/health`). Documented rather than hidden - see
Limitations.

**Error handling:** every error is `{"error": {"code": "...",
"message": "..."}}` (section 31), via a single `AppError` exception
class and two global FastAPI exception handlers - no route returns a
differently-shaped error. Invalid cycle index and unknown machine ID →
404; invalid query parameters (e.g. `horizon=999`) → 422 via Pydantic's
own validation, wrapped in the same error envelope. Internal exceptions
never leak a stack trace to the client.

**CORS:** unchanged from Part 4 - only `http://localhost:5173` (and
`127.0.0.1:5173`) allowed, centralized in `backend/app/core/config.py`.
Verified: an `evil.com` origin gets no `access-control-allow-origin`
header.

**Testing:** `backend/tests/test_api.py` - 43 checks across the 12
required test areas (health, energy summary/history/forecast, machine
listing, valid analysis, invalid cycle, anomaly, recommendations,
dashboard, invalid machine ID, CORS), all against real project data,
all passing. No pytest dependency added - plain assertions, same
pattern as `ml/recommendation/tests.py`.

**Commands:**
```powershell
uvicorn backend.app.main:app --reload
python backend/tests/test_api.py
```
Docs: `http://localhost:8000/docs` (Swagger) and `/redoc`.

**Data/model provenance:** every energy response states
`"UCI Tetouan City Power Consumption"`; every machine response states
`"UCI Condition Monitoring of Hydraulic Systems"` and
`"controlled experimental test-rig data - not a live industrial
facility"`. `/api/machines` always returns exactly one entry.

**Limitations:**
- Per-cycle anomaly-explanation endpoints take ~1.7-3s due to Part 8's
  `detect_anomaly()` re-extracting features internally; acceptable for
  a local MVP, not tuned further to avoid touching Part 8's logic.
- `/api/alerts` reflects only the *latest* cycle's status - it is a
  snapshot view, not a historical alert log.
- `/api/recommendations` (GET) and the energy-pairing in `/analyze`
  use real but (per Part 9's own documented caveat) *unrelated*
  energy/machine datasets when both are requested together.
- No authentication - this is an unauthenticated local MVP by design,
  per the spec.

## 18. React Dashboard (Part 11)

**Objective:** a professional industrial-monitoring frontend consuming
Part 10's real API - no fabricated metrics anywhere, verified by an
explicit source audit (see below) and by screenshot QA of the actual
running app, not just a successful build.

**Stack:** React 19 + Vite + Tailwind CSS v4 + Recharts + React Router
+ lucide-react (icons). No Redux - a single small `LayoutContext` holds
one boolean (mobile sidebar open/closed); all data fetching uses plain
hooks (`useFetch`, `useApiHealth`, `useOverviewData`).

**Pages:** Overview (`/`), Energy Intelligence (`/energy`), Machine
Health (`/machines`), Alerts (`/alerts`), Recommendations
(`/recommendations`) - routed with React Router, active nav state in
the sidebar.

**API layer:** `frontend/src/services/api.js` - every backend call goes
through one `request()` function with a 15s timeout and the backend's
own `{"error": {"code","message"}}` envelope surfaced as a typed
`ApiError`. No component calls `fetch()` directly (verified by source
grep).

**No fake data - verified, not just claimed:**
- `/api/machines` always renders exactly the machines the backend
  returns (currently 1) - no invented fleet.
- KPI cards, chart data, recommendation priorities, and alert counts
  all come from live API responses - confirmed by matching on-screen
  values against direct API calls during testing (e.g. cycle 301's
  "3 - close to total failure" / "ANOMALY" / "CRITICAL" recommendation
  in the browser screenshot matches the raw JSON from Part 10's own
  tests exactly).
- Recommendation priority filter buttons only show priorities the
  backend actually returned for the current data (`All`, `LOW` in the
  current dataset state - not a hardcoded five-button row).
- Missing/unavailable values render as "Data unavailable", never a
  placeholder number.
- Explicit source audit run before completion: grepped for `savings`,
  `cost`, `failure_probability`, `RUL`, `downtime`, hardcoded machine
  counts - none found outside real API field names/comments.

**The primary demo interaction** (`/machines`, "Cycle Analysis"): enter
a cycle index, click **Analyze Cycle**, and the real
`POST /api/machines/analyze` response renders across three panels
(Health, Anomaly, Recommendations) - tested live with cycle 301
(produces `3 - close to total failure`, `ANOMALY` at score 0.663, and
a CRITICAL `MACHINE_INSPECTION` recommendation, matching Part 9/10's
own output) and with an invalid cycle (999999 → the backend's actual
404 message rendered in an `ErrorState` with a working Retry button).

**Visual QA - actually performed, not assumed.** Playwright (already
available in this environment) was used to run the built app against
the live backend and screenshot every page at desktop (1440px) and
mobile (390px) widths, plus the Analyze Cycle interaction in its
loading, success, and error states. **Two real bugs were found this
way and fixed before completion:**
1. The zone-consumption lines on the Energy Intelligence chart
   silently failed to render (a Recharts quirk with `<Line>` elements
   wrapped in a `<>` Fragment inside a conditional) - fixed by
   rendering each conditional `<Line>` as a direct child instead.
2. The sidebar did not collapse on a 390px mobile viewport, squeezing
   all content into an unusably narrow column - fixed with a proper
   slide-in drawer (scrim, close button, hamburger toggle in the
   header) via a new small `LayoutContext`.

Both fixes were verified by re-running the same screenshot capture and
visually confirming the result, not just re-running the build.

**Loading/error/empty states:** every API-driven section has its own
loading label (e.g. "Analyzing sensor state..."), its own `ErrorState`
with the backend's real message and a Retry button, and an honest
empty state ("No active alerts", "No recommendations generated for the
current state.") - none of these are simulated in the screenshots
above; they were triggered by real API responses (an empty alerts list
and a deliberately invalid cycle index).

**Responsiveness:** desktop primary, verified functional at mobile
width (390px) after the sidebar-drawer fix - single-column KPI cards,
full-width chart, working hamburger navigation.

**Commands:**
```powershell
uvicorn backend.app.main:app --reload
cd frontend && npm install && npm run dev
```
Frontend: `http://localhost:5173`. Backend must be running first.

**Limitations:**
- First interaction after backend startup inherits Part 10's documented
  ~9s cold-start / ~3s per-cycle-analysis cost - the UI shows "Analyzing
  sensor state..." rather than freezing, but does not hide the wait.
- Alerts and the Overview "Active Alerts" KPI reflect only the most
  recently evaluated cycle (Part 10's snapshot design), not a
  historical log - stated explicitly on the Alerts page.
- The production build's single JS bundle is ~692KB (202KB gzipped) -
  acceptable for a local MVP; code-splitting was not added, per the
  "avoid unnecessary complexity" project guideline.

## 19. Interactive What-If Simulation Foundation (Part 12)

**Why added:** to let a future dashboard interaction ("what if this
sensor read differently?") run through the SAME trained models Parts
7/8 already use, rather than a hardcoded `if vibration > X: anomaly`
rule. This part is backend-only foundation - no UI yet (Part 13).

**Key architectural finding (verified by inspection before writing any
code):** every feature in `ml/machine_health/features.py` is a
per-cycle statistic computed independently along `axis=1` of each
sensor's `(n_cycles, n_samples)` matrix - no cross-cycle dependency
(unlike the energy module's lag/rolling features). This means a single
synthetic cycle, shaped `(1, n_samples)` per sensor, can be pushed
through `build_feature_table()`, `predict_from_sensors()`, and
`detect_anomaly()` **completely unmodified** and get a mathematically
correct result. **Zero lines of Parts 6-11 were changed** to build
this - `ml/machine_health/simulate.py` only constructs the input shape
those functions already expect.

**How baseline cycles work:** `extract_baseline_cycle()` copies one
real cycle's raw samples (`.copy()`, explicitly) out of the cached
full-dataset matrices for all 17 sensors. The cached matrices
themselves - and the files on disk - are never touched; verified by a
dedicated test that re-reads `PS1.txt` fresh from disk after running
simulation API calls and confirms the in-memory cache still matches
byte-for-byte.

**How perturbations work:** `multiply` (positive, finite factor) or
`offset` (any finite value), applied elementwise to a sensor's full
array, preserving its exact sampling structure (100 Hz/6000 samples,
10 Hz/600, or 1 Hz/60 - whichever that sensor actually has). Multiple
sensors can be perturbed in one request; each sensor may appear at
most once (duplicate perturbations on the same sensor are rejected as
ambiguous).

**Which sensors can be perturbed - and a bug caught along the way:**
only the 14 physical sensors (`PS1-6`, `EPS1`, `FS1`, `FS2`, `TS1-4`,
`VS1`). `CE`, `CP` and `SE` are excluded as an **explicit whitelist**,
not a string-match on their documentation text. The first
implementation excluded only `CE`/`CP` by matching the word "virtual"
in `SENSOR_METADATA`'s quantity string, missing `SE` (which this
project's own instructions explicitly group with `CE`/`CP`, even
though the raw UCI documentation doesn't literally label `SE`
"(virtual)"). Found via a real test assertion, not manual review, and
fixed with an explicit list plus a module-level assertion that no
virtual channel can ever appear in it.

**Reused, not retrained:** the exact same `models/machine_health_classifier.joblib`
and `models/machine_anomaly_detector.joblib` (and their cached
`load_model()` from Part 10), the same `StandardScaler`, the same
Part 8 WARNING/ANOMALY thresholds. A dedicated test
(`TEST12_*`/`sim_baseline_matches_real_api`) confirms a simulation's
baseline result (zero perturbations) is bit-identical to calling the
normal `/machines/{id}/health` and `/machines/{id}/anomaly` endpoints
directly for the same cycle.

**Real, model-driven results - not hardcoded:** cycle 1714 (a healthy
reference cycle) with `VS1` (vibration) multiplied ×5 flips the
**Part 7 classifier's own prediction** from `100 - full efficiency` to
`20 - reduced efficiency`, and the anomaly status from `NORMAL` to
`WARNING` - both are the real trained models responding to the
perturbed input, not an if/else rule. A simulation is equally valid if
the prediction does *not* change - the requirement is that real models
processed real (perturbed) features, not that the outcome differs.

**API:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/machines/simulate/sensors` | Which sensors/modes are valid (for Part 13's UI) |
| POST | `/api/machines/simulate` | Run a what-if scenario |

Request:
```json
{
  "machine_id": "hydraulic_test_rig",
  "baseline_cycle_index": 1714,
  "perturbations": [{"sensor": "VS1", "mode": "multiply", "value": 5.0}]
}
```
Response: `simulation: true`, `scenario_type: "what_if"`, `baseline` and
`simulated` blocks (each with real `health` + `anomaly` results),
`changes` (real before/after sensor means), and a `note` field stating
plainly this is not a live measurement or physical digital twin.

**Validation (all via the project's existing `{"error":{"code","message"}}`
envelope):** unknown/virtual sensor → 400, invalid `mode` → 422
(Pydantic enum), out-of-range `baseline_cycle_index` or unknown
`machine_id` → 404, NaN/Infinite/zero/negative-multiply values → 400.

**Testing:** `ml/machine_health/test_simulate.py` (47 checks, all the
spec's 13 required cases plus 2 extra) and `backend/tests/test_simulation.py`
(17 checks, API-level) - both passing. Full regression: `backend/tests/test_api.py`
(43 checks), `ml/recommendation/tests.py` (14 checks), and Parts 6/7/8
smoke scripts all re-run and produced **identical** output to before
this part - zero regression.

**Commands:**
```powershell
python ml/machine_health/test_simulate.py
python backend/tests/test_simulation.py
```

**Limitations:**
- Recommendations (Part 9) are deliberately NOT included in the
  simulation result yet - the spec's own Step 7 function outline stops
  at the anomaly detector, and Part 13+ is where UI/deeper integration
  belongs. Wiring it in later is a one-line addition (the function
  already returns clean health/anomaly dicts Part 9 already accepts).
- Perturbations are elementwise across a sensor's entire cycle (a
  uniform shift/scale), not a shaped or localized change within the
  60-second window.
- This is a statistical what-if against a trained model, not a
  physical simulation - a changed (or unchanged) prediction is not a
  guarantee about real-world behaviour, stated in every response's
  `note` field.

## 20. Machine What-If Simulator UI (Part 13)

**Objective:** a frontend for Part 12's real simulation backend - no new
ML logic, no fabricated predictions, visually consistent with the
existing dashboard.

**Route:** `/machine-simulator`, added to the sidebar (flask icon, no
emoji - matching the existing icon-only nav style) between Machine
Health and Alerts.

**Default baseline cycle - backend-confirmed, not assumed.** Rather
than hardcoding cycle 1714 (or any number), the page calls
`GET /machines/{id}/health` with no `cycle_index` on load - the same
"latest available cycle" default the existing Machine Health page
already uses - and reads the `cycle_index` the backend actually chose
(currently 2204, a real healthy/reference cycle) as the simulator's
starting point. The user can load any other real cycle in range.

**Design decision worth documenting - how baseline sensor values are
shown without a new backend endpoint.** Part 12's API has no
"give me sensor X's raw reading for cycle Y" endpoint - only
`POST /machines/simulate`, whose `changes` field returns real
`baseline_mean`/`unit` per sensor, but only for sensors actually
included in a request. To show every physical sensor's real baseline
value before the user changes anything, the page makes one real
`/machines/simulate` call with an **identity perturbation**
(`multiply × 1.0`) for all 14 sensors at once - the exact existing
request format, no backend change, and the resulting numbers are 100%
real (the backend computed them by actually running the pipeline).
This was the frontend-only solution the spec asked to prefer over a
backend change.

**Sensor list and modes** come from `GET /machines/simulate/sensors`
(14 physical sensors; `CE`/`CP`/`SE` never appear as options - excluded
by the backend, confirmed in the UI copy).

**Real-time feel without extra API calls (section 19):** each active
sensor change shows a **client-computed preview**
(`baseline × value` or `baseline + value`) that updates instantly as
the slider moves, explicitly labelled *"(client preview, not yet
analyzed)"* so it is never confused with a real model output. The
backend is only called when **ANALYZE SCENARIO** is clicked.

**Result display:** Baseline and Simulated shown side by side (stacked
on mobile), each with real predicted condition, confidence, anomaly
status/score, and top deviations (reusing the existing
`SensorDeviationChart` component). A `SIMULATED SCENARIO` badge and the
API's own `note` field (verbatim) make it unambiguous this is a
what-if result, never a live measurement. A "Scenario Changes" table
and a baseline-vs-simulated bar chart (`SensorComparisonBarChart`,
new - Recharts, matching the project's existing chart style) both
render only the real `changes` values from the API - no fabricated
time series, since Part 12 only returns scalar cycle-summary numbers.

**Recommendations intentionally omitted for simulated scenarios** - a
plain note states integration is deferred, per the spec's explicit
instruction not to fabricate a recommendation just because a sensor
changed.

**Verified live** (Playwright, real backend): loaded the default
cycle (2204, `100 - full efficiency` / `NORMAL`), added `VS1 × 5`,
clicked Analyze - result: `20 - reduced efficiency` / `ANOMALY`
(score 0.543), reproducing the same real behaviour pattern documented
in Part 12 (a different starting cycle than Part 12's 1714 example,
same genuine model response). Reset correctly cleared changes and
results while keeping the loaded baseline. Also tested: multiple
sensors, an out-of-range cycle index client-side guard, and mobile
width (390px) - **two real layout bugs found and fixed** before
completion: the baseline-cycle caption text overflowed into an
unreadable narrow column, and the sensor-change row's 12-column grid
did not adapt below `lg` width. Both fixed with responsive
flex/grid classes and re-verified by screenshot.

**Commands:** same as Part 11 - `uvicorn backend.app.main:app --reload`
and `cd frontend && npm run dev`.

**Limitations:**
- The one-time "identity perturbation" call to populate baseline
  values costs one extra real backend round-trip per baseline-cycle
  load (a few seconds, per Part 10's documented per-cycle cost) -
  acceptable for this MVP, not optimized further.
- Perturbations are elementwise across a sensor's whole cycle (Part
  12's own limitation), not a localized change.
- No recommendation integration yet for simulated scenarios, as
  instructed.

## 21. Energy + Production What-If Simulator (Part 14)

**Core idea:** higher energy consumption is not automatically
inefficient - if production rises proportionally, that's normal.
`energy_intensity = energy / production` is the metric that actually
matters, and Part 14 lets the user compare it between a baseline and a
manual scenario.

**Critical data limitation, stated plainly:** the Tetouan dataset has
**no production data**. This is a manual what-if layer, not a real
historical comparison - every number comes from the user's own inputs,
never from the dataset or the Part 6 Random Forest model (which is
**not called, modified, or retrained** here).

**Where it lives:** a new card ("Energy + Production What-If") inside
the existing **Energy Intelligence** page, not a new sidebar route -
unlike Part 13's Machine Simulator, this directly extends existing
energy functionality rather than being a separate concern, and the
spec's own instructions for Part 14 (unlike Part 13) didn't ask for a
new nav item.

**Backend (follows existing architecture exactly):**
- `backend/app/core/config.py` - added `ENERGY_INTENSITY_WARNING_THRESHOLD_PERCENT
  = 5.0`, documented as a **prototype/demo threshold, not an industry
  standard, not derived from any dataset** (there is none to derive it
  from) - centralized here rather than buried in the frontend, per
  instruction.
- `backend/app/schemas/energy.py` - added `EnergyScenarioRequest`/`Response`.
- `backend/app/services/energy_service.py` - added
  `run_energy_production_scenario()`: validates inputs (production
  must be > 0, energy must be ≥ 0 - rejects the divide-by-zero case
  explicitly), computes both intensities and all three percent
  changes, classifies `NORMAL`/`WARNING` against the single threshold
  above, and writes a plain-language explanation. Pure arithmetic - no
  model inference.
- `backend/app/routes/energy.py` - added `POST /api/energy/simulate`,
  mounted on the existing energy router (same prefix convention as
  `/energy/summary`, `/history`, `/forecast`).

**Classification logic - not "energy increased = alert":** the rule
compares the **intensity** change, not the raw energy change, so
Part 14's TEST 2 (both +50%) correctly classifies as proportional
while TEST 3 (production +20%, energy +50%) correctly warns, and TEST 4
(production up, energy down) correctly does **not** warn - verified
numerically (see test results below), not just asserted.

**Frontend:** `components/energy-simulator/{EnergyScenarioForm,
EnergyScenarioResult}.jsx` + `hooks/useEnergyScenario.js`. Same
preview-vs-authoritative pattern as Part 13: baseline/scenario fields
show a **client-computed intensity preview** (one division, clearly
labelled "(preview)") as the user types, but the actual `NORMAL`/
`WARNING` classification, percentages, and explanation only ever come
from the real `POST /energy/simulate` response after "Analyze
Scenario" - never duplicated or recomputed differently in two places.

**Verified against the spec's exact 5 test cases (all passing, real
numbers):**

| Test | Production | Energy | Baseline→Scenario Intensity | Result |
|---|---|---|---|---|
| 1 (identical) | 1000→1000 | 10000→10000 | 10.0→10.0 | NORMAL |
| 2 (proportional) | 1000→1500 (+50%) | 10000→15000 (+50%) | 10.0→10.0 (0%) | NORMAL/PROPORTIONAL |
| 3 (disproportionate) | 1000→1200 (+20%) | 10000→15000 (+50%) | 10.0→12.5 (+25%) | **ENERGY EFFICIENCY WARNING** |
| 4 (production up, energy down) | 1000→1200 | 10000→9500 | 10.0→7.92 (improved) | NORMAL (no false warning) |
| 5 (invalid) | 0, negative | any | - | 400, rejected, no divide-by-zero |

**Testing:** `backend/tests/test_energy_simulation.py` (35 checks,
including all 5 spec tests plus threshold/note presence checks) - all
passing. Live Playwright screenshot testing on the actual running app
reproduced all of the above exactly, plus reset and mobile width
(390px) - **zero layout bugs this time**, since the same responsive
patterns fixed in Part 13 (`lg:grid-cols-2`, stacked panels) were used
from the start.

**Regression:** `backend/tests/test_api.py` (43), `test_simulation.py`
(17, Part 12), `ml/machine_health/test_simulate.py` (47, Part 12),
`ml/recommendation/tests.py` (14) all re-run - **zero failures**, zero
change in output. Raw Tetouan data MD5 unchanged; all three
`models/*.joblib` files untouched (original timestamps).

**Commands:**
```powershell
python backend/tests/test_energy_simulation.py
```

**Limitations:**
- Entirely a manual what-if layer - there is no real production
  dataset behind it, by design, and every response says so.
- The 5% threshold is a single global constant for this prototype, not
  tuned per scenario type or industry.
- No historical log of past what-if scenarios - each analysis is
  stateless, matching Part 12/13's own simulation pattern.

## 22. Unified Dashboard Integration (Part 15)

**Objective:** turn Overview into the main command center, surfacing
existing energy/machine intelligence, alerts, recommendations, and
both what-if simulators (Parts 13/14) from one screen - integration
only, no new ML models, no new backend endpoints (all existing APIs
reused), no fabricated data.

**Overview page rebuilt** (`frontend/src/pages/Overview.jsx`) around
6 real sections:
1. **5 KPI cards** - Current Energy, Energy Forecast, Machine Status,
   Active Alerts, Recommendations - all from the existing
   `/api/dashboard/summary` and `/api/alerts` responses.
2. **Industrial Intelligence Flow** - a new, purely presentational
   diagram (`components/overview/IntelligenceFlow.jsx`) showing the
   real pipeline (Data → Energy + Machine Intelligence → Anomaly/
   Efficiency Analysis → Decision Engine → Alerts + Recommendations →
   Operator Action). No API calls, no invented metrics.
3. **Energy Consumption** chart (reused `EnergyHistoryChart`) with a
   "View Energy Intelligence" link.
4. **Machine Intelligence** + **Active Alerts** side by side - the
   alerts panel reuses a newly-extracted `AlertRow` component (see
   below) so Overview and the Alerts page render identical real alert
   data from one implementation, not two.
5. **AI Recommendations** (reused `RecommendationList`) with a
   "View All Recommendations" link.
6. **What-If Scenarios** - two new compact navigation cards
   (`components/overview/WhatIfAccessCards.jsx`) linking to
   `/machine-simulator` and `/energy` - descriptions only, no
   simulator logic duplicated on Overview.

**Small, backward-compatible refactor:** `Alerts.jsx`'s inline alert
row JSX was extracted into `components/alerts/AlertRow.jsx` (section
16's "avoid unnecessary duplication" instruction) - the Alerts page's
own output is visually unchanged, verified by rebuilding and
re-screenshotting it.

**Sidebar** (`components/layout/Sidebar.jsx`) - grouped under
**Monitor** / **Simulate** / **Decide** section labels, per section
12's suggestion. No route was added, removed, or renamed; the active-
link highlighting and mobile drawer behaviour from Part 11 are
unchanged.

**No backend changes.** Every section is built from existing endpoints
(`/dashboard/summary`, `/alerts`, `/energy/history`,
`/recommendations`). Section 17's instruction to only add a new
endpoint if genuinely necessary did not apply here.

**Data honesty preserved:** the Data Context card now also notes that
the Energy + Production What-If (Part 14) uses manual inputs only,
alongside the existing Tetouan/hydraulic provenance notes - no
wording anywhere calls either dataset "live factory" or "real-time
industrial" data.

**Regression testing - live, not assumed.** After the Overview/
Sidebar/Alerts changes, re-ran: the full Part 13 Machine What-If
regression (`VS1 × 5` on the real default cycle - reproduced the
identical `100 → 20`, `NORMAL → ANOMALY`, score `0.543` result) and
the full Part 14 regression (Test C: `1000→1200` production,
`10000→15000` energy - reproduced the identical `+20%` / `+50%` /
`+25%`, `ENERGY EFFICIENCY WARNING` result) - both via Playwright
against the live app, confirming pixel-for-pixel identical backend
behaviour, not just "the code looks unchanged." All five backend test
suites (`test_api.py` 43, `test_simulation.py` 17, 
`test_energy_simulation.py` 35, `ml/machine_health/test_simulate.py`
47, `ml/recommendation/tests.py` 14) re-run with zero failures. Raw
Tetouan data MD5 and all three `models/*.joblib` files unchanged.

**Commands:** unchanged from Part 11 -
`uvicorn backend.app.main:app --reload` and `cd frontend && npm run dev`.

**Limitations:**
- The Intelligence Flow diagram is a static illustration of the real
  pipeline, not a live-updating data-flow visualization.
- "Recommendations" KPI count reflects only the capped
  `top_recommendations` list already returned by `/dashboard/summary`
  (currently up to 5), not a separate full count.
- Sidebar grouping is visual only - no new permissions, roles, or
  route changes.

---

## 23. Final Validation & Demo Readiness (Part 16)

**Objective:** make the existing system stable, tested and honest for a
live demonstration. No new models, no retraining, no dataset changes, no
new features, no dependency upgrades.

**Real bugs found and fixed:**
1. **Slow anomaly requests.** Every anomaly lookup re-extracted features
   for all 2205 cycles, so `/api/alerts`, `/api/dashboard/summary` and
   `/api/recommendations` took ~3-5 s each, and the Overview's three
   parallel calls took ~30 s on a cold server (the frontend timeout is
   15 s). `machine_service` now caches the Part 8 results (same function,
   same outputs, thread-safe), `dashboard_service` reuses the cached
   scores, and the API warms its caches at startup. Warm requests now
   take milliseconds.
2. **Zero baseline energy returned HTTP 500.** `POST /api/energy/simulate`
   divided by zero when `baseline_energy = 0`. It now returns a clear 400
   (a zero baseline makes the comparison undefined). Zero *scenario*
   energy remains valid. Regression tests added.

**Startup note:** the backend pre-computes its caches at startup, which
takes roughly 30 seconds. Wait for `GET /api/health` to respond (and for
"Application startup complete" in the log) before opening the dashboard.

**How to run the tests:**
```
pytest -q
pytest -q ml/recommendation/tests.py ml/machine_health/test_simulate.py
```
(the second command covers suites that pytest does not collect by
default). Install `pytest` and `httpx` first if they are not present.

**Data-integrity audit:** searched backend, ML and frontend code for
mock/fake/random data, hardcoded predictions, stray `fetch` calls and
external AI/LLM calls. None found: health, anomaly and recommendation
outputs all come from the trained models / rule engine; the only fixed
values in the UI are navigation labels, pipeline diagram text and the
clearly-labelled default What-If inputs.

### Current limitations

The current prototype uses public datasets and simulated What-If inputs.
It is not yet connected to live industrial IoT/SCADA systems.

- Energy data is **city-level** electricity consumption (UCI Tetouan
  City), not factory production data.
- Machine data is a **controlled public hydraulic test-rig** dataset
  (UCI Condition Monitoring of Hydraulic Systems). Very high accuracy on
  it does not imply the same accuracy on real industrial equipment.
- Production values in the Energy What-If are **manual demo inputs**,
  and its 5% energy-intensity threshold is a prototype value, not an
  industry standard.
- Anomaly scores measure deviation from learned normal behaviour. They
  are not failure probabilities and not Remaining Useful Life.
- No claims are made about guaranteed downtime reduction or cost savings.

### Future scope

- Live IoT / SCADA data ingestion
- Remaining Useful Life estimation (requires run-to-failure data)
- Edge deployment
- Multi-factory control
- Multi-industry scaling

---

## 24. Machine What-If Recommendation Integration (Part 18)

The **AI Recommendations** panel at the bottom of the Machine What-If Simulator
(`/machine-simulator`) now shows real, scenario-specific recommendations instead
of a placeholder.

**How simulation results reach the existing engine.** No second engine and no new
rules were added. `POST /api/machines/simulate` runs the simulation exactly as
before (Part 7 classifier + Part 8 anomaly detector on the modified sensors). The
backend (`simulation_service.build_scenario_recommendations`) then passes the
**simulated** health and anomaly outputs - not the baseline - to the existing Part 9
`generate_recommendations()`. All decision rules still live only in
`ml/recommendation/`.

**API change (additive, backward compatible).** The simulate response keeps every
existing field and gains three optional ones: `recommendations` (same item schema as
`/api/recommendations`), `recommendations_error`, and `recommendation_note`. If the
engine fails, the simulation result is still returned with `recommendations: null`
and an error message, and the panel shows an error state.

**What the user sees.** After **Analyze Scenario**: the evaluated scenario (changed
sensors and the simulated outputs used), each recommendation (priority, category,
title, suggested action, reason, evidence incl. the sensor deviations, rule
confidence, limitations), sorted by priority; a clear "no action required" state
when the engine finds no abnormal signal; and a disclaimer. Every new analysis
clears the previous scenario first, so stale recommendations are never shown - not
while loading, after a failed analysis, or after **Reset Scenario**.

**Examples (real model + rule-engine output on cycle 1714; not hardcoded):**
VS1 x5 -> reduced efficiency / WARNING -> LOW preventive maintenance (inspect
mechanical condition); VS1 x5 plus TS2 +30 -> ANOMALY -> MEDIUM machine inspection
(mechanical and cooling areas); VS1 x1 (unchanged) -> continue monitoring.

**Running the tests.**
```
pytest -q backend/tests/test_scenario_recommendations.py   # Part 18, real assertions
pytest -q
pytest -q ml/recommendation/tests.py ml/machine_health/test_simulate.py
```
**Important:** the older suites (`backend/tests/test_api.py`,
`test_energy_simulation.py`, `test_simulation.py`, `ml/recommendation/tests.py`,
`ml/machine_health/test_simulate.py`) record results with a `check()` helper and do
not use `assert`, so under `pytest` they only prove the code runs without raising -
a failed check does not fail pytest. To actually verify them, run each as a script
(the exit code reflects failures):
```
python -m backend.tests.test_api
python -m backend.tests.test_energy_simulation
python -m backend.tests.test_simulation
python -m ml.recommendation.tests
python -m ml.machine_health.test_simulate
```

**Known limitations.**
- The engine's *persistence* rule uses the real anomaly history of a real cycle. A
  what-if scenario has none, so persistence is intentionally not applied and
  recommendations come from the simulated health and anomaly outputs only.
- The engine only reflects what Parts 7/8 detect: a sensor change the models do not
  flag produces "continue monitoring", and a flagged change is an anomaly, not a
  confirmed failure.
- Results are hypothetical what-if outputs on a public test-rig dataset, not a
  diagnosis of a real machine, and nothing guarantees prevented downtime.
- Editing the sensor-change rows after an analysis does not clear the displayed
  result until **Analyze Scenario** or **Reset Scenario** is used again.
