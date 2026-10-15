"""AeroGuard Phase 4 (Items 43-53): generalisation across aircraft configurations,
abstention, uncertainty under shift, and a second simulator (JSBSim).

Governed by ``experiments/phase4/PROTOCOL.md`` (SHA-256 below). This package only
ADDS code: nothing under ``aeroguard/``, ``aeroguard_dataset/``, ``ml/`` or
``scripts/`` is modified, and existing implementations are imported unchanged
wherever the protocol allows.

Modules
    configs      parameter ranges, Sobol configuration design, OOD construction (Item 43)
    sim          trim and trajectory simulation at a configuration's air density,
                 pilot-equivalent control scaling, per-configuration datasets (Item 43)
    panel        derivative and 1 s temporal-window features, usable rows (reuses ml/)
    models       feature sets, RF fitting, thresholds, rules, frozen-model scoring
    metrics      row, event, false-warning and coverage metrics; bootstrap
    uncertainty  uncertainty scores, abstention, split conformal (Items 46-47)
    jsbsim_sim   JSBSim feasibility checks and trajectory generation (Items 48-49)
    published    comparison of the model with published reference values (Item 50)

Importing this package reads no data.
"""

PROTOCOL_RELPATH = "experiments/phase4/PROTOCOL.md"
PROTOCOL_SHA256 = "54fd8d5442d0d6d29119dd2ddaa0bfb9ac141946bc87b0b69957a71b6c035f2f"

FROZEN_MODEL_RELPATH = "outputs/ml_v03/models/primary_model_D_1s.joblib"
FROZEN_MODEL_SHA256 = "707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3"
FROZEN_THRESHOLD = 0.8585534589255494

DATA_SEEDS = {"D0": 20261015, "D1": 20261016}
MODEL_SEEDS = (20260817, 20261101, 20261102, 20261103, 20261104)
ROBUST_MODEL_SEEDS = MODEL_SEEDS[:3]
import os as _os
BOOT_B, BOOT_SEED = int(_os.environ.get("P4_SMOKE_B", 1000)), 20261015
DT = 0.01
HORIZON_S = 5.0
TRAIN_STRIDE = 5          # every 5th usable row (0.05 s) for fitting and thresholds
