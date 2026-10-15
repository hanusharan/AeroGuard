"""Phase 4 experiment runner (experiments/phase4/PROTOCOL.md; deviations in DEVIATIONS.md).

usage:
  python scripts/run_phase4.py <data_dir> <run_dir> primary     # sections 2-8 on (P0, D0)
  python scripts/run_phase4.py <data_dir> <run_dir> jsbsim      # section 11 (needs primary)
  python scripts/run_phase4.py <data_dir> <run_dir> robust      # section 13 (needs primary)

<data_dir> holds the generated panels (outside Git); fitted models and score arrays are
written there too. <run_dir> (under outputs/phase4/) receives small JSON/CSV results only.
"""

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from phase4 import (BOOT_B, BOOT_SEED, DATA_SEEDS, DT, MODEL_SEEDS, PROTOCOL_RELPATH, PROTOCOL_SHA256,  # noqa: E402
                    ROBUST_MODEL_SEEDS, TRAIN_STRIDE)
from phase4 import configs as C  # noqa: E402
from phase4 import metrics as M  # noqa: E402
from phase4 import models as MD  # noqa: E402
from phase4 import uncertainty as U  # noqa: E402
from phase4.panel import FEATURES_D, FEATURES_XD, stride_rows  # noqa: E402

PRIMARY_SEED = MODEL_SEEDS[0]
RF_NAMES = ("M_D", "M_D_noSM", "M_A")
RULES = ("R_AoA", "R_SM")
GROUPS = ("SEEN", "IDH", "OOD", "C00")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def dump(obj, path):
    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)
    json.dump(obj, open(path, "w"), indent=1, default=conv)


def strip(d):
    """Drop private keys (bootstrap replicate arrays) before writing."""
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if not str(k).startswith("_")}
    return d


# ------------------------------------------------------------------------------------------------ data
def load_seed(data_dir: Path, seed_name: str):
    d = data_dir / seed_name
    cfgs = json.load(open(d / "configs.json"))
    frames, metas = [], []
    for c in cfgs:
        frames.append(pd.read_parquet(d / f"{c['config_id']}.parquet"))
        metas.append(pd.read_csv(d / f"{c['config_id']}_meta.csv"))
    df = pd.concat(frames, ignore_index=True)
    meta = pd.concat(metas, ignore_index=True)
    m = meta.set_index("trajectory_id")
    df["split"] = df["trajectory_id"].map(m["split"]).astype("category")
    df["generation_mode"] = df["trajectory_id"].map(m["generation_mode"]).astype("category")
    df["config_id"] = df["config_id"].astype("category")
    if df["split"].isna().any():
        raise SystemExit("STOP: rows without a split")
    return cfgs, df, meta


def populations(df: pd.DataFrame, part: dict) -> dict:
    cid = df["config_id"].astype(str)
    tr = cid.isin(part["TRAIN"])
    pops = {"SEEN": df.loc[tr & (df["split"] == "test")],
            "IDH": df.loc[cid.isin(part["IDH"])],
            "OOD": df.loc[cid.isin(part["OOD"])],
            "C00": df.loc[cid == "C00"]}
    fit = {"train": stride_rows(df.loc[tr & (df["split"] == "train")].reset_index(drop=True), TRAIN_STRIDE),
           "val": stride_rows(df.loc[tr & (df["split"] == "val")].reset_index(drop=True), TRAIN_STRIDE)}
    # leakage guards: no fitting trajectory in any evaluation population
    fit_ids = set(fit["train"]["trajectory_id"]) | set(fit["val"]["trajectory_id"])
    for g, p in pops.items():
        if fit_ids & set(p["trajectory_id"].unique()):
            raise SystemExit(f"STOP: fitting trajectory found in {g}")
    return {k: v.reset_index(drop=True) for k, v in pops.items()}, fit


def score_all(fitted: dict, rules: dict, frozen, pop: pd.DataFrame) -> dict:
    out = {}
    for key, f in fitted.items():
        out[key] = {"score": MD.score_rf(f, pop), "threshold": f["threshold"], "prob": True}
    for r in RULES:
        out[r] = {"score": MD.score_rule(r, pop), "threshold": rules[r]["threshold"], "prob": False}
    if frozen is not None:
        out["F_v03"] = {"score": MD.score_frozen(frozen, pop), "threshold": frozen["threshold"], "prob": True}
    return out


# ------------------------------------------------------------------------------------------------ primary
def primary(data_dir: Path, run_dir: Path):
    cfgs, df, meta = load_seed(data_dir, "D0")
    part = C.partition([dict(c) for c in cfgs], "P0")
    pops, fit = populations(df, part)
    del df
    log("populations", {g: (len(p), p["trajectory_id"].nunique()) for g, p in pops.items()}, "fit", {k: len(v) for k, v in fit.items()})
    model_dir = data_dir / "models_P0_D0"; model_dir.mkdir(exist_ok=True)

    fitted = {}
    for name in RF_NAMES + ("X_D", "X_D_noSM"):
        for s in MODEL_SEEDS:
            p = model_dir / f"{name}_{s}.joblib"
            if p.exists():
                fitted[(name, s)] = joblib.load(p)
            else:
                t0 = time.time()
                fitted[(name, s)] = MD.fit_rf(name, fit["train"], fit["val"], s, n_jobs=4)
                joblib.dump(fitted[(name, s)], p)
                log("fit", name, s, f"{time.time() - t0:.0f}s thr={fitted[(name, s)]['threshold']:.4f}")
    rules = MD.fit_rules(fit["train"], fit["val"])
    joblib.dump(rules, model_dir / "rules.joblib")
    frozen = MD.load_frozen(REPO)
    res = {"protocol_sha256": PROTOCOL_SHA256, "partition": part,
           "thresholds": {f"{n}|{s}": f["threshold"] for (n, s), f in fitted.items()} | {r: rules[r]["threshold"] for r in RULES},
           "fit_rows": {k: int(len(v)) for k, v in fit.items()},
           "fit_trajectories": {k: int(v["trajectory_id"].nunique()) for k, v in fit.items()}}

    # ---- scores on every evaluation population (primary seed for all models; all seeds for M_* RFs)
    scores = {}
    for g, pop in pops.items():
        f_primary = {n: fitted[(n, PRIMARY_SEED)] for n in RF_NAMES}
        scores[g] = score_all(f_primary, rules, frozen, pop)
        for n in RF_NAMES:
            for s in MODEL_SEEDS[1:]:
                scores[g][f"{n}|{s}"] = {"score": MD.score_rf(fitted[(n, s)], pop), "threshold": fitted[(n, s)]["threshold"], "prob": True}
        np.savez_compressed(data_dir / f"scores_P0_D0_{g}.npz", **{k: v["score"] for k, v in scores[g].items()})
        log("scored", g)

    # ---- section 3: metrics per group (bootstrap) and per configuration (point)
    group_metrics, reps = {}, {}
    for g, pop in pops.items():
        group_metrics[g] = {}
        for k in ("M_D", "M_D_noSM", "M_A", "R_AoA", "R_SM", "F_v03"):
            sc = scores[g][k]
            r = M.evaluate(pop, sc["score"], sc["threshold"], sc["score"] if sc["prob"] else None,
                           seed=BOOT_SEED + GROUPS.index(g), return_reps=True)
            reps[(g, k)] = r.pop("_reps")
            group_metrics[g][k] = r
        for n in RF_NAMES:  # across-seed summaries (point estimates)
            per = {}
            for s in MODEL_SEEDS:
                key = n if s == PRIMARY_SEED else f"{n}|{s}"
                sc = scores[g][key]
                r = M.evaluate(pop, sc["score"], sc["threshold"], sc["score"], boot=False)
                per[s] = {"pr_auc": r["row"]["pr_auc"], "event_recall": r["event"]["event_recall"],
                          "median_lead_s": r["event"]["median_lead_s"], "ece": r["row"]["ece"]}
            group_metrics[g][f"{n}_seeds"] = {"per_seed": per, **{m: {"median": float(np.median([v[m] for v in per.values()])),
                                              "min": float(np.min([v[m] for v in per.values()])), "max": float(np.max([v[m] for v in per.values()]))}
                                              for m in ("pr_auc", "event_recall", "median_lead_s", "ece")}}
        log("metrics", g)
    res["group_metrics"] = strip(group_metrics)

    per_cfg = {}
    for g, pop in pops.items():
        for cid in pop["config_id"].astype(str).unique():
            m = (pop["config_id"].astype(str) == cid).to_numpy()
            sub = pop.loc[m].reset_index(drop=True)
            per_cfg[cid] = {"group": g}
            for k in ("M_D", "M_D_noSM", "M_A", "R_AoA", "R_SM", "F_v03"):
                sc = scores[g][k]
                r = M.evaluate(sub, sc["score"][m], sc["threshold"], sc["score"][m] if sc["prob"] else None, boot=False)
                per_cfg[cid][k] = strip(r)
            per_cfg[cid]["evaluable"] = per_cfg[cid]["M_D"]["event"]["n_events"] >= 15
    un = C.unfamiliarity([dict(c) for c in cfgs], part["TRAIN"])
    for cid in per_cfg:
        per_cfg[cid].update(un[cid])
    res["per_config"] = per_cfg

    # ---- section 4: item 44
    d = {}
    for met, rk in (("pr_auc", "pr_auc"), ("event_recall", "event_recall")):
        a = group_metrics["IDH"]["M_D"]; b = group_metrics["SEEN"]["M_D"]
        pa = a["row"][met] if met == "pr_auc" else a["event"][met]
        pb = b["row"][met] if met == "pr_auc" else b["event"][met]
        diff_reps = reps[("IDH", "M_D")][rk] - reps[("SEEN", "M_D")][rk]
        d[met] = {"IDH": pa, "SEEN": pb, "delta": pa - pb, "ci95": M.ci(diff_reps)}
    seen_pr = group_metrics["SEEN"]["M_D"]["row"]["pr_auc"]
    worst = {c: per_cfg[c]["M_D"]["row"]["pr_auc"] - seen_pr for c in part["IDH"]}
    d["per_config_pr_auc_minus_seen"] = worst
    d["generalises_within_envelope"] = bool(d["pr_auc"]["delta"] >= -0.05 and d["event_recall"]["delta"] >= -0.10
                                            and min(worst.values()) >= -0.10)
    res["item44"] = d

    # ---- section 5: item 45
    rows = []
    for cid, v in per_cfg.items():
        rows.append({"config_id": cid, "group": v["group"], "d_ood": v["d_ood"], "n_out": v["n_params_outside_train_range"],
                     **{f"{k}_pr_auc": v[k]["row"]["pr_auc"] for k in ("M_D", "M_D_noSM", "M_A", "R_AoA", "R_SM", "F_v03")},
                     **{f"{k}_recall": v[k]["event"]["event_recall"] for k in ("M_D", "M_D_noSM", "M_A", "R_AoA", "R_SM", "F_v03")},
                     "M_D_median_lead": v["M_D"]["event"]["median_lead_s"], "n_events": v["M_D"]["event"]["n_events"],
                     "evaluable": v["evaluable"]})
    tab = pd.DataFrame(rows).sort_values("config_id")
    tab.to_csv(run_dir / "per_config.csv", index=False)
    rho, pval = spearmanr(tab["d_ood"], tab["M_D_pr_auc"] - seen_pr)
    res["item45"] = {"spearman_pr_auc_drop_vs_d_ood": {"rho": float(rho), "p": float(pval), "n_configs": int(len(tab)),
                                                       "note": "descriptive; TRAIN configurations have d_ood = 0"}}

    # ---- sections 6-7: items 46-47
    tr_X = fit["train"][FEATURES_D].to_numpy(dtype=np.float32)
    nov = U.Novelty(tr_X)
    val = fit["val"]
    pv = {s: MD.score_rf(fitted[("M_D", s)], val) for s in MODEL_SEEDS}
    u_val = {"U_amb": U.u_amb(pv[PRIMARY_SEED]), "U_ens": U.u_ens(list(pv.values())),
             "U_nov": nov(val[FEATURES_D].to_numpy(dtype=np.float32))}
    tau = {k: U.abstain_threshold(v) for k, v in u_val.items()}
    qhat = U.conformal_qhat(pv[PRIMARY_SEED], val["future_stall_5s"].to_numpy())
    item46, item47 = {"tau": tau}, {"qhat": qhat}
    for g, pop in pops.items():
        p = scores[g]["M_D"]["score"]
        u = {"U_amb": U.u_amb(p),
             "U_ens": U.u_ens([scores[g]["M_D" if s == PRIMARY_SEED else f"M_D|{s}"]["score"] for s in MODEL_SEEDS]),
             "U_nov": nov(pop[FEATURES_D].to_numpy(dtype=np.float32))}
        np.savez_compressed(data_dir / f"uncertainty_P0_D0_{g}.npz", **u)
        pred = p > scores[g]["M_D"]["threshold"]
        ev = M.event_table(pop["trajectory_id"].to_numpy(), pop["time"].to_numpy(), pop["is_unsafe"].to_numpy(), p, scores[g]["M_D"]["threshold"])
        item46[g] = {k: U.abstention_report(pop, pred, u[k], tau[k], ev) for k in u}
        y = pop["future_stall_5s"].to_numpy()
        item47[g] = {"M_D": {"ece": group_metrics[g]["M_D"]["row"]["ece"], "brier": group_metrics[g]["M_D"]["row"]["brier"]},
                     "F_v03": {"ece": group_metrics[g]["F_v03"]["row"]["ece"], "brier": group_metrics[g]["F_v03"]["row"]["brier"]},
                     "conformal": U.conformal_report(p, y, qhat),
                     "error_auroc": {k: item46[g][k]["error_auroc"] for k in u}}
        log("uncertainty", g)
    useful = {}
    for k in ("U_amb", "U_ens", "U_nov"):
        a = all(item46[g][k]["error_retained"] < item46[g][k]["error_all"] for g in GROUPS)
        b = item46["OOD"][k]["abstention_rate"] > item46["SEEN"][k]["abstention_rate"]
        useful[k] = {"retained_error_lower_in_every_group": a, "abstains_more_on_OOD_than_SEEN": b, "useful": a and b}
    item46["decision"] = useful
    inf = {}
    for k in ("U_amb", "U_ens", "U_nov"):
        s_ = item47["SEEN"]["error_auroc"][k]
        ok = all(item47[g]["error_auroc"][k] >= 0.6 and item47[g]["error_auroc"][k] >= s_ - 0.1 for g in ("IDH", "OOD"))
        inf[k] = {"remains_informative_under_shift": bool(ok)}
    item47["decision"] = inf
    item47["conformal_coverage_failure_on_OOD"] = item47["OOD"]["conformal"]["coverage"] < 0.85
    res["item46"] = item46; res["item47"] = item47

    # ---- section 8: item 52 slices
    res["item52"] = slices(pops, scores, meta, cfgs)

    # ---- section 13 primary paired intervals (K1-K4)
    k = {}
    for g in ("IDH", "OOD"):
        pop, sc = pops[g], scores[g]
        k[g] = {"K1_K2_M_D_minus_M_A": M.paired_diff_ci(pop, sc["M_D"]["score"], sc["M_D"]["threshold"], sc["M_A"]["score"], sc["M_A"]["threshold"]),
                "K3_M_D_minus_R_AoA": M.paired_diff_ci(pop, sc["M_D"]["score"], sc["M_D"]["threshold"], sc["R_AoA"]["score"], sc["R_AoA"]["threshold"]),
                "K4_M_D_minus_M_D_noSM": M.paired_diff_ci(pop, sc["M_D"]["score"], sc["M_D"]["threshold"], sc["M_D_noSM"]["score"], sc["M_D_noSM"]["threshold"])}
    res["item53_primary_paired"] = k
    dump(res, run_dir / "primary.json")
    log("primary done")


def slices(pops, scores, meta, cfgs) -> dict:
    cfg = {c["config_id"]: c for c in cfgs}
    ws = np.array([C.wing_loading(c) for c in cfgs]); ws_cut = np.quantile(ws, [1 / 3, 2 / 3]).tolist()
    m = meta.set_index("trajectory_id")
    out = {"wing_loading_tertile_cuts_N_m2": ws_cut}

    def attrs(pop):
        tid = pop["trajectory_id"]
        cid = pop["config_id"].astype(str)
        v0 = tid.map(m["v0_over_vstall"]).to_numpy()
        rho = cid.map({k: v["rho"] for k, v in cfg.items()}).to_numpy(dtype=float)
        wl = cid.map({k: C.wing_loading(v) for k, v in cfg.items()}).to_numpy(dtype=float)
        return {"regime": pop["generation_mode"].astype(str).to_numpy(),
                "v0_bin": np.select([v0 < 1.6, v0 < 2.2], ["[1.148,1.6)", "[1.6,2.2)"], "[2.2,2.869]"),
                "rho_bin": np.select([rho < 1.012, rho < 1.118], ["[0.905,1.012)", "[1.012,1.118)"], "[1.118,1.225]"),
                "wing_loading_bin": np.select([wl <= ws_cut[0], wl <= ws_cut[1]], ["T1", "T2"], "T3")}

    for scope in ("ALL", "OOD"):
        gs = GROUPS if scope == "ALL" else ("OOD",)
        pop = pd.concat([pops[g] for g in gs], ignore_index=True)
        sc = {k: (np.concatenate([scores[g][k]["score"] for g in gs]), scores[gs[0]][k]["threshold"]) for k in ("M_D", "M_A", "R_AoA")}
        a = attrs(pop)
        a["set"] = np.concatenate([np.full(len(pops[g]), g) for g in gs])
        res = {}
        for dim, vals in a.items():
            if scope == "OOD" and dim == "set":
                continue
            res[dim] = {}
            for v in sorted(set(vals)):
                msk = vals == v
                sub = pop.loc[msk].reset_index(drop=True)
                res[dim][v] = {}
                for k, (s, thr) in sc.items():
                    r = M.evaluate(sub, s[msk], thr, s[msk] if k != "R_AoA" else None)
                    r["insufficient"] = r["event"]["n_events"] < 10
                    res[dim][v][k] = strip(r)
        # event entry rate (event-level only)
        res["entry_rate"] = {}
        for k, (s, thr) in sc.items():
            ev = M.event_table(pop["trajectory_id"].to_numpy(), pop["time"].to_numpy(), pop["is_unsafe"].to_numpy(), s, thr)
            key = pd.MultiIndex.from_frame(pop[["trajectory_id", "time"]])
            da = pd.Series(np.degrees(pop["dalpha_dt"].to_numpy(dtype=float)), index=key)
            ev["entry_deg_s"] = da.reindex(pd.MultiIndex.from_frame(ev[["trajectory_id", "crossing_time"]])).to_numpy()
            ev["bin"] = np.select([ev["entry_deg_s"] < 2, ev["entry_deg_s"] < 5], ["<2", "2-5"], ">=5")
            res["entry_rate"][k] = {b: {**M.event_summary(e), "insufficient": len(e) < 10} for b, e in ev.groupby("bin")}
        out[scope] = res
        log("slices", scope)
    return out


# ------------------------------------------------------------------------------------------------ jsbsim
def jsbsim(data_dir: Path, run_dir: Path):
    model_dir = data_dir / "models_P0_D0"
    jdf = pd.read_parquet(data_dir / "JSB" / "c172p.parquet")
    jm = pd.read_csv(data_dir / "JSB" / "c172p_meta.csv").set_index("trajectory_id")
    jdf["split"] = jdf["trajectory_id"].map(jm["split"])
    jtest = jdf.loc[jdf["split"] == "test"].reset_index(drop=True)
    jtr = stride_rows(jdf.loc[jdf["split"] == "train"].reset_index(drop=True), TRAIN_STRIDE)
    jva = stride_rows(jdf.loc[jdf["split"] == "val"].reset_index(drop=True), TRAIN_STRIDE)
    rules = joblib.load(model_dir / "rules.joblib")
    cfgs, df, _ = load_seed(data_dir, "D0")
    part = C.partition([dict(c) for c in cfgs], "P0")
    pops, fit = populations(df, part)
    del df
    nov = U.Novelty(fit["train"][FEATURES_XD].to_numpy(dtype=np.float32))
    tau = U.abstain_threshold(nov(fit["val"][FEATURES_XD].to_numpy(dtype=np.float32)))
    res = {"n_rows": {"test": len(jtest), "all": len(jdf), "native_train": len(jtr), "native_val": len(jva)},
           "n_trajectories": {"test": int(jtest["trajectory_id"].nunique()), "all": int(jdf["trajectory_id"].nunique())},
           "crossing_rate_by_regime": jm.groupby("generation_mode")["whether_stall_occurred"].mean().to_dict(),
           "termination_by_regime": {k: v.value_counts().to_dict() for k, v in jm.groupby("generation_mode")["termination_reason"]},
           "abstention_tau_U_nov_XD": tau}
    out = {}
    for name in ("X_D", "X_D_noSM"):
        for s in MODEL_SEEDS:
            cross = joblib.load(model_dir / f"{name}_{s}.joblib")
            native = MD.fit_rf(name, jtr, jva, s, n_jobs=4)
            for pop_name, pop in (("JSB_test", jtest), ("JSB_all", jdf), ("AG_IDH", pops["IDH"])):
                sc = MD.score_rf(cross, pop)
                r = M.evaluate(pop, sc, cross["threshold"], sc, boot=(s == PRIMARY_SEED))
                if pop_name != "AG_IDH" and s == PRIMARY_SEED:
                    r["abstention_rate_U_nov"] = float((nov(pop[FEATURES_XD].to_numpy(dtype=np.float32)) > tau).mean())
                out[f"cross|{name}|{s}|{pop_name}"] = strip(r)
            sn = MD.score_rf(native, jtest)
            out[f"native|{name}|{s}|JSB_test"] = strip(M.evaluate(jtest, sn, native["threshold"], sn, boot=(s == PRIMARY_SEED)))
            out[f"native|{name}|{s}|threshold"] = native["threshold"]
            log("jsbsim", name, s)
    for r in RULES:
        for pop_name, pop in (("JSB_test", jtest), ("JSB_all", jdf)):
            out[f"cross|{r}|-|{pop_name}"] = strip(M.evaluate(pop, MD.score_rule(r, pop), rules[r]["threshold"]))
    res["results"] = out
    dump(res, run_dir / "jsbsim.json")
    log("jsbsim done")


# ------------------------------------------------------------------------------------------------ robustness
def robust(data_dir: Path, run_dir: Path):
    runs = []
    prim = json.load(open(run_dir / "primary.json"))
    # primary combination: all five seeds already fitted and scored at full resolution
    for g in ("IDH", "OOD"):
        for s in MODEL_SEEDS:
            ps = prim["group_metrics"][g]
            row = {"partition": "P0", "data": "D0", "seed": s, "group": g, "resolution": "0.01s"}
            for n in RF_NAMES:
                v = ps[f"{n}_seeds"]["per_seed"][str(s)]
                row[f"{n}_pr_auc"], row[f"{n}_recall"], row[f"{n}_lead"] = v["pr_auc"], v["event_recall"], v["median_lead_s"]
            row["R_AoA_recall"] = ps["R_AoA"]["event"]["event_recall"]
            runs.append(row)
    for dname in ("D0", "D1"):
        cfgs, df, _ = load_seed(data_dir, dname)
        for pname in ("P0", "P1", "P2"):
            if (pname, dname) == ("P0", "D0"):
                continue
            part = C.partition([dict(c) for c in cfgs], pname)
            pops, fit = populations(df, part)
            pops = {g: stride_rows(pops[g], TRAIN_STRIDE) for g in ("IDH", "OOD")}
            rules = MD.fit_rules(fit["train"], fit["val"])
            for s in ROBUST_MODEL_SEEDS:
                fitted = {n: MD.fit_rf(n, fit["train"], fit["val"], s, n_jobs=4) for n in RF_NAMES}
                for g, pop in pops.items():
                    row = {"partition": pname, "data": dname, "seed": s, "group": g, "resolution": "0.05s"}
                    for n, f in fitted.items():
                        r = M.evaluate(pop, MD.score_rf(f, pop), f["threshold"], boot=False, dt_eff=DT * TRAIN_STRIDE)
                        row[f"{n}_pr_auc"], row[f"{n}_recall"], row[f"{n}_lead"] = r["row"]["pr_auc"], r["event"]["event_recall"], r["event"]["median_lead_s"]
                    r = M.evaluate(pop, MD.score_rule("R_AoA", pop), rules["R_AoA"]["threshold"], boot=False, dt_eff=DT * TRAIN_STRIDE)
                    row["R_AoA_recall"] = r["event"]["event_recall"]
                    runs.append(row)
                log("robust", pname, dname, s)
        del df
    tab = pd.DataFrame(runs)
    tab.to_csv(run_dir / "robustness_runs.csv", index=False)
    claims = {"K1": ("M_D_pr_auc", "M_A_pr_auc", "gt", ("IDH", "OOD")),
              "K2": ("M_D_lead", "M_A_lead", "gt", ("IDH", "OOD")),
              "K3": ("M_D_recall", "R_AoA_recall", "ge", ("IDH", "OOD")),
              "K4": ("M_D_pr_auc", "M_D_noSM_pr_auc", "ge", ("OOD",))}
    pk = {"K1": ("K1_K2_M_D_minus_M_A", "pr_auc"), "K2": ("K1_K2_M_D_minus_M_A", "median_lead_s"),
          "K3": ("K3_M_D_minus_R_AoA", "event_recall"), "K4": ("K4_M_D_minus_M_D_noSM", "pr_auc")}
    out = {}
    for k, (a, b, op, gs) in claims.items():
        for g in gs:
            t = tab[tab["group"] == g]
            hold = (t[a] > t[b]) if op == "gt" else (t[a] >= t[b])
            frac = float(hold.mean())
            pd_ = prim["item53_primary_paired"][g][pk[k][0]][pk[k][1]]
            lo, hi = pd_["ci95"]
            excl = lo is not None and lo > 0  # interval entirely above zero, i.e. in favour of the claim
            verdict = "persists" if (frac >= 0.9 and excl) else ("fragile" if frac >= 0.5 else "not supported")
            out[f"{k}|{g}"] = {"sign_holds_fraction": frac, "n_runs": int(len(t)), "primary_diff": pd_["diff"],
                               "primary_ci95": pd_["ci95"], "primary_ci_excludes_zero_in_favour": bool(excl), "verdict": verdict}
    dump(out, run_dir / "robustness.json")
    log("robust done")


if __name__ == "__main__":
    data_dir, run_dir, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    run_dir.mkdir(parents=True, exist_ok=True)
    from phase4.models import sha256
    if sha256(REPO / PROTOCOL_RELPATH) != PROTOCOL_SHA256:
        raise SystemExit("STOP: protocol hash differs")
    {"primary": primary, "jsbsim": jsbsim, "robust": robust}[stage](data_dir, run_dir)
