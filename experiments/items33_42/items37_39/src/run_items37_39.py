"""Run Items 37-39 on the stored scores (PROTOCOL.md in the parent directory). Writes only small JSON/Markdown files,
exclusively, below outputs/items33_42/items37_39/run_<UTC>/. No model is trained or re-scored.

usage: run_items37_39.py <repo_root> <data_dir> <phase3_scratch_run_dir> <item33_scratch_run_dir>
"""

import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

repo, data_dir, p3, i33 = (Path(a).resolve() for a in sys.argv[1:5])
sys.path[:0] = [str(repo), str(repo / "experiments/items33_42/item33/src"), str(Path(__file__).resolve().parent)]
import items37_39 as m  # noqa: E402
from item33.population import key_hash, row_keys, assert_consecutive_steps  # noqa: E402
from phase3.population import usable_mask  # noqa: E402
from ml.temporal_config import temporal_feature_columns  # noqa: E402

PROTOCOL_SHA256 = "07b170eda959870964fefeaedf73e1ed3ff8db1f696fe0fc4e8f408a12c09bfb"
PANEL_SHA = {"train": "1a39472881280e084f3cab5d94fa4c80382d65a7075df59cd7a45fd4d5af4b43",
             "val": "9416fc8005b206eefbcdbeeb0d043a45036e8b2d6251ae3850b176765565a0e0",
             "test": "c03634b4cc793c57bbe065e710a4a98bfe2bf69fdf5a55beb56a1c0ba33241b8"}
P3_RUN = "outputs/phase3/run_20261013T140820817642Z"
I33_RUN = "outputs/items33_42/item33/run_20261013T162344038252Z"
CONDS, SEEDS = ("C0", "C1", "C2", "C3", "X1"), (20260817, 20261101, 20261102, 20261103, 20261104)
P3_METHODS = ("aoa_signed", "aoa_two_sided", "instantaneous_model_a", "frozen_temporal")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def need(cond, msg):
    if not cond:
        raise SystemExit(f"STOP: {msg}")


# ---- integrity of every input ----------------------------------------------------------------------------------------
need(sha(repo / "experiments/items33_42/items37_39/PROTOCOL.md") == PROTOCOL_SHA256, "protocol hash differs")
for s, h in PANEL_SHA.items():
    need(sha(data_dir / f"ml_temporal_v03/temporal_{s}.parquet") == h, f"{s} panel hash differs")
p3_audit = json.load(open(repo / P3_RUN / "audit.json"))["run_files"]
i33_audit = json.load(open(repo / I33_RUN / "audit.json"))["files"]
p3_thr = json.load(open(repo / P3_RUN / "metrics_primary.json"))["thresholds"]
methods = {}
for nm in P3_METHODS:
    f = p3 / f"scores_{nm}.npy"
    need(sha(f) == p3_audit[f.name], f"Phase 3 score hash differs: {nm}")
    methods[nm] = {"family": "phase3", "condition": nm, "seed": None, "threshold": float(p3_thr[nm]), "score": np.load(f)}
for c in CONDS:
    for s in SEEDS:
        f = i33 / f"scores_{c}_{s}.npy"
        need(sha(f) == i33_audit[f.name]["sha256"], f"Item 33 score hash differs: {c} {s}")
        thr = json.load(open(repo / I33_RUN / f"threshold_{c}_{s}.json"))["threshold"]
        methods[f"{c}|{s}"] = {"family": "item33", "condition": c, "seed": s, "threshold": float(thr), "score": np.load(f)}

# ---- common population -----------------------------------------------------------------------------------------------
win = list(temporal_feature_columns(1.0))
cols = ["trajectory_id", "time", "is_unsafe", "future_stall_5s", "future_stall_5s_available", "time_to_stall"] + win
test = pd.read_parquet(data_dir / "ml_temporal_v03/temporal_test.parquet", columns=cols)
mask = usable_mask(test)
sub = test.loc[mask].reset_index(drop=True)
keys = row_keys(sub); assert_consecutive_steps(keys)
kh = key_hash(keys)
need(kh == json.load(open(repo / I33_RUN / "population.json"))["test_key_hash"], "population key hash differs from Item 33")
for k, v in methods.items():
    need(v["score"].shape == (len(sub),) and np.isfinite(v["score"]).all(), f"score vector does not match the population: {k}")
traj = sub["trajectory_id"].to_numpy(); times = sub["time"].to_numpy(); label = sub["future_stall_5s"].to_numpy(); unsafe = sub["is_unsafe"].to_numpy().astype(bool)
order = list(pd.unique(traj))
meta = pd.read_csv(repo / "data/metadata/trajectory_metadata_v3.csv")
regime = dict(zip(meta["trajectory_id"], meta["generation_mode"]))

# ---- Item 39: counts -----------------------------------------------------------------------------------------------
manifest = pd.read_csv(repo / "data/splits/split_manifest_v3.csv")
counts = {"splits": {}}
panel_ids = {}
for s in ("train", "val", "test"):
    df = test if s == "test" else pd.read_parquet(data_dir / f"ml_temporal_v03/temporal_{s}.parquet", columns=["trajectory_id", "time", "future_stall_5s_available"] + win)
    um = usable_mask(df)
    u = df.loc[um]
    ids_all = pd.unique(df["trajectory_id"]); ids_use = set(pd.unique(u["trajectory_id"]))
    panel_ids[s] = set(ids_all)
    excl = [t for t in ids_all if t not in ids_use]
    em = meta.set_index("trajectory_id").loc[excl] if excl else meta.iloc[:0]
    g = u.groupby("trajectory_id")["time"]
    counts["splits"][s] = {
        "trajectories_in_manifest": int((manifest["split"] == s).sum()), "trajectories_in_panel": int(len(ids_all)),
        "trajectories_with_usable_rows": int(len(ids_use)), "trajectories_excluded": int(len(excl)),
        "excluded_reasons": {"termination_reason": em["termination_reason"].value_counts().to_dict() if len(em) else {},
                             "n_steps_max_among_excluded": int(em["n_steps"].max()) if len(em) else None,
                             "rule": "a trajectory needs more than 600 steps for any row to have a full 1 s history and a full 5 s label horizon"},
        "panel_rows": int(len(df)), "usable_rows": int(um.sum()),
        "eligible_seconds_span": float((g.max() - g.min()).sum()), "eligible_seconds_rows": float(um.sum() * m.DT),
        "duplicate_keys": int(df.duplicated(["trajectory_id", "time"]).sum()),
    }
counts["split_overlap"] = {f"{a}&{b}": len(panel_ids[a] & panel_ids[b]) for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
ic = ["initial_airspeed", "initial_altitude", "initial_alpha"]
counts["duplicate_initial_conditions_in_metadata"] = int(meta.duplicated(ic).sum())
ev0 = m.event_table(traj, times, unsafe, methods["frozen_temporal"]["score"], methods["frozen_temporal"]["threshold"])
traj_with_unsafe = set(test.loc[test["is_unsafe"].astype(bool), "trajectory_id"])
traj_with_events = set(ev0["trajectory_id"])
outside = []
first_use = sub.groupby("trajectory_id")["time"].min(); last_use = sub.groupby("trajectory_id")["time"].max()
for t in sorted(traj_with_unsafe - traj_with_events):
    ut = test.loc[(test["trajectory_id"] == t) & test["is_unsafe"].astype(bool), "time"]
    if t not in first_use.index:
        why = "trajectory has no usable rows"
    elif ut.min() > last_use[t]:
        why = "unsafe rows only after the last usable row (final 5 s, no label horizon)"
    elif ut.max() < first_use[t]:
        why = "unsafe rows only before the first usable row (first 1 s, no full history)"
    else:
        why = "other"
    outside.append({"trajectory_id": t, "reason": why, "regime": regime.get(t)})
reg_rows = []
for r in sorted(set(regime[t] for t in order)):
    tm = np.array([regime[t] == r for t in traj])
    ev_r = ev0[[regime[t] == r for t in ev0["trajectory_id"]]]
    reg_rows.append({"regime": r, "trajectories": int(len(set(traj[tm]))), "rows": int(tm.sum()), "positive_rows": int((label[tm] == 1).sum()),
                     "events": int(len(ev_r)), "event_bearing_trajectories": int(ev_r["trajectory_id"].nunique())})
counts["test_events"] = {
    "events": int(len(ev0)), "first_events": int(ev0["first_event"].sum()), "later_events": int((~ev0["first_event"]).sum()),
    "trajectories_with_events": int(len(traj_with_events)), "trajectories_without_events": int(len(order) - len(traj_with_events)),
    "left_censored_events": int(ev0["left_censored"].sum()),
    "trajectories_with_any_unsafe_run_in_panel": int(len(traj_with_unsafe)), "trajectories_with_unsafe_runs_excluded": outside,
    "positive_rows": int((label == 1).sum()), "negative_rows": int((label == 0).sum()),
}
counts["test_by_regime"] = reg_rows
counts["independent_units"] = {"rows": int(len(sub)), "trajectories": int(len(order)), "event_bearing_trajectories": int(len(traj_with_events)),
                               "note": "rows within a trajectory are strongly dependent; trajectories are the resampling unit; event metrics rest on the event-bearing trajectories"}

# ---- Items 37 and 38 per method ---------------------------------------------------------------------------------------
H = 3600.0
res = {}
for k, v in methods.items():
    out = {"family": v["family"], "condition": v["condition"], "seed": v["seed"], "threshold": v["threshold"], "false_alarms": {}, "coverage": {}}
    for gap in m.MERGE_GAPS_S:
        c = m.false_alarm_counts(traj, times, label, unsafe, v["score"], v["threshold"], gap)
        blk = {"episodes_total": int(c["total"].sum()), "true": int(c["true"].sum()), "ongoing": int(c["ongoing"].sum()), "false": int(c["false"].sum()),
               "per_hour_span": m.ratio_bootstrap(c["false"], c["span_s"], H)}
        if gap == 0.0:
            blk["existing_definition_false_incl_ongoing_per_hour_span"] = m.ratio_bootstrap(c["false"] + c["ongoing"], c["span_s"], H)
            blk["per_hour_rows_denominator"] = m.ratio_bootstrap(c["false"], c["rows_s"], H)
            d = blk["true"] + blk["false"]
            blk["episode_precision"] = blk["true"] / d if d else None
            blk["trajectories_with_a_false_episode"] = int((c["false"] > 0).sum())
            blk["false_episodes_by_regime"] = {r: int(sum(c["false"][i] for i, t in enumerate(order) if regime[t] == r)) for r in sorted(set(regime.values()))}
        out["false_alarms"][f"gap_{gap:g}s"] = blk
    ev = m.event_table(traj, times, unsafe, v["score"], v["threshold"])
    out["events_warned"] = int(ev["warned"].sum()); out["events"] = int(len(ev))
    for L in m.LEADS_S:
        cov = {}
        for tag, kw in (("primary_all_events", {}), ("primary_first_events", {"first_only": True}), ("sustained_all_events", {"sustained": True})):
            num, den = m.coverage_per_trajectory(ev, order, L, **kw)
            cov[tag] = m.ratio_bootstrap(num, den)
        cov["events_ineligible_at_L"] = int(len(ev) - cov["primary_all_events"]["denominator"])
        out["coverage"][f"{L:g}s"] = cov
    res[k] = out

# ---- cross-checks against values stored by earlier runs -----------------------------------------------------------------
p3m = json.load(open(repo / P3_RUN / "metrics_primary.json"))["methods"]
checks = {}
for nm in P3_METHODS:
    op = p3m[nm]["operating_point"]
    checks[nm] = {"events_warned_equal": res[nm]["events_warned"] == op["events"]["n_warned"],
                  "existing_definition_rate_equal": abs(res[nm]["false_alarms"]["gap_0s"]["existing_definition_false_incl_ongoing_per_hour_span"]["point"]
                                                        - op["false_alarms"]["false_alarm_episodes_per_eligible_hour"]) < 1e-9}
for c in CONDS:
    for s in SEEDS:
        e = json.load(open(repo / I33_RUN / f"event_level_{c}_{s}.json"))["own_threshold"]["events"]
        checks[f"{c}|{s}"] = {"events_warned_equal": res[f"{c}|{s}"]["events_warned"] == e["n_warned"]}
need(all(all(v.values()) for v in checks.values()), f"cross-check against stored records failed: {checks}")

# ---- outputs -------------------------------------------------------------------------------------------------------------
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
od = repo / "outputs/items33_42/items37_39" / f"run_{stamp}"
od.mkdir(parents=True, exist_ok=False)
def W(name, obj):
    with open(od / name, "x") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=lambda o: o.item() if hasattr(o, "item") else str(o))
banner = ("Regenerated v0.3 copy; previously exposed test data; not blind or independent; rates are per simulated hour of eligible "
          "evaluation time, not operational rates; simulation only.")
W("counts_item39.json", {"banner": banner, "population_key_hash": kh, **counts})
W("false_alarms_item37.json", {"banner": banner, "methods": {k: {x: v[x] for x in ("family", "condition", "seed", "threshold", "false_alarms")} for k, v in res.items()}})
W("coverage_item38.json", {"banner": banner, "methods": {k: {x: v[x] for x in ("family", "condition", "seed", "threshold", "events", "events_warned", "coverage")} for k, v in res.items()}})
W("cross_checks.json", checks)
W("provenance.json", {"protocol_sha256": PROTOCOL_SHA256, "panels": PANEL_SHA, "phase3_scores": {n: p3_audit[f"scores_{n}.npy"] for n in P3_METHODS},
                      "item33_scores": {f"{c}|{s}": i33_audit[f"scores_{c}_{s}.npy"]["sha256"] for c in CONDS for s in SEEDS},
                      "code": {p.name: sha(p) for p in sorted(Path(__file__).resolve().parent.glob("*.py"))}, "utc": stamp,
                      "bootstrap": {"B": m.B, "seed": m.SEED, "pct": list(m.PCT), "unit": "trajectory"}})

# ---- report (every number from the records above) ------------------------------------------------------------------------
f = lambda x, p=4: "undefined" if x is None else format(float(x), f".{p}g")
ci = lambda r, p=4: f"{f(r['point'], p)} [{f(r['ci_lo'], p)}, {f(r['ci_hi'], p)}]"
L = [f"# Items 37–39 report (run `{od.name}`)\n", f"> {banner}\n", f"Protocol SHA-256 `{PROTOCOL_SHA256}` (committed before this run). Population: {len(sub):,} usable test rows, {len(order)} trajectories.\n"]
L.append("## Item 39 — trajectory and event counts\n")
L.append("| Split | Trajectories (manifest / panel) | With usable rows | Excluded | Usable rows | Eligible time (span) |\n|---|---|---|---|---|---|")
for s, d in counts["splits"].items():
    L.append(f"| {s} | {d['trajectories_in_manifest']} / {d['trajectories_in_panel']} | {d['trajectories_with_usable_rows']} | {d['trajectories_excluded']} | {d['usable_rows']:,} | {d['eligible_seconds_span']:.2f} s ({d['eligible_seconds_span']/3600:.3f} h) |")
te = counts["test_events"]
L.append(f"\nTest events: {te['events']} ({te['first_events']} first, {te['later_events']} later) in {te['trajectories_with_events']} trajectories; {te['trajectories_without_events']} usable trajectories have no event. "
         f"{len(te['trajectories_with_unsafe_runs_excluded'])} further trajectories contain an unsafe run that lies outside the usable rows (excluded; reasons in `counts_item39.json`). Left-censored events (stall already under way at the first usable row): {te['left_censored_events']}. "
         f"Positive rows {te['positive_rows']:,}, negative rows {te['negative_rows']:,}. Split overlap {counts['split_overlap']}; duplicate keys {[d['duplicate_keys'] for d in counts['splits'].values()]}; duplicate initial conditions in the metadata: {counts['duplicate_initial_conditions_in_metadata']}.\n")
L.append("| Regime (test, usable) | Trajectories | Rows | Positive rows | Events | Event-bearing trajectories |\n|---|---|---|---|---|---|")
for r in reg_rows:
    L.append(f"| {r['regime']} | {r['trajectories']} | {r['rows']:,} | {r['positive_rows']:,} | {r['events']} | {r['event_bearing_trajectories']} |")
L.append("\nIndependent evidence: the frames are not independent. The 456 test trajectories are the resampling unit, and event-level results rest on the "
         f"{te['trajectories_with_events']} event-bearing trajectories.\n")
L.append("## Item 37 — false-warning episodes per simulated flight hour (primary: no merging, FALSE episodes only)\n")
L.append("| Method | Threshold | Episodes | True | Ongoing | False | False / sim. hour [95% CI] | Existing definition (incl. ongoing) | Merge 1 s | Merge 2 s | Episode precision |\n|---|---|---|---|---|---|---|---|---|---|---|")
for k in P3_METHODS:
    a = res[k]["false_alarms"]
    g0 = a["gap_0s"]
    L.append(f"| {k} | {f(res[k]['threshold'], 6)} | {g0['episodes_total']} | {g0['true']} | {g0['ongoing']} | {g0['false']} | {ci(g0['per_hour_span'])} | {ci(g0['existing_definition_false_incl_ongoing_per_hour_span'])} | {ci(a['gap_1s']['per_hour_span'])} | {ci(a['gap_2s']['per_hour_span'])} | {f(g0['episode_precision'])} |")
L.append("\nRetrained Item 33 models (own validation-selected thresholds), primary rate summarised across the five seeds (every seed and interval in `false_alarms_item37.json`):\n")
L.append("| Condition | Median false / sim. hour | Min | Max | Median false episodes |\n|---|---|---|---|---|")
for c in CONDS:
    rates = [res[f"{c}|{s}"]["false_alarms"]["gap_0s"]["per_hour_span"]["point"] for s in SEEDS]
    n = [res[f"{c}|{s}"]["false_alarms"]["gap_0s"]["false"] for s in SEEDS]
    L.append(f"| {c} | {f(np.median(rates))} | {f(min(rates))} | {f(max(rates))} | {f(np.median(n))} |")
L.append(f"\nThe denominator is {counts['splits']['test']['eligible_seconds_span']/3600:.3f} simulated hours, so each false episode adds about {3600/counts['splits']['test']['eligible_seconds_span']:.2f} per hour; intervals are wide.\n")
L.append("## Item 38 — warning coverage at lead times (primary: existing lead-time definition, all events)\n")
L.append("| Method | Events warned | Coverage at 2 s [95% CI] | Coverage at 4 s [95% CI] | Sustained warning, 2 s | Sustained warning, 4 s | Eligible events at 4 s |\n|---|---|---|---|---|---|---|")
for k in P3_METHODS:
    cv = res[k]["coverage"]
    L.append(f"| {k} | {res[k]['events_warned']}/{res[k]['events']} | {ci(cv['2s']['primary_all_events'])} | {ci(cv['4s']['primary_all_events'])} | {ci(cv['2s']['sustained_all_events'])} | {ci(cv['4s']['sustained_all_events'])} | {int(cv['4s']['primary_all_events']['denominator'])} |")
L.append("\n| Item 33 condition | Median coverage at 2 s (min–max over seeds) | Median coverage at 4 s (min–max) |\n|---|---|---|")
for c in CONDS:
    c2 = [res[f"{c}|{s}"]["coverage"]["2s"]["primary_all_events"]["point"] for s in SEEDS]
    c4 = [res[f"{c}|{s}"]["coverage"]["4s"]["primary_all_events"]["point"] for s in SEEDS]
    L.append(f"| {c} | {f(np.median(c2))} ({f(min(c2))}–{f(max(c2))}) | {f(np.median(c4))} ({f(min(c4))}–{f(max(c4))}) |")
L.append("\nAll lead times (0.5, 1, 2, 3, 4, 5 s), first-event-only coverage and per-seed intervals are in `coverage_item38.json`. The primary definition credits a warning that was active at some point in the 5 s before the crossing; the sustained definition requires the warning to stay on from t − L until the crossing.\n")
L.append("## Checks and limitations\n")
L.append("- Every input hash matched its audit record; all score vectors match the common population; the existing-definition false-alarm rates and warned-event counts reproduce the values stored by Phase 3 and Item 33 (`cross_checks.json`).")
L.append("- Previously exposed test data on a regenerated copy; about 1.49 simulated hours and 76 events in 57 trajectories; trajectories may share regime dependencies that the trajectory bootstrap does not model; thresholds are each model's own validation-selected threshold, not a matched operating point.")
L.append("- No acceptable false-alarm rate or required coverage is defined; nothing here is an operational rate or evidence about real aircraft.")
with open(od / "REPORT.md", "x") as fh:
    fh.write("\n".join(L) + "\n")
print(od)
