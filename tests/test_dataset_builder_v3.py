"""Focused tests for aeroguard_dataset/dataset_builder_v3.py: the v0.3
full-dataset orchestrator that dispatches "gradual_approach_v3" to the
locked Candidate D v3 profile builder while "normal"/"stall" go through
the unmodified, standard build_control_profile()/NORMAL_CONTROL_CONFIG/
STALL_CONTROL_CONFIG -- same as v0.1/v0.2.
"""
import dataclasses
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from aeroguard_dataset.config import GenerationConfig
from aeroguard_dataset.dataset_builder_v3 import (
    GRADUAL_APPROACH_V3_REGIME_NAME,
    assign_regime_list,
    build_dataset_v3,
    generate_one_trajectory_v3,
)


def test_assign_regime_list_exact_counts():
    counts = {"normal": 5, "stall": 3, GRADUAL_APPROACH_V3_REGIME_NAME: 2}
    rng = np.random.default_rng(0)
    modes = assign_regime_list(counts, rng)
    assert len(modes) == 10
    assert modes.count("normal") == 5
    assert modes.count("stall") == 3
    assert modes.count(GRADUAL_APPROACH_V3_REGIME_NAME) == 2


def test_assign_regime_list_shuffles_not_blocked():
    """Regression guard: modes must be interleaved, not id-ordered blocks
    (same convention as dataset_builder.assign_regimes)."""
    counts = {"normal": 20, "stall": 20, GRADUAL_APPROACH_V3_REGIME_NAME: 20}
    rng = np.random.default_rng(0)
    modes = assign_regime_list(counts, rng)
    # if it were still blocked, the first 20 would all be identical
    assert len(set(modes[:20])) > 1


def test_unknown_regime_raises():
    from aeroguard.aircraft import Aircraft
    from aeroguard_dataset.events import resolve_stall_boundary

    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    cfg = GenerationConfig()
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        generate_one_trajectory_v3(0, "not_a_real_regime", rng, aircraft, cfg, boundary, v_floor=10.0, gamma_max_rad=0.785)


def test_build_dataset_v3_rejects_mismatched_counts():
    cfg = dataclasses.replace(GenerationConfig(), n_trajectories=10)
    with pytest.raises(AssertionError):
        build_dataset_v3(cfg, {"normal": 3, "stall": 3, GRADUAL_APPROACH_V3_REGIME_NAME: 3}, verbose=False)  # sums to 9, not 10


def test_build_dataset_v3_small_batch_end_to_end():
    cfg = dataclasses.replace(GenerationConfig(), seed=7, n_trajectories=6, dataset_version="test-v3-small")
    counts = {"normal": 2, "stall": 2, GRADUAL_APPROACH_V3_REGIME_NAME: 2}
    raw_df, processed_df, metadata_df, v0_check = build_dataset_v3(cfg, counts, verbose=False)
    assert len(metadata_df) == 6
    assert set(metadata_df["generation_mode"].unique()) <= set(counts.keys())
    assert metadata_df["generation_mode"].value_counts().to_dict() == counts
    assert (raw_df["altitude"] > 0).all()
    assert v0_check["v0_min_above_vstall"]
    assert metadata_df["trajectory_id"].is_unique
