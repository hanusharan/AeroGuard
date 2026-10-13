"""AeroGuard Item 33: control-input ablation.

Governed by the locked protocol ``experiments/items33_42/item33/PROTOCOL.md`` (v0.3, SHA-256
below; lock record ``PROTOCOL_LOCK.json``). This package only ADDS code. Nothing under ``ml/``,
``phase3/``, ``aeroguard/``, ``aeroguard_dataset/`` or ``scripts/`` is modified; existing
implementations are imported and reused unchanged wherever the protocol allows it.

Importing this package reads no data and loads no model. Every result computed with this code
on the regenerated v0.3 copy is a controlled re-evaluation of previously exposed data. It is not
blind, not independent replication, and says nothing about real aircraft.

Modules
    conditions      declarative feature-ablation conditions and fail-closed validation
    guards          protocol lock, output-path and exclusive-write guards
    population      split-restricted loading, row identity, population and split checks
    fitting         seeded forest builder, per-condition fit, threshold selection, single-shot ledger
    bootstrap       paired trajectory bootstrap (seed-averaged and regime-stratified)
    summary         seed-panel summaries and the permitted evidence wording
    operating_point validation-only matched operating point
    masking         inference-time input replacement for the frozen model (separate family)
    register        comparison register and machine-readable row schema
    report          report generated only from machine-readable results
    driver          gated execution (gates are NOT passed by importing or testing this package)
"""

# --- protocol lock (PROTOCOL_LOCK.json) -------------------------------------------------
PROTOCOL_RELPATH = "experiments/items33_42/item33/PROTOCOL.md"
LOCK_RELPATH = "experiments/items33_42/item33/PROTOCOL_LOCK.json"
PROTOCOL_SHA256 = "742f55a9cc4e5da0474de84bf40cc6ffcb63a4ed46f12c3d2536ac57b21c4dc7"

# --- protected artifacts ----------------------------------------------------------------------
FROZEN_MODEL_SHA256 = "707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3"
FROZEN_MODEL_RELPATH = "outputs/ml_v03/models/primary_model_D_1s.joblib"
FROZEN_METRICS_RELPATH = "outputs/ml_v03/metrics/primary_model_metrics.json"
PHASE3_PROTOCOL_SHA256 = "da9c62fa1d41beef6ae53aabaedda0eecb623fa5ee06c237c21191011d2a97f2"
PHASE3_PROTOCOL_RELPATH = "experiments/phase3/PROTOCOL.md"
BASELINE_MANIFEST_RELPATH = "baselines/v0.3.sha256"
FROZEN_THRESHOLD = 0.8585534589255494   # strict ">" (frozen model record)

# Paths below which Item 33 never writes (relative to the tree root).
PROTECTED_RELPATHS = (
    "outputs/ml_v03", "outputs/phase3", "outputs/analysis_v11", "outputs/ml_baseline", "outputs/ml_temporal",
    "outputs/final", "experiments/phase3", "paper", "baselines", "data", "aeroguard", "aeroguard_dataset", "ml", "phase3",
    FROZEN_MODEL_RELPATH,
)

# --- output layout (PROTOCOL.md section 13) -------------------------------------------------------
OUTPUT_ROOT_RELPATH = "outputs/items33_42/item33"

# --- regenerated-data file hashes, relative to the tree's data/ directory (PROTOCOL.md section 7)
DATA_FILE_SHA256 = {
    "processed/processed_dataset_v3.parquet": "a533f9e940c16ab8bfddf3a4ca98d4326a17655247274142d98280ed03b4a38e",
    "ml_temporal_v03/temporal_train.parquet": "1a39472881280e084f3cab5d94fa4c80382d65a7075df59cd7a45fd4d5af4b43",
    "ml_temporal_v03/temporal_val.parquet": "9416fc8005b206eefbcdbeeb0d043a45036e8b2d6251ae3850b176765565a0e0",
    "ml_temporal_v03/temporal_test.parquet": "c03634b4cc793c57bbe065e710a4a98bfe2bf69fdf5a55beb56a1c0ba33241b8",
}
SPLIT_MANIFEST_RELPATH = "data/splits/split_manifest_v3.csv"
SPLIT_MANIFEST_SHA256 = "d7d6eb825d10c6acd870e4c418f2a552ec82dc60e5e12e723f12ada11e4202fb"
METADATA_RELPATH = "data/metadata/trajectory_metadata_v3.csv"
METADATA_SHA256 = "924e0df6ccb303a264579c3f9ba6a5c84e69e0d14bbb58feaa6e0b66abdde05d"
PHASE3_ROW_KEYS_SHA256 = "893c7d30d5b0c1a4f268242a4b6c74bded00071a06476c9ef6ead22bc0420f62"      # row_keys.npz (scratch)
PHASE3_FROZEN_SCORES_SHA256 = "37801481115a4632590df95d1f5f88ac487c28e8c452d5a6540431920d61f6e9"  # scores_frozen_temporal.npy

# --- fixed experimental constants (PROTOCOL.md sections 5-10) ---------------------------------------
DT = 0.01
WINDOW_S = 1.0
SEEDS = (20260817, 20261101, 20261102, 20261103, 20261104)   # forest random_state; matched across conditions
PRIMARY_SEED = 20260817                                       # the frozen model's forest seed
BOOTSTRAP_B = 1000
BOOTSTRAP_SEED = 20261013
BOOTSTRAP_INTERVAL_PCT = (2.5, 97.5)
N_PRIMARY_CONTRASTS = 2
BONFERRONI_INTERVAL_PCT = (2.5 / N_PRIMARY_CONTRASTS, 100.0 - 2.5 / N_PRIMARY_CONTRASTS)   # (1.25, 98.75)
MASK_SEEDS = (20261201, 20261202, 20261203, 20261204, 20261205)
