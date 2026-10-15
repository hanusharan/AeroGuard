"""Run Items 40-42 (PROTOCOL.md in the parent directory). Writes only below outputs/items33_42/items40_42/run_<UTC>/,
exclusively. No model is trained; the frozen model and the Phase 3 instantaneous model are only used to score the
validation split (read-only, hash-checked).

usage: run_items40_42.py <repo_root> <data_dir> <phase3_scratch_run_dir> <item33_scratch_run_dir> <items37_39_run_dir>
"""

import hashlib, inspect, json, sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score  # noqa: E402

repo, data_dir, p3, i33, r3739 = (Path(a).resolve() for a in sys.argv[1:6])
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(repo), str(repo / "experiments/items33_42/item33/src"), str(repo / "experiments/items33_42/items37_39/src"), str(HERE)]
import items40_42 as m  # noqa: E402
import items37_39 as m37  # noqa: E402
from item33.population import key_hash, row_keys, assert_consecutive_steps  # noqa: E402
from item33.conditions import features_for  # noqa: E402
from phase3 import instantaneous, rules  # noqa: E402
from phase3.population import usable_mask  # noqa: E402
from ml.temporal_config import temporal_feature_columns  # noqa: E402

PROTOCOL_SHA256 = "9076e0aca72ff90e830a8932e8bca3128c6c882bb0b330e629cb7a2cdeef7242"
FROZEN_SHA256 = "707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3"
PANEL_SHA = {"train": "1a39472881280e084f3cab5d94fa4c80382d65a7075df59cd7a45fd4d5af4b43",
             "val": "9416fc8005b206eefbcdbeeb0d043a45036e8b2d6251ae3850b176765565a0e0",
             "test": "c03634b4cc793c57bbe065e710a4a98bfe2bf69fdf5a55beb56a1c0ba33241b8"}
P3_RUN = repo / "outputs/phase3/run_20261013T140820817642Z"
I33_RUN = repo / "outputs/items33_42/item33/run_20261013T162344038252Z"
CONDS, SEEDS = ("C0", "C1", "C2", "C3", "X1"), (20260817, 20261101, 20261102, 20261103, 20261104)
P3_METHODS = ("aoa_signed", "aoa_two_sided", "instantaneous_model_a", "frozen_temporal")
CMP = ("frozen_temporal", "instantaneous_model_a", "aoa_signed")           # M1, M2, M3
PAIRS = (("frozen_temporal", "instantaneous_model_a"), ("frozen_temporal", "aoa_signed"))
FORBIDDEN = {"future_stall_5s", "future_stall_5s_available", "is_unsafe", "time_to_stall", "trajectory_id", "time", "split"}
EVIDENCE = "Simulation only; regenerated v0.3 copy; previously exposed test data (not blind, not independent replication)."
H = 3600.0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def need(cond, msg):
    if not cond:
        raise SystemExit(f"STOP: {msg}")


rj = lambda p: json.load(open(p))
log = {"order_of_operations": []}
step = lambda s: log["order_of_operations"].append(s)

# ---- integrity ----------------------------------------------------------------------------------------------------------
need(sha(repo / "experiments/items33_42/items40_42/PROTOCOL.md") == PROTOCOL_SHA256, "protocol hash differs")
for s, h in PANEL_SHA.items():
    need(sha(data_dir / f"ml_temporal_v03/temporal_{s}.parquet") == h, f"{s} panel hash differs")
frozen_path = repo / "outputs/ml_v03/models/primary_model_D_1s.joblib"
need(sha(frozen_path) == FROZEN_SHA256, "frozen model hash differs")
ma_path = p3 / "instantaneous_model_a.joblib"
need(sha(ma_path) == rj(P3_RUN / "model_a_fit_record.json")["model_sha256"], "instantaneous model hash differs from its fit record")
p3_audit = rj(P3_RUN / "audit.json")["run_files"]
i33_audit = rj(I33_RUN / "audit.json")["files"]
frozen_feats = list(rj(repo / "outputs/ml_v03/metrics/primary_model_metrics.json")["feature_columns"])
win = list(temporal_feature_columns(1.0))
base = ["trajectory_id", "time", "is_unsafe", "future_stall_5s", "future_stall_5s_available", "time_to_stall"] + win
cols = list(dict.fromkeys(base + list(instantaneous.INSTANTANEOUS_FEATURES) + frozen_feats))


def population(split, columns):
    df = pd.read_parquet(data_dir / f"ml_temporal_v03/temporal_{split}.parquet", columns=columns)
    sub = df.loc[usable_mask(df)].reset_index(drop=True)
    k = row_keys(sub); assert_consecutive_steps(k)
    return sub, k


# ---- Item 40: validation scoring and matched thresholds (the test split is not read in this block) ----------------------
step("load validation population")
val, _ = population("val", cols)
frozen = joblib.load(frozen_path)
need(list(frozen.feature_names_in_) == frozen_feats, "frozen model feature names differ from the stored list")
model_a = joblib.load(ma_path)
step("score validation: aoa_signed, instantaneous_model_a, frozen_temporal")
val_scores = {"aoa_signed": rules.score_signed(val["alpha"].to_numpy()),
              "instantaneous_model_a": instantaneous.predict_scores(model_a, val, np.ones(len(val), dtype=bool)),
              "frozen_temporal": frozen.predict_proba(val[frozen_feats])[:, 1]}
m37.blocks(val["trajectory_id"].to_numpy())  # raises if a trajectory is not contiguous
vfirst = m.first_rows(val["trajectory_id"].to_numpy())
vg = val.groupby("trajectory_id", sort=False)["time"]
val_hours = float((vg.max() - vg.min()).sum()) / H
vlab = val["future_stall_5s"].to_numpy(); vuns = val["is_unsafe"].to_numpy().astype(bool)
matched = {nm: {f"{R:g}": m.matched_threshold(val_scores[nm], vfirst, vlab, vuns, val_hours, R) for R in m.TARGET_RATES} for nm in CMP}
val_grid = {nm: np.quantile(val_scores[nm], m.QUANTILE_LEVELS[::10]) for nm in CMP}
step("matched thresholds selected from validation only")
val_score_hashes = {nm: hashlib.sha256(np.ascontiguousarray(s, dtype=np.float64).tobytes()).hexdigest() for nm, s in val_scores.items()}
del val

# ---- test population and stored scores -----------------------------------------------------------------------------------
step("load test population and stored test scores")
test, tkeys = population("test", cols)
need(key_hash(tkeys) == rj(I33_RUN / "population.json")["test_key_hash"], "test population key hash differs")
scores = {}
for nm in P3_METHODS:
    f = p3 / f"scores_{nm}.npy"; need(sha(f) == p3_audit[f.name], f"Phase 3 score hash differs: {nm}")
    scores[nm] = np.load(f)
i33_scores = {}
for c in CONDS:
    for s in SEEDS:
        f = i33 / f"scores_{c}_{s}.npy"; need(sha(f) == i33_audit[f.name]["sha256"], f"Item 33 score hash differs: {c} {s}")
        i33_scores[(c, s)] = np.load(f)
traj = test["trajectory_id"].to_numpy(); times = test["time"].to_numpy()
y = test["future_stall_5s"].to_numpy().astype(int); unsafe = test["is_unsafe"].to_numpy().astype(bool)
order = list(pd.unique(traj)); T = len(order)
tfirst = m.first_rows(traj)
starts, ends = m37.blocks(traj)
span = np.array([times[b - 1] - times[a] for a, b in zip(starts, ends)])
tidx = np.repeat(np.arange(T), ends - starts)
C = m.draw_counts(T)

# ---- Item 40: test metrics at matched points, paired contrasts ------------------------------------------------------------
step("evaluate matched thresholds on test")
per_traj = {}
item40 = {"target_rates_per_sim_hour": list(m.TARGET_RATES), "validation_eligible_hours": val_hours, "methods": {}, "contrasts": {},
          "n_contrasts": 0, "note": "contrasts are descriptive and unadjusted; validation-matched rates are not equal on test"}
for nm in CMP:
    item40["methods"][nm] = {}
    for R in m.TARGET_RATES:
        thr = matched[nm][f"{R:g}"]["threshold"]
        pred = scores[nm] > thr
        fstart = m.false_episode_starts(tfirst, y, unsafe, pred)
        fnum = np.bincount(tidx, weights=fstart, minlength=T)
        ev = m37.event_table(traj, times, unsafe, scores[nm], thr)
        cov = {f"{L:g}": m37.coverage_per_trajectory(ev, order, L) for L in (2.0, 4.0)}
        sus = {f"{L:g}": m37.coverage_per_trajectory(ev, order, L, sustained=True) for L in (2.0, 4.0)}
        tp = int((pred & (y == 1)).sum()); npred = int(pred.sum())
        reps = {"fa": m.ratio_reps(fnum, span, C, H), **{f"cov{L}": m.ratio_reps(*cov[L], C) for L in cov}}
        pts = {"fa": fnum.sum() / span.sum() * H, **{f"cov{L}": cov[L][0].sum() / cov[L][1].sum() for L in cov}}
        per_traj[(nm, R)] = (pts, reps)
        item40["methods"][nm][f"{R:g}"] = {
            **matched[nm][f"{R:g}"],
            "test_false_episodes": int(fnum.sum()), "test_false_per_sim_hour": m.interval(pts["fa"], reps["fa"]),
            **{f"test_coverage_{L}s": {**m.interval(pts[f"cov{L}"], reps[f"cov{L}"]), "covered": int(cov[L][0].sum()), "eligible": int(cov[L][1].sum())} for L in cov},
            **{f"test_sustained_coverage_{L}s": m.interval(sus[L][0].sum() / sus[L][1].sum(), m.ratio_reps(*sus[L], C)) for L in sus},
            "test_row_precision": tp / npred if npred else None, "test_row_recall": tp / int((y == 1).sum()),
        }
for a, b in PAIRS:
    for R in m.TARGET_RATES:
        (pa, ra), (pb, rb) = per_traj[(a, R)], per_traj[(b, R)]
        for k, lab in (("cov2", "coverage_2s"), ("cov4", "coverage_4s"), ("fa", "false_per_sim_hour")):
            item40["contrasts"][f"{a} - {b} | R={R:g} | {lab}"] = m.interval(pa[k] - pb[k], ra[k] - rb[k])
item40["n_contrasts"] = len(item40["contrasts"])

# ---- Item 42: leakage and invalid-metric checks ---------------------------------------------------------------------------
step("Item 42 checks")
checks = {}
def rec(cid, status, **ev):
    checks[cid] = {"status": status, **ev}

man = pd.read_csv(repo / "data/splits/split_manifest_v3.csv")
ids = {s: set(pd.read_parquet(data_dir / f"ml_temporal_v03/temporal_{s}.parquet", columns=["trajectory_id"])["trajectory_id"]) for s in ("train", "val", "test")}
ov = {f"{a}&{b}": len(ids[a] & ids[b]) for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
dup_man = int(man["trajectory_id"].duplicated().sum())
rec("L1", "PASS" if not any(ov.values()) and dup_man == 0 else "FAIL", panel_overlap=ov, manifest_duplicate_ids=dup_man)

flists = {"frozen_temporal": frozen_feats, "instantaneous_model_a": list(getattr(model_a, "feature_names_in_", instantaneous.INSTANTANEOUS_FEATURES)),
          **{f"item33_{c}": features_for(c) for c in CONDS}}
bad = {k: sorted(set(v) & FORBIDDEN) for k, v in flists.items() if set(v) & FORBIDDEN}
rec("L2", "FAIL" if bad else "PASS", forbidden_found=bad, n_feature_lists=len(flists))

full_ap = float(average_precision_score(y, scores["frozen_temporal"]))
screen = {}
for f in frozen_feats:
    x = test[f].to_numpy(dtype=float)
    screen[f] = max(float(average_precision_score(y, x)), float(average_precision_score(y, -x)))
top = sorted(screen.items(), key=lambda kv: -kv[1])[:5]
rec("L3", "FLAG" if top[0][1] >= 0.95 or top[0][1] >= full_ap else "PASS", full_model_pr_auc=full_ap, top_single_features=top,
    prevalence=float(y.mean()), all_features=screen)

trn, _ = population("train", ["trajectory_id", "time", "alpha", "future_stall_5s", "future_stall_5s_available"] + win)
vla, _ = population("val", ["trajectory_id", "time", "alpha", "future_stall_5s", "future_stall_5s_available"] + win)
rule = rules.fit_signed_aoa(trn["alpha"].to_numpy(), trn["future_stall_5s"].to_numpy().astype(int), vla["alpha"].to_numpy(), vla["future_stall_5s"].to_numpy().astype(int))
stored_thr = rj(P3_RUN / "aoa_rule.json")["threshold_rad"]
rec("L4", "PASS" if float(rule.threshold_rad) == float(stored_thr) else "FAIL", refit_threshold=float(rule.threshold_rad), stored_threshold=stored_thr)
del trn, vla

sig = list(inspect.signature(m.matched_threshold).parameters)
test_loaded_after = log["order_of_operations"].index("matched thresholds selected from validation only") < log["order_of_operations"].index("load test population and stored test scores")
rec("L5", "PASS" if sig[:4] == ["val_score", "val_first", "val_label", "val_unsafe"] and test_loaded_after else "FAIL",
    signature=sig, test_loaded_after_threshold_selection=test_loaded_after)

boot = rj(P3_RUN / "bootstrap.json")
diffs = {}
for nm in P3_METHODS:
    diffs[f"{nm}|pr_auc"] = abs(float(average_precision_score(y, scores[nm])) - boot["per_method"][f"{nm}|pr_auc"]["point"])
    diffs[f"{nm}|roc_auc"] = abs(float(roc_auc_score(y, scores[nm])) - boot["per_method"][f"{nm}|roc_auc"]["point"])
for e in rj(I33_RUN / "metrics_primary.json"):
    if e.get("analysis_family") == "retrained_ablation" and e["metric"] in ("pr_auc", "roc_auc") and (e["condition"], e["seed"]) in i33_scores:
        fn = average_precision_score if e["metric"] == "pr_auc" else roc_auc_score
        diffs[f"{e['condition']}|{e['seed']}|{e['metric']}"] = abs(float(fn(y, i33_scores[(e["condition"], e["seed"])])) - e["value"])
rec("M1", "PASS" if max(diffs.values()) <= 1e-12 else "FAIL", n_values_checked=len(diffs), max_abs_difference=max(diffs.values()))

trap = {nm: m.trapezoid_pr_auc(y, scores[nm]) for nm in CMP}
rec("M2", "PASS", pr_auc_is="sklearn average_precision_score (step)", trapezoid_for_information={nm: {"average_precision": float(average_precision_score(y, scores[nm])), "trapezoid": trap[nm]} for nm in CMP})
prev = float(y.mean())
aps = {nm: boot["per_method"][f"{nm}|pr_auc"]["point"] for nm in P3_METHODS}
rec("M3", "PASS" if all(v > prev for v in aps.values()) else "FAIL", prevalence=prev, pr_auc=aps)

r37 = rj(r3739 / "false_alarms_item37.json")["methods"]; r38 = rj(r3739 / "coverage_item38.json")["methods"]; r39 = rj(r3739 / "counts_item39.json")
intervals = []
def walk(o, path):
    if isinstance(o, dict):
        if "ci_lo" in o and "ci_hi" in o and "point" in o:
            intervals.append((path, o))
        for k, v in o.items():
            walk(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f"{path}[{i}]")
for name, obj in (("phase3_bootstrap", boot), ("item33_contrasts", rj(I33_RUN / "paired_contrasts.json")), ("items37", r37), ("items38", r38), ("item40", item40)):
    walk(obj, name)
for c in rj(I33_RUN / "paired_contrasts.json")["contrasts"]:
    b = c["summary"]["bootstrap_seed_mean"]; intervals.append((f"item33/{c['register_id']}/{c['summary']['comparison']}/seed_mean", b))
bad_order = [p for p, o in intervals if o["ci_lo"] is not None and o["ci_lo"] > o["ci_hi"]]
outside = [p for p, o in intervals if o["ci_lo"] is not None and o["point"] is not None and not (o["ci_lo"] - 1e-12 <= o["point"] <= o["ci_hi"] + 1e-12)]
undefined = sum(int(o.get("n_undefined_replicates", 0) or 0) for _, o in intervals)
rec("M4", "FAIL" if bad_order else ("FLAG" if outside else "PASS"), n_intervals=len(intervals), lower_above_upper=bad_order,
    point_outside_interval=outside, total_undefined_replicates=undefined)

m5 = []
for k, v in r37.items():
    for g, blk in v["false_alarms"].items():
        if blk["episodes_total"] != blk["true"] + blk["ongoing"] + blk["false"]:
            m5.append(f"{k}/{g}: episode classes do not sum")
for k, v in r38.items():
    for L, cv in v["coverage"].items():
        for tag in ("primary_all_events", "primary_first_events", "sustained_all_events"):
            if not (cv[tag]["numerator"] <= cv[tag]["denominator"] <= v["events"]):
                m5.append(f"{k}/{L}/{tag}: covered <= eligible <= events violated")
for nm in CMP:
    ev = m37.event_table(traj, times, unsafe, scores[nm], rj(P3_RUN / "metrics_primary.json")["thresholds"][nm])
    lt = ev["lead_s"].dropna()
    if not ((lt > 0) & (lt <= 5.0 + 1e-9)).all():
        m5.append(f"{nm}: lead time outside (0, 5] s")
reg = r39["test_by_regime"]; te = r39["test_events"]
if sum(r["events"] for r in reg) != te["events"] or sum(r["positive_rows"] for r in reg) != te["positive_rows"] or sum(r["trajectories"] for r in reg) != T:
    m5.append("regime counts do not sum to the totals")
rec("M5", "FAIL" if m5 else "PASS", problems=m5)

failed = [k for k, v in checks.items() if v["status"] == "FAIL"]
need(not failed, f"Item 42 checks failed: {failed}")

# ---- outputs ---------------------------------------------------------------------------------------------------------------
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
od = repo / "outputs/items33_42/items40_42" / f"run_{stamp}"
(od / "figures").mkdir(parents=True, exist_ok=False)
def W(name, obj):
    with open(od / name, "x") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, default=lambda o: o.item() if hasattr(o, "item") else str(o))
W("item40_matched_operating_points.json", {"banner": EVIDENCE, **item40})

# ---- Item 41: figures -------------------------------------------------------------------------------------------------------
step("Item 41 figures and report")
COL = {"frozen_temporal": "C0", "instantaneous_model_a": "C1", "aoa_signed": "C2"}
def save(fig, name, caption):
    fig.text(0.01, 0.005, EVIDENCE, fontsize=6, color="0.35")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(od / "figures" / name, dpi=120); plt.close(fig)
    return f"![{caption}](figures/{name})\n\n*{caption}* {EVIDENCE}\n"
figs = []
fig, ax = plt.subplots(figsize=(6, 4.5))
for nm in CMP:
    p, r, _ = precision_recall_curve(y, scores[nm]); ax.plot(r, p, color=COL[nm], label=f"{nm} (PR-AUC {aps[nm]:.3f})")
ax.axhline(prev, ls="--", color="0.5", label=f"prevalence {prev:.3f}"); ax.set_xlabel("recall"); ax.set_ylabel("precision"); ax.legend(fontsize=8)
figs.append(save(fig, "a_pr_curves.png", "Figure (a): test precision-recall curves."))
fig, ax = plt.subplots(figsize=(6, 4))
for nm in CMP:
    Ls = [float(k[:-1]) for k in r38[nm]["coverage"]]; cv = [r38[nm]["coverage"][k]["primary_all_events"] for k in r38[nm]["coverage"]]
    ax.errorbar(Ls, [c["point"] for c in cv], yerr=[[c["point"] - c["ci_lo"] for c in cv], [c["ci_hi"] - c["point"] for c in cv]], color=COL[nm], marker="o", capsize=3, label=nm)
ax.set_xlabel("lead time L (s)"); ax.set_ylabel("events warned at least L s ahead"); ax.set_ylim(0, 1.02); ax.legend(fontsize=8)
figs.append(save(fig, "b_coverage_vs_lead.png", "Figure (b): coverage against lead time at each method's own validation-selected threshold (Items 37-39), 95% trajectory-bootstrap intervals."))
curve = {}
for nm in CMP:
    pts = []
    for thr in val_grid[nm]:
        fa = m.false_episode_starts(tfirst, y, unsafe, scores[nm] > thr).sum() / span.sum() * H
        ev = m37.event_table(traj, times, unsafe, scores[nm], thr); n_, d_ = m37.coverage_per_trajectory(ev, order, 4.0)
        pts.append((float(fa), float(n_.sum() / d_.sum())))
    curve[nm] = pts
W("figure_c_curve_points.json", {"note": "test-derived, descriptive only; thresholds are every 10th validation quantile level of the Item 40 grid", "points": curve})
fig, ax = plt.subplots(figsize=(6, 4.5))
for nm in CMP:
    a = np.array(curve[nm]); ax.plot(a[:, 0], a[:, 1], color=COL[nm], marker=".", label=nm)
ax.set_xscale("symlog", linthresh=1); ax.set_xlabel("test false-warning episodes per simulated hour"); ax.set_ylabel("coverage at 4 s"); ax.legend(fontsize=8)
figs.append(save(fig, "c_false_alarm_vs_coverage.png", "Figure (c): test false-episode rate against coverage at 4 s over the validation threshold grid (every 10th level). Descriptive, drawn from test data, not used for any choice."))
con = rj(I33_RUN / "paired_contrasts.json")["contrasts"]
fig, ax = plt.subplots(figsize=(6, 3.8))
lbl = [f"{c['register_id']}: {c['summary']['reference']} - {c['summary']['comparison']} ({c['summary']['metric']})" for c in con]
bs = [c["summary"]["bootstrap_seed_mean"] for c in con]
ax.errorbar([b["point"] for b in bs], range(len(bs)), xerr=[[b["point"] - b["ci_lo"] for b in bs], [b["ci_hi"] - b["point"] for b in bs]], fmt="o", capsize=3)
ax.axvline(0, color="0.5", ls="--"); ax.set_yticks(range(len(bs))); ax.set_yticklabels(lbl, fontsize=7); ax.invert_yaxis(); ax.set_xlabel("seed-mean difference (95% trajectory-bootstrap interval)")
figs.append(save(fig, "d_item33_contrasts.png", "Figure (d): Item 33 control-input ablation contrasts. All intervals include 0: no difference demonstrated; not evidence of no effect."))
fig, ax = plt.subplots(figsize=(6.5, 4.8))
ck = [k for k in item40["contrasts"] if "coverage" in k]
cv = [item40["contrasts"][k] for k in ck]
ax.errorbar([c["point"] for c in cv], range(len(cv)), xerr=[[c["point"] - c["ci_lo"] for c in cv], [c["ci_hi"] - c["point"] for c in cv]], fmt="o", capsize=3)
ax.axvline(0, color="0.5", ls="--"); ax.set_yticks(range(len(cv))); ax.set_yticklabels([k.replace("frozen_temporal", "frozen").replace("instantaneous_model_a", "instantaneous") for k in ck], fontsize=6.5); ax.invert_yaxis()
ax.set_xlabel("coverage difference (95% paired trajectory-bootstrap interval)")
figs.append(save(fig, "e_item40_coverage_contrasts.png", f"Figure (e): Item 40 coverage contrasts at validation-matched false-warning rates (descriptive, unadjusted; {item40['n_contrasts']} contrasts in total)."))

# ---- Item 41: headline statements (derived from the records) and report -------------------------------------------------
def stmt(sid, text, source, rec_):
    return {"id": sid, "text": text, "source": source, "point": rec_["point"], "ci_lo": rec_["ci_lo"], "ci_hi": rec_["ci_hi"],
            "sign": "positive" if rec_["point"] > 0 else ("negative" if rec_["point"] < 0 else "zero"),
            "includes_zero": bool(rec_["ci_lo"] <= 0 <= rec_["ci_hi"])}
fmt = lambda x, p=4: "—" if x is None else format(float(x), f".{p}g")
ci = lambda r, p=4: f"{fmt(r['point'], p)} [{fmt(r['ci_lo'], p)}, {fmt(r['ci_hi'], p)}]"
inc = lambda r: "interval includes 0" if r["ci_lo"] <= 0 <= r["ci_hi"] else "interval excludes 0"
heads = []
for k in ("frozen_temporal - instantaneous_model_a | pr_auc", "frozen_temporal - aoa_signed | pr_auc", "instantaneous_model_a - aoa_signed | pr_auc"):
    r = boot["paired_differences"][k]
    heads.append(stmt(f"P3:{k}", f"Phase 3 {k}: {ci(r)}; {inc(r)}.", "outputs/phase3/run_20261013T140820817642Z/bootstrap.json", r))
for c in con:
    if c["summary"]["metric"] == "pr_auc":
        b = c["summary"]["bootstrap_seed_mean"]
        heads.append(stmt(f"I33:{c['register_id']}", f"Item 33 {c['register_id']} ({c['status']}) PR-AUC {c['summary']['reference']} - {c['summary']['comparison']}: {ci(b)}; {inc(b)}.",
                          "outputs/items33_42/item33/run_20261013T162344038252Z/paired_contrasts.json", b))
for k, r in item40["contrasts"].items():
    heads.append(stmt(f"I40:{k}", f"Item 40 {k}: {ci(r)}; {inc(r)}.", f"{od.relative_to(repo)}/item40_matched_operating_points.json", r))
W("headline_statements.json", heads)

mask_rows = rj(I33_RUN / "masking_results.json")["rows"]
md = [r["delta_vs_unmasked"] for r in mask_rows if r.get("delta_vs_unmasked") is not None]
srcs = [P3_RUN / "bootstrap.json", P3_RUN / "metrics_primary.json", I33_RUN / "paired_contrasts.json", I33_RUN / "masking_results.json",
        r3739 / "counts_item39.json", r3739 / "false_alarms_item37.json", r3739 / "coverage_item38.json", od / "item40_matched_operating_points.json"]
Lr = [f"# AeroGuard comparison report — Items 33–40 (run `{od.name}`)\n", f"> {EVIDENCE} Rates are per simulated hour of eligible evaluation time. "
      "No acceptable false-alarm rate, required coverage or meaningful-effect margin is defined. Nothing here is evidence about real aircraft, and no causal claim is made.\n",
      f"Generated from machine-readable results only (protocol SHA-256 `{PROTOCOL_SHA256}`). Every headline statement is re-derived independently by the Item 42 checks (`item42_checks.json`).\n",
      "## 1. Threshold-free comparison (Phase 3, paired trajectory bootstrap, B = 1000)\n",
      "| Method | PR-AUC [95% CI] | ROC-AUC [95% CI] |\n|---|---|---|"]
for nm in P3_METHODS:
    Lr.append(f"| {nm} | {ci(boot['per_method'][nm + '|pr_auc'])} | {ci(boot['per_method'][nm + '|roc_auc'])} |")
Lr.append(f"\nPrevalence (positive-row fraction): {prev:.4f}. Paired differences:\n")
Lr += [f"- {h['text']}" for h in heads if h["id"].startswith("P3:")]
Lr.append("\n" + figs[0])
Lr.append("## 2. Control-input ablation (Item 33, retrained models, seed mean over 5 seeds)\n")
Lr += [f"- {h['text']}" for h in heads if h["id"].startswith("I33:")]
Lr.append(f"\nNo difference was demonstrated for any PR-AUC contrast. This does not show that the conditions perform alike (no margin was defined). "
          f"Frozen-model input masking (a different analysis) changed PR-AUC by {min(md):.3f} to {max(md):.3f}.\n")
Lr.append(figs[3])
Lr.append("## 3. Data counts, false warnings and coverage at each method's own threshold (Items 37–39)\n")
s3 = r39["splits"]["test"]
Lr.append(f"Test: {s3['usable_rows']:,} usable rows, {s3['trajectories_with_usable_rows']} trajectories, {s3['eligible_seconds_span']/3600:.3f} eligible simulated hours, "
          f"{te['events']} stall events in {te['trajectories_with_events']} trajectories. Thresholds are not matched across methods here, so these rows are not ranked.\n")
Lr.append("| Method | False episodes / sim. hour [95% CI] | Coverage 2 s | Coverage 4 s |\n|---|---|---|---|")
for nm in P3_METHODS:
    Lr.append(f"| {nm} | {ci(r37[nm]['false_alarms']['gap_0s']['per_hour_span'])} | {ci(r38[nm]['coverage']['2s']['primary_all_events'])} | {ci(r38[nm]['coverage']['4s']['primary_all_events'])} |")
Lr.append("\n" + figs[1])
Lr.append("## 4. Fair comparison at validation-matched false-warning rates (Item 40)\n")
Lr.append("Thresholds were chosen on validation data only so that each method's validation false-episode rate is at most R per simulated hour. "
          "R is a comparison grid, not an acceptable rate. Test rates are not equal across methods and are shown next to coverage.\n")
Lr.append("| Method | R | Threshold | Val. rate | Test false / sim. hour [95% CI] | Test coverage 2 s | Test coverage 4 s | Sustained 4 s |\n|---|---|---|---|---|---|---|---|")
for nm in CMP:
    for R in m.TARGET_RATES:
        e = item40["methods"][nm][f"{R:g}"]
        Lr.append(f"| {nm} | {R:g} | {fmt(e['threshold'], 6)} | {fmt(e['val_rate'])} | {ci(e['test_false_per_sim_hour'])} | {ci(e['test_coverage_2s'])} | {ci(e['test_coverage_4s'])} | {ci(e['test_sustained_coverage_4s'])} |")
Lr.append(f"\nPaired contrasts ({item40['n_contrasts']} in total, unadjusted, descriptive; \"interval excludes 0\" is not a p-value):\n")
Lr += [f"- {h['text']}" for h in heads if h["id"].startswith("I40:")]
Lr.append("\n" + figs[4] + "\n" + figs[2])
Lr.append("## 5. Checks (Item 42)\n")
Lr.append("| Check | Status |\n|---|---|")
Lr += [f"| {k} | {v['status']} |" for k, v in checks.items()]
Lr.append("\nC1 (headline statements re-derived) and C2 (wording scan) are recorded in `item42_checks.json` after this report is written.\n")
Lr.append("## 6. Limitations\n")
Lr.append("- Previously exposed test data on a regenerated copy; about 1.49 simulated hours and 76 events in 57 trajectories; intervals are wide.")
Lr.append("- The trajectory bootstrap treats trajectories as exchangeable; shared simulator regimes may make it understate uncertainty.")
Lr.append("- One simulated aircraft with scripted, open-loop controls. Nothing here transfers to real aircraft without new evidence.\n")
Lr.append("## Sources\n")
Lr += [f"- `{p.relative_to(repo)}` — SHA-256 `{sha(p)}`" for p in srcs]
with open(od / "REPORT.md", "x") as fh:
    fh.write("\n".join(Lr) + "\n")

# ---- Item 42: C1 independent re-derivation, C2 wording scan -------------------------------------------------------------
c1 = []
b2 = rj(P3_RUN / "bootstrap.json")["paired_differences"]
c2x = {c["register_id"]: c["summary"]["bootstrap_seed_mean"] for c in rj(I33_RUN / "paired_contrasts.json")["contrasts"] if c["summary"]["metric"] == "pr_auc"}
i40 = rj(od / "item40_matched_operating_points.json")["contrasts"]
report_text = open(od / "REPORT.md").read()
for h in rj(od / "headline_statements.json"):
    fam, key = h["id"].split(":", 1)
    src = b2[key] if fam == "P3" else (c2x[key] if fam == "I33" else i40[key])
    ok = (np.sign(src["point"]) == {"positive": 1, "negative": -1, "zero": 0}[h["sign"]]
          and bool(src["ci_lo"] <= 0 <= src["ci_hi"]) == h["includes_zero"]
          and (("interval includes 0" in h["text"]) == h["includes_zero"]) and h["text"] in report_text)
    c1.append({"id": h["id"], "ok": bool(ok)})
rec("C1", "PASS" if all(x["ok"] for x in c1) else "FAIL", n_statements=len(c1), failed=[x["id"] for x in c1 if not x["ok"]])
scan_files = sorted(set(list(P3_RUN.glob("REPORT*.md")) + list(I33_RUN.glob("REPORT*.md")) + [r3739 / "REPORT.md", od / "REPORT.md"]))
c2 = {str(p.relative_to(repo)): m.wording_scan(open(p).read().splitlines()) for p in scan_files}
nflag = sum(x["flag"] for v in c2.values() for x in v)
rec("C2", "FLAG" if nflag else "PASS", n_hits=sum(len(v) for v in c2.values()), n_flagged=nflag,
    flagged=[{"file": f, **x} for f, v in c2.items() for x in v if x["flag"]], manual_review="see C2_REVIEW.md (added after the run)" if nflag else None)
W("item42_checks.json", {"banner": EVIDENCE, "checks": checks, "order_of_operations": log["order_of_operations"]})
W("provenance.json", {"protocol_sha256": PROTOCOL_SHA256, "panels": PANEL_SHA, "frozen_model_sha256": FROZEN_SHA256,
                      "instantaneous_model_sha256": sha(ma_path), "validation_score_array_sha256": val_score_hashes,
                      "code": {p.name: sha(p) for p in sorted(HERE.glob("*.py"))}, "utc": stamp,
                      "bootstrap": {"B": m.B, "seed": m.SEED, "pct": list(m.PCT), "unit": "trajectory"}})
need(checks["C1"]["status"] != "FAIL", f"C1 failed: {checks['C1']['failed']}")
print(od)
print(json.dumps({k: v["status"] for k, v in checks.items()}))
