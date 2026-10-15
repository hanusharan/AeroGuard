"""Evidence wording, comparison register and row schema, the validation-only matched operating point, and masking
(PROTOCOL.md sections 9.2, 9.4, 9.5, 10, 13). Synthetic data only."""

import copy

import numpy as np
import pandas as pd
import pytest

from item33 import MASK_SEEDS, conditions as cond, masking, operating_point as mop, register, summary


# --- summary / wording ----------------------------------------------------------------------------------------------------

def test_seed_panel_is_descriptive_and_has_no_interval():
    p = summary.seed_panel({1: 0.10, 2: 0.14, 3: 0.12})
    assert p["mean"] == pytest.approx(0.12) and p["median"] == 0.12 and p["min"] == 0.10 and p["max"] == 0.14
    assert p["sd_ddof1"] == pytest.approx(np.std([0.10, 0.14, 0.12], ddof=1))
    assert "ci_lo" not in p and "not a confidence interval" in p["note"]
    with pytest.raises(ValueError):
        summary.seed_panel({1: float("nan")})


def test_sign_consistency_treats_zero_as_inconsistent():
    assert summary.sign_consistent([0.1, 0.2, 0.3]) and summary.sign_consistent([-0.1, -0.2])
    assert not summary.sign_consistent([0.1, 0.0, 0.3]) and not summary.sign_consistent([0.1, -0.2]) and not summary.sign_consistent([])


def test_primary_wording_follows_the_protocol_rules():
    up = [0.02, 0.03, 0.025, 0.021, 0.04]
    a = summary.evidence_statement("primary", 0.01, 0.05, up, 0.005, 0.06)
    assert a["label"] == "difference_demonstrated" and not a["marginal_level_only"]
    b = summary.evidence_statement("primary", 0.01, 0.05, up, -0.001, 0.06)
    assert b["label"] == "difference_demonstrated" and b["marginal_level_only"] and "marginal-level evidence only" in b["text"]
    c = summary.evidence_statement("primary", 0.01, 0.05, [0.02, -0.01, 0.03, 0.02, 0.02])
    assert c["label"] == "inconsistent_across_seeds"
    d = summary.evidence_statement("primary", -0.01, 0.05, up)
    assert d["label"] == "no_difference_demonstrated" and "alike" in d["text"]
    e = summary.evidence_statement("primary", -0.05, -0.01, [-0.02] * 5)
    assert e["label"] == "difference_demonstrated"
    f = summary.evidence_statement("primary", None, None, up)
    assert f["label"] == "undefined"


@pytest.mark.parametrize("status", ["secondary", "exploratory", "sensitivity", "technical", "descriptive"])
def test_nonprimary_comparisons_are_only_ever_observed_never_demonstrated(status):
    for lo, hi in ((0.01, 0.05), (-0.01, 0.05)):
        s = summary.evidence_statement(status, lo, hi, [0.02] * 5)
        assert "demonstrated" not in s["text"] and "observed" in s["text"] and status in s["text"]
        assert s["label"] in ("difference_observed", "no_difference_observed")


def test_generated_statements_never_use_banned_wording():
    for status in summary.STATUSES:
        for lo, hi in ((0.01, 0.05), (-0.01, 0.05), (None, None)):
            s = summary.evidence_statement(status, lo, hi, [0.02] * 5, -0.001, 0.06)
            low = s["text"].lower()
            assert not any(w in low for w in summary.BANNED_PHRASES)
    for bad in ("confirmatory result", "validated", "control-free model", "independent", "blind test", "negligible", "equivalent", "the model relies on controls"):
        with pytest.raises(ValueError):
            summary.assert_wording_clean(bad)
    with pytest.raises(ValueError):
        summary.evidence_statement("unknown", 0.0, 1.0, [])


# --- register / schema -------------------------------------------------------------------------------------------------------

def test_register_matches_the_protocol_roles():
    assert register.validate_register() is True
    reg = register.register_by_id()
    assert register.PRIMARY_IDS == ("D1", "D2")
    assert reg["D1"]["comparison"] == "C0 - C1" and reg["D2"]["comparison"] == "C0 - C2" and reg["SEC-2"]["comparison"] == "C1 - C2"
    assert reg["X-a"]["status"] == "exploratory" and reg["X-b"]["comparison"] == "C0 - X1" and reg["X-b"]["status"] == "exploratory"
    assert reg["D1"]["adjustment"].startswith("Bonferroni") and reg["X-a"]["adjustment"] == "none"
    assert [r["id"] for r in register.REGISTER if r["status"] == "primary"] == ["D1", "D2"]


def test_the_register_rejects_a_changed_primary_set(monkeypatch):
    bad = copy.deepcopy(register.REGISTER)
    bad[2]["status"] = "primary"
    monkeypatch.setattr(register, "REGISTER", bad)
    monkeypatch.setattr(register, "PRIMARY_IDS", tuple(r["id"] for r in bad if r["status"] == "primary"))
    with pytest.raises(ValueError):
        register.validate_register()


def test_metric_rows_have_a_deterministic_schema():
    r = register.metric_row(analysis_family=register.FAMILY_RETRAINED, condition="C1", seed=20260817, metric="pr_auc", value=0.5,
                            population_id="p", register_id="D1")
    assert tuple(r) == register.ROW_FIELDS and r["status"] == "primary" and r["evidence_category"] == "E2"
    assert "not blind" in r["exposure_label"] and "not independent replication" in r["exposure_label"]
    nan_row = register.metric_row(analysis_family=register.FAMILY_RETRAINED, condition="C0", seed=1, metric="pr_auc", value=float("nan"),
                                  population_id="p", register_id="EST")
    assert nan_row["value"] is None


def test_masking_rows_never_use_retrained_condition_labels_and_families_stay_apart():
    ok = register.metric_row(analysis_family=register.FAMILY_MASKING, condition="M-A|MS1", seed=None, metric="pr_auc", value=0.4,
                             population_id="p", register_id="M")
    assert ok["analysis_family"] == "frozen_model_masking"
    with pytest.raises(ValueError):
        register.metric_row(analysis_family=register.FAMILY_MASKING, condition="C1", seed=None, metric="pr_auc", value=0.4, population_id="p", register_id="M")
    with pytest.raises(ValueError):
        register.metric_row(analysis_family="mixed", condition="C1", seed=1, metric="pr_auc", value=0.4, population_id="p", register_id="D1")
    with pytest.raises(ValueError):
        register.metric_row(analysis_family=register.FAMILY_RETRAINED, condition="C1", seed=1, metric="pr_auc", value=0.4, population_id="p", register_id="nope")
    with pytest.raises(ValueError):
        register.validate_row({**ok, "extra": 1})
    assert register.FAMILY_MASKING != register.FAMILY_RETRAINED == "retrained_ablation"


# --- matched operating point ---------------------------------------------------------------------------------------------------

def test_fpr_and_matched_threshold_on_a_known_fixture():
    y = np.array([0] * 10 + [1] * 4)
    s = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9] + [0.55, 0.65, 0.95, 0.99])
    assert mop.fpr_at(y, s, 0.65) == pytest.approx(0.4)                    # negatives above 0.65: 0.7, 0.8, 0.85, 0.9
    m = mop.matched_threshold(y, s, 0.2)
    assert m["achieved_fpr"] <= 0.2 and m["threshold"] == pytest.approx(0.8)
    assert mop.fpr_at(y, s, m["threshold"]) == pytest.approx(m["achieved_fpr"]) == pytest.approx(0.2)
    smaller = [c for c in np.unique(s) if c < m["threshold"]]
    assert all(mop.fpr_at(y, s, c) > 0.2 for c in smaller)                 # it is the SMALLEST admissible threshold
    zero = mop.matched_threshold(y, s, 0.0)
    assert zero["achieved_fpr"] == 0.0 and zero["threshold"] == pytest.approx(0.9)


def test_matching_uses_strict_greater_than_and_handles_ties():
    y = np.array([0, 0, 0, 0, 1, 1])
    s = np.array([0.5, 0.5, 0.5, 0.7, 0.9, 0.5])
    m = mop.matched_threshold(y, s, 0.25)
    assert m["threshold"] == pytest.approx(0.5) and m["achieved_fpr"] == pytest.approx(0.25)    # only the 0.7 negative exceeds 0.5


def test_the_reference_condition_is_matched_to_a_threshold_no_larger_than_its_own():
    rng = np.random.default_rng(0)
    y = (rng.random(400) < 0.3).astype(int)
    val = {"C0": y * 0.6 + rng.random(400), "C1": y * 0.3 + rng.random(400)}
    res = mop.matched_thresholds(y, val, "C0", 1.1)
    target = mop.fpr_at(y, val["C0"], 1.1)
    for name, r in res.items():
        assert r["target_fpr"] == pytest.approx(target) and r["achieved_fpr"] <= target + 1e-12 and r["reference"] == "C0"
    assert res["C0"]["threshold"] <= 1.1


def test_matching_takes_only_validation_inputs_and_refuses_bad_inputs():
    import inspect
    assert list(inspect.signature(mop.matched_threshold).parameters) == ["y_val", "score_val", "target_fpr"]
    assert list(inspect.signature(mop.matched_thresholds).parameters) == ["y_val", "val_scores", "reference", "reference_threshold"]
    with pytest.raises(ValueError):
        mop.matched_threshold(np.ones(5, dtype=int), np.arange(5.0), 0.1)             # no negatives
    with pytest.raises(ValueError):
        mop.matched_threshold(np.array([0, 1]), np.array([0.1, np.nan]), 0.1)
    with pytest.raises(ValueError):
        mop.matched_threshold(np.array([0, 1]), np.array([0.1, 0.2]), 1.5)
    with pytest.raises(ValueError):
        mop.matched_thresholds(np.array([0, 1]), {"C1": np.array([0.1, 0.2])}, "C0", 0.5)


# --- masking ----------------------------------------------------------------------------------------------------------------------------

def frame(n_traj=4, length=30, seed=0):
    rng = np.random.default_rng(seed)
    parts = []
    for i in range(n_traj):
        d = {f: rng.standard_normal(length) for f in cond.C0_FEATURES}
        d["elevator"] = np.linspace(0, 1, length) + i
        d["throttle"] = np.full(length, 0.1 * (i + 1))
        df = pd.DataFrame(d)
        df.insert(0, "trajectory_id", f"t{i}")
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


FEATS = list(cond.C0_FEATURES)


def test_mask_sets_are_exactly_those_in_the_protocol():
    assert masking.MASK_SETS == {"M-A": ("elevator", "throttle"), "M-B": ("elevator_change_1s",), "M-C": ("elevator", "throttle", "elevator_change_1s")}
    assert masking.METHODS == ("MS1", "MS2", "MS3") and masking.ANALYSIS_FAMILY == "frozen_model_masking"
    assert not set(masking.MASK_SETS) & set(cond.CONDITION_ORDER)


@pytest.mark.parametrize("ms", list(masking.MASK_SETS))
@pytest.mark.parametrize("method", ["MS1", "MS2", "MS3"])
def test_masking_replaces_columns_keeps_the_schema_and_never_modifies_the_input(ms, method):
    df = frame(); before = df.copy(deep=True)
    med = {c: 0.123 for c in masking.MASK_SETS[ms]}
    out = masking.apply_mask(df, FEATS, ms, method, medians=med, seed=MASK_SEEDS[0])
    assert list(out.columns) == FEATS and len(out) == len(df) and out.index.equals(df.index)      # replaced, never dropped
    pd.testing.assert_frame_equal(df, before)                                                        # input untouched
    others = [c for c in FEATS if c not in masking.MASK_SETS[ms]]
    pd.testing.assert_frame_equal(out[others], df[others])                                           # derived columns NOT recomputed
    for c in masking.MASK_SETS[ms]:
        assert sorted(out[c]) == pytest.approx(sorted(df[c])) if method != "MS1" else (out[c] == 0.123).all()


def test_ms1_is_a_constant_equal_to_the_supplied_training_median():
    df = frame()
    out = masking.apply_mask(df, FEATS, "M-A", "MS1", medians={"elevator": 0.5, "throttle": 0.25})
    assert (out["elevator"] == 0.5).all() and (out["throttle"] == 0.25).all()
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, FEATS, "M-A", "MS1", medians={"elevator": 0.5})
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, FEATS, "M-A", "MS1", medians={"elevator": 0.5, "throttle": float("nan")})


def test_ms2_uses_one_global_permutation_for_every_column_of_the_set():
    df = frame()
    out = masking.apply_mask(df, FEATS, "M-A", "MS2", seed=MASK_SEEDS[1])
    perm = np.random.default_rng(MASK_SEEDS[1]).permutation(len(df))
    assert np.array_equal(out["elevator"].to_numpy(), df["elevator"].to_numpy()[perm])
    assert np.array_equal(out["throttle"].to_numpy(), df["throttle"].to_numpy()[perm])
    pairs_before = set(zip(df["elevator"].round(9), df["throttle"].round(9)))
    pairs_after = set(zip(out["elevator"].round(9), out["throttle"].round(9)))
    assert pairs_before == pairs_after                                         # the joint of the set is preserved


def test_ms3_permutes_inside_each_trajectory_only():
    df = frame()
    out = masking.apply_mask(df, FEATS, "M-C", "MS3", seed=MASK_SEEDS[2])
    for tid, g in df.groupby("trajectory_id", sort=False):
        o = out.loc[g.index]
        for c in masking.MASK_SETS["M-C"]:
            assert sorted(o[c]) == pytest.approx(sorted(g[c]))                  # same multiset within the trajectory
    assert not np.array_equal(out["elevator"].to_numpy(), df["elevator"].to_numpy())
    rng = np.random.default_rng(MASK_SEEDS[2])
    idx = np.arange(len(df))
    for s in range(0, len(df), 30):
        idx[s:s + 30] = s + rng.permutation(30)
    assert np.array_equal(out["elevator"].to_numpy(), df["elevator"].to_numpy()[idx])


def test_masking_is_reproducible_and_seed_dependent():
    df = frame()
    a = masking.apply_mask(df, FEATS, "M-B", "MS2", seed=MASK_SEEDS[0])
    b = masking.apply_mask(df, FEATS, "M-B", "MS2", seed=MASK_SEEDS[0])
    c = masking.apply_mask(df, FEATS, "M-B", "MS2", seed=MASK_SEEDS[1])
    pd.testing.assert_frame_equal(a, b)
    assert not a["elevator_change_1s"].equals(c["elevator_change_1s"])


def test_masking_refuses_unspecified_choices_and_schema_problems():
    df = frame()
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, FEATS, "M-Z", "MS1", medians={})
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, FEATS, "M-A", "MS9")
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, FEATS, "M-A", "MS2", seed=1)                   # not a pre-specified permutation seed
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, FEATS, "M-A", "MS2")
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df.drop(columns=["dq_dt"]), FEATS, "M-A", "MS2", seed=MASK_SEEDS[0])
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(df, [f for f in FEATS if f != "elevator"], "M-A", "MS2", seed=MASK_SEEDS[0])   # masked column not a model feature
    interleaved = df.sample(frac=1.0, random_state=0).reset_index(drop=True)
    with pytest.raises(masking.MaskingError):
        masking.apply_mask(interleaved, FEATS, "M-A", "MS3", seed=MASK_SEEDS[0])
