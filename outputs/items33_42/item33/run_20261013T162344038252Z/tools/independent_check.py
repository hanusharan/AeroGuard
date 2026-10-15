"""Independent re-verification of the Item 33 headline numbers (does not use the fast bootstrap path for point estimates)."""
import json, sys, time
from pathlib import Path
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from item33 import bootstrap as bs, conditions as cond, SEEDS

rd = Path(sys.argv[1]); out = Path(sys.argv[2])
y = np.load(rd / "test_labels.npy"); z = np.load(rd / "test_keys.npz", allow_pickle=False); traj = np.asarray(z["trajectory_id"]).astype(str)
rows = json.load(open(rd / "metrics_primary.json"))
rec = {(r["condition"], r["seed"], r["metric"]): r["value"] for r in rows}
worst = 0.0; pts = {}
for c in cond.CONDITION_ORDER:
    for s in SEEDS:
        sc = np.load(rd / f"scores_{c}_{s}.npy")
        assert sc.shape == y.shape and np.isfinite(sc).all()
        ap, roc = average_precision_score(y, sc), roc_auc_score(y, sc)
        worst = max(worst, abs(ap - rec[(c, s, "pr_auc")]), abs(roc - rec[(c, s, "roc_auc")]))
        pts[(c, s)] = ap
pc = {(c["register_id"], c["summary"]["reference"], c["summary"]["comparison"], c["summary"]["metric"]): c["summary"] for c in json.load(open(rd / "paired_contrasts.json"))["contrasts"]}
worst_delta = 0.0
for (rid, ref, cmp_, metric), summ in pc.items():
    if metric != "pr_auc":
        continue
    for s in SEEDS:
        worst_delta = max(worst_delta, abs((pts[(ref, s)] - pts[(cmp_, s)]) - summ["per_seed"][str(s)]["point"]))
    worst_delta = max(worst_delta, abs(np.mean([pts[(ref, s)] - pts[(cmp_, s)] for s in SEEDS]) - summ["seed_estimates"]["mean"]),
                      abs(np.median([pts[(ref, s)] - pts[(cmp_, s)] for s in SEEDS]) - summ["seed_estimates"]["median"]))
scores = {bs.method_key(c, s): np.load(rd / f"scores_{c}_{s}.npy") for c in cond.CONDITION_ORDER for s in SEEDS}
t = time.time()
chk = bs.verify_fast_replicates(traj, y, scores, seed=20261013, n=40)
res = {"point_estimates_recomputed_with_scikit_learn": {"n": 50, "max_abs_difference_vs_recorded": worst},
       "per_seed_deltas_mean_median_recomputed": {"max_abs_difference_vs_recorded": worst_delta},
       "bootstrap_fast_path_vs_scikit_learn_on_real_scores": {**{k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in chk.items()}, "seconds": time.time() - t},
       "all_checks_within_1e-10": bool(worst < 1e-10 and worst_delta < 1e-10 and chk["max_abs_difference"] < 1e-10)}
json.dump(res, open(out, "x"), indent=2); print(json.dumps(res, indent=2))
