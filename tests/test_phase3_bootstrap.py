"""Phase 3 tests: the paired trajectory bootstrap (Item 32; PROTOCOL.md section 9.3).

Synthetic data only. The unit of resampling is the trajectory, one draw is shared by every
method within a replicate, and the approved configuration is B = 1000, seed 20261013.
"""

import inspect
import os
import sys

import numpy as np
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import phase3
from phase3 import analysis as an


def _data(n_traj=20, seed=0, positive_rate=0.3):
    rng = np.random.default_rng(seed)
    lengths = rng.integers(40, 90, n_traj)
    traj = np.concatenate([[f"t{i:02d}"] * int(m) for i, m in enumerate(lengths)])
    y = (rng.random(len(traj)) < positive_rate).astype(int)
    scores = {
        "a": y * 0.6 + rng.random(len(traj)),
        "b": y * 0.3 + rng.random(len(traj)),
        "c": rng.random(len(traj)),
    }
    return traj, y, scores


def _events(traj, seed=1):
    rng = np.random.default_rng(seed)
    out = {}
    for m in ("a", "b", "c"):
        d = {}
        for t in dict.fromkeys(traj):
            if rng.random() < 0.5:
                d[t] = [(bool(rng.random() < 0.7), float(rng.uniform(0.1, 5.0))) for _ in range(int(rng.integers(1, 3)))]
        out[m] = d
    return out


def test_the_approved_configuration_is_recorded_in_the_package():
    assert phase3.BOOTSTRAP_B == 1000 and phase3.BOOTSTRAP_SEED == 20261013 and phase3.BOOTSTRAP_INTERVAL_PCT == (2.5, 97.5)


def test_the_protocol_wrapper_has_no_b_or_seed_argument_and_passes_the_approved_values(monkeypatch):
    assert list(inspect.signature(an.run_protocol_bootstrap).parameters) == ["traj_ids", "y", "scores", "pairs", "events"]
    seen = {}

    def fake(traj_ids, y, scores, pairs, B, seed, events=None):
        seen.update(B=B, seed=seed)
        return {"config": {}}, {}

    monkeypatch.setattr(an, "trajectory_bootstrap", fake)
    traj, y, scores = _data()
    an.run_protocol_bootstrap(traj, y, scores, [("a", "b")])
    assert seen == {"B": 1000, "seed": 20261013}


def test_draw_rows_keeps_every_drawn_trajectory_whole_and_counts_repeats():
    traj, _, _ = _data(8, seed=3)
    starts, ends, codes = an.trajectory_blocks(traj)
    draw = np.array([3, 3, 0, 7, 3, 1])
    rows = an.draw_rows(draw, starts, ends)
    naive = np.concatenate([np.arange(starts[t], ends[t]) for t in draw])
    assert np.array_equal(rows, naive)
    counts = np.bincount(codes[rows], minlength=len(starts))
    lengths = ends - starts
    assert counts[3] == 3 * lengths[3] and counts[0] == lengths[0] and counts[2] == 0   # whole blocks, drawn multiplicity
    assert (counts % np.maximum(lengths, 1) == 0).all()                                   # never a partial trajectory
    assert an.draw_rows(np.array([], dtype=int), starts, ends).size == 0


def test_point_estimates_equal_a_direct_computation_on_the_full_data():
    traj, y, scores = _data()
    summary, _ = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=20, seed=1)
    for m in scores:
        assert summary["per_method"][f"{m}|pr_auc"]["point"] == average_precision_score(y, scores[m])
        assert summary["per_method"][f"{m}|roc_auc"]["point"] == roc_auc_score(y, scores[m])
    d = summary["paired_differences"]["a - b | pr_auc"]
    assert d["point"] == pytest.approx(average_precision_score(y, scores["a"]) - average_precision_score(y, scores["b"]))


def test_replicate_zero_is_reproduced_by_hand_from_the_seeded_draw():
    traj, y, scores = _data(12, seed=4)
    ev = _events(traj)
    _, reps = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=3, seed=777, events=ev)
    starts, ends, _ = an.trajectory_blocks(traj)
    uniques = list(dict.fromkeys(traj))
    rng = np.random.default_rng(777)
    draw = rng.integers(0, len(starts), size=len(starts))
    rows = np.concatenate([np.arange(starts[t], ends[t]) for t in draw])
    assert reps["a|pr_auc"][0] == pytest.approx(average_precision_score(y[rows], scores["a"][rows]))
    assert reps["c|roc_auc"][0] == pytest.approx(roc_auc_score(y[rows], scores["c"][rows]))
    drawn_events = [e for t in draw for e in ev["a"].get(uniques[t], [])]
    warned = [lead for w, lead in drawn_events if w]
    assert reps["a|event_recall"][0] == pytest.approx(len(warned) / len(drawn_events))
    assert reps["a|median_lead_s"][0] == pytest.approx(float(np.median(warned)))


def test_the_same_draw_is_shared_by_every_method_so_differences_are_paired():
    traj, y, scores = _data(seed=5)
    summary, reps = an.trajectory_bootstrap(traj, y, scores, [("a", "b"), ("a", "c")], B=60, seed=9)
    for (a, b) in (("a", "b"), ("a", "c")):
        diff = reps[f"{a}|pr_auc"] - reps[f"{b}|pr_auc"]
        lo, hi = np.percentile(diff[np.isfinite(diff)], [2.5, 97.5])
        got = summary["paired_differences"][f"{a} - {b} | pr_auc"]
        assert got["ci_lo"] == pytest.approx(lo) and got["ci_hi"] == pytest.approx(hi)
        assert got["ci_includes_zero"] == (lo <= 0.0 <= hi)
    # a method scored identically to itself has an identically-zero paired difference
    s2, r2 = an.trajectory_bootstrap(traj, y, {"a": scores["a"], "a2": scores["a"].copy()}, [("a", "a2")], B=30, seed=9)
    assert np.all(r2["a|pr_auc"] == r2["a2|pr_auc"])
    assert s2["paired_differences"]["a - a2 | pr_auc"]["ci_lo"] == 0.0


def test_a_fixed_seed_gives_identical_results_and_a_different_seed_does_not():
    traj, y, scores = _data(seed=6)
    s1, r1 = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=25, seed=5)
    s2, r2 = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=25, seed=5)
    s3, r3 = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=25, seed=6)
    assert all(np.array_equal(r1[k], r2[k], equal_nan=True) for k in r1) and s1 == s2
    assert not np.array_equal(r1["a|pr_auc"], r3["a|pr_auc"])


def test_replicates_without_positives_are_counted_not_silently_dropped():
    rng = np.random.default_rng(0)
    traj = np.concatenate([["pos_traj"] * 60, ["neg_a"] * 60, ["neg_b"] * 60])
    y = np.concatenate([(rng.random(60) < 0.5).astype(int), np.zeros(120, dtype=int)])
    y[0] = 1
    scores = {"a": rng.random(180), "b": rng.random(180)}
    summary, reps = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=300, seed=2)
    n_nan = int(np.isnan(reps["a|pr_auc"]).sum())
    assert n_nan > 0   # some replicates omit the only positive-bearing trajectory
    assert summary["per_method"]["a|pr_auc"]["n_undefined_replicates"] == n_nan
    assert summary["paired_differences"]["a - b | pr_auc"]["n_undefined_replicates"] == n_nan
    ok = reps["a|pr_auc"][np.isfinite(reps["a|pr_auc"])]
    assert summary["per_method"]["a|pr_auc"]["ci_lo"] == pytest.approx(np.percentile(ok, 2.5))


def test_the_summary_records_the_unit_pairing_interval_and_configuration():
    traj, y, scores = _data(seed=8)
    summary, _ = an.trajectory_bootstrap(traj, y, scores, [("a", "b")], B=10, seed=3)
    c = summary["config"]
    assert c["unit"] == "trajectory" and c["B"] == 10 and c["seed"] == 3 and c["n_trajectories"] == 20 and c["n_rows"] == len(y)
    assert "percentile" in c["interval"] and "shared by every method" in c["pairing"]


def test_invalid_inputs_are_refused():
    traj, y, scores = _data(seed=9)
    shuffled = np.random.default_rng(0).permutation(len(traj))
    with pytest.raises(ValueError):
        an.trajectory_bootstrap(traj[shuffled], y, scores, [("a", "b")], B=3, seed=1)   # interleaved trajectories
    with pytest.raises(ValueError):
        an.trajectory_bootstrap(traj, y, scores, [("a", "zzz")], B=3, seed=1)
    with pytest.raises(ValueError):
        an.trajectory_bootstrap(traj, y[:-1], scores, [("a", "b")], B=3, seed=1)
    with pytest.raises(ValueError):
        an.trajectory_bootstrap(traj, y, {"a": scores["a"][:-1], "b": scores["b"]}, [("a", "b")], B=3, seed=1)
