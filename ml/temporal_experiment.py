"""Stage 4 orchestration: the Model A/B/C/D hierarchy evaluated across
history windows, lead-time analysis, false-alarm control, regime/
airspeed/generalization checks, and the physics/information diagnosis.

Nothing here fits anything on TEST -- every model is tuned/thresholded
on TRAIN/VAL only, exactly mirroring ml/training.py and
ml/ablation.py's existing discipline. See
scripts/run_temporal_experiment.py for the driver that calls these
functions in order and writes outputs/ml_temporal/.
"""

import json
import os
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score

from . import temporal_config as tcfg
from .calibration import select_threshold_train_then_val
from .events import aggregate_event_results, compute_event_level_results, compute_false_alarm_stats
from .evaluation import compute_classification_metrics
from .metrics import airspeed_bin_breakdown, regime_breakdown, threshold_sweep
from .models import build_random_forest
from .temporal_features import common_subset_mask, usable_mask_for_window

# Finer lead-time buckets than the baseline's (Task 6 asks explicitly for
# a 0-0.5s / 0.5-1s split in addition to the existing 1s-wide buckets).
LEAD_TIME_BINS_FINE: List[Tuple[float, float]] = [(0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 4), (4, 5)]

DIAGNOSIS_VARIABLES: List[str] = ["alpha", "dalpha_dt", "V", "dV_dt", "gamma", "dq_dt", "elevator", "stall_margin"]
DIAGNOSIS_LEAD_TIMES_S: List[float] = [1, 2, 3, 4, 5]


class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        return super().default(obj)


def lead_time_bucket_analysis_fine(time_to_stall: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Same procedure as ml.metrics.lead_time_bucket_analysis, with the
    finer Task-6 bucket edges."""
    from .metrics import lead_time_bucket_analysis
    return lead_time_bucket_analysis(time_to_stall, y_true, y_pred, bins=LEAD_TIME_BINS_FINE)


# ---------------------------------------------------------------------------
# Core fit / evaluate helpers (reused by every model in the hierarchy)
# ---------------------------------------------------------------------------

def get_xy(df: pd.DataFrame, feature_cols: List[str], mask: pd.Series, target_col: str = tcfg.TARGET_COL):
    """Mirrors ml/features.py:get_xy's leakage guard, specialized for
    the temporal feature panel's own row-population masks."""
    forbidden = set(feature_cols) & {tcfg.TARGET_COL, tcfg.TARGET_AVAILABLE_COL, "is_unsafe",
                                      "trajectory_id", "time", "split", "time_to_stall"}
    if forbidden:
        raise ValueError(f"Feature set includes forbidden column(s): {sorted(forbidden)}")
    sub = df.loc[mask]
    X = sub[feature_cols].copy()
    y = sub[target_col].to_numpy().astype(int)
    if X.isna().any().any():
        bad_cols = X.columns[X.isna().any()].tolist()
        raise ValueError(f"Unexpected NaN in feature columns after masking: {bad_cols}")
    return X, y, sub


def fit_rf_and_threshold(X_train, y_train, X_val, y_val, rf_params: dict):
    """TRAIN-fit, VAL-scored, TRAIN-then-VAL threshold selection. TEST
    is never referenced in this function."""
    model = build_random_forest(**rf_params)
    model.fit(X_train, y_train)
    train_proba = model.predict_proba(X_train)[:, 1]
    val_proba = model.predict_proba(X_val)[:, 1]
    threshold, threshold_info = select_threshold_train_then_val(y_train, train_proba, y_val, val_proba)
    return model, threshold, threshold_info


def fractions_detected_at_least(event_results, horizon_s: float) -> Dict[str, float]:
    """Task 6: fraction of ALL stall events (warned or not) detected
    with at least X seconds of lead time, for X in {1,2,3,4,5} (capped
    at the labeling horizon -- lead time is never credited beyond it,
    see ml/events.py's module docstring)."""
    n_events = len(event_results)
    if n_events == 0:
        return {}
    lead_times = np.array([r.lead_time_s if r.warned else -1.0 for r in event_results])
    out = {}
    for x in (1, 2, 3, 4, 5):
        if x > horizon_s + 1e-9:
            continue
        out[f">={x}s"] = float(np.sum(lead_times >= x) / n_events)
    return out


def evaluate_on_test(model, threshold: float, X_test, y_test: np.ndarray, test_sub: pd.DataFrame) -> Tuple[dict, np.ndarray, np.ndarray]:
    test_proba = model.predict_proba(X_test)[:, 1]
    test_pred = (test_proba > threshold).astype(int)
    metrics = compute_classification_metrics(y_test, test_pred, test_proba)
    lead_df = lead_time_bucket_analysis_fine(test_sub["time_to_stall"].to_numpy(), y_test, test_pred)
    event_results = compute_event_level_results(test_sub, test_pred, tcfg.LABELING_HORIZON_S)
    event_agg = aggregate_event_results(event_results)
    frac_early = fractions_detected_at_least(event_results, tcfg.LABELING_HORIZON_S)
    result = {
        "threshold": threshold,
        "test_metrics": metrics,
        "lead_time_recall_bucket": lead_df.to_dict(orient="records"),
        "event_level": event_agg,
        "fraction_of_events_detected_at_least": frac_early,
    }
    return result, test_proba, test_pred


# ---------------------------------------------------------------------------
# Hyperparameter tuning (ONE tuning pass, then hyperparameters are frozen
# and reused unchanged for every model in the hierarchy -- Task 4/
# mirrors ml/ablation.py's existing "isolate the feature effect, not a
# confounding hyperparameter change" philosophy).
# ---------------------------------------------------------------------------

TUNING_GRID = [
    {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5, "class_weight": "balanced_subsample"},
    {"n_estimators": 200, "max_depth": 20, "min_samples_leaf": 5, "class_weight": "balanced_subsample"},
]


def tune_rf_hyperparameters(splits: dict, tuning_window_s: float = 2.0, verbose: bool = True) -> Tuple[dict, list]:
    """Tunes on Model D at a single representative window
    (state + derivatives + temporal features -- the richest feature
    set actually used anywhere in the hierarchy), on the common-subset
    population, by VAL PR-AUC. TEST is never touched here."""
    from sklearn.metrics import average_precision_score

    train, val = splits["train"], splits["val"]
    feats = tcfg.model_d_features(tuning_window_s)
    train_mask = common_subset_mask(train)
    val_mask = common_subset_mask(val)
    Xtr, ytr, _ = get_xy(train, feats, train_mask)
    Xv, yv, _ = get_xy(val, feats, val_mask)

    log = []
    best_params, best_pr_auc = None, -np.inf
    for params in TUNING_GRID:
        model = build_random_forest(**params)
        model.fit(Xtr, ytr)
        val_proba = model.predict_proba(Xv)[:, 1]
        pr_auc = float(average_precision_score(yv, val_proba))
        log.append({"params": params, "val_pr_auc": pr_auc})
        if verbose:
            print(f"    tuning {params} -> VAL PR-AUC={pr_auc:.4f}")
        if pr_auc > best_pr_auc:
            best_pr_auc, best_params = pr_auc, params
    if verbose:
        print(f"  SELECTED (frozen for the whole hierarchy): {best_params}")
    return best_params, log


# ---------------------------------------------------------------------------
# Task 4/5/8: the fair, common-subset window ablation (B, C_w, D_w)
# ---------------------------------------------------------------------------

def evaluate_frozen_baseline(test_df: pd.DataFrame, mask: pd.Series) -> dict:
    """Re-scores the ALREADY-FROZEN Stage-3 baseline RF (not retrained)
    on this experiment's row population, for an honest side-by-side
    reference -- Model A exactly as it already exists."""
    from .train_baseline import CORE_FEATURES

    model = joblib.load(os.path.join(tcfg.BASELINE_MODELS_DIR, "random_forest.joblib"))
    with open(os.path.join(tcfg.BASELINE_OUTPUTS_DIR, "model_metrics.json")) as f:
        baseline_metrics = json.load(f)
    threshold = baseline_metrics["random_forest"]["threshold"]

    Xte, yte, test_sub = get_xy(test_df, CORE_FEATURES, mask)
    res, proba, pred = evaluate_on_test(model, threshold, Xte, yte, test_sub)
    res["feature_columns"] = CORE_FEATURES
    res["n_features"] = len(CORE_FEATURES)
    res["note"] = ("Frozen outputs/ml_baseline/models/random_forest.joblib, NOT retrained here -- "
                    "re-scored on this experiment's row population for reference only.")
    return res


def run_window_ablation(splits: dict, rf_params: dict, windows_s: List[float] = None, verbose: bool = True) -> Dict[str, dict]:
    windows_s = windows_s or tcfg.HISTORY_WINDOWS_S
    train, val, test = splits["train"], splits["val"], splits["test"]

    common_train_mask = common_subset_mask(train, windows_s)
    common_val_mask = common_subset_mask(val, windows_s)
    common_test_mask = common_subset_mask(test, windows_s)

    population = {
        "note": ("Rows with a full history window at the LARGEST window under comparison "
                 f"({max(windows_s)}s) -- required so every model in this table is trained and "
                 "evaluated on IDENTICAL rows (Task 5). This is a strictly easier/longer-trajectory "
                 "population than the primary test set -- see the primary-population model for a "
                 "realistic-scale number."),
        "train_rows": int(common_train_mask.sum()), "val_rows": int(common_val_mask.sum()), "test_rows": int(common_test_mask.sum()),
        "train_rows_pct_of_usable": float(common_train_mask.sum() / train[tcfg.TARGET_AVAILABLE_COL].sum()),
        "test_trajectories": int(test.loc[common_test_mask, "trajectory_id"].nunique()),
        "test_trajectories_total": int(test["trajectory_id"].nunique()),
    }
    if verbose:
        print(f"  common-subset population: train={population['train_rows']:,} val={population['val_rows']:,} test={population['test_rows']:,} "
              f"({population['test_trajectories']}/{population['test_trajectories_total']} test trajectories)")

    results: Dict[str, dict] = {"common_subset_population": population}

    results["A_frozen_baseline"] = evaluate_frozen_baseline(test, common_test_mask)
    if verbose:
        print(f"  A_frozen_baseline: PR-AUC={results['A_frozen_baseline']['test_metrics']['pr_auc']:.4f}")

    Xtr, ytr, _ = get_xy(train, tcfg.STATE_DERIVATIVE_FEATURES, common_train_mask)
    Xv, yv, _ = get_xy(val, tcfg.STATE_DERIVATIVE_FEATURES, common_val_mask)
    Xte, yte, test_sub = get_xy(test, tcfg.STATE_DERIVATIVE_FEATURES, common_test_mask)
    model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
    res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)
    res["feature_columns"], res["n_features"] = tcfg.STATE_DERIVATIVE_FEATURES, len(tcfg.STATE_DERIVATIVE_FEATURES)
    results["B_state_derivatives"] = res
    if verbose:
        print(f"  B_state_derivatives: PR-AUC={res['test_metrics']['pr_auc']:.4f}")

    for w in windows_s:
        wtag = tcfg._fmt(w)
        for prefix, feat_fn in (("C", tcfg.model_c_features), ("D", tcfg.model_d_features)):
            feats = feat_fn(w)
            Xtr, ytr, _ = get_xy(train, feats, common_train_mask)
            Xv, yv, _ = get_xy(val, feats, common_val_mask)
            Xte, yte, test_sub = get_xy(test, feats, common_test_mask)
            model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
            res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)
            res["feature_columns"], res["n_features"] = feats, len(feats)
            key = f"{prefix}_{wtag}s"
            results[key] = res
            b1 = next((r["recall"] for r in res["lead_time_recall_bucket"] if r["bucket"] == "1-2s"), float("nan"))
            b2 = next((r["recall"] for r in res["lead_time_recall_bucket"] if r["bucket"] == "2-3s"), float("nan"))
            if verbose:
                print(f"  {key}: PR-AUC={res['test_metrics']['pr_auc']:.4f} recall(1-2s)={b1:.3f} recall(2-3s)={b2:.3f}")

    return results


# ---------------------------------------------------------------------------
# Task 5 (item 1) / primary realistic-population model
# ---------------------------------------------------------------------------

def run_primary_model(splits: dict, rf_params: dict, window_s: float, verbose: bool = True):
    """Model D at ONE chosen window, trained/evaluated on ITS OWN
    maximal usable population (not the harder common-subset
    restriction) -- the 'realistic deployment scale' number Task 5
    explicitly asks not to conflate with the common-subset comparison."""
    train, val, test = splits["train"], splits["val"], splits["test"]
    feats = tcfg.model_d_features(window_s)

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
        "train_rows_pct_of_usable": float(train_mask.sum() / train[tcfg.TARGET_AVAILABLE_COL].sum()),
        "test_trajectories": int(test.loc[test_mask, "trajectory_id"].nunique()),
        "test_trajectories_total": int(test["trajectory_id"].nunique()),
    }
    val_proba = model.predict_proba(Xv)[:, 1]
    res["val_threshold_sweep"] = threshold_sweep(yv, val_proba).to_dict(orient="records")
    return model, thr, res, proba, pred, test_sub, test_mask


# ---------------------------------------------------------------------------
# Task 7: false-alarm control for the strongest candidate model
# ---------------------------------------------------------------------------

def run_false_alarm_analysis(test_sub: pd.DataFrame, y_true: np.ndarray, pred: np.ndarray) -> dict:
    n_test_trajectories = test_sub["trajectory_id"].nunique()
    episode_stats = compute_false_alarm_stats(test_sub, pred, n_test_trajectories)

    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    row_level_fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else float("nan")

    total_test_seconds = float(test_sub.groupby("trajectory_id")["time"].apply(lambda s: s.max() - s.min()).sum())
    false_alarms_per_minute = (episode_stats["n_false_alarm_episodes"] / (total_test_seconds / 60.0)) if total_test_seconds > 0 else float("nan")

    # Warning COMPOSITION by proximity to the nearest actual crossing
    # (NOT "precision by bucket" in the usual sense -- every row with
    # time_to_stall <= 5s has future_stall_5s==1 by construction, so a
    # warned row in that range is a true positive by definition; the
    # informative breakdown is how far from a real crossing the false
    # alarms tend to fire, which THIS decomposes).
    tts = test_sub["time_to_stall"].to_numpy()
    warned = pred.astype(bool)
    n_total_warned_rows = int(warned.sum())
    rows = []
    for lo, hi in LEAD_TIME_BINS_FINE:
        m = warned & (tts > lo) & (tts <= hi)
        rows.append({
            "time_to_nearest_crossing_bucket": f"{lo}-{hi}s", "true_positive_by_construction": True,
            "n_warned_rows": int(m.sum()),
            "fraction_of_all_warnings": (int(m.sum()) / n_total_warned_rows) if n_total_warned_rows else float("nan"),
        })
    m_far = warned & (np.isnan(tts) | (tts > 5.0))
    rows.append({
        "time_to_nearest_crossing_bucket": ">5s_or_no_future_crossing", "true_positive_by_construction": False,
        "n_warned_rows": int(m_far.sum()),
        "fraction_of_all_warnings": (int(m_far.sum()) / n_total_warned_rows) if n_total_warned_rows else float("nan"),
    })

    return {
        "episode_level": episode_stats,
        "row_level_false_positive_rate": row_level_fpr,
        "false_alarms_per_minute": false_alarms_per_minute,
        "total_test_trajectory_seconds": total_test_seconds,
        "warning_composition_by_time_to_nearest_crossing": rows,
    }


# ---------------------------------------------------------------------------
# Task 10: regime / airspeed post-hoc breakdown (never a model input)
# ---------------------------------------------------------------------------

def load_test_metadata(test_sub: pd.DataFrame) -> pd.DataFrame:
    metadata = pd.read_csv(tcfg.METADATA_PATH)[["trajectory_id", "generation_mode", "initial_airspeed"]]
    return test_sub.merge(metadata, on="trajectory_id", how="left")


def run_regime_airspeed_breakdown(test_sub: pd.DataFrame, y_true: np.ndarray, pred: np.ndarray, proba: np.ndarray):
    merged = load_test_metadata(test_sub)
    regime_df = regime_breakdown(y_true, pred, proba, merged["generation_mode"].to_numpy())
    airspeed_df = airspeed_bin_breakdown(y_true, pred, merged["initial_airspeed"].to_numpy())

    lead_time_by_regime_rows = []
    for r in pd.unique(merged["generation_mode"]):
        m = (merged["generation_mode"] == r).to_numpy()
        df = lead_time_bucket_analysis_fine(test_sub.loc[m, "time_to_stall"].to_numpy(), y_true[m], pred[m])
        df["regime"] = r
        lead_time_by_regime_rows.append(df)
    lead_time_by_regime = pd.concat(lead_time_by_regime_rows, ignore_index=True)

    airspeed_bins = (30, 40, 50, 60, 75)
    labels = [f"{airspeed_bins[i]}-{airspeed_bins[i+1]}" for i in range(len(airspeed_bins) - 1)]
    binned = pd.cut(merged["initial_airspeed"], bins=airspeed_bins, labels=labels, include_lowest=True)
    lead_time_by_airspeed_rows = []
    for label in labels:
        m = (binned == label).to_numpy()
        if m.sum() == 0:
            continue
        df = lead_time_bucket_analysis_fine(test_sub.loc[m, "time_to_stall"].to_numpy(), y_true[m], pred[m])
        df["airspeed_bin_m_s"] = label
        lead_time_by_airspeed_rows.append(df)
    lead_time_by_airspeed = pd.concat(lead_time_by_airspeed_rows, ignore_index=True)

    return regime_df, airspeed_df, lead_time_by_regime, lead_time_by_airspeed


# ---------------------------------------------------------------------------
# Task 9: physics / information diagnosis
# ---------------------------------------------------------------------------

def physics_information_diagnosis(df: pd.DataFrame, lead_times_s: List[float] = None, tolerance_s: float = 0.25,
                                   safe_threshold_s: float = 10.0) -> Tuple[pd.DataFrame, dict]:
    """For rows whose actual time_to_stall is within `tolerance_s` of
    each target lead time (1..5s), compare each diagnostic variable's
    distribution against 'safe' rows (no future crossing within
    `safe_threshold_s`). Quantifies separability with the single-
    feature ROC-AUC of using that variable alone to distinguish the
    two populations (0.5 = complete overlap/no information, 1.0 =
    perfectly separable) -- direction-agnostic (max(auc, 1-auc)) since
    we only care about distinguishability, not sign convention.

    Returns (summary_df, samples) where samples[(lead_time, var)] =
    (near_crossing_values, safe_values), kept for the Task-12
    distribution plots.
    """
    lead_times_s = lead_times_s or DIAGNOSIS_LEAD_TIMES_S
    tts = df["time_to_stall"].to_numpy()
    safe_mask = np.isnan(tts) | (tts > safe_threshold_s)

    rows = []
    samples: Dict[Tuple[float, str], Tuple[np.ndarray, np.ndarray]] = {}
    for L in lead_times_s:
        near_mask = (tts > L - tolerance_s) & (tts <= L + tolerance_s)
        for var in DIAGNOSIS_VARIABLES:
            if var not in df.columns:
                continue
            near_vals = df.loc[near_mask, var].dropna().to_numpy()
            safe_vals = df.loc[safe_mask, var].dropna().to_numpy()
            samples[(L, var)] = (near_vals, safe_vals)
            if len(near_vals) < 20 or len(safe_vals) < 20:
                auc = float("nan")
            else:
                labels = np.concatenate([np.ones(len(near_vals)), np.zeros(len(safe_vals))])
                scores = np.concatenate([near_vals, safe_vals])
                try:
                    raw_auc = roc_auc_score(labels, scores)
                    auc = max(raw_auc, 1 - raw_auc)
                except ValueError:
                    auc = float("nan")
            rows.append({
                "lead_time_s": L, "variable": var, "n_near_crossing": len(near_vals), "n_safe": len(safe_vals),
                "separability_auc": auc,
                "near_crossing_mean": float(np.mean(near_vals)) if len(near_vals) else None,
                "near_crossing_std": float(np.std(near_vals)) if len(near_vals) else None,
                "safe_mean": float(np.mean(safe_vals)) if len(safe_vals) else None,
                "safe_std": float(np.std(safe_vals)) if len(safe_vals) else None,
            })
    return pd.DataFrame(rows), samples


# ---------------------------------------------------------------------------
# Task 11: generalization check (train excluding the 'stall' regime)
# ---------------------------------------------------------------------------

def run_generalization_check(splits: dict, rf_params: dict, window_s: float, verbose: bool = True) -> dict:
    train, val, test = splits["train"], splits["val"], splits["test"]
    metadata = pd.read_csv(tcfg.METADATA_PATH)[["trajectory_id", "generation_mode"]]

    train_regime = train.merge(metadata, on="trajectory_id", how="left")["generation_mode"].to_numpy()
    feats = tcfg.model_d_features(window_s)

    non_stall_train_mask = usable_mask_for_window(train, window_s) & (train_regime != "stall")
    val_mask = usable_mask_for_window(val, window_s)
    test_mask = usable_mask_for_window(test, window_s)

    Xtr, ytr, _ = get_xy(train, feats, non_stall_train_mask)
    Xv, yv, _ = get_xy(val, feats, val_mask)
    Xte, yte, test_sub = get_xy(test, feats, test_mask)

    if verbose:
        n_traj_excluded = train.loc[usable_mask_for_window(train, window_s) & (train_regime == "stall"), "trajectory_id"].nunique()
        print(f"  generalization check: trained on {len(Xtr):,} rows, EXCLUDING {n_traj_excluded} 'stall'-regime "
              f"train trajectories entirely; evaluating on the full TEST split (including 'stall' regime)")

    model, thr, thr_info = fit_rf_and_threshold(Xtr, ytr, Xv, yv, rf_params)
    res, proba, pred = evaluate_on_test(model, thr, Xte, yte, test_sub)

    merged = load_test_metadata(test_sub)
    regime_df = regime_breakdown(yte, pred, proba, merged["generation_mode"].to_numpy())

    return {
        "description": "Model D retrained with ALL 'stall'-regime trajectories removed from TRAIN (val/test unchanged); "
                        "tests whether temporal patterns generalize to a regime never seen in training, or merely "
                        "memorize regime-specific trajectory shapes.",
        "train_population": {
            "n_rows": int(non_stall_train_mask.sum()),
            "n_trajectories": int(train.loc[non_stall_train_mask, "trajectory_id"].nunique()),
        },
        "excluded_regime": "stall",
        "threshold": thr,
        "test_metrics": res["test_metrics"],
        "event_level": res["event_level"],
        "fraction_of_events_detected_at_least": res["fraction_of_events_detected_at_least"],
        "regime_breakdown": regime_df.to_dict(orient="records"),
    }
