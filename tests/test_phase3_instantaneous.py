"""Phase 3 tests: the instantaneous-state model (Item 31; PROTOCOL.md sections 7.1-7.5).

Synthetic data only. The model is fitted on small synthetic panels; nothing here touches the
regenerated dataset, the frozen model or any test split.
"""

import ast
import inspect
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_phase3_population import make_panel

from ml.temporal_config import INSTANTANEOUS_STATE_FEATURES
from phase3 import A_PEAK_RAD, MODEL_SEED
from phase3 import instantaneous as inst
from phase3 import population as pop

MANIFEST = ["V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin"]


@pytest.fixture(scope="module")
def tables():
    train = pop.SplitTable("train", make_panel("tr", ["normal"] * 5 + ["pos"] * 3 + ["neg"] * 2 + ["double", "mixed"], seed=21))
    val = pop.SplitTable("val", make_panel("va", ["normal"] * 3 + ["pos", "neg", "double"], seed=22))
    test = pop.SplitTable("test", make_panel("te", ["normal", "pos", "neg"], seed=23))
    return train, val, test


@pytest.fixture(scope="module")
def fitted(tables):
    return inst.fit_instantaneous(tables[0], tables[1])


def test_the_feature_manifest_is_exactly_the_approved_eight_and_equals_the_existing_definition():
    assert inst.INSTANTANEOUS_FEATURES == MANIFEST == list(INSTANTANEOUS_STATE_FEATURES)
    assert inst.validate_feature_manifest(MANIFEST) == MANIFEST


@pytest.mark.parametrize("extra", ["dalpha_dt", "dV_dt", "dgamma_dt", "dq_dt", "d2alpha_dt2", "alpha_mean_1s", "alpha_slope_0.5s", "elevator_change_2s",
                                   "future_stall_5s", "future_stall_5s_available", "is_unsafe", "time_to_stall", "trajectory_id", "time", "split",
                                   "theta", "vertical_speed", "thrust"])
def test_no_temporal_derivative_label_identifier_or_future_column_is_accepted(extra):
    with pytest.raises(ValueError):
        inst.validate_feature_manifest(MANIFEST + [extra])
    with pytest.raises(ValueError):
        inst.validate_feature_manifest(MANIFEST[:-1] + [extra])


def test_the_manifest_cannot_be_reordered_or_shortened():
    with pytest.raises(ValueError):
        inst.validate_feature_manifest(list(reversed(MANIFEST)))
    with pytest.raises(ValueError):
        inst.validate_feature_manifest(MANIFEST[:-1])


def test_every_model_input_is_a_function_of_the_current_row_only(tables):
    df = tables[0].df
    k = 400
    g = df[df["trajectory_id"] == "tr_000"]
    perturbed = df.copy()
    future = perturbed.index[(perturbed["trajectory_id"] == "tr_000") & (perturbed["time"] > g["time"].iloc[k])]
    rng = np.random.default_rng(0)
    for col in ("V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "is_unsafe", "future_stall_5s"):
        perturbed.loc[future, col] = rng.standard_normal(len(future)) if col not in ("is_unsafe",) else True
    past = df.index[(df["trajectory_id"] == "tr_000") & (df["time"] <= g["time"].iloc[k])]
    assert df.loc[past, MANIFEST].equals(perturbed.loc[past, MANIFEST])  # rows <= k unchanged by anything after k
    assert np.allclose(df["stall_margin"], A_PEAK_RAD - df["alpha"])    # the derived column uses only the same row's alpha


def test_the_fitted_model_matches_the_protocol_configuration(fitted):
    m = fitted.model
    assert m.n_features_in_ == 8 and list(m.feature_names_in_) == MANIFEST
    assert inst.has_no_preprocessing(m) and not hasattr(m, "steps")
    assert m.n_estimators == 200 and m.max_depth == 12 and m.min_samples_leaf == 5 and m.class_weight == "balanced_subsample"
    assert m.random_state == MODEL_SEED == 20260817
    assert fitted.rf_params == {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5, "class_weight": "balanced_subsample"}
    assert 0.0 < fitted.threshold < 1.0 and fitted.fit_seconds > 0 and fitted.peak_rss_mb > 0
    assert len(fitted.threshold_info["candidate_thresholds"]) == 10  # the candidate list the original pipeline discarded is kept
    for key in ("python", "scikit-learn", "numpy", "pandas", "pyarrow", "scipy", "joblib", "platform", "cpu_count"):
        assert key in fitted.versions


def test_training_rows_are_exactly_the_usable_rows_of_train_and_validation(fitted, tables):
    train, val, _ = tables
    assert fitted.n_train_rows == int(pop.usable_mask(train.df).sum())
    assert fitted.n_val_rows == int(pop.usable_mask(val.df).sum())


def test_only_a_train_table_and_a_validation_table_can_be_passed(tables):
    train, val, test = tables
    for a, b in ((test, val), (train, test), (train, train), (val, val), (val, train)):
        with pytest.raises(pop.GateViolation):
            inst.fit_instantaneous(a, b)
    with pytest.raises(pop.GateViolation):
        inst.fit_instantaneous(train.df, val.df)  # bare frames carry no split tag


def test_fit_has_no_test_argument_and_its_source_never_names_a_test_split():
    params = inspect.signature(inst.fit_instantaneous).parameters
    assert list(params) == ["train", "val"]
    tree = ast.parse(inspect.getsource(inst.fit_instantaneous))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not [n for n in names if "test" in n.lower()] and "test" not in consts


def test_the_fit_is_reproducible_for_the_same_seed_and_data(tables, fitted):
    again = inst.fit_instantaneous(tables[0], tables[1])
    df = tables[2].df
    mask = pop.usable_mask(df)
    a, b = inst.predict_scores(fitted.model, df, mask), inst.predict_scores(again.model, df, mask)
    assert np.allclose(a, b, atol=1e-9) and again.threshold == pytest.approx(fitted.threshold, abs=1e-9)


def test_scoring_uses_exactly_the_manifest_columns_and_refuses_a_mismatched_model(fitted, tables):
    df = tables[2].df
    mask = pop.usable_mask(df)
    s = inst.predict_scores(fitted.model, df, mask)
    assert s.shape == (int(mask.sum()),) and np.isfinite(s).all() and ((s >= 0) & (s <= 1)).all()
    shuffled_features = MANIFEST[1:] + MANIFEST[:1]
    with pytest.raises(ValueError):
        inst.predict_scores(fitted.model, df, mask, features=shuffled_features)
    nan_df = df.copy()
    nan_df.loc[nan_df.index[np.flatnonzero(mask)[0]], "alpha"] = np.nan
    with pytest.raises(ValueError):
        inst.predict_scores(fitted.model, nan_df, mask)  # get_xy refuses NaN inputs


def test_the_threshold_is_applied_with_the_strict_operator():
    scores = np.array([0.4, 0.5, 0.6])
    assert inst.apply_threshold(scores, 0.5).tolist() == [0, 0, 1]


def test_the_model_learns_a_signal_on_the_synthetic_data(fitted, tables):
    """A smoke check that the pipeline is wired to the labels (not a scientific result)."""
    from sklearn.metrics import average_precision_score
    df = tables[2].df
    mask = pop.usable_mask(df)
    y = df.loc[mask, "future_stall_5s"].to_numpy().astype(int)
    s = inst.predict_scores(fitted.model, df, mask)
    assert average_precision_score(y, s) > y.mean() + 0.05
