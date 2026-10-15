"""Item 34 (PROTOCOL.md alongside). Fits T1 = C0 + elevator_change_0.5s for 5 seeds, scores test once per model, and
compares with the stored Item 33 C0 scores. Models and score arrays go to scratch; small records to outputs/.

usage: run_item34.py <repo_root> <data_dir> <item33_scratch_run_dir> <scratch_out_dir>
"""

import hashlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

repo, data_dir, i33, scr = (Path(a).resolve() for a in sys.argv[1:5])
sys.path[:0] = [str(repo), str(repo / "experiments/items33_42/item33/src"), str(repo / "experiments/items33_42/items37_39/src"),
                str(repo / "experiments/items33_42/items40_42/src")]
from item33.conditions import features_for  # noqa: E402
from item33.fitting import build_forest  # noqa: E402
from item33.population import key_hash, row_keys, assert_consecutive_steps  # noqa: E402
from ml.calibration import select_threshold_train_then_val  # noqa: E402
from ml.temporal_experiment import get_xy  # noqa: E402
from ml.temporal_config import temporal_feature_columns  # noqa: E402
from phase3.population import usable_mask  # noqa: E402
import items37_39 as m37  # noqa: E402
import items40_42 as m40  # noqa: E402

PROTOCOL_SHA256 = sys.argv[5] if len(sys.argv) > 5 else None
SEEDS = (20260817, 20261101, 20261102, 20261103, 20261104)
I33_RUN = repo / "outputs/items33_42/item33/run_20261013T162344038252Z"
FEATS = features_for("C0") + ["elevator_change_0.5s"]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(repo / "experiments/items33_42/item34/PROTOCOL.md") == PROTOCOL_SHA256, "protocol hash differs"
cols = list(dict.fromkeys(["trajectory_id", "time", "is_unsafe", "future_stall_5s", "future_stall_5s_available"] + list(temporal_feature_columns(1.0)) + FEATS))
load = lambda s: pd.read_parquet(data_dir / f"ml_temporal_v03/temporal_{s}.parquet", columns=cols)
tr, va = load("train"), load("val")
xtr, ytr, _ = get_xy(tr, FEATS, pd.Series(usable_mask(tr), index=tr.index))
xva, yva, _ = get_xy(va, FEATS, pd.Series(usable_mask(va), index=va.index))
del tr, va
scr.mkdir(parents=True, exist_ok=True)
fits = {}
for s in SEEDS:
    t0 = time.time()
    mdl = build_forest(s); mdl.fit(xtr, ytr)
    thr, info = select_threshold_train_then_val(ytr, mdl.predict_proba(xtr)[:, 1], yva, mdl.predict_proba(xva)[:, 1])
    joblib.dump(mdl, scr / f"model_T1_{s}.joblib")
    fits[s] = {"model": mdl, "threshold": float(thr), "threshold_info": info, "fit_seconds": time.time() - t0}
    print(f"fitted seed {s} in {time.time() - t0:.0f} s", flush=True)
del xtr, ytr, xva, yva

te = load("test"); sub = te.loc[usable_mask(te)].reset_index(drop=True); del te
keys = row_keys(sub); assert_consecutive_steps(keys)
assert key_hash(keys) == json.load(open(I33_RUN / "population.json"))["test_key_hash"], "population differs"
y = sub["future_stall_5s"].to_numpy().astype(int)
xte, _, _ = get_xy(sub, FEATS, pd.Series(np.ones(len(sub), bool), index=sub.index))
i33a = json.load(open(I33_RUN / "audit.json"))["files"]
S1, S0, thr0 = {}, {}, {}
for s in SEEDS:
    S1[s] = fits[s]["model"].predict_proba(xte)[:, 1]; np.save(scr / f"scores_T1_{s}.npy", S1[s])
    f0 = i33 / f"scores_C0_{s}.npy"; assert sha(f0) == i33a[f0.name]["sha256"], "C0 score hash differs"
    S0[s] = np.load(f0); thr0[s] = json.load(open(I33_RUN / f"threshold_C0_{s}.json"))["threshold"]

traj = sub["trajectory_id"].to_numpy(); times = sub["time"].to_numpy(); unsafe = sub["is_unsafe"].to_numpy().astype(bool)
order = list(pd.unique(traj)); T = len(order)
starts, ends = m37.blocks(traj); tidx = np.repeat(np.arange(T), ends - starts)
C = m40.draw_counts(T)
ap = lambda sc, w=None: average_precision_score(y, sc, sample_weight=w)
per_seed, reps = {}, np.zeros((len(C), len(SEEDS)))
for j, s in enumerate(SEEDS):
    per_seed[s] = {"pr_auc_T1": ap(S1[s]), "pr_auc_T0": ap(S0[s]), "roc_auc_T1": roc_auc_score(y, S1[s]), "roc_auc_T0": roc_auc_score(y, S0[s]),
                   "threshold_T1": fits[s]["threshold"], "threshold_T0": thr0[s], "fit_seconds": fits[s]["fit_seconds"]}
    per_seed[s]["delta_pr_auc"] = per_seed[s]["pr_auc_T1"] - per_seed[s]["pr_auc_T0"]
    for nm, sc, th in (("T1", S1[s], fits[s]["threshold"]), ("T0", S0[s], thr0[s])):
        fa = m37.false_alarm_counts(traj, times, y, unsafe, sc, th)
        ev = m37.event_table(traj, times, unsafe, sc, th)
        per_seed[s][f"false_per_sim_hour_{nm}"] = float(fa["false"].sum() / fa["span_s"].sum() * 3600)
        for L in (2.0, 4.0):
            n_, d_ = m37.coverage_per_trajectory(ev, order, L); per_seed[s][f"coverage_{L:g}s_{nm}"] = float(n_.sum() / d_.sum())
for b, c in enumerate(C):
    w = c[tidx].astype(float)
    reps[b] = [ap(S1[s], w) - ap(S0[s], w) for s in SEEDS]
d = np.array([per_seed[s]["delta_pr_auc"] for s in SEEDS])
res = {"banner": "Simulation only; regenerated v0.3 copy; previously exposed test data (not blind, not independent replication). No causal claim.",
       "protocol_sha256": PROTOCOL_SHA256, "features_T1": FEATS, "per_seed": per_seed,
       "D34_seed_mean": m40.interval(d.mean(), reps.mean(axis=1)),
       "seed_spread": {"min": d.min(), "max": d.max(), "sd_ddof1": d.std(ddof=1), "sign_consistent": bool((d > 0).all() or (d < 0).all())},
       "score_sha256": {f"T1_{s}": sha(scr / f"scores_T1_{s}.npy") for s in SEEDS}, "model_sha256": {f"T1_{s}": sha(scr / f"model_T1_{s}.joblib") for s in SEEDS},
       "bootstrap": {"B": len(C), "seed": m40.SEED, "pct": list(m40.PCT), "unit": "trajectory", "paired": True}}
r = res["D34_seed_mean"]
res["statement"] = ("No difference was demonstrated (the interval includes 0); this does not show the conditions perform alike." if r["includes_zero"]
                    else "The interval excludes 0: a difference in predictive information under this resampling model (not causal; simulation only).")
od = repo / "outputs/items33_42/item34" / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
od.mkdir(parents=True)
json.dump(res, open(od / "results.json", "x"), indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(od); print(json.dumps(r)); print(res["statement"])
