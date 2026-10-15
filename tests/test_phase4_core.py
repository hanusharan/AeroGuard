"""Phase 4 (Items 43-53): synthetic and known-answer tests. No research data are read."""

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

import aeroguard_dataset.paths  # noqa: F401
from aeroguard.aircraft import Aircraft
from aeroguard_dataset.trajectory_sim import simulate_trajectory
from simulate import trim_level_flight

from phase4 import configs as C
from phase4 import metrics as M
from phase4 import sim as S
from phase4 import uncertainty as U
from phase4.panel import FEATURES_D, FEATURES_D_NOSM, FEATURES_XD, stride_rows


# ------------------------------------------------------------------ Item 43: configurations
def test_design_is_fixed_and_complete():
    cf = C.design()
    ids = [c["config_id"] for c in cf]
    assert ids[0] == "C00" and len(ids) == 23 and len(set(ids)) == 23
    assert sum(c["set"] == "TRAIN" for c in cf) == 12
    assert sum(c["set"] == "IDH" for c in cf) == 4
    assert sum(c["set"] == "OOD" for c in cf) == 6
    assert cf == C.design()  # deterministic


def test_core_box_and_ranges():
    for c in C.design():
        for p in C.PARAMS:
            lo, hi, kind = C.RANGES[p]
            v = c[p] / (C.base_value(p) if kind == "rel" else 1.0)
            assert lo - 1e-9 <= v <= hi + 1e-9, (c["config_id"], p)
            if c["set"] in ("TRAIN", "IDH"):
                assert C.CORE_LO - 1e-12 <= c[f"u_{p}"] <= C.CORE_HI + 1e-12


def test_ood_groups_are_in_outer_band():
    cf = {c["config_id"]: c for c in C.design()}
    for cid, grp in C.OOD_GROUPS.items():
        names = C.PARAMS if grp == "all" else list(grp)
        for p in names:
            u = cf[cid][f"u_{p}"]
            assert u < C.CORE_LO or u > C.CORE_HI, (cid, p, u)


def test_baseline_config_reproduces_v03_aircraft():
    ac = C.make_aircraft(C.baseline_config())
    assert ac == Aircraft()


def test_partitions_disjoint_and_cover_core():
    cf = C.design()
    for name in ("P0", "P1", "P2"):
        p = C.partition(cf, name)
        assert len(p["TRAIN"]) == 12 and len(p["IDH"]) == 4
        assert not set(p["TRAIN"]) & set(p["IDH"])
        assert set(p["TRAIN"]) | set(p["IDH"]) == {c["config_id"] for c in cf if c["set"] in ("TRAIN", "IDH")}
    assert C.partition(cf, "P1") != C.partition(cf, "P0")


def test_unfamiliarity_zero_for_training_configs():
    cf = C.design()
    tr = C.partition(cf, "P0")["TRAIN"]
    un = C.unfamiliarity(cf, tr)
    assert all(un[t]["d_ood"] == 0.0 for t in tr)
    assert un["O06"]["n_params_outside_train_range"] == 15


# ------------------------------------------------------------------ simulation at configurable density
def test_trim_and_sim_identical_to_originals_at_sea_level():
    ac = Aircraft()
    a, t, e = trim_level_flight(ac, 42.0)
    a2, t2, e2, _ = S.trim_level_flight_rho(ac, 42.0, 1.225)
    assert (a, t, e) == (a2, t2, e2)
    prof = S.build_profile("gradual_approach_v3", np.random.default_rng(5), a, t, e, 20.0)
    r1 = simulate_trajectory("x", ac, prof, 42.0, 0.0, a, 900.0, 0.0, 20.0, 0.01, 13.07, np.radians(45))
    r2 = S.simulate_trajectory_rho("x", ac, prof, 42.0, 0.0, a, 900.0, 0.0, 20.0, 0.01, 13.07, np.radians(45), 1.225)
    for k in ("t", "V", "alpha", "theta", "gamma", "altitude", "pitch_rate", "elevator", "throttle"):
        assert np.array_equal(getattr(r1, k), getattr(r2, k)), k
    assert r1.termination_reason == r2.termination_reason


def test_lower_density_needs_more_alpha():
    ac = Aircraft()
    assert S.trim_level_flight_rho(ac, 45.0, 0.95)[0] > S.trim_level_flight_rho(ac, 45.0, 1.225)[0]


def test_control_scale_is_one_for_baseline_and_scales_pulses():
    env = S.config_envelope(C.baseline_config())
    assert env["elevator_scale"] == pytest.approx(1.0, abs=1e-12)
    prof = S.build_profile("stall", np.random.default_rng(1), 0.05, 0.4, 0.016, 20.0)
    sc = S.scale_profile(prof, 2.0)
    assert [p.magnitude * 2 for p in prof.elevator_pulses] == [p.magnitude for p in sc.elevator_pulses]
    assert [p.start for p in prof.elevator_pulses] == [p.start for p in sc.elevator_pulses]
    assert sc.throttle_pulses == prof.throttle_pulses


def test_generate_config_small_is_deterministic():
    cfg = C.design()[3]
    n = {"normal": 1, "stall": 1, "gradual_approach_v3": 1}
    f1, m1, _ = S.generate_config(cfg, 3, 123, n)
    f2, m2, _ = S.generate_config(cfg, 3, 123, n)
    pd.testing.assert_frame_equal(m1, m2)
    for a, b in zip(f1, f2):
        pd.testing.assert_frame_equal(a, b)
    assert set(m1["split"]) <= {"train", "val", "test"}


# ------------------------------------------------------------------ feature sets
def test_feature_sets():
    assert len(FEATURES_D) == 23 and "stall_margin" in FEATURES_D
    assert len(FEATURES_D_NOSM) == 22 and "stall_margin" not in FEATURES_D_NOSM
    assert len(FEATURES_XD) == 20 and not {"elevator", "throttle", "elevator_change_1s"} & set(FEATURES_XD)


def test_stride_rows_per_trajectory():
    df = pd.DataFrame({"trajectory_id": ["a"] * 7 + ["b"] * 3, "time": list(range(7)) + list(range(3))})
    out = stride_rows(df, 3)
    assert out["time"].tolist() == [0, 3, 6, 0]


# ------------------------------------------------------------------ metrics
def test_weighted_ap_matches_sklearn():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500); s = np.round(rng.random(500), 2)  # ties on purpose
    w = rng.integers(0, 4, 500).astype(float)
    ss = M.SortedScores(y, s)
    assert ss.ap() == pytest.approx(average_precision_score(y, s), abs=1e-12)
    assert ss.ap(w) == pytest.approx(average_precision_score(y, s, sample_weight=w), abs=1e-12)


def test_weighted_median():
    assert M.weighted_median([1, 2, 3], [1, 1, 1]) == 2
    assert M.weighted_median([1, 2, 3, 4], [1, 1, 1, 1]) == 2.5
    assert M.weighted_median([1, 2, 3], [0, 0, 2]) == 3


def test_ece_perfect_calibration_is_zero():
    p = np.repeat([0.05, 0.55], 1000); y = np.r_[np.r_[np.ones(50), np.zeros(950)], np.r_[np.ones(550), np.zeros(450)]]
    assert M.ece(y, p) == pytest.approx(0.0, abs=1e-12)


def _toy_population():
    t = np.round(np.arange(0, 10, 0.01), 2)
    unsafe = (t >= 8.0) & (t < 8.5)
    y = ((t >= 3.0) & (t < 8.0)).astype(int)
    score = np.where((t >= 5.0) & (t < 9.0), 0.9, 0.1)
    return pd.DataFrame({"trajectory_id": "a", "time": t, "is_unsafe": unsafe, "future_stall_5s": y}), score


def test_event_lead_time_known_answer():
    df, score = _toy_population()
    r = M.evaluate(df, score, 0.5, boot=False)
    assert r["event"]["n_events"] == 1 and r["event"]["event_recall"] == 1.0
    assert r["event"]["median_lead_s"] == pytest.approx(3.0, abs=1e-9)


# ------------------------------------------------------------------ uncertainty
def test_conformal_marginal_coverage_on_exchangeable_data():
    rng = np.random.default_rng(1)
    p = rng.random(20000); y = (rng.random(20000) < p).astype(int)
    q = U.conformal_qhat(p[:10000], y[:10000], 0.1)
    rep = U.conformal_report(p[10000:], y[10000:], q)
    assert 0.88 <= rep["coverage"] <= 0.92


def test_abstain_threshold_fraction():
    u = np.arange(1000.0)
    tau = U.abstain_threshold(u, 0.05)
    assert np.mean(u > tau) == pytest.approx(0.05, abs=0.002)


def test_novelty_larger_far_from_training():
    rng = np.random.default_rng(2)
    tr = rng.normal(size=(5000, 3))
    nov = U.Novelty(tr, n_ref=2000, k=5)
    near, far = nov(rng.normal(size=(100, 3))), nov(rng.normal(loc=6, size=(100, 3)))
    assert far.mean() > 3 * near.mean()


def test_risk_coverage_monotone_for_informative_score():
    err = np.r_[np.zeros(900), np.ones(100)]; u = np.r_[np.zeros(900), np.ones(100)]
    rc = U.risk_coverage(err, u)
    assert rc["selective_risk"][0] == 0.0 and rc["selective_risk"][-1] == pytest.approx(0.1)
