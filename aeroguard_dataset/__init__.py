"""AeroGuard Stage 2: trajectory-generation and dataset-auditing pipeline.

This package builds on top of the validated physics engine in
``aeroguard/`` and the corrected numerical trim solver in
``scripts/simulate.py``. It does not modify either.

Submodules:
    paths              -- import bootstrapping (sys.path) and shared path constants
    config              -- all generation parameters in one documented place
    events              -- stall / post-stall ("post-peak CL") event detection
    control_profiles    -- smooth, bounded control-perturbation generation
    trajectory_sim      -- single-trajectory RK4 simulation with validity-envelope enforcement
    features            -- causal derived-feature computation
    labeling            -- causal future_stall_5s label computation
    dataset_builder      -- orchestrates generation of the full trajectory dataset
    splitting            -- deterministic trajectory-level train/val/test split
    audit                -- dataset-quality audit report
    visualize             -- audit plots
"""
