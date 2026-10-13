"""Paired trajectory bootstrap, seed-averaged contrasts, stratified resampling and undefined replicates
(PROTOCOL.md sections 9.1-9.3). Synthetic data only."""

import inspect

import numpy as np
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

import item33
from item33 import bootstrap as bs
from phase3.analysis import draw_rows
from phase3.population import trajectory_blocks

SEEDS = (11, 12, 13)


def make(n_traj=14, seed=0, positive_rate=0.3, methods=("C0", "C1", "C2")):
    rng = np.random.default_rng(seed)
    lengths = rng.integers(40, 90, n_traj)
    traj = np.concatenate([[f"t{i:02d}"] * int(m) for i, m in enumerate(lengths)])
    y = (rng.random(len(traj)) < positive_rate).astype(int)
    scores = {}
    for c, strength in zip(methods, (0.9, 0.5, 0.2)):
        for s in SEEDS:
            scores[bs.method_key(c, s)] = y * strength + rng.random(len(traj))
    return traj, y, scores


def test_point_estimates_equal_a_direct_computation():
    traj, y, scores = make()
    pt = bs.point_estimates(y, scores, ("pr_auc", "roc_auc"))
    for k, s in scores.items():
        assert pt[f"{k}|pr_auc"] == average_precision_score(y, s) and pt[f"{k}|roc_auc"] == roc_auc_score(y, s)


def test_replicate_zero_is_reproduced_by_hand_from_the_seeded_draw():
    traj, y, scores = make(seed=3)
    reps = bs.bootstrap_replicates(traj, y, scores, B=3, seed=777, metrics=("pr_auc", "roc_auc"))
    starts, ends, _ = trajectory_blocks(traj)
    draw = np.random.default_rng(777).integers(0, len(starts), size=len(starts))
    rows = np.concatenate([np.arange(starts[t], ends[t]) for t in draw])
    k = bs.method_key("C0", SEEDS[0])
    assert reps[f"{k}|pr_auc"][0] == pytest.approx(average_precision_score(y[rows], scores[k][rows]))
    assert reps[f"{k}|roc_auc"][0] == pytest.approx(roc_auc_score(y[rows], scores[k][rows]))


def test_one_draw_is_shared_by_every_method_so_a_self_pair_is_exactly_zero():
    traj, y, scores = make(seed=5)
    k = bs.method_key("C0", SEEDS[0])
    twin = {"a": scores[k], "b": scores[k].copy()}
    reps = bs.bootstrap_replicates(traj, y, twin, B=40, seed=9)
    assert np.array_equal(reps["a|pr_auc"], reps["b|pr_auc"])


def test_a_fixed_seed_is_deterministic_and_another_seed_differs():
    traj, y, scores = make(seed=6)
    r1 = bs.bootstrap_replicates(traj, y, scores, B=25, seed=5)
    r2 = bs.bootstrap_replicates(traj, y, scores, B=25, seed=5)
    r3 = bs.bootstrap_replicates(traj, y, scores, B=25, seed=6)
    k = f"{bs.method_key('C0', SEEDS[0])}|pr_auc"
    assert all(np.array_equal(r1[x], r2[x], equal_nan=True) for x in r1)
    assert not np.array_equal(r1[k], r3[k])


def test_whole_trajectories_are_resampled_never_individual_rows():
    traj, _, _ = make(seed=2)
    starts, ends, codes = trajectory_blocks(traj)
    draw = np.array([3, 3, 0, 7, 3, 1])
    rows = draw_rows(draw, starts, ends)
    counts = np.bincount(codes[rows], minlength=len(starts))
    lengths = ends - starts
    assert (counts % lengths == 0).all() and counts[3] == 3 * lengths[3] and counts[5] == 0


def test_replicates_without_positives_are_counted_not_silently_dropped():
    rng = np.random.default_rng(0)
    traj = np.concatenate([["pos"] * 60, ["neg_a"] * 60, ["neg_b"] * 60])
    y = np.concatenate([(rng.random(60) < 0.5).astype(int), np.zeros(120, dtype=int)]); y[0] = 1
    scores = {bs.method_key(c, s): rng.random(180) for c in ("C0", "C1") for s in SEEDS}
    reps = bs.bootstrap_replicates(traj, y, scores, B=300, seed=2)
    arr = reps[f"{bs.method_key('C0', SEEDS[0])}|pr_auc"]
    n_nan = int(np.isnan(arr).sum())
    assert n_nan > 0                                                       # some replicates omit the only positive-bearing trajectory
    pt = bs.point_estimates(y, scores)
    c = bs.contrast_summary("C0", "C1", SEEDS, pt, reps)
    assert c["bootstrap_seed_mean"]["n_undefined_replicates"] == n_nan
    assert all(v["n_undefined_replicates"] == n_nan for v in c["per_seed"].values())
    ok = (reps[f"{bs.method_key('C0', SEEDS[0])}|pr_auc"] - reps[f"{bs.method_key('C1', SEEDS[0])}|pr_auc"])
    assert c["per_seed"][SEEDS[0]]["ci_lo"] == pytest.approx(np.percentile(ok[np.isfinite(ok)], 2.5))


def test_percentile_interval_counts_undefined_and_handles_all_undefined():
    lo, hi, nu = bs.percentile_interval(np.array([np.nan, 1.0, 2.0, 3.0]))
    assert nu == 1 and lo == pytest.approx(np.percentile([1, 2, 3], 2.5))
    assert bs.percentile_interval(np.array([np.nan, np.nan])) == (None, None, 2)


def test_seed_averaged_contrast_is_assembled_exactly_as_specified():
    traj, y, scores = make(seed=8)
    reps = bs.bootstrap_replicates(traj, y, scores, B=60, seed=3)
    pt = bs.point_estimates(y, scores)
    c = bs.contrast_summary("C0", "C1", SEEDS, pt, reps, bonferroni=True)
    per = [pt[f"{bs.method_key('C0', s)}|pr_auc"] - pt[f"{bs.method_key('C1', s)}|pr_auc"] for s in SEEDS]
    assert [c["per_seed"][s]["point"] for s in SEEDS] == pytest.approx(per)
    assert c["seed_estimates"]["mean"] == pytest.approx(np.mean(per)) and c["seed_estimates"]["median"] == pytest.approx(np.median(per))
    assert c["seed_estimates"]["min"] == pytest.approx(min(per)) and c["seed_estimates"]["max"] == pytest.approx(max(per))
    assert c["seed_estimates"]["sd_ddof1"] == pytest.approx(np.std(per, ddof=1))
    mean_rep = np.mean([reps[f"{bs.method_key('C0', s)}|pr_auc"] - reps[f"{bs.method_key('C1', s)}|pr_auc"] for s in SEEDS], axis=0)
    lo, hi = np.percentile(mean_rep, [2.5, 97.5])
    assert c["bootstrap_seed_mean"]["ci_lo"] == pytest.approx(lo) and c["bootstrap_seed_mean"]["ci_hi"] == pytest.approx(hi)
    blo, bhi = np.percentile(mean_rep, [1.25, 98.75])
    adj = c["bootstrap_seed_mean_bonferroni"]
    assert adj["ci_lo"] == pytest.approx(blo) and adj["ci_hi"] == pytest.approx(bhi) and adj["m"] == 2
    assert adj["ci_lo"] <= c["bootstrap_seed_mean"]["ci_lo"] and adj["ci_hi"] >= c["bootstrap_seed_mean"]["ci_hi"]


def test_seed_variability_and_bootstrap_uncertainty_stay_in_separate_blocks():
    traj, y, scores = make(seed=9)
    reps = bs.bootstrap_replicates(traj, y, scores, B=30, seed=1)
    c = bs.contrast_summary("C0", "C2", SEEDS, bs.point_estimates(y, scores), reps)
    assert "ci_lo" not in c["seed_estimates"] and "ci_hi" not in c["seed_estimates"]            # no interval across seeds
    assert set(c) >= {"per_seed", "seed_estimates", "bootstrap_seed_mean"}
    assert "combined" not in " ".join(c) and "total_interval" not in c
    assert "not combined with seed variability" in c["bootstrap_seed_mean"]["note"]
    assert "no interval across seeds" in c["seed_estimates"]["note"]


def test_sign_consistency_flag():
    traj, y, scores = make(seed=10)
    reps = bs.bootstrap_replicates(traj, y, scores, B=10, seed=1)
    pt = bs.point_estimates(y, scores)
    assert bs.contrast_summary("C0", "C2", SEEDS, pt, reps)["seed_estimates"]["sign_consistent"] is True
    pt2 = dict(pt); pt2[f"{bs.method_key('C0', SEEDS[0])}|pr_auc"] = pt[f"{bs.method_key('C2', SEEDS[0])}|pr_auc"] - 0.1
    assert bs.contrast_summary("C0", "C2", SEEDS, pt2, reps)["seed_estimates"]["sign_consistent"] is False


def test_the_protocol_wrapper_has_no_b_or_seed_argument_and_passes_the_locked_values(monkeypatch):
    assert list(inspect.signature(bs.run_protocol_bootstrap).parameters) == ["traj_ids", "y", "scores", "strata", "metrics"]
    seen = {}
    monkeypatch.setattr(bs, "bootstrap_replicates", lambda *a, **k: seen.update(k) or {})
    bs.run_protocol_bootstrap(np.array(["a"]), np.array([1]), {})
    assert seen["B"] == 1000 == item33.BOOTSTRAP_B and seen["seed"] == 20261013 == item33.BOOTSTRAP_SEED


def test_invalid_inputs_are_refused():
    traj, y, scores = make(seed=11)
    shuffled = np.random.default_rng(0).permutation(len(traj))
    with pytest.raises(ValueError):
        bs.bootstrap_replicates(traj[shuffled], y, scores, B=3, seed=1)            # interleaved trajectories
    with pytest.raises(ValueError):
        bs.bootstrap_replicates(traj, y[:-1], scores, B=3, seed=1)
    with pytest.raises(ValueError):
        bs.bootstrap_replicates(traj, y, {"a": scores[bs.method_key("C0", 11)][:-1]}, B=3, seed=1)
    with pytest.raises(ValueError):
        bs.bootstrap_replicates(traj, y, scores, B=3, seed=1, metrics=("f1",))


# --- stratified resampling -------------------------------------------------------------------------------------------

def test_stratified_draws_fix_the_stratum_counts_in_every_replicate():
    traj, y, scores = make(n_traj=12, seed=4)
    uniq = list(dict.fromkeys(traj.tolist()))
    strata = {t: ("A" if i < 4 else "B" if i < 9 else "C") for i, t in enumerate(uniq)}
    starts, ends, n_traj, groups = bs._draw_plan(traj, strata)
    assert [len(g) for g in groups] == [4, 5, 3]
    rng = np.random.default_rng(1)
    for _ in range(200):
        d = bs._draw(rng, n_traj, groups)
        assert len(d) == 12
        assert sum(x < 4 for x in d) == 4 and sum(4 <= x < 9 for x in d) == 5 and sum(x >= 9 for x in d) == 3


def test_stratified_replicate_zero_is_reproduced_by_hand():
    traj, y, scores = make(n_traj=12, seed=5)
    uniq = list(dict.fromkeys(traj.tolist()))
    strata = {t: ("A" if i % 2 == 0 else "B") for i, t in enumerate(uniq)}
    reps = bs.bootstrap_replicates(traj, y, scores, B=2, seed=42, strata=strata)
    starts, ends, _ = trajectory_blocks(traj)
    rng = np.random.default_rng(42)
    parts = []
    for name in ("A", "B"):
        members = np.array([i for i, t in enumerate(uniq) if strata[t] == name])
        parts.append(members[rng.integers(0, members.size, size=members.size)])
    rows = np.concatenate([np.arange(starts[t], ends[t]) for t in np.concatenate(parts)])
    k = bs.method_key("C0", SEEDS[0])
    assert reps[f"{k}|pr_auc"][0] == pytest.approx(average_precision_score(y[rows], scores[k][rows]))


def test_stratification_refuses_a_trajectory_without_a_stratum():
    traj, y, scores = make(n_traj=6)
    uniq = list(dict.fromkeys(traj.tolist()))
    with pytest.raises(ValueError):
        bs.bootstrap_replicates(traj, y, scores, B=2, seed=1, strata={t: "A" for t in uniq[:-1]})
