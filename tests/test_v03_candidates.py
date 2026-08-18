"""Focused tests for the v0.3 precursor-calibration candidate control
profiles (aeroguard_dataset/control_profiles_v03_candidates.py). These
candidates are calibration-only (outputs/v03_calibration/), not part of
the validated v0.1/v0.2 dataset -- these tests only check the candidates
are well-formed and actually simulate without error, not that they
achieve any particular precursor outcome (that's what calibration
measures empirically).
"""
import dataclasses
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard.aircraft import Aircraft

from aeroguard_dataset.config import GenerationConfig, RegimeControlConfig
from aeroguard_dataset.control_profiles_v03_candidates import V03_CANDIDATES
from aeroguard_dataset.dataset_builder import build_dataset


def test_five_candidates_defined():
    assert len(V03_CANDIDATES) == 5


def test_candidates_are_valid_regime_configs():
    for name, cfg in V03_CANDIDATES.items():
        assert isinstance(cfg, RegimeControlConfig), name
        assert cfg.elevator.magnitude_min > 0
        assert cfg.elevator.magnitude_max >= cfg.elevator.magnitude_min
        assert cfg.elevator.rise_s_min > 0
        assert cfg.elevator.rise_s_max >= cfg.elevator.rise_s_min
        assert cfg.elevator.hold_s_max >= cfg.elevator.hold_s_min >= 0
        assert cfg.elevator.fall_s_max >= cfg.elevator.fall_s_min > 0


def test_candidates_do_not_modify_v2_config():
    """The candidates module must not mutate the shared, validated v0.2
    NEAR_BOUNDARY_CONTROL_CONFIG it imports dataclasses/specs from."""
    from aeroguard_dataset.config import NEAR_BOUNDARY_CONTROL_CONFIG
    assert NEAR_BOUNDARY_CONTROL_CONFIG.elevator.magnitude_min == 0.12
    assert NEAR_BOUNDARY_CONTROL_CONFIG.elevator.magnitude_max == 0.20
    assert NEAR_BOUNDARY_CONTROL_CONFIG.elevator.rise_s_min == 0.4
    assert NEAR_BOUNDARY_CONTROL_CONFIG.elevator.rise_s_max == 1.0


def test_each_candidate_simulates_without_error():
    """Smoke test: a tiny (n=3) batch per candidate must generate cleanly
    through the real (unmodified) build_dataset/simulate_trajectory path."""
    aircraft = Aircraft()
    for name, cand_cfg in V03_CANDIDATES.items():
        cfg = dataclasses.replace(
            GenerationConfig(),
            seed=1,
            n_trajectories=3,
            dataset_version=f"test-{name}",
            regime_proportions={"near_boundary": 1.0},
        )
        raw_df, processed_df, metadata_df, _ = build_dataset(
            cfg, verbose=False, regime_control_configs={"near_boundary": cand_cfg}
        )
        assert len(metadata_df) == 3
        assert metadata_df["generation_mode"].eq("near_boundary").all()
        assert metadata_df["n_sanity_issues"].eq(0).all(), name
        assert raw_df["V"].gt(0).all()
