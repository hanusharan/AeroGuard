"""v0.3-specific orchestration helpers for the final temporal
early-warning experiment (v0.2 vs v0.3).

Every DATASET-VERSION-AGNOSTIC piece of Stage-4 infrastructure is reused
UNCHANGED, by direct import, from ml/temporal_experiment.py,
ml/temporal_features.py, ml/metrics.py, ml/events.py, ml/models.py, and
ml/calibration.py: get_xy's leakage guard, fit_rf_and_threshold's
TRAIN-then-VAL threshold selection, evaluate_on_test's metrics/lead-time/
event-level bundle, the episode/false-alarm logic, and the physics/
information diagnosis. Only the pieces that are inherently
dataset-version-specific are added here:

  - Model A ("instantaneous baseline"): v0.2's Model A was a FROZEN,
    already-existing Stage-3 model, re-scored only. No such frozen
    model exists for v0.3 (Stage 3 was never run on v0.3 data), so the
    correct like-for-like analogue is to freshly fit the SAME
    architecture/feature-set/hyperparameters on v0.3's own train split
    -- not a methodology deviation, the honest equivalent of what v0.2
    did with its own already-trained model.
  - Metadata merges (regime, initial_airspeed) against
    trajectory_metadata_v3.csv instead of trajectory_metadata_v2.csv.
  - The Phase-7 generalization check, generalized to accept WHICH
    regime to exclude from TRAIN (v0.2 hardcoded 'stall'; this
    experiment's critical check excludes 'gradual_approach_v3' instead
    -- see outputs/ml_v03/v03_temporal_ml_report.md Sec 11).

Nothing here fits anything on TEST -- same discipline as
ml/temporal_experiment.py.
"""

from typing import Dict, List

import pandas as pd

from . import temporal_config_v03 as v3cfg
from .metrics import regime_breakdown, airspeed_bin_breakdown
from .temporal_experiment import evaluate_on_test, fit_rf_and_threshold, get_xy, lead_time_bucket_analysis_fine
from .temporal_features import common_subset_mask, usable_mask_for_window


# ---------------------------------------------------------------------------
# Model A: instantaneous-state baseline, freshly fit on v0.3 (see module
# docstring for why "freshly fit" is the correct v0.2-Model-A analogue).
# ---------------------------------------------------------------------------

def fit_model_a_instantaneous(splits: dict, rf_params: dict, mask_fn, verbose: bool = True) -> dict:
    """mask_fn(df) -> boolean row mask; pass a v0.3 common-subset mask
    (e.g. lambda df: common_subset_mask(df, v3cfg.HISTORY_WINDOWS_S)) so
    Model A is evaluated on the SAME row population as B/D in the
    common-subset ablation table (mirrors v0.2's A_frozen_baseline,
    which was also scored on the common-subset population)."""
    train, val, test = splits["train"], splits["val"], splits["test"]
    feats = v3cfg.INSTANTANEOUS_STATE_FEATURES

    train_mask, val_mask, test_mask = mask_fn(train), mask_fn(val), mask_fn(test)
    Xtr, ytr, _ = get_xy(train, feats, train_mask)
    Xv, yv, _ = get_xy(val, feats, val_mask)
    Xte, yte, test_sub = get_xy(test, feats, test_mask)

    model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
    res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)
    res["feature_columns"], res["n_features"] = feats, len(feats)
    res["note"] = ("Freshly fit on v0.3's own train split -- same RF architecture/hyperparameters "
                    "and same 8-feature instantaneous-state set as v0.2's Model A; v0.2's Model A was "
                    "a frozen pre-existing model re-scored, not retrained, because it already existed. "
                    "No frozen v0.3 baseline exists, so fitting fresh here is the correct like-for-like "
                    "analogue, not a methodology deviation.")
    if verbose:
        print(f"  A (v0.3, retrained): PR-AUC={res['test_metrics']['pr_auc']:.4f}")
    return {"model": model, "threshold": thr, "result": res, "proba": proba, "pred": pred, "test_sub": test_sub, "test_mask": test_mask}


# ---------------------------------------------------------------------------
# Common-subset ablation: B + D_w for w in v3cfg.HISTORY_WINDOWS_S (Model C
# deliberately skipped -- v0.2 already showed it never helps, see
# ml/temporal_config_v03.py's module docstring).
# ---------------------------------------------------------------------------

def run_common_subset_ablation_v03(splits: dict, rf_params: dict, windows_s: List[float] = None, verbose: bool = True):
    """Returns (results, a_bundle) -- results is the JSON-serializable
    metrics dict; a_bundle carries Model A's fitted model/proba/pred/
    test_sub so callers (e.g. the PR-curve plot) don't need to refit it."""
    windows_s = windows_s or v3cfg.HISTORY_WINDOWS_S
    train, val, test = splits["train"], splits["val"], splits["test"]

    common_train_mask = common_subset_mask(train, windows_s)
    common_val_mask = common_subset_mask(val, windows_s)
    common_test_mask = common_subset_mask(test, windows_s)

    population = {
        "note": (f"Rows with a full history window at the LARGEST window under comparison "
                 f"({max(windows_s)}s) -- identical row population for A/B/D in this table."),
        "train_rows": int(common_train_mask.sum()), "val_rows": int(common_val_mask.sum()), "test_rows": int(common_test_mask.sum()),
        "test_trajectories": int(test.loc[common_test_mask, "trajectory_id"].nunique()),
        "test_trajectories_total": int(test["trajectory_id"].nunique()),
    }
    if verbose:
        print(f"  common-subset population: train={population['train_rows']:,} val={population['val_rows']:,} test={population['test_rows']:,} "
              f"({population['test_trajectories']}/{population['test_trajectories_total']} test trajectories)")

    results: Dict[str, dict] = {"common_subset_population": population}

    a_bundle = fit_model_a_instantaneous(splits, rf_params, lambda df: common_subset_mask(df, windows_s), verbose=verbose)
    results["A_v03_retrained"] = a_bundle["result"]

    Xtr, ytr, _ = get_xy(train, v3cfg.STATE_DERIVATIVE_FEATURES, common_train_mask)
    Xv, yv, _ = get_xy(val, v3cfg.STATE_DERIVATIVE_FEATURES, common_val_mask)
    Xte, yte, test_sub = get_xy(test, v3cfg.STATE_DERIVATIVE_FEATURES, common_test_mask)
    model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
    res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)
    res["feature_columns"], res["n_features"] = v3cfg.STATE_DERIVATIVE_FEATURES, len(v3cfg.STATE_DERIVATIVE_FEATURES)
    results["B_state_derivatives"] = res
    if verbose:
        print(f"  B_state_derivatives: PR-AUC={res['test_metrics']['pr_auc']:.4f}")

    for w in windows_s:
        wtag = v3cfg._fmt(w)
        feats = v3cfg.model_d_features(w)
        Xtr, ytr, _ = get_xy(train, feats, common_train_mask)
        Xv, yv, _ = get_xy(val, feats, common_val_mask)
        Xte, yte, test_sub = get_xy(test, feats, common_test_mask)
        model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
        res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)
        res["feature_columns"], res["n_features"] = feats, len(feats)
        key = f"D_{wtag}s"
        results[key] = res
        b1 = next((r["recall"] for r in res["lead_time_recall_bucket"] if r["bucket"] == "1-2s"), float("nan"))
        b2 = next((r["recall"] for r in res["lead_time_recall_bucket"] if r["bucket"] == "2-3s"), float("nan"))
        b3 = next((r["recall"] for r in res["lead_time_recall_bucket"] if r["bucket"] == "3-4s"), float("nan"))
        if verbose:
            print(f"  {key}: PR-AUC={res['test_metrics']['pr_auc']:.4f} recall(1-2s)={b1:.3f} recall(2-3s)={b2:.3f} recall(3-4s)={b3:.3f}")

    return results, a_bundle


# ---------------------------------------------------------------------------
# Primary model: Model D at the primary window, own realistic-scale
# population (mirrors ml.temporal_experiment.run_primary_model exactly).
# ---------------------------------------------------------------------------

def run_primary_model_v03(splits: dict, rf_params: dict, window_s: float, verbose: bool = True):
    train, val, test = splits["train"], splits["val"], splits["test"]
    feats = v3cfg.model_d_features(window_s)

    train_mask = usable_mask_for_window(train, window_s)
    val_mask = usable_mask_for_window(val, window_s)
    test_mask = usable_mask_for_window(test, window_s)

    Xtr, ytr, _ = get_xy(train, feats, train_mask)
    Xv, yv, _ = get_xy(val, feats, val_mask)
    Xte, yte, test_sub = get_xy(test, feats, test_mask)

    if verbose:
        print(f"  primary model population (window={window_s}s, own usable rows): "
              f"train={len(Xtr):,} val={len(Xv):,} test={len(Xte):,} "
              f"({test.loc[test_mask, 'trajectory_id'].nunique()}/{test['trajectory_id'].nunique()} test trajectories)")

    model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
    res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)
    res["feature_columns"], res["n_features"], res["window_s"] = feats, len(feats), window_s
    res["population"] = {
        "train_rows": int(train_mask.sum()), "val_rows": int(val_mask.sum()), "test_rows": int(test_mask.sum()),
        "test_trajectories": int(test.loc[test_mask, "trajectory_id"].nunique()),
        "test_trajectories_total": int(test["trajectory_id"].nunique()),
    }
    return model, thr, res, proba, pred, test_sub, test_mask


# ---------------------------------------------------------------------------
# Regime / airspeed breakdown against v0.3's OWN metadata file.
# ---------------------------------------------------------------------------

def load_test_metadata_v03(test_sub: pd.DataFrame) -> pd.DataFrame:
    metadata = pd.read_csv(v3cfg.METADATA_PATH)[["trajectory_id", "generation_mode", "initial_airspeed"]]
    return test_sub.merge(metadata, on="trajectory_id", how="left")


def run_regime_airspeed_breakdown_v03(test_sub: pd.DataFrame, y_true, pred, proba):
    merged = load_test_metadata_v03(test_sub)
    regime_df = regime_breakdown(y_true, pred, proba, merged["generation_mode"].to_numpy())
    airspeed_df = airspeed_bin_breakdown(y_true, pred, merged["initial_airspeed"].to_numpy())

    lead_time_by_regime_rows = []
    for r in pd.unique(merged["generation_mode"]):
        m = (merged["generation_mode"] == r).to_numpy()
        df = lead_time_bucket_analysis_fine(test_sub.loc[m, "time_to_stall"].to_numpy(), y_true[m], pred[m])
        df["regime"] = r
        lead_time_by_regime_rows.append(df)
    lead_time_by_regime = pd.concat(lead_time_by_regime_rows, ignore_index=True)

    return regime_df, airspeed_df, lead_time_by_regime


# ---------------------------------------------------------------------------
# Phase 7: generalization check, generalized to any excluded regime.
# The critical run for this experiment excludes 'gradual_approach_v3'.
# ---------------------------------------------------------------------------

def run_generalization_check_v03(splits: dict, rf_params: dict, window_s: float, exclude_regime: str, verbose: bool = True) -> dict:
    train, val, test = splits["train"], splits["val"], splits["test"]
    metadata = pd.read_csv(v3cfg.METADATA_PATH)[["trajectory_id", "generation_mode"]]

    train_regime = train.merge(metadata, on="trajectory_id", how="left")["generation_mode"].to_numpy()
    feats = v3cfg.model_d_features(window_s)

    excl_train_mask = usable_mask_for_window(train, window_s) & (train_regime != exclude_regime)
    val_mask = usable_mask_for_window(val, window_s)
    test_mask = usable_mask_for_window(test, window_s)

    Xtr, ytr, _ = get_xy(train, feats, excl_train_mask)
    Xv, yv, _ = get_xy(val, feats, val_mask)
    Xte, yte, test_sub = get_xy(test, feats, test_mask)

    if verbose:
        n_traj_excluded = train.loc[usable_mask_for_window(train, window_s) & (train_regime == exclude_regime), "trajectory_id"].nunique()
        print(f"  generalization check: trained on {len(Xtr):,} rows, EXCLUDING {n_traj_excluded} '{exclude_regime}' "
              f"train trajectories entirely; evaluating on the full TEST split (including '{exclude_regime}')")

    model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
    res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)

    merged = load_test_metadata_v03(test_sub)
    regime_df = regime_breakdown(yte, pred, proba, merged["generation_mode"].to_numpy())

    return {
        "description": (f"Model D ({window_s}s) retrained with ALL '{exclude_regime}'-regime trajectories removed "
                         "from TRAIN (val/test unchanged); tests whether the multi-second precursor is learned as "
                         "transferable physics or is regime-specific memorization."),
        "train_population": {
            "n_rows": int(excl_train_mask.sum()),
            "n_trajectories": int(train.loc[excl_train_mask, "trajectory_id"].nunique()),
        },
        "excluded_regime": exclude_regime,
        "threshold": thr,
        "test_metrics": res["test_metrics"],
        "event_level": res["event_level"],
        "fraction_of_events_detected_at_least": res["fraction_of_events_detected_at_least"],
        "lead_time_recall_bucket": res["lead_time_recall_bucket"],
        "regime_breakdown": regime_df.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Phase 4/8: fraction of events detected at least X seconds early, extended
# with the 0.5s threshold the report explicitly asks for (v0.2's version only
# covered whole-second thresholds 1..5).
# ---------------------------------------------------------------------------

def fractions_detected_at_least_v03(event_results, horizon_s: float) -> Dict[str, float]:
    import numpy as np
    n_events = len(event_results)
    if n_events == 0:
        return {}
    lead_times = np.array([r.lead_time_s if r.warned else -1.0 for r in event_results])
    out = {}
    for x in (0.5, 1, 2, 3, 4, 5):
        if x > horizon_s + 1e-9:
            continue
        out[f">={x}s"] = float(np.sum(lead_times >= x) / n_events)
    return out
