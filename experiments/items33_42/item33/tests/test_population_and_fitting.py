"""Population identity, split isolation, threshold selection without test access, failure recording and the single-shot
ledger (PROTOCOL.md sections 5, 6, 7, 11). Synthetic only; the stand-in forest does no learning."""

import inspect

import numpy as np
import pandas as pd
import pytest

from item33 import OUTPUT_ROOT_RELPATH, SEEDS, FROZEN_MODEL_RELPATH
from item33 import conditions as cond
from item33 import fitting, population as pop
from item33.guards import GateViolation, DataIntegrityError
from ml.calibration import select_threshold_train_then_val
from synth import StubForest, make_manifest, make_metadata, make_panel, make_splits


@pytest.fixture(scope="module")
def splits():
    return make_splits()


def tables(splits):
    return {s: pop.SplitTable(split=s, df=df) for s, df in splits.items()}


# --- population ---------------------------------------------------------------------------------------

def test_the_usable_population_is_label_available_and_a_full_window(splits):
    for s, df in splits.items():
        n_traj = df["trajectory_id"].nunique()
        assert int(pop.usable_mask(df).sum()) == n_traj * 200            # rows 100..299 of 800 per trajectory


def test_the_population_does_not_depend_on_the_condition_features(splits):
    df = splits["test"]
    mask = pop.usable_mask(df)
    for c in cond.CONDITION_ORDER:
        x = cond.select_columns(df.loc[mask], c)
        assert len(x) == int(mask.sum())                                  # selecting columns never changes the rows


def test_key_hash_is_deterministic_and_order_sensitive(splits):
    sub = splits["test"].loc[pop.usable_mask(splits["test"])].reset_index(drop=True)
    k = pop.row_keys(sub)
    assert pop.key_hash(k) == pop.key_hash(pop.row_keys(sub.copy()))
    swapped = pd.concat([sub.iloc[200:400], sub.iloc[:200], sub.iloc[400:]], ignore_index=True)
    assert pop.key_hash(pop.row_keys(swapped)) != pop.key_hash(k)
    shifted = sub.copy(); shifted.loc[5, "time"] = shifted.loc[5, "time"] + 0.5
    with pytest.raises(pop.KeyMismatchError):
        pop.key_hash(pop.row_keys(shifted))


def test_identical_populations_pass_and_a_dropped_row_is_caught(splits):
    sub = splits["test"].loc[pop.usable_mask(splits["test"])].reset_index(drop=True)
    k = pop.row_keys(sub)
    h = pop.assert_identical_populations({c: k for c in cond.CONDITION_ORDER})
    assert h == pop.key_hash(k)
    short = pop.row_keys(sub.drop(index=7).reset_index(drop=True))
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_identical_populations({"C0": k, "C1": short})


def test_trajectory_ids_are_disjoint_across_the_three_synthetic_splits(splits):
    ids = {s: set(df["trajectory_id"].unique()) for s, df in splits.items()}
    pop.assert_no_trajectory_overlap(ids)
    leaky = dict(ids); leaky["test"] = leaky["test"] | {next(iter(ids["train"]))}
    with pytest.raises(Exception):
        pop.assert_no_trajectory_overlap(leaky)


def test_load_split_refuses_a_split_outside_the_whitelist_before_reading(splits):
    calls = []
    reader = lambda path, columns: (calls.append(path), splits["train"][list(columns)])[1]
    with pytest.raises(GateViolation):
        pop.load_split("/nowhere", "test", ["alpha"], allowed_splits=("train", "val"), reader=reader)
    assert calls == []                                                       # the reader was never called
    t = pop.load_split("/nowhere", "train", ["alpha", "trajectory_id"], allowed_splits=("train", "val"), reader=reader)
    assert t.split == "train" and len(calls) == 1 and list(t.df.columns) == ["alpha", "trajectory_id"]
    with pytest.raises(ValueError):
        pop.load_split("/nowhere", "holdout", ["alpha"], allowed_splits=("train",), reader=reader)


def test_load_split_rejects_a_reader_that_omits_a_requested_column(splits):
    with pytest.raises(DataIntegrityError):
        pop.load_split("/x", "train", ["alpha", "missing_col"], ("train",), reader=lambda p, columns: splits["train"][["alpha"]])


def test_regime_mapping_and_strata(splits):
    meta = make_metadata(splits)
    traj = pd.unique(splits["test"]["trajectory_id"])
    m = pop.regime_of_trajectories(traj, meta)
    assert set(m) == set(traj)
    sizes = pop.stratum_sizes(m)
    assert sum(sizes.values()) == len(traj) and list(sizes) == sorted(sizes)
    with pytest.raises(DataIntegrityError):
        pop.regime_of_trajectories(list(traj) + ["unknown_traj"], meta)
    with pytest.raises(DataIntegrityError):
        pop.regime_of_trajectories(traj, pd.concat([meta, meta.iloc[:1]]))
    with pytest.raises(DataIntegrityError):
        pop.stratum_sizes({})


def test_column_constancy_and_training_medians(splits):
    c = pop.column_constancy(splits["train"], "throttle")
    assert c["n_trajectories"] == 10 and c["n_constant_within_trajectory"] == 10 and c["n_distinct_constant_values"] == 10
    df = pd.DataFrame({"a": [1.0, 2.0, 100.0, 4.0], "b": [5.0, 5.0, 5.0, 9.0]})
    med = pop.training_medians(df, ["a", "b"], [True, True, False, True])
    assert med == {"a": 2.0, "b": 5.0}                                      # the masked-out row (100.0) is not used
    with pytest.raises(DataIntegrityError):
        pop.training_medians(pd.DataFrame({"a": [1.0, np.nan]}), ["a"], [True, True])


# --- fitting --------------------------------------------------------------------------------------------

def test_the_fit_signature_has_no_test_argument():
    assert list(inspect.signature(fitting.fit_condition).parameters) == ["condition", "seed", "train", "val", "builder", "keep_scores"]
    assert "test" not in " ".join(inspect.signature(fitting.fit_condition).parameters)


def test_fit_refuses_wrong_split_tags_and_unlisted_seeds(splits):
    t = tables(splits)
    with pytest.raises(GateViolation):
        fitting.fit_condition("C0", SEEDS[0], t["test"], t["val"], builder=StubForest)
    with pytest.raises(GateViolation):
        fitting.fit_condition("C0", SEEDS[0], t["train"], t["test"], builder=StubForest)
    with pytest.raises(GateViolation):
        fitting.fit_condition("C0", SEEDS[0], t["val"], t["train"], builder=StubForest)
    with pytest.raises(GateViolation):
        fitting.fit_condition("C0", 12345, t["train"], t["val"], builder=StubForest)


@pytest.mark.parametrize("c", cond.CONDITION_ORDER)
def test_each_condition_is_fitted_on_exactly_its_columns_and_usable_rows(splits, c):
    t = tables(splits)
    seen = {}
    def builder(seed):
        m = StubForest(seed); seen["m"] = m; return m
    fit = fitting.fit_condition(c, SEEDS[1], t["train"], t["val"], builder=builder)
    assert seen["m"].columns == cond.features_for(c) == fit.features
    assert fit.n_train_rows == int(pop.usable_mask(splits["train"]).sum())
    assert fit.n_val_rows == int(pop.usable_mask(splits["val"]).sum())
    assert fit.seed == SEEDS[1] and fit.rf_params == fitting.RF_PARAMS
    assert fit.record()["status"] == "FITTED" and fit.record()["n_features"] == cond.EXPECTED_N_FEATURES[c]


def test_the_threshold_comes_from_the_existing_train_then_validation_procedure(splits):
    t = tables(splits)
    fit = fitting.fit_condition("C0", SEEDS[0], t["train"], t["val"], builder=StubForest)
    y_tr = splits["train"].loc[pop.usable_mask(splits["train"]), "future_stall_5s"].to_numpy().astype(int)
    y_va = splits["val"].loc[pop.usable_mask(splits["val"]), "future_stall_5s"].to_numpy().astype(int)
    thr, info = select_threshold_train_then_val(y_tr, fit.train_score, y_va, fit.val_score)
    assert fit.threshold == thr and fit.threshold_info == info and info["method"] == "top_k_train_f1_then_best_val_f1"


def test_threshold_selection_never_sees_test_labels(splits, monkeypatch):
    t = tables(splits)
    seen = {}
    real = fitting.select_threshold_train_then_val
    def spy(y_tr, s_tr, y_va, s_va, **kw):
        seen["lens"] = (len(y_tr), len(y_va)); seen["labels"] = (y_tr, y_va)
        return real(y_tr, s_tr, y_va, s_va, **kw)
    monkeypatch.setattr(fitting, "select_threshold_train_then_val", spy)
    poisoned_test = splits["test"].copy(); poisoned_test["future_stall_5s"] = 1.0       # would change any result that read it
    fit1 = fitting.fit_condition("C0", SEEDS[0], t["train"], t["val"], builder=StubForest)
    t2 = dict(t); t2["test"] = pop.SplitTable("test", poisoned_test)
    fit2 = fitting.fit_condition("C0", SEEDS[0], t2["train"], t2["val"], builder=StubForest)
    assert fit1.threshold == fit2.threshold
    assert seen["lens"] == (fit1.n_train_rows, fit1.n_val_rows)


def test_nan_in_a_selected_feature_is_refused(splits):
    t = tables(splits)
    bad = splits["train"].copy()
    bad.loc[bad.index[150], "alpha"] = np.nan                                   # row 150 of the first trajectory is a usable row
    with pytest.raises(ValueError):
        fitting.fit_condition("C0", SEEDS[0], pop.SplitTable("train", bad), t["val"], builder=StubForest)


def test_failed_fits_are_recorded_not_dropped_and_protocol_violations_propagate(splits):
    t = tables(splits)
    calls = []
    def broken(seed):
        calls.append(seed); raise RuntimeError("synthetic failure")
    out = fitting.try_fit("C0", SEEDS[0], t["train"], t["val"], builder=broken)
    assert isinstance(out, fitting.FitFailure) and out.record()["status"] == "FAILED"
    assert out.error_type == "RuntimeError" and "synthetic failure" in out.error and "Traceback" in out.traceback
    assert calls == [SEEDS[0]]                                                    # not retried
    with pytest.raises(GateViolation):
        fitting.try_fit("C0", 1, t["train"], t["val"], builder=StubForest)       # seed not pre-specified


def test_strict_threshold_operator():
    s = np.array([0.1, 0.5, 0.5, 0.9])
    assert fitting.apply_threshold(s, 0.5).tolist() == [0, 0, 0, 1]


def test_scoring_requires_the_test_tag_and_matching_feature_names(splits):
    t = tables(splits)
    fit = fitting.fit_condition("C1", SEEDS[0], t["train"], t["val"], builder=StubForest)
    with pytest.raises(GateViolation):
        fitting.score_test(fit, t["val"])
    score = fitting.score_test(fit, t["test"])
    assert len(score) == int(pop.usable_mask(splits["test"]).sum()) and np.isfinite(score).all()
    with pytest.raises(ValueError):
        fitting.score_rows(fit.model, splits["test"], cond.features_for("C0"), pop.usable_mask(splits["test"]))


def test_the_single_shot_ledger_allows_one_scoring_per_model(tmp_path):
    run = tmp_path / OUTPUT_ROOT_RELPATH / "run_1"
    led = fitting.SingleShotLedger(run, tmp_path)
    led.claim("C0", SEEDS[0])
    led.claim("C0", SEEDS[1])
    with pytest.raises(GateViolation):
        led.claim("C0", SEEDS[0])
    with pytest.raises(GateViolation):
        fitting.SingleShotLedger(tmp_path / "outside", tmp_path).claim("C0", 1)


def test_models_are_never_written_to_the_frozen_model_path_or_over_an_existing_file(tmp_path):
    with pytest.raises(GateViolation):
        fitting.save_model_exclusive(StubForest(1), tmp_path / FROZEN_MODEL_RELPATH, tmp_path)
    p = tmp_path / OUTPUT_ROOT_RELPATH / "run_1" / "m.joblib"
    fitting.save_model_exclusive(StubForest(1), p, tmp_path)
    with pytest.raises(FileExistsError):
        fitting.save_model_exclusive(StubForest(2), p, tmp_path)


def test_the_seeded_builder_reproduces_the_existing_parameter_set_without_fitting():
    from ml import config
    from ml.models import build_random_forest
    ours = fitting.build_forest(config.ML_SEED).get_params()
    theirs = build_random_forest(**fitting.RF_PARAMS).get_params()          # instantiation only; nothing is fitted
    assert ours == theirs
    assert fitting.build_forest(SEEDS[3]).get_params()["random_state"] == SEEDS[3]
    for bad in (-1, 2 ** 32, 1.5):
        with pytest.raises(ValueError):
            fitting.build_forest(bad)
