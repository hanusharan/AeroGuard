"""Phase 3 tests: the TRAIN-ONLY negative-alpha investigation (PROTOCOL.md section 5.4).

Synthetic data only. The Q3 > 0 decision rule is applied mechanically; Q4 can never reach it.
"""

import ast
import inspect
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_phase3_population import make_panel  # synthetic generator shared by the Phase 3 tests

from phase3 import A_PEAK_RAD, HORIZON_STEPS
from phase3 import analysis as an
from phase3 import population as pop


def _train(kinds, seed=11):
    return pop.SplitTable("train", make_panel("tr", kinds, seed=seed))


def _brute_force(df):
    """Independent re-derivation with explicit loops (no cumulative sums, no shared helpers)."""
    mask = pop.usable_mask(df)
    q3 = pos_rows = neg_rows = 0
    neg_traj = set()
    for tid, g in df.groupby("trajectory_id", sort=False):
        alpha = g["alpha"].to_numpy()
        unsafe = np.abs(alpha) > A_PEAK_RAD
        neg_rows += int((unsafe & (alpha < 0)).sum())
        pos_rows += int((unsafe & (alpha > 0)).sum())
        if (unsafe & (alpha < 0)).any():
            neg_traj.add(tid)
        usable = mask[g.index.to_numpy()]
        label = g["future_stall_5s"].to_numpy()
        for i in range(len(g) - HORIZON_STEPS):
            win = slice(i + 1, i + HORIZON_STEPS + 1)
            has_neg = bool((unsafe[win] & (alpha[win] < 0)).any())
            has_pos = bool((unsafe[win] & (alpha[win] > 0)).any())
            if usable[i] and label[i] == 1.0 and has_neg and not has_pos:
                q3 += 1
    return {"pos": pos_rows, "neg": neg_rows, "neg_traj": len(neg_traj), "q3": q3}


def test_q1_q2_q3_match_an_independent_brute_force_count():
    tab = _train(["normal", "pos", "neg", "double", "mixed", "neg", "normal"])
    got = an.negative_alpha_q1_q3(tab)
    want = _brute_force(tab.df)
    assert got["q1_unsafe_rows_alpha_positive"] == want["pos"] and got["q1_unsafe_rows_alpha_negative"] == want["neg"]
    assert got["q2_trajectories_with_negative_side_unsafe_row"] == want["neg_traj"] == 3
    assert got["q3_negative_only_positive_rows"] == want["q3"] > 0
    assert got["split"] == "train" and got["n_trajectories"] == 7


def test_the_decision_rule_is_q3_greater_than_zero_and_nothing_else():
    assert an.q3_decision(0) is False and an.q3_decision(1) is True and an.q3_decision(10_000) is True
    assert list(inspect.signature(an.q3_decision).parameters) == ["q3"]
    only_positive = an.negative_alpha_q1_q3(_train(["normal", "pos", "double", "normal"]))
    assert only_positive["q3_negative_only_positive_rows"] == 0 and only_positive["run_two_sided"] is False
    with_negative = an.negative_alpha_q1_q3(_train(["normal", "neg", "pos"]))
    assert with_negative["q3_negative_only_positive_rows"] > 0 and with_negative["run_two_sided"] is True


def test_a_mixed_trajectory_counts_only_the_rows_whose_window_holds_no_positive_side_sample():
    tab = _train(["mixed"])
    got = an.negative_alpha_q1_q3(tab)
    assert got["q3_negative_only_positive_rows"] == _brute_force(tab.df)["q3"]
    assert 0 < got["q3_negative_only_positive_rows"] < got["n_usable_positive_rows"]


def test_only_the_train_split_is_accepted():
    df = make_panel("v", ["normal", "neg"], seed=2)
    for bad in (pop.SplitTable("val", df), pop.SplitTable("test", df)):
        with pytest.raises(pop.GateViolation):
            an.negative_alpha_q1_q3(bad)
        with pytest.raises(pop.GateViolation):
            an.negative_alpha_q4(bad, 0.2)
    with pytest.raises(pop.GateViolation):
        an.negative_alpha_q1_q3(df)  # a bare DataFrame carries no split tag


def test_the_investigation_code_cannot_reference_validation_or_test_files():
    for fn in (an.negative_alpha_q1_q3, an.negative_alpha_q4):
        tree = ast.parse(inspect.getsource(fn).lstrip())
        strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        idents = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not [s for s in strings if "temporal_val" in s or "temporal_test" in s or s in ("val", "test")]
        assert not [i for i in idents if i in ("load_split", "read_parquet", "SPLITS")]


def test_a_stored_label_that_disagrees_with_is_unsafe_stops_the_investigation():
    df = make_panel("c", ["normal", "neg"], seed=4)
    bad = df.copy()
    i = bad.index[(bad["trajectory_id"] == "c_001") & (bad["future_stall_5s"] == 1.0)][0]
    bad.loc[i, "future_stall_5s"] = 0.0
    with pytest.raises(an.LabelSemanticsError):
        an.negative_alpha_q1_q3(pop.SplitTable("train", bad))
    bad2 = df.copy()
    bad2.loc[bad2.index[0], "future_stall_5s_available"] = False
    with pytest.raises(an.LabelSemanticsError):
        an.negative_alpha_q1_q3(pop.SplitTable("train", bad2))


def test_missing_columns_and_non_finite_alpha_are_refused():
    df = make_panel("m", ["normal", "neg"], seed=5)
    with pytest.raises(ValueError):
        an.negative_alpha_q1_q3(pop.SplitTable("train", df.drop(columns=["is_unsafe"])))
    bad = df.copy()
    bad.loc[bad.index[5], "alpha"] = np.nan
    with pytest.raises(ValueError):
        an.negative_alpha_q1_q3(pop.SplitTable("train", bad))


def test_q4_counts_usable_rows_below_minus_tau_by_label_and_never_feeds_the_decision():
    tab = _train(["normal", "neg", "mixed", "pos"], seed=7)
    before = an.negative_alpha_q1_q3(tab)
    tau = 0.2172
    q4 = an.negative_alpha_q4(tab, tau)
    mask = pop.usable_mask(tab.df)
    sel = mask & (tab.df["alpha"].to_numpy() < -tau)
    lab = tab.df["future_stall_5s"].to_numpy()
    assert q4["q4_usable_rows_alpha_below_minus_tau"] == int(sel.sum()) > 0
    assert q4["q4_of_which_label_1"] == int((sel & (lab == 1.0)).sum()) and q4["q4_of_which_label_0"] == int((sel & (lab == 0.0)).sum())
    assert q4["influences_q3_decision"] is False
    assert an.negative_alpha_q1_q3(tab) == before  # Q4 changed nothing about Q1-Q3 or the decision
    assert "q4" not in inspect.getsource(an.q3_decision)


def test_trajectories_must_be_contiguous_and_ordered():
    df = make_panel("o", ["neg", "normal"], seed=6)
    shuffled = pop.SplitTable("train", df.sample(frac=1.0, random_state=1).reset_index(drop=True))
    with pytest.raises(pop.KeyMismatchError):
        an.negative_alpha_q1_q3(shuffled)
