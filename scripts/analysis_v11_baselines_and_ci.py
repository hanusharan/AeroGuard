"""AeroGuard v1.1 analysis: reproduction check, rule baselines, and bootstrap
confidence intervals for the frozen v0.3 primary model.

This script does NOT retrain or modify the frozen v1.0 model. It:
  1. Rebuilds the v0.3 TEST feature panel and scores it with the frozen
     model (outputs/ml_v03/models/primary_model_D_1s.joblib) at the frozen
     threshold, and checks the result against the published v1.0 metrics.
  2. Fits the two existing rule baselines (angle-of-attack threshold, and
     stall-margin + alpha-rate trend rule) on TRAIN/VAL only, using the same
     calibration procedure as the v0.2 baseline stage, and evaluates them on
     exactly the same TEST rows as the primary model.
  3. Computes 95% bootstrap confidence intervals by resampling TEST
     trajectories (not rows), plus paired intervals for the PR-AUC
     difference between the model and each rule.

Prerequisite: the v0.3 dataset must exist (python scripts/generate_dataset_v3.py).

Run:  python scripts/analysis_v11_baselines_and_ci.py
Outputs: outputs/analysis_v11/
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from ml import temporal_config_v03 as v3cfg
from ml.baselines import AoAThresholdRule, TrendRule
from ml.events import aggregate_event_results, compute_event_level_results
from ml.temporal_data_v03 import load_temporal_splits
from ml.temporal_experiment import get_xy, run_false_alarm_analysis
from ml.temporal_features import usable_mask_for_window

OUT_DIR = os.path.join(v3cfg.PROJECT_ROOT, "outputs", "analysis_v11")
PUBLISHED = os.path.join(v3cfg.METRICS_DIR, "primary_model_metrics.json")
N_BOOT = int(os.environ.get("AEROGUARD_N_BOOT", "1000"))
BOOT_SEED = 20261011  # new seed, distinct from all v1.0 seeds


def event_summary(test_sub, pred):
    results = compute_event_level_results(test_sub, pred, v3cfg.LABELING_HORIZON_S)
    return results, aggregate_event_results(results)


def per_trajectory_events(results):
    by_traj = {}
    for r in results:
        by_traj.setdefault(r.trajectory_id, []).append(r)
    return by_traj


def bootstrap(traj_ids, row_index_by_traj, y, scores_by_model, events_by_model, n_boot, seed):
    """Resample TEST trajectories with replacement. Returns per-replicate
    PR-AUC per model, event recall and median lead time per model."""
    rng = np.random.default_rng(seed)
    n = len(traj_ids)
    out = {m: {"pr_auc": [], "event_recall": [], "median_lead_s": []} for m in scores_by_model}
    for b in range(n_boot):
        pick = traj_ids[rng.integers(0, n, n)]
        rows = np.concatenate([row_index_by_traj[t] for t in pick])
        yb = y[rows]
        for m, s in scores_by_model.items():
            out[m]["pr_auc"].append(average_precision_score(yb, s[rows]) if yb.any() else np.nan)
            evs = [e for t in pick for e in events_by_model[m].get(t, [])]
            warned = [e.lead_time_s for e in evs if e.warned]
            out[m]["event_recall"].append(len(warned) / len(evs) if evs else np.nan)
            out[m]["median_lead_s"].append(float(np.median(warned)) if warned else np.nan)
        if (b + 1) % 100 == 0:
            print(f"  bootstrap {b + 1}/{n_boot}")
    return {m: {k: np.array(v, dtype=float) for k, v in d.items()} for m, d in out.items()}


def ci(a):
    a = a[~np.isnan(a)]
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    published = json.load(open(PUBLISHED))
    thr = float(published["threshold"])
    feats = v3cfg.model_d_features(v3cfg.PRIMARY_WINDOW_S)

    print("STEP 0: load v0.3 temporal splits")
    splits = load_temporal_splits(force=False, verbose=True)
    train, val, test = splits["train"], splits["val"], splits["test"]
    w = v3cfg.PRIMARY_WINDOW_S
    tr_m, va_m, te_m = usable_mask_for_window(train, w), usable_mask_for_window(val, w), usable_mask_for_window(test, w)
    Xte, yte, test_sub = get_xy(test, feats, te_m)
    test_sub = test_sub.reset_index(drop=True)

    print("STEP 1: reproduce frozen-model TEST metrics")
    model = joblib.load(os.path.join(v3cfg.MODELS_DIR, "primary_model_D_1s.joblib"))
    proba = model.predict_proba(Xte)[:, 1]
    pred = (proba >= thr).astype(int)
    rf_events, rf_agg = event_summary(test_sub, pred)
    repro = {
        "pr_auc": {"published": published["test_metrics"]["pr_auc"], "reproduced": float(average_precision_score(yte, proba))},
        "event_recall": {"published": published["event_level"]["event_recall"], "reproduced": rf_agg["event_recall"]},
        "n_events": {"published": published["event_level"]["n_events"], "reproduced": rf_agg["n_events"]},
        "median_lead_time_s": {"published": published["event_level"]["median_lead_time_s"], "reproduced": rf_agg["median_lead_time_s"]},
        "test_rows": {"published": published["population"]["test_rows"], "reproduced": int(len(test_sub))},
    }
    for k, v in repro.items():
        print(f"  {k}: published={v['published']} reproduced={v['reproduced']}")

    print("STEP 2: rule baselines (fit on TRAIN/VAL, same TEST rows)")
    y_tr = train.loc[tr_m, v3cfg.TARGET_COL].to_numpy().astype(int)
    y_va = val.loc[va_m, v3cfg.TARGET_COL].to_numpy().astype(int)
    aoa = AoAThresholdRule().fit(train.loc[tr_m, "alpha"].to_numpy(), y_tr, val.loc[va_m, "alpha"].to_numpy(), y_va)
    trend = TrendRule().fit(
        train.loc[tr_m, "stall_margin"].to_numpy(), train.loc[tr_m, "dalpha_dt"].to_numpy(), y_tr,
        val.loc[va_m, "stall_margin"].to_numpy(), val.loc[va_m, "dalpha_dt"].to_numpy(), y_va,
    )
    aoa_score = aoa.predict_score(test_sub["alpha"].to_numpy())
    aoa_pred = aoa.predict(test_sub["alpha"].to_numpy())
    tr_score = trend.predict_score(test_sub["stall_margin"].to_numpy(), test_sub["dalpha_dt"].to_numpy())
    tr_pred = trend.predict(test_sub["stall_margin"].to_numpy(), test_sub["dalpha_dt"].to_numpy())
    aoa_events, aoa_agg = event_summary(test_sub, aoa_pred)
    tr_events, tr_agg = event_summary(test_sub, tr_pred)

    models = {
        "temporal_rf_frozen": (proba, pred, rf_events, rf_agg),
        "aoa_threshold_rule": (aoa_score, aoa_pred, aoa_events, aoa_agg),
        "margin_trend_rule": (tr_score, tr_pred, tr_events, tr_agg),
    }
    point = {}
    for name, (score, p, _ev, agg) in models.items():
        fa = run_false_alarm_analysis(test_sub, yte, p)
        point[name] = {
            "pr_auc": float(average_precision_score(yte, score)),
            "event_recall": agg["event_recall"], "n_warned": agg["n_warned"], "n_events": agg["n_events"],
            "median_lead_time_s": agg["median_lead_time_s"],
            "false_alarms_per_hour": float(fa["false_alarms_per_minute"]) * 60.0,
        }
        print(f"  {name}: {point[name]}")

    print(f"STEP 3: bootstrap over TEST trajectories (n_boot={N_BOOT})")
    traj = test_sub["trajectory_id"].to_numpy()
    traj_ids = pd.unique(traj)
    row_index_by_traj = {t: np.flatnonzero(traj == t) for t in traj_ids}
    boot = bootstrap(
        traj_ids, row_index_by_traj, yte,
        {m: v[0] for m, v in models.items()},
        {m: per_trajectory_events(v[2]) for m, v in models.items()},
        N_BOOT, BOOT_SEED,
    )
    intervals = {m: {k: ci(v) for k, v in d.items()} for m, d in boot.items()}
    paired = {
        f"temporal_rf_minus_{m}": {
            "pr_auc_diff_point": point["temporal_rf_frozen"]["pr_auc"] - point[m]["pr_auc"],
            "pr_auc_diff_ci95": ci(boot["temporal_rf_frozen"]["pr_auc"] - boot[m]["pr_auc"]),
        }
        for m in ("aoa_threshold_rule", "margin_trend_rule")
    }

    result = {
        "description": "v1.1 analysis: reproduction check, rule baselines, 95% trajectory-bootstrap CIs. Frozen v1.0 model not retrained.",
        "n_test_trajectories": int(len(traj_ids)), "n_boot": N_BOOT, "bootstrap_seed": BOOT_SEED,
        "frozen_threshold": thr,
        "reproduction_check": repro,
        "point_estimates": point,
        "ci95": intervals,
        "paired_pr_auc_differences": paired,
        "rule_calibration": {"aoa": aoa.calibration_info, "trend": trend.calibration_info},
        "runtime_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(OUT_DIR, "baselines_and_ci.json"), "w") as f:
        json.dump(result, f, indent=2, default=float)

    rows = []
    for m in models:
        p, c = point[m], intervals[m]
        rows.append({
            "model": m,
            "pr_auc": round(p["pr_auc"], 3), "pr_auc_ci95": f"[{c['pr_auc'][0]:.3f}, {c['pr_auc'][1]:.3f}]",
            "event_recall": f"{p['n_warned']}/{p['n_events']} ({p['event_recall']:.1%})",
            "event_recall_ci95": f"[{c['event_recall'][0]:.1%}, {c['event_recall'][1]:.1%}]",
            "median_lead_s": p["median_lead_time_s"],
            "median_lead_ci95_s": f"[{c['median_lead_s'][0]:.2f}, {c['median_lead_s'][1]:.2f}]",
            "false_alarms_per_hour": round(p["false_alarms_per_hour"], 2),
        })
    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "baselines_and_ci_summary.csv"), index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print(json.dumps(paired, indent=2))
    print(f"done in {time.time() - t0:.0f}s -> {OUT_DIR}")


if __name__ == "__main__":
    main()
