"""Gated driver for AeroGuard Phase 3 (Items 28-32). Governed by the LOCKED protocol
``experiments/phase3/PROTOCOL.md`` (SHA-256 in ``phase3.PROTOCOL_SHA256``).

Subcommands, one per protocol gate, each of which runs only when passed ``--confirm-gate Gx``
(a deliberate-friction guard: pass it ONLY after the researcher has approved that gate):

    g4   lock + data-integrity + train-only negative-alpha investigation (Q1-Q3)
    g5   population / count reconciliation (labels and keys only, no scores)
    g6   fit the AoA rule(s) and the instantaneous model on TRAIN/VALIDATION; Q4 (train only)
    g7   score the test population ONCE per method; metrics; Item 30 decision count
    g8   paired trajectory bootstrap, report, audit

Safety properties enforced in code:
  * run only from an execution tree without ``.git`` (a ``git archive`` copy), never from the repository;
  * every output goes to ``<tree>/outputs/phase3/run_<UTC>/``, created exclusively, never overwritten;
  * a gate cannot run before the previous gate's record says PASS;
  * G4-G6 cannot open the test panel (``phase3.population.load_split`` whitelist); G7 is single-shot;
  * the protocol file, the four data files and the frozen model are re-hashed before use.

Nothing is run on import. This script modifies no historical file.
"""

import argparse
import json
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml.events import compute_event_level_results  # noqa: E402  (reused unchanged)
from phase3 import (  # noqa: E402
    BOOTSTRAP_B,
    BOOTSTRAP_SEED,
    DATA_FILE_SHA256,
    FROZEN_METRICS_RELPATH,
    FROZEN_MODEL_RELPATH,
    FROZEN_MODEL_SHA256,
    HORIZON_S,
    MODEL_SEED,
    PROTOCOL_RELPATH,
    PROTOCOL_SHA256,
)
from phase3 import analysis, instantaneous, population, rules  # noqa: E402

GATES = ("G4", "G5", "G6", "G7", "G8")
PREVIOUS = {"G5": "G4", "G6": "G5", "G7": "G6", "G8": "G7"}
BANNER = ("Computed on regenerated v0.3 data (Item 26 copy; hashes in the protocol lock). "
          "Not independent replication. Simulation only: nothing here establishes real-aircraft safety.")
M_AOA, M_MODEL_A, M_FROZEN, M_AOA_2S = "aoa_signed", "instantaneous_model_a", "frozen_temporal", "aoa_two_sided"


@dataclass
class RunConfig:
    root: Path
    item26_dir: Optional[Path] = None
    git_commit: str = "unrecorded"
    protocol_sha256: str = PROTOCOL_SHA256
    frozen_model_sha256: str = FROZEN_MODEL_SHA256
    data_hashes: Dict[str, str] = field(default_factory=lambda: dict(DATA_FILE_SHA256))
    expected_counts: Optional[Dict[str, int]] = None  # None -> population.REPORTED_COUNTS

    @property
    def protocol_path(self) -> Path:
        return self.root / PROTOCOL_RELPATH

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def frozen_model_path(self) -> Path:
        return self.root / FROZEN_MODEL_RELPATH

    @property
    def frozen_metrics_path(self) -> Path:
        return self.root / FROZEN_METRICS_RELPATH

    @property
    def counts(self) -> Dict[str, int]:
        return dict(population.REPORTED_COUNTS if self.expected_counts is None else self.expected_counts)


# ---------------------------------------------------------------------------------------
# I/O helpers: exclusive creation only, below outputs/phase3/
# ---------------------------------------------------------------------------------------

def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, Path):
        return str(o)
    return o


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def out_path(cfg: RunConfig, run_dir: Path, name: str) -> Path:
    return population.assert_phase3_output_path(Path(run_dir) / name, cfg.root)


def write_json(cfg: RunConfig, run_dir: Path, name: str, obj) -> Path:
    path = out_path(cfg, run_dir, name)
    with open(path, "x") as f:  # 'x': fails if the file exists - nothing is ever overwritten
        json.dump(_jsonable(obj), f, indent=2)
    return path


def write_text(cfg: RunConfig, run_dir: Path, name: str, text: str) -> Path:
    path = out_path(cfg, run_dir, name)
    with open(path, "x") as f:
        f.write(text)
    return path


def write_npy(cfg: RunConfig, run_dir: Path, name: str, arr: np.ndarray) -> Path:
    path = out_path(cfg, run_dir, name)
    with open(path, "xb") as f:
        np.save(f, arr, allow_pickle=False)
    return path


def new_run_dir(cfg: RunConfig) -> Path:
    if (cfg.root / ".git").exists():
        raise population.GateViolation("refusing to run in a git checkout: use an execution tree built with `git archive` (PROTOCOL.md section 4)")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = population.assert_phase3_output_path(cfg.root / "outputs" / "phase3" / f"run_{stamp}", cfg.root)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def gate_file(run_dir: Path, gate: str) -> Path:
    return Path(run_dir) / f"gate_{gate}.json"


def require_gate_pass(run_dir: Path, gate: str) -> dict:
    path = gate_file(run_dir, gate)
    if not path.is_file():
        raise population.GateViolation(f"gate {gate} has no record in {run_dir}; it must PASS first")
    rec = json.loads(path.read_text())
    if rec.get("status") != "PASS":
        raise population.GateViolation(f"gate {gate} did not pass (status {rec.get('status')!r})")
    return rec


def require_confirm(gate: str, given: Optional[str]) -> None:
    if given != gate:
        raise population.GateViolation(f"gate {gate} requires --confirm-gate {gate} (given {given!r}); pass it only after that gate is approved")


def read_json(path) -> dict:
    return json.loads(Path(path).read_text())


def frozen_metrics(cfg: RunConfig) -> dict:
    return read_json(cfg.frozen_metrics_path)


def method_columns(cfg: RunConfig, with_events: bool = False) -> List[str]:
    cols = list(population.KEY_COLUMNS) + [population.TARGET_COL, population.AVAILABLE_COL] + list(population.WINDOW_COLUMNS) + list(instantaneous.INSTANTANEOUS_FEATURES)
    if with_events:
        cols += ["is_unsafe", "time_to_stall"] + list(frozen_metrics(cfg)["feature_columns"])
    return list(dict.fromkeys(cols))


def pip_freeze() -> List[str]:
    try:
        out = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, timeout=60)
        return out.stdout.splitlines() if out.returncode == 0 else [f"pip freeze failed: {out.stderr.strip()[:200]}"]
    except Exception as exc:  # pragma: no cover
        return [f"pip freeze unavailable: {exc}"]


# ---------------------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------------------

def _preflight(cfg: RunConfig, check_data: bool = True) -> Dict[str, object]:
    """Before any step reads data: protocol, frozen model and the four data files are re-hashed."""
    info = {"protocol_sha256": population.verify_protocol(cfg.protocol_path, cfg.protocol_sha256)}
    got = population.sha256_file(cfg.frozen_model_path)
    if got != cfg.frozen_model_sha256:
        raise population.DataIntegrityError(f"frozen model hash differs: {got}")
    info["frozen_model_sha256"] = got
    if check_data:
        info["data_files"] = population.verify_file_hashes(cfg.data_dir, cfg.data_hashes)
    return info


def _item26_records(cfg: RunConfig) -> Dict[str, object]:
    if cfg.item26_dir is None:
        raise population.GateViolation("--item26-dir is required")
    gate_a = read_json(cfg.item26_dir / "audit_out" / "gen_diag" / "gate_A.json")
    gate_b = read_json(cfg.item26_dir / "audit_out" / "gate_B.json")
    if not (gate_a.get("all_gate_A_pass") is True and gate_b.get("all_gate_B_pass") is True):
        raise population.DataIntegrityError("Item 26 gate A/B records do not both pass")
    return {"gate_A": {k: gate_a[k] for k in ("all_gate_A_pass", "processed_rows", "processed_trajectories", "metadata_max_relative_difference") if k in gate_a},
            "gate_B": {k: v for k, v in gate_b.items() if k == "all_gate_B_pass" or "row" in k or "usable" in k or "trajector" in k}}


def gate_g4(cfg: RunConfig, run_dir: Path) -> dict:
    pre = _preflight(cfg)
    item26 = _item26_records(cfg)
    lock = {
        "protocol": {"path": PROTOCOL_RELPATH, "sha256": pre["protocol_sha256"]},
        "frozen_model": {"path": FROZEN_MODEL_RELPATH, "sha256": pre["frozen_model_sha256"]},
        "seeds": {"forest_random_state": MODEL_SEED, "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_B": BOOTSTRAP_B},
        "environment": {**instantaneous.library_versions(), "pip_freeze": pip_freeze()},
        "git_commit_of_execution_tree": cfg.git_commit,
        "created_utc": utc_now(),
        "tree_root": str(cfg.root),
        "banner": BANNER,
    }
    write_json(cfg, run_dir, "protocol_lock.json", lock)
    write_json(cfg, run_dir, "data_provenance.json", {"banner": BANNER, "data_files": pre["data_files"], "item26_records": item26})
    train = population.load_split(cfg.data_dir, "train", analysis.NEGATIVE_ALPHA_COLUMNS, allowed_splits=("train",))
    q = analysis.negative_alpha_q1_q3(train)
    write_json(cfg, run_dir, "negative_alpha_train.json", q)
    return {"run_two_sided": q["run_two_sided"], "q3": q["q3_negative_only_positive_rows"], "data_files_verified": len(pre["data_files"])}


def gate_g5(cfg: RunConfig, run_dir: Path) -> dict:
    pre = _preflight(cfg)
    fm = frozen_metrics(cfg)
    needed = list(dict.fromkeys(method_columns(cfg, with_events=True)))
    schema = {}
    for split in population.SPLITS:
        schema[split] = population.schema_missing_columns(population.panel_path(cfg.data_dir, split), needed)
    cols = ["trajectory_id", "time", "is_unsafe", population.TARGET_COL, population.AVAILABLE_COL] + list(population.WINDOW_COLUMNS)
    observed: Dict[str, int] = {}
    ids: Dict[str, set] = {}
    eligible_keys = None
    labels_test = None
    events = None
    for split in population.SPLITS:
        tab = population.load_split(cfg.data_dir, split, cols, allowed_splits=population.SPLITS)
        df = tab.df
        population.row_keys(df)
        summ = population.summarize_population(df)
        mask = population.usable_mask(df)
        sub = df.loc[mask].reset_index(drop=True)
        keys = population.row_keys(sub)
        population.assert_consecutive_steps(keys)
        observed[f"trajectories_{split}"] = summ["trajectories_total"]
        observed[f"panel_rows_{split}"] = summ["rows_total"]
        observed[f"usable_rows_{split}"] = summ["rows_usable"]
        ids[split] = set(df["trajectory_id"].unique())
        if split == "test":
            observed["test_trajectories_with_usable_rows"] = summ["trajectories_with_usable_rows"]
            observed["test_positive_rows"] = summ["positives"]
            observed["test_negative_rows"] = summ["negatives"]
            observed["test_trajectories_with_any_unsafe_run"] = summ["trajectories_with_any_unsafe_run"]
            ev = population.count_events(sub)
            observed.update({"test_events": ev["events"], "test_first_events": ev["first_events"], "test_later_events": ev["later_events"],
                             "test_trajectories_with_events": ev["trajectories_with_events"]})
            eligible_keys = keys
            labels_test = sub[population.TARGET_COL].to_numpy().astype(int)
            events = ev
    observed["dataset_rows"] = sum(observed[f"panel_rows_{s}"] for s in population.SPLITS)
    observed["dataset_trajectories"] = sum(observed[f"trajectories_{s}"] for s in population.SPLITS)
    population.assert_no_trajectory_overlap(ids)
    manifest = pd.read_csv(cfg.data_dir / "splits" / "split_manifest_v3.csv")
    manifest_ok = all(set(manifest.loc[manifest["split"] == s, "trajectory_id"]) == ids[s] for s in population.SPLITS)
    hours = population.eligible_time(eligible_keys)
    stored_fa = read_json(cfg.root / "outputs" / "ml_v03" / "metrics" / "false_alarm_analysis.json")
    hours_matches_stored = abs(hours["span_seconds"] - float(stored_fa["total_test_trajectory_seconds"])) < 1e-6
    cross = population.compare_with_item26(
        eligible_keys, labels_test,
        pd.read_parquet(cfg.item26_dir / "audit_out" / "score" / "row_keys.parquet"),
        np.load(cfg.item26_dir / "audit_out" / "score" / "labels.npy", allow_pickle=False),
    )
    mismatches = population.compare_counts(observed, cfg.counts)
    problems = list(mismatches)
    problems += [f"schema: {split} panel lacks {miss}" for split, miss in schema.items() if miss]
    if not manifest_ok:
        problems.append("trajectory ids per split differ from the tracked split manifest")
    if not hours_matches_stored:
        problems.append(f"eligible span {hours['span_seconds']} s differs from the stored {stored_fa['total_test_trajectory_seconds']} s")
    if not (cross["keys_equal"] and cross["labels_equal"]):
        problems.append(f"Item 26 cross-check failed: {cross}")
    payload = {"banner": BANNER, "observed_counts": observed, "expected_counts": cfg.counts, "count_mismatches": mismatches,
               "eligible_time_test": hours, "eligible_span_matches_stored": hours_matches_stored, "split_manifest_matches": manifest_ok,
               "item26_cross_check": cross, "schema_missing_columns": schema, "events": events, "data_files": pre["data_files"], "problems": problems}
    write_json(cfg, run_dir, "population.json", payload)
    if problems:
        raise population.KeyMismatchError("; ".join(problems))
    return {"n_problems": 0, "usable_rows_test": observed["usable_rows_test"]}


def gate_g6(cfg: RunConfig, run_dir: Path) -> dict:
    require_gate_pass(run_dir, "G5")
    pre = _preflight(cfg)
    q = read_json(Path(run_dir) / "negative_alpha_train.json")
    run_two_sided = bool(q["run_two_sided"])  # decided at G4 from Q3 alone; Q4 below cannot change it
    cols = method_columns(cfg)
    train = population.load_split(cfg.data_dir, "train", cols, allowed_splits=("train", "val"))
    val = population.load_split(cfg.data_dir, "val", cols, allowed_splits=("train", "val"))
    tr_mask, va_mask = population.usable_mask(train.df), population.usable_mask(val.df)
    a_tr, a_va = train.df.loc[tr_mask, "alpha"].to_numpy(), val.df.loc[va_mask, "alpha"].to_numpy()
    y_tr = train.df.loc[tr_mask, population.TARGET_COL].to_numpy().astype(int)
    y_va = val.df.loc[va_mask, population.TARGET_COL].to_numpy().astype(int)
    rule = rules.fit_signed_aoa(a_tr, y_tr, a_va, y_va)
    summary = rules.rule_summary(rule)
    cand = summary["calibration_info"]["candidate_thresholds_rad"]
    summary["reference_only"] = {
        "stored_credibility_v1_1_threshold_rad": 0.21723935451615506,
        "stored_candidate_range_rad": [0.21723897, 0.21724784],
        "selected_within_stored_candidate_range": bool(0.21723897 <= rule.threshold_rad <= 0.21724784),
        "note": "diagnostic context only; the selected threshold is the output of the procedure on the Phase 3 rows",
    }
    summary["n_train_rows"], summary["n_val_rows"] = int(tr_mask.sum()), int(va_mask.sum())
    write_json(cfg, run_dir, "aoa_rule.json", summary)
    fit = instantaneous.fit_instantaneous(train, val)
    model_path = out_path(cfg, run_dir, "instantaneous_model_a.joblib")
    if model_path.exists():  # pragma: no cover - the run directory is fresh
        raise population.GateViolation("model artifact already exists")
    joblib.dump(fit.model, model_path)
    model_sha = population.sha256_file(model_path)
    write_json(cfg, run_dir, "feature_manifest.json", {"features": fit.features, "excluded": sorted(instantaneous.EXCLUDED_EXACT), "banner": BANNER})
    write_json(cfg, run_dir, "model_a_config.json", {"algorithm": "RandomForestClassifier", "rf_params": fit.rf_params, "random_state": fit.seed,
                                                       "n_jobs": -1, "preprocessing": "none", "versions": fit.versions, "model_sha256": model_sha})
    write_json(cfg, run_dir, "model_a_fit_record.json", {"threshold": fit.threshold, "operator": "strict >", "threshold_info": fit.threshold_info,
                                                           "n_train_rows": fit.n_train_rows, "n_val_rows": fit.n_val_rows, "fit_seconds": fit.fit_seconds,
                                                           "peak_rss_mb": fit.peak_rss_mb, "model_sha256": model_sha})
    if run_two_sided:
        rule2 = rules.fit_two_sided_aoa(a_tr, y_tr, a_va, y_va)
        write_json(cfg, run_dir, "aoa_two_sided_rule.json", rules.rule_summary(rule2))
    q4 = analysis.negative_alpha_q4(train, rule.threshold_rad)
    write_json(cfg, run_dir, "negative_alpha_q4.json", q4)
    return {"aoa_threshold_rad": rule.threshold_rad, "n_candidates": len(cand), "model_a_threshold": fit.threshold, "two_sided_fitted": run_two_sided,
            "data_files_verified": len(pre["data_files"])}


def _eligible_test(cfg: RunConfig, tab: population.SplitTable):
    mask = population.usable_mask(tab.df)
    sub = tab.df.loc[mask].reset_index(drop=True)
    keys = population.row_keys(sub)
    population.assert_consecutive_steps(keys)
    return sub, keys, sub[population.TARGET_COL].to_numpy().astype(int)


def gate_g7(cfg: RunConfig, run_dir: Path) -> dict:
    require_gate_pass(run_dir, "G6")
    lock = out_path(cfg, run_dir, "g7_started.lock")
    with open(lock, "x") as f:  # single-shot: a second attempt cannot start (PROTOCOL.md section 11)
        f.write(utc_now())
    pre = _preflight(cfg)
    aoa = read_json(Path(run_dir) / "aoa_rule.json")
    fit_rec = read_json(Path(run_dir) / "model_a_fit_record.json")
    model_path = Path(run_dir) / "instantaneous_model_a.joblib"
    if population.sha256_file(model_path) != fit_rec["model_sha256"]:
        raise population.DataIntegrityError("instantaneous model file changed since G6")
    fm = frozen_metrics(cfg)
    feats_frozen = list(fm["feature_columns"])
    test = population.load_split(cfg.data_dir, "test", method_columns(cfg, with_events=True), allowed_splits=population.SPLITS)
    sub, keys, y = _eligible_test(cfg, test)
    frozen = joblib.load(cfg.frozen_model_path)
    if list(frozen.feature_names_in_) != feats_frozen:
        raise ValueError("frozen model feature names differ from the stored feature list")
    model_a = joblib.load(model_path)
    scores = {
        M_AOA: rules.score_signed(sub["alpha"].to_numpy()),
        M_MODEL_A: instantaneous.predict_scores(model_a, sub, np.ones(len(sub), dtype=bool)),
        M_FROZEN: frozen.predict_proba(sub[feats_frozen])[:, 1],
    }
    thresholds = {M_AOA: aoa["threshold_rad"], M_MODEL_A: fit_rec["threshold"], M_FROZEN: float(fm["threshold"])}
    two_sided_path = Path(run_dir) / "aoa_two_sided_rule.json"
    if two_sided_path.is_file():
        scores[M_AOA_2S] = rules.score_two_sided(sub["alpha"].to_numpy())
        thresholds[M_AOA_2S] = read_json(two_sided_path)["threshold_rad"]
    sets = [population.make_prediction_set(nm, keys, s) for nm, s in scores.items()]
    population.assert_common_population(keys, y, sets)
    metrics = {}
    for nm, s in scores.items():
        pred = (s > thresholds[nm]).astype(int)
        metrics[nm] = {"threshold_free": analysis.threshold_free_metrics(y, s), "operating_point": analysis.operating_point(sub, y, s, thresholds[nm])}
        ev = analysis.events_by_trajectory(compute_event_level_results(sub, pred, HORIZON_S))
        write_json(cfg, run_dir, f"events_{nm}.json", {str(k): v for k, v in ev.items()})
        write_npy(cfg, run_dir, f"scores_{nm}.npy", np.asarray(s, dtype=float))
    write_npy(cfg, run_dir, "labels.npy", y)
    with open(out_path(cfg, run_dir, "row_keys.npz"), "xb") as f:
        np.savez(f, trajectory_id=np.asarray(keys.traj).astype(str), step=keys.step)
    # Item 30: decision counts only (no labels, no metrics) on the eligible rows of each split
    eq = {}
    for split in population.SPLITS:
        tab = test if split == "test" else population.load_split(cfg.data_dir, split, method_columns(cfg), allowed_splits=population.SPLITS)
        sub_s = tab.df.loc[population.usable_mask(tab.df)]
        eq[split] = rules.equivalence_report(sub_s["alpha"].to_numpy(), aoa["threshold_rad"])
    write_json(cfg, run_dir, "equivalence_check.json", {"tau_alpha_rad": aoa["threshold_rad"], "by_split": eq,
                                                          "note": "Item 30 is mathematically equivalent to Item 28; decision counts only, not evaluated as a separate method"})
    write_json(cfg, run_dir, "metrics_primary.json", {"banner": BANNER, "methods": metrics, "thresholds": thresholds,
                                                        "population": {"n_rows": len(keys), "n_trajectories": int(pd.unique(keys.traj).size),
                                                                       "n_positive": int(y.sum()), "n_negative": int((1 - y).sum())}})
    rows = []
    for nm, m in metrics.items():
        op = m["operating_point"]
        rows.append({"method": nm, "pr_auc": m["threshold_free"]["pr_auc"], "roc_auc": m["threshold_free"]["roc_auc"], "threshold": thresholds[nm],
                     "precision": op["classification"]["precision"], "recall": op["classification"]["recall"], "f1": op["classification"]["f1"],
                     "events": op["events"]["n_events"], "events_warned": op["events"]["n_warned"], "median_lead_s": op["events"]["median_lead_time_s"],
                     "false_alarm_episodes_per_hour": op["false_alarms"]["false_alarm_episodes_per_eligible_hour"]})
    with open(out_path(cfg, run_dir, "metrics_primary.csv"), "x") as f:
        f.write(pd.DataFrame(rows).to_csv(index=False))
    after = population.verify_file_hashes(cfg.data_dir, cfg.data_hashes)  # data files unchanged after the last read
    return {"methods": list(scores), "n_rows": len(keys), "data_files_verified_before": len(pre["data_files"]), "data_files_verified_after": len(after)}


def _report(cfg: RunConfig, run_dir: Path, metrics: dict, boot: dict, equiv: dict) -> str:
    L: List[str] = [f"# AeroGuard Phase 3 results ({Path(run_dir).name})", "", f"> {BANNER}", "",
                    "Generated from the machine-readable results of this run. No practical-significance criterion is defined (D10); no claim of practical superiority is made.", ""]
    pop = metrics["population"]
    L += ["## Population", f"{pop['n_rows']} rows, {pop['n_trajectories']} trajectories, {pop['n_positive']} positive / {pop['n_negative']} negative rows (rows, trajectories and events are distinct units).", ""]
    L += ["## Threshold-free metrics with paired trajectory-bootstrap 95% intervals", f"B = {boot['config']['B']}, seed {boot['config']['seed']}, unit = trajectory, {boot['config']['interval']}.", "",
          "| method | PR-AUC | 95% interval | ROC-AUC | 95% interval |", "|---|---|---|---|---|"]
    for nm in metrics["methods"]:
        a, b = boot["per_method"][f"{nm}|pr_auc"], boot["per_method"][f"{nm}|roc_auc"]
        L.append(f"| {nm} | {a['point']:.4f} | [{a['ci_lo']:.4f}, {a['ci_hi']:.4f}] | {b['point']:.4f} | [{b['ci_lo']:.4f}, {b['ci_hi']:.4f}] |")
    L += ["", "## Paired differences (PR-AUC primary contrast first)", "", "| difference | point | 95% interval | interval includes 0 | undefined replicates |", "|---|---|---|---|---|"]
    for key, d in boot["paired_differences"].items():
        lo = "n/a" if d["ci_lo"] is None else f"[{d['ci_lo']:.4f}, {d['ci_hi']:.4f}]"
        L.append(f"| {key} | {d['point']:.4f} | {lo} | {d['ci_includes_zero']} | {d['n_undefined_replicates']} |")
    primary = boot["paired_differences"].get(f"{M_FROZEN} - {M_MODEL_A} | pr_auc")
    L += ["", "## Reading of the primary contrast (rules fixed in the protocol, section 9.4)"]
    if primary is not None:
        if primary["ci_includes_zero"]:
            L.append("The paired interval for the primary contrast includes 0: no difference was demonstrated under this protocol. This does not show the models are equivalent.")
        else:
            L.append("The paired interval for the primary contrast excludes 0: statistical evidence of a difference under this resampling model (not a p-value; not evidence of cause; practical significance not assessed).")
    L += ["A higher score for one model is not proof that temporal reasoning caused it.", "",
          "## Threshold-dependent metrics: NOT MATCHED across methods; do not rank",
          "Each method is at its own validation-selected operating point (strict >).", "",
          "| method | threshold | precision | recall | F1 | events warned / events | median lead (s) | false-alarm episodes / eligible hour |", "|---|---|---|---|---|---|---|---|"]
    for nm, m in metrics["methods"].items():
        op = m["operating_point"]
        c, e, fa = op["classification"], op["events"], op["false_alarms"]
        med = e["median_lead_time_s"]
        L.append(f"| {nm} | {metrics['thresholds'][nm]:.6g} | {c['precision']:.4f} | {c['recall']:.4f} | {c['f1']:.4f} | {e['n_warned']} / {e['n_events']} | "
                 f"{'n/a' if med is None else f'{med:.3f}'} | {fa['false_alarm_episodes_per_eligible_hour']:.3f} |")
    L += ["", "Event-level numbers come from few independent trajectories; see the protocol (section 9.3).", "",
          "## Item 30 (stall margin)", "Mathematically equivalent to Item 28; not evaluated as a separate method. Decision counts only:", ""]
    for split, r in equiv["by_split"].items():
        L.append(f"- {split}: {r['n_disagree']} disagreeing rows of {r['n_rows']} ({r['n_disagree_exactly_at_threshold']} exactly at the threshold)")
    L += ["", "## Limitations", "See PROTOCOL.md sections 10, 12 and 20: prior test exposure, regenerated data, one simulated aircraft, few independent event trajectories."]
    return "\n".join(L) + "\n"


def gate_g8(cfg: RunConfig, run_dir: Path) -> dict:
    require_gate_pass(run_dir, "G7")
    rd = Path(run_dir)
    metrics = read_json(rd / "metrics_primary.json")
    names = list(metrics["methods"])
    y = np.load(rd / "labels.npy", allow_pickle=False)
    keys = np.load(rd / "row_keys.npz", allow_pickle=False)
    traj = keys["trajectory_id"]
    scores = {nm: np.load(rd / f"scores_{nm}.npy", allow_pickle=False) for nm in names}
    events = {nm: {k: [(bool(w), float(l)) for w, l in v] for k, v in read_json(rd / f"events_{nm}.json").items()} for nm in names}
    pairs = [(M_FROZEN, M_MODEL_A), (M_FROZEN, M_AOA), (M_MODEL_A, M_AOA)]
    boot, reps = analysis.run_protocol_bootstrap(traj, y, scores, pairs, events=events)
    write_json(cfg, rd, "bootstrap.json", boot)
    with open(out_path(cfg, rd, "bootstrap_replicates.npz"), "xb") as f:
        np.savez(f, **{k.replace("|", "__").replace(" ", "_"): v for k, v in reps.items()})
    equiv = read_json(rd / "equivalence_check.json")
    write_text(cfg, rd, "REPORT.md", _report(cfg, rd, metrics, boot, equiv))
    base = population.verify_baseline_manifest(cfg.root)
    audit = {
        "protocol_sha256": population.verify_protocol(cfg.protocol_path, cfg.protocol_sha256),
        "frozen_model_sha256": population.sha256_file(cfg.frozen_model_path),
        "frozen_model_unchanged": population.sha256_file(cfg.frozen_model_path) == cfg.frozen_model_sha256,
        "baseline_manifest": base,
        "data_files": population.verify_file_hashes(cfg.data_dir, cfg.data_hashes),
        "run_files": {p.name: population.sha256_file(p) for p in sorted(rd.iterdir()) if p.is_file() and p.name != "audit.json"},
    }
    write_json(cfg, rd, "audit.json", audit)
    if base["n_failed"] or not audit["frozen_model_unchanged"]:
        raise population.DataIntegrityError("protected artifact check failed")
    return {"B": BOOTSTRAP_B, "seed": BOOTSTRAP_SEED, "baseline_ok": base["n_ok"]}


GATE_FUNCS: Dict[str, Callable[[RunConfig, Path], dict]] = {"G4": gate_g4, "G5": gate_g5, "G6": gate_g6, "G7": gate_g7, "G8": gate_g8}


def record_gate(cfg: RunConfig, run_dir: Path, gate: str, status: str, payload: dict) -> Path:
    path = gate_file(run_dir, gate)
    if path.exists():
        raise population.GateViolation(f"gate {gate} already has a record in {run_dir}")
    population.assert_phase3_output_path(path, cfg.root)
    with open(path, "x") as f:
        json.dump(_jsonable({"gate": gate, "status": status, "utc": utc_now(), **payload}), f, indent=2)
    return path


def execute_gate(cfg: RunConfig, gate: str, confirm: Optional[str], run_dir: Optional[Path] = None) -> Tuple[str, dict, Path]:
    """Run one gate. Returns (status, payload, run_dir). A confirmation or ordering problem raises
    before anything is written; a failure inside the gate is recorded as FAIL."""
    gate = gate.upper()
    if gate not in GATES:
        raise ValueError(f"unknown gate {gate}")
    require_confirm(gate, confirm)
    if gate == "G4":
        run_dir = new_run_dir(cfg)
    else:
        if run_dir is None:
            raise population.GateViolation(f"gate {gate} requires --run-dir")
        run_dir = population.assert_phase3_output_path(Path(run_dir), cfg.root)
        require_gate_pass(run_dir, PREVIOUS[gate])
        if gate_file(run_dir, gate).exists():
            raise population.GateViolation(f"gate {gate} already ran in {run_dir}; it is single-shot")
    try:
        payload = GATE_FUNCS[gate](cfg, run_dir)
        status = "PASS"
    except Exception as exc:  # recorded, never swallowed silently
        status, payload = "FAIL", {"error_type": type(exc).__name__, "error": str(exc), "trace_tail": traceback.format_exc().splitlines()[-6:]}
    record_gate(cfg, run_dir, gate, status, {"payload": payload})
    return status, payload, run_dir


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="gate", required=True)
    for g in ("g4", "g5", "g6", "g7", "g8"):
        s = sub.add_parser(g)
        s.add_argument("--confirm-gate", required=True, help=f"must equal {g.upper()}; pass only after that gate is approved")
        s.add_argument("--root", default=str(ROOT), help="execution tree (no .git)")
        if g != "g4":
            s.add_argument("--run-dir", required=True)
        if g in ("g4", "g5"):
            s.add_argument("--item26-dir", required=True, help="Item 26 scratch tree (read-only records)")
        if g == "g4":
            s.add_argument("--git-commit", default="unrecorded")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cfg = RunConfig(root=Path(args.root).resolve(), item26_dir=Path(args.item26_dir).resolve() if getattr(args, "item26_dir", None) else None,
                    git_commit=getattr(args, "git_commit", "unrecorded"))
    status, payload, run_dir = execute_gate(cfg, args.gate, args.confirm_gate, Path(args.run_dir) if getattr(args, "run_dir", None) else None)
    print(json.dumps({"gate": args.gate.upper(), "status": status, "run_dir": str(run_dir), "payload": _jsonable(payload)}, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
