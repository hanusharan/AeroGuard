"""AeroGuard Phase 3 (Items 28-32): AoA baseline, instantaneous-state model and
temporal-vs-instantaneous comparison.

Everything here is governed by the locked protocol ``experiments/phase3/PROTOCOL.md``
(v0.2, SHA-256 below). This package only ADDS code: no historical module under
``ml/``, ``aeroguard/``, ``aeroguard_dataset/`` or ``scripts/`` is modified, and
existing implementations are imported and reused unchanged wherever the protocol
allows it (``ml.baselines.AoAThresholdRule``, ``ml.temporal_experiment``
helpers, ``ml.events``, ``ml.evaluation``).

Modules
    rules          signed / two-sided AoA rule wrappers (fail closed on invalid input)
                   and the stall-margin equivalence helpers (Items 28, 30)
    population     split-restricted loaders, row keys, common-population checks,
                   data-integrity checks (Item 29)
    instantaneous  the 8-feature instantaneous-state model (Item 31)
    analysis       negative-alpha investigation, metrics, paired trajectory
                   bootstrap (Items 28, 29, 32)

Importing this package does not read any data and imports no heavy dependency.
All results computed with this code on the regenerated v0.3 copy are labelled
"regenerated data" and are never described as independent replication.
"""

# --- protocol lock (PROTOCOL.md section 21 / approval record) -----------------------
PROTOCOL_SHA256 = "da9c62fa1d41beef6ae53aabaedda0eecb623fa5ee06c237c21191011d2a97f2"
PROTOCOL_RELPATH = "experiments/phase3/PROTOCOL.md"

# --- protected frozen model (PROTOCOL.md section 9.1) --------------------------------
FROZEN_MODEL_SHA256 = "707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3"
FROZEN_MODEL_RELPATH = "outputs/ml_v03/models/primary_model_D_1s.joblib"
FROZEN_METRICS_RELPATH = "outputs/ml_v03/metrics/primary_model_metrics.json"
BASELINE_MANIFEST_RELPATH = "baselines/v0.3.sha256"

# --- regenerated-data file hashes, relative to the tree's data/ directory (PROTOCOL.md section 3)
DATA_FILE_SHA256 = {
    "processed/processed_dataset_v3.parquet": "a533f9e940c16ab8bfddf3a4ca98d4326a17655247274142d98280ed03b4a38e",
    "ml_temporal_v03/temporal_train.parquet": "1a39472881280e084f3cab5d94fa4c80382d65a7075df59cd7a45fd4d5af4b43",
    "ml_temporal_v03/temporal_val.parquet": "9416fc8005b206eefbcdbeeb0d043a45036e8b2d6251ae3850b176765565a0e0",
    "ml_temporal_v03/temporal_test.parquet": "c03634b4cc793c57bbe065e710a4a98bfe2bf69fdf5a55beb56a1c0ba33241b8",
}

# --- fixed experimental constants (PROTOCOL.md sections 5, 7, 8, 9, 11) --------------
DT = 0.01                       # s, uniform timestep (generation_config_v3.json)
HORIZON_S = 5.0                 # label horizon, future_stall_5s
HORIZON_STEPS = 500             # round(HORIZON_S / DT)
WINDOW_S = 1.0                  # history window defining the common population
WARMUP_STEPS = 100              # round(WINDOW_S / DT): rows without a full window
A_PEAK_RAD = 0.28044009791924895  # resolved_stall_boundary.alpha_at_cl_peak_rad
MODEL_SEED = 20260817           # ml.config.ML_SEED (forest random_state)
BOOTSTRAP_B = 1000              # D15
BOOTSTRAP_SEED = 20261013       # D15 (chosen before any Phase 3 scoring)
BOOTSTRAP_INTERVAL_PCT = (2.5, 97.5)
