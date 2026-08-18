"""AeroGuard Stage 3: the ML early-warning experiment.

Builds on top of the FROZEN, finalized Dataset v0.2
(data/*_v2.* files) and does not modify it, the physics engine
(aeroguard/), or the dataset-generation pipeline (aeroguard_dataset/).

Submodules:
    config       -- paths, feature sets, seeds, all experiment parameters
    data          -- loading data/*_v2.* and verifying split integrity
    features       -- feature-set definitions and leakage guards
    baselines       -- AoA-threshold and trend rule-based warnings
    models           -- Logistic Regression / Random Forest / HistGB builders
    training          -- TRAIN/VAL fitting, tuning, threshold selection
    evaluation         -- classification metrics and curves
    events              -- event-level lead-time and false-alarm analysis
    ablation             -- feature-set ablation (A/B/C) on one model family
"""
