"""Feature membership, counts, order, nesting, leakage exclusion and fail-closed behaviour (PROTOCOL.md sections 3, 4, 14)."""

import copy
import json

import pandas as pd
import pytest

from item33 import conditions as cond

C0 = [
    "V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin", "dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt",
    "d2alpha_dt2", "alpha_mean_1s", "alpha_min_1s", "alpha_max_1s", "alpha_range_1s", "alpha_slope_1s", "alpha_trend_1s", "V_slope_1s",
    "gamma_slope_1s", "pitch_rate_slope_1s", "elevator_change_1s",
]


def test_c0_is_the_literal_frozen_list_in_the_frozen_order():
    assert list(cond.C0_FEATURES) == C0 and len(C0) == 23 == len(set(C0))


@pytest.mark.parametrize("name,n,removed", [
    ("C0", 23, []),
    ("C1", 21, ["elevator", "throttle"]),
    ("C2", 20, ["elevator", "throttle", "elevator_change_1s"]),
    ("C3", 16, ["elevator", "throttle", "elevator_change_1s", "dq_dt", "dV_dt", "pitch_rate_slope_1s", "V_slope_1s"]),
    ("X1", 22, ["elevator_change_1s"]),
])
def test_exact_membership_count_and_order_of_every_condition(name, n, removed):
    feats = cond.features_for(name)
    assert feats == [f for f in C0 if f not in removed]       # C0's order with the removed names deleted
    assert len(feats) == n == cond.EXPECTED_N_FEATURES[name]
    assert set(feats).isdisjoint(removed)


def test_features_for_is_deterministic():
    assert cond.features_for("C2") == cond.features_for("C2")
    assert cond.build_manifest() == cond.build_manifest()


def test_the_conditions_are_nested_as_the_protocol_states():
    s = {k: set(cond.features_for(k)) for k in cond.CONDITION_ORDER}
    assert s["C3"] < s["C2"] < s["C1"] < s["C0"]
    assert s["C2"] < s["X1"] < s["C0"]
    assert cond.CONDITION_ORDER == ("C0", "C1", "C2", "C3", "X1")


def test_the_sixteen_retained_features_are_common_to_every_condition():
    common = set.intersection(*[set(cond.features_for(k)) for k in cond.CONDITION_ORDER])
    assert common == set(cond.features_for("C3")) and len(common) == 16


def test_the_default_manifest_validates():
    assert cond.validate_manifest()["C1"]["n_features"] == 21


def test_unknown_condition_is_refused():
    with pytest.raises(cond.ManifestError):
        cond.features_for("C9")


@pytest.mark.parametrize("bad", ["future_stall_5s", "future_stall_5s_available", "is_unsafe", "time_to_stall", "trajectory_id", "time",
                                 "split", "thrust", "theta", "vertical_speed"])
def test_every_leakage_or_excluded_field_is_refused(bad):
    with pytest.raises(cond.ManifestError):
        cond.assert_no_forbidden(["alpha", bad])
    m = copy.deepcopy(cond.build_manifest())
    m["C0"]["features"] = m["C0"]["features"][:-1] + [bad]
    with pytest.raises(cond.ManifestError):
        cond.validate_manifest(m)


def test_no_manifest_contains_a_forbidden_field():
    for name in cond.CONDITION_ORDER:
        assert set(cond.features_for(name)).isdisjoint(cond.FORBIDDEN_COLUMNS)


def test_missing_duplicate_extra_and_reordered_features_are_rejected():
    base = cond.build_manifest()
    missing = copy.deepcopy(base); missing["C1"]["features"] = missing["C1"]["features"][:-1]
    dup = copy.deepcopy(base); dup["C1"]["features"] = dup["C1"]["features"] + ["alpha"]
    reordered = copy.deepcopy(base); reordered["C2"]["features"] = list(reversed(reordered["C2"]["features"]))
    extra = copy.deepcopy(base); extra["X1"]["features"] = extra["X1"]["features"] + ["not_a_feature"]
    wrong_count = copy.deepcopy(base); wrong_count["C3"]["n_features"] = 17
    for bad in (missing, dup, reordered, extra, wrong_count):
        with pytest.raises(cond.ManifestError):
            cond.validate_manifest(bad)


def test_conditions_must_be_exactly_the_five_in_order():
    m = cond.build_manifest()
    del m["X1"]
    with pytest.raises(cond.ManifestError):
        cond.validate_manifest(m)


def test_select_columns_returns_the_condition_columns_in_order():
    df = pd.DataFrame({f: [1.0, 2.0] for f in C0 + ["time", "extra"]})
    out = cond.select_columns(df, "C1")
    assert list(out.columns) == cond.features_for("C1") and "elevator" not in out.columns


def test_select_columns_fails_closed_on_missing_or_duplicated_columns():
    df = pd.DataFrame({f: [1.0] for f in C0})
    with pytest.raises(cond.ManifestError):
        cond.select_columns(df.drop(columns=["dq_dt"]), "C0")
    dup = pd.concat([df, df[["alpha"]]], axis=1)
    with pytest.raises(cond.ManifestError):
        cond.select_columns(dup, "C0")


def test_c0_equals_the_existing_source_definition():
    assert cond.verify_against_source() is True


def test_c0_must_equal_the_stored_record_and_a_difference_fails_closed(tmp_path):
    record = tmp_path / "metrics.json"
    record.write_text(json.dumps({"feature_columns": C0}))
    assert cond.verify_against_stored_record(json.loads(record.read_text())["feature_columns"]) is True
    with pytest.raises(cond.ManifestError):
        cond.verify_against_stored_record(C0[:-1] + ["thrust"])
    with pytest.raises(cond.ManifestError):
        cond.verify_against_stored_record(list(reversed(C0)))
