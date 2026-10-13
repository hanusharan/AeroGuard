"""Gated execution of Item 33 (PROTOCOL.md section 17).

IMPORTING THIS MODULE, OR RUNNING THE SYNTHETIC TESTS, PASSES NO GATE. Each gate runs only with
``--confirm-gate <gate>`` naming it, only from an execution tree without ``.git``, only after the protocol lock
verifies, only after its prerequisite gates recorded PASS in the same run directory, and only once. Every output
is created exclusively below ``outputs/items33_42/item33/run_<UTC>/``.

Gate bodies are written against injectable dependencies (``Deps``) so that the whole sequence can be exercised
on synthetic data in the tests (``RunConfig.dry_run``). A dry run is labelled as such in every record and
report; it is never a research result.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from ml.events import compute_event_level_results  # reused unchanged
from phase3.analysis import events_by_trajectory, operating_point  # reused unchanged
from phase3.instantaneous import library_versions  # reused unchanged
from phase3.population import schema_missing_columns, verify_baseline_manifest  # reused unchanged

from . import (
    BASELINE_MANIFEST_RELPATH, BOOTSTRAP_B, BOOTSTRAP_INTERVAL_PCT, BOOTSTRAP_SEED, DATA_FILE_SHA256, FROZEN_METRICS_RELPATH,
    FROZEN_MODEL_RELPATH, FROZEN_MODEL_SHA256, FROZEN_THRESHOLD, LOCK_RELPATH, MASK_SEEDS, METADATA_RELPATH, METADATA_SHA256,
    OUTPUT_ROOT_RELPATH, PHASE3_FROZEN_SCORES_SHA256, PHASE3_ROW_KEYS_SHA256, PRIMARY_SEED, PROTOCOL_SHA256, SEEDS,
    SPLIT_MANIFEST_RELPATH, SPLIT_MANIFEST_SHA256,
)
from . import bootstrap as bs
from . import conditions as cond
from . import fitting, masking, operating_point as mop, population as pop, register, report, summary
from .guards import (
    DataIntegrityError, GateViolation, assert_no_git, assert_output_path, jsonable, sha256_file, verify_protocol_lock,
    write_json_exclusive, write_text_exclusive,
)

GATES = ("G33-1", "G33-2", "G33-4a", "G33-4b", "G33-5a", "G33-5b", "G33-6")
PREREQ: Dict[str, Tuple[str, ...]] = {
    "G33-1": (), "G33-2": ("G33-1",), "G33-4a": ("G33-2",), "G33-4b": ("G33-4a",), "G33-5a": ("G33-4b",),
    "G33-5b": ("G33-2",), "G33-6": ("G33-5a",),
}
LOAD_COLUMNS = list(dict.fromkeys(["trajectory_id", "time", "future_stall_5s", "future_stall_5s_available", "is_unsafe", "time_to_stall"] + list(cond.C0_FEATURES)))
MASK_COLUMNS = sorted({c for cols in masking.MASK_SETS.values() for c in cols})
TARGET = pop.TARGET_COL
BANNER = report.BANNER
HORIZON_S = 5.0


@dataclass
class RunConfig:
    root: Path
    git_commit: str = "unrecorded"
    data_hashes: Dict[str, str] = field(default_factory=lambda: dict(DATA_FILE_SHA256))
    expected_counts: Optional[Dict[str, int]] = None
    phase3_dir: Optional[Path] = None            # scratch Phase 3 run directory (read-only): frozen anchor scores, row keys
    phase3_frozen_scores_sha256: str = PHASE3_FROZEN_SCORES_SHA256
    dry_run: bool = False
    bootstrap_B: int = BOOTSTRAP_B
    seeds: Tuple[int, ...] = SEEDS

    def __post_init__(self):
        self.root = Path(self.root)
        if not self.dry_run and (self.bootstrap_B != BOOTSTRAP_B or tuple(self.seeds) != SEEDS or self.expected_counts is not None):
            raise GateViolation("B, seeds and expected counts are fixed by the protocol; overriding them is allowed only in a dry run")

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def frozen_model_path(self) -> Path:
        return self.root / FROZEN_MODEL_RELPATH

    @property
    def counts(self) -> Dict[str, int]:
        return dict(pop.REPORTED_COUNTS if self.expected_counts is None else self.expected_counts)


@dataclass
class Deps:
    """Injection points. Defaults are the real implementations; the tests inject synthetic ones."""
    reader: Optional[Callable] = None
    builder: Callable = fitting.build_forest
    verify_hashes: Callable = pop.verify_file_hashes
    schema_missing: Callable = schema_missing_columns
    load_model: Optional[Callable] = None
    metadata: Optional[Callable[[], pd.DataFrame]] = None
    split_manifest: Optional[Callable[[], pd.DataFrame]] = None
    pip_freeze: Optional[Callable[[], List[str]]] = None

    def model_loader(self):
        if self.load_model is not None:
            return self.load_model
        import joblib
        return joblib.load


# ---------------------------------------------------------------------------------------------
# I/O helpers: exclusive creation, run directory, gate records
# ---------------------------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_dir(cfg: RunConfig) -> Path:
    assert_no_git(cfg.root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = assert_output_path(cfg.root / OUTPUT_ROOT_RELPATH / f"run_{stamp}", cfg.root)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def gate_file(run_dir: Path, gate: str) -> Path:
    return Path(run_dir) / f"gate_{gate}.json"


def read_json(path) -> dict:
    return json.loads(Path(path).read_text())


def require_gate_pass(run_dir: Path, gate: str) -> dict:
    path = gate_file(run_dir, gate)
    if not path.is_file():
        raise GateViolation(f"gate {gate} has no record in {run_dir}; it must PASS first")
    rec = read_json(path)
    if rec.get("status") != "PASS":
        raise GateViolation(f"gate {gate} did not pass (status {rec.get('status')!r})")
    return rec


def require_confirm(gate: str, given: Optional[str]) -> None:
    if given != gate:
        raise GateViolation(f"gate {gate} requires --confirm-gate {gate} (given {given!r}); pass it only after that gate is authorized")


def W(cfg: RunConfig, run_dir: Path, name: str, obj) -> Path:
    return write_json_exclusive(Path(run_dir) / name, obj, cfg.root)


def save_npy(cfg: RunConfig, run_dir: Path, name: str, arr) -> Path:
    target = assert_output_path(Path(run_dir) / name, cfg.root)
    with open(target, "xb") as f:
        np.save(f, np.asarray(arr))
    return target


def save_npz(cfg: RunConfig, run_dir: Path, name: str, **arrays) -> Path:
    target = assert_output_path(Path(run_dir) / name, cfg.root)
    with open(target, "xb") as f:
        np.savez(f, **arrays)
    return target


def record_gate(cfg: RunConfig, run_dir: Path, gate: str, status: str, payload: dict) -> Path:
    path = gate_file(run_dir, gate)
    if path.exists():
        raise GateViolation(f"gate {gate} already has a record in {run_dir}")
    return write_json_exclusive(path, {"gate": gate, "status": status, "utc": utc_now(), "dry_run": cfg.dry_run, **payload}, cfg.root)


def pip_freeze_real() -> List[str]:
    try:
        out = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, timeout=60)
        return out.stdout.splitlines() if out.returncode == 0 else [f"pip freeze failed: {out.stderr.strip()[:200]}"]
    except Exception as exc:  # pragma: no cover
        return [f"pip freeze unavailable: {exc}"]


def _load(cfg: RunConfig, deps: Deps, split: str, columns, allowed) -> pop.SplitTable:
    return pop.load_split(cfg.data_dir, split, columns, allowed, reader=deps.reader)


def _eligible(table: pop.SplitTable):
    mask = pop.usable_mask(table.df)
    sub = table.df.loc[mask].reset_index(drop=True)
    keys = pop.row_keys(sub)
    pop.assert_consecutive_steps(keys)
    return sub, keys, sub[TARGET].to_numpy().astype(int)


def _fit_order(cfg: RunConfig) -> List[Tuple[str, int]]:
    return [(c, int(s)) for s in cfg.seeds for c in cond.CONDITION_ORDER]


def observed_counts(summaries: Mapping[str, Mapping[str, int]], events: Mapping[str, int]) -> Dict[str, int]:
    """Counts in the vocabulary of ``phase3.population.REPORTED_COUNTS`` (G33-1 reconciles these against the record)."""
    return {
        "trajectories_train": summaries["train"]["trajectories_total"], "trajectories_val": summaries["val"]["trajectories_total"],
        "trajectories_test": summaries["test"]["trajectories_total"],
        "panel_rows_train": summaries["train"]["rows_total"], "panel_rows_val": summaries["val"]["rows_total"],
        "panel_rows_test": summaries["test"]["rows_total"],
        "usable_rows_train": summaries["train"]["rows_usable"], "usable_rows_val": summaries["val"]["rows_usable"],
        "usable_rows_test": summaries["test"]["rows_usable"],
        "test_trajectories_with_usable_rows": summaries["test"]["trajectories_with_usable_rows"],
        "test_positive_rows": summaries["test"]["positives"], "test_negative_rows": summaries["test"]["negatives"],
        "test_events": events["events"], "test_first_events": events["first_events"], "test_later_events": events["later_events"],
        "test_trajectories_with_events": events["trajectories_with_events"],
        "test_trajectories_with_any_unsafe_run": summaries["test"].get("trajectories_with_any_unsafe_run", 0),
    }


# ---------------------------------------------------------------------------------------------
# G33-1: data-dependent checks (reads panels; loads the frozen model; no training, no scoring)
# ---------------------------------------------------------------------------------------------

def gate_g33_1(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    prot = verify_protocol_lock(cfg.root)
    tracked = {}
    if not cfg.dry_run:
        base = verify_baseline_manifest(cfg.root)
        if base["n_failed"]:
            raise DataIntegrityError(f"baseline manifest failures: {base['failures'][:3]}")
        if sha256_file(cfg.frozen_model_path) != FROZEN_MODEL_SHA256:
            raise DataIntegrityError("frozen model hash differs from the locked value")
        for rel, want in ((SPLIT_MANIFEST_RELPATH, SPLIT_MANIFEST_SHA256), (METADATA_RELPATH, METADATA_SHA256)):
            got = sha256_file(cfg.root / rel)
            if got != want:
                raise DataIntegrityError(f"{rel} hash differs from the locked value")
            tracked[rel] = got
        cond.verify_against_stored_record(read_json(cfg.root / FROZEN_METRICS_RELPATH)["feature_columns"])
    cond.verify_against_source()
    hashes = deps.verify_hashes(cfg.data_dir, cfg.data_hashes)
    schema = {}
    for s in pop.SPLITS:
        missing = deps.schema_missing(cfg.data_dir / pop.panel_relpath(s), LOAD_COLUMNS)
        schema[s] = missing
        if missing:
            raise DataIntegrityError(f"{s} panel lacks column(s) {missing}")

    tables = {s: _load(cfg, deps, s, LOAD_COLUMNS, pop.SPLITS) for s in pop.SPLITS}
    summaries = {s: pop.summarize_population(t.df) for s, t in tables.items()}
    test = tables["test"]
    test_mask = pop.usable_mask(test.df)
    events = pop.count_events(test.df, test_mask)
    observed = observed_counts(summaries, events)
    expected = {k: v for k, v in cfg.counts.items() if k not in ("dataset_rows", "dataset_trajectories")}
    mismatches = pop.compare_counts(observed, expected)
    if mismatches:
        raise DataIntegrityError("counts do not reconcile: " + "; ".join(mismatches))

    ids = {s: set(t.df["trajectory_id"].unique()) for s, t in tables.items()}
    pop.assert_no_trajectory_overlap(ids)
    manifest = deps.split_manifest() if deps.split_manifest else pd.read_csv(cfg.root / SPLIT_MANIFEST_RELPATH)
    for s in pop.SPLITS:
        if set(manifest.loc[manifest["split"] == s, "trajectory_id"]) != ids[s]:
            raise DataIntegrityError(f"{s}: panel trajectory ids differ from the split manifest")

    sub, keys, y = _eligible(test)
    kh = pop.key_hash(keys)
    phase3_keys = None
    if cfg.phase3_dir is not None:
        p3 = Path(cfg.phase3_dir) / "row_keys.npz"
        if not cfg.dry_run and sha256_file(p3) != PHASE3_ROW_KEYS_SHA256:
            raise DataIntegrityError("Phase 3 row_keys.npz hash differs from the recorded value")
        z = np.load(p3, allow_pickle=False)
        pop.assert_same_keys(pop.RowKeys(traj=np.asarray(z["trajectory_id"]).astype(str), step=np.asarray(z["step"])),
                             pop.RowKeys(traj=np.asarray(keys.traj).astype(str), step=keys.step), label="test keys vs Phase 3")
        phase3_keys = "equal"

    metadata = deps.metadata() if deps.metadata else pd.read_csv(cfg.root / METADATA_RELPATH)
    regimes = pop.regime_of_trajectories(pd.unique(keys.traj), metadata)
    sizes = pop.stratum_sizes(regimes)
    tr_sub = tables["train"].df.loc[pop.usable_mask(tables["train"].df)]
    structure = {c: pop.column_constancy(tr_sub, c) for c in ("throttle", "elevator")}
    medians = pop.training_medians(tables["train"].df, MASK_COLUMNS, pop.usable_mask(tables["train"].df))

    frozen_check = {"checked": False}
    if not cfg.dry_run:
        model = deps.model_loader()(cfg.frozen_model_path)
        names = getattr(model, "feature_names_in_", None)
        frozen_check = {"checked": True, "n_features_in": int(getattr(model, "n_features_in_", -1)),
                        "feature_names_in": None if names is None else list(names)}
        if names is not None and list(names) != list(cond.C0_FEATURES):
            raise DataIntegrityError("frozen model feature_names_in_ differs from C0")
        if frozen_check["n_features_in"] != len(cond.C0_FEATURES):
            raise DataIntegrityError("frozen model n_features_in_ differs from 23")

    pop_rec = {"banner": BANNER, "summaries": summaries, "observed_counts": observed, "expected_counts": expected,
               "count_mismatches": mismatches, "test_events": events, "test_key_hash": kh,
               "eligible_time_test": pop.eligible_time(keys), "n_rows": len(keys),
               "n_trajectories": int(pd.unique(keys.traj).size)}
    W(cfg, run_dir, "population.json", pop_rec)
    W(cfg, run_dir, "data_provenance.json", {
        "banner": BANNER, "data_files": hashes, "tracked_identifiers": tracked, "schema_missing": schema,
        "original_dataset": "absent; no hash found; regenerated copy is not shown to be byte-identical",
        "phase3_row_keys": phase3_keys})
    W(cfg, run_dir, "strata.json", {"by_trajectory": regimes, "sizes": sizes})
    W(cfg, run_dir, "structure_checks.json", structure)
    W(cfg, run_dir, "masking_medians.json", {"source": "training usable rows only", "medians": medians})
    W(cfg, run_dir, "frozen_model_check.json", frozen_check)
    return {"protocol_sha256": prot, "test_key_hash": kh, "stratum_sizes": sizes, "n_rows_test": len(keys)}


# ---------------------------------------------------------------------------------------------
# G33-2: freeze
# ---------------------------------------------------------------------------------------------

def spec_hash(spec: Mapping) -> str:
    return hashlib.sha256(json.dumps(jsonable(spec), sort_keys=True).encode()).hexdigest()


def gate_g33_2(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    prot = verify_protocol_lock(cfg.root)
    manifest = cond.validate_manifest()
    cond.verify_against_source()
    register.validate_register()
    spec = {
        "protocol_sha256": prot, "conditions": manifest, "seeds": list(cfg.seeds), "primary_seed": PRIMARY_SEED,
        "rf_params": fitting.RF_PARAMS, "bootstrap": {"B": cfg.bootstrap_B, "seed": BOOTSTRAP_SEED, "pct": list(BOOTSTRAP_INTERVAL_PCT)},
        "masking": {"sets": {k: list(v) for k, v in masking.MASK_SETS.items()}, "methods": list(masking.METHODS), "seeds": list(MASK_SEEDS)},
        "register": register.REGISTER, "frozen_threshold": FROZEN_THRESHOLD,
    }
    h = spec_hash(spec)
    freeze_ref = {"specification_sha256": h, "frozen_before_any_scoring": True, "utc": utc_now()}
    pf = deps.pip_freeze() if deps.pip_freeze else pip_freeze_real()
    W(cfg, run_dir, "conditions_manifest.json", manifest)
    W(cfg, run_dir, "seeds.json", {"forest_seeds": list(cfg.seeds), "primary_seed": PRIMARY_SEED, "bootstrap_seed": BOOTSTRAP_SEED,
                                   "masking_permutation_seeds": list(MASK_SEEDS)})
    W(cfg, run_dir, "protocol_lock.json", {"protocol_sha256": prot, "lock_record": LOCK_RELPATH, "git_commit": cfg.git_commit,
                                           "tree_root": str(cfg.root), "created_utc": utc_now(), "banner": BANNER})
    W(cfg, run_dir, "environment.json", {"versions": library_versions(), "python": sys.version, "platform": platform.platform(),
                                         "cpu_count": os.cpu_count(), "pip_freeze": pf})
    W(cfg, run_dir, "freeze.json", {**freeze_ref, "specification": spec})
    return freeze_ref


# ---------------------------------------------------------------------------------------------
# G33-4a / G33-4b: fitting (train and validation only)
# ---------------------------------------------------------------------------------------------

def _persist_fit(cfg: RunConfig, run_dir: Path, fit: fitting.FitResult, y_val: np.ndarray) -> dict:
    name = f"{fit.condition}_{fit.seed}"
    mpath = fitting.save_model_exclusive(fit.model, Path(run_dir) / f"model_{name}.joblib", cfg.root)
    rec = fit.record()
    rec["model_sha256"] = sha256_file(mpath)
    rec["dry_run"] = cfg.dry_run
    W(cfg, run_dir, f"fit_record_{name}.json", rec)
    W(cfg, run_dir, f"threshold_{name}.json", {"condition": fit.condition, "seed": fit.seed, "threshold": fit.threshold,
                                               "operator": "strict >", "info": fit.threshold_info})
    save_npy(cfg, run_dir, f"val_scores_{name}.npy", fit.val_score)
    return rec


def _val_labels(cfg: RunConfig, run_dir: Path, val: pop.SplitTable) -> np.ndarray:
    _, _, y = _eligible(val)
    path = Path(run_dir) / "val_labels.npy"
    if path.exists():
        if not np.array_equal(np.load(path), y):
            raise DataIntegrityError("validation labels changed between fits")
    else:
        save_npy(cfg, run_dir, "val_labels.npy", y)
    return y


def gate_g33_4a(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    verify_protocol_lock(cfg.root)
    train = _load(cfg, deps, "train", LOAD_COLUMNS, ("train", "val"))
    val = _load(cfg, deps, "val", LOAD_COLUMNS, ("train", "val"))
    c, s = _fit_order(cfg)[0]
    out = fitting.try_fit(c, s, train, val, builder=deps.builder)
    if isinstance(out, fitting.FitFailure):
        W(cfg, run_dir, "failures_G33-4a.json", [out.record()])
        raise RuntimeError(f"the first fit failed: {out.error_type}: {out.error}")
    y_val = _val_labels(cfg, run_dir, val)
    rec = _persist_fit(cfg, run_dir, out, y_val)
    return {"stopped_for_cost_reconfirmation": True, "condition": c, "seed": s, "fit_seconds": rec["fit_seconds"],
            "peak_rss_mb": rec["peak_rss_mb"], "n_train_rows": rec["n_train_rows"], "threshold": rec["threshold"],
            "next": "G33-4b fits the remaining models only after separate authorization"}


def _fit_state(rd: Path, c: str, s: int) -> str:
    """'complete' when all four artifacts of a fit exist, 'absent' when none does, otherwise 'partial'."""
    name = f"{c}_{s}"
    present = [(Path(rd) / f).is_file() for f in (f"model_{name}.joblib", f"fit_record_{name}.json", f"threshold_{name}.json", f"val_scores_{name}.npy")]
    return "complete" if all(present) else ("absent" if not any(present) else "partial")


def gate_g33_4b(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    """Fit every remaining (condition, seed). The gate is resumable: a fit whose four artifacts all exist and whose model hash
    matches its record is kept and skipped (it is never refitted); a partially written fit stops the gate. Settings are identical
    on a resumed invocation, so an interruption (for example a background time limit) does not change any result."""
    verify_protocol_lock(cfg.root)
    train = _load(cfg, deps, "train", LOAD_COLUMNS, ("train", "val"))
    val = _load(cfg, deps, "val", LOAD_COLUMNS, ("train", "val"))
    y_val = _val_labels(cfg, run_dir, val)
    failures, done, kept = [], [], []
    for c, s in _fit_order(cfg)[1:]:
        state = _fit_state(run_dir, c, s)
        name = f"{c}_{s}"
        if state == "partial":
            raise DataIntegrityError(f"fit {name} has partial artifacts; it was interrupted mid-write and needs a recorded decision")
        if state == "complete":
            rec = read_json(Path(run_dir) / f"fit_record_{name}.json")
            if sha256_file(Path(run_dir) / f"model_{name}.joblib") != rec["model_sha256"]:
                raise DataIntegrityError(f"model file for {name} differs from its fit record")
            kept.append(name)
            continue
        out = fitting.try_fit(c, s, train, val, builder=deps.builder)
        if isinstance(out, fitting.FitFailure):
            failures.append(out.record())
            continue
        _persist_fit(cfg, run_dir, out, y_val)
        done.append(name)
        del out
    W(cfg, run_dir, "failures.json", failures)
    W(cfg, run_dir, "fit_progress.json", {"fitted_in_this_invocation": done, "kept_from_an_earlier_invocation": kept,
                                          "note": "kept fits were hash-verified and not refitted; settings are identical across invocations"})
    if failures:
        raise RuntimeError(f"{len(failures)} fit(s) failed; recorded in failures.json; none was retried or dropped")
    return {"fitted_in_this_invocation": len(done), "kept_from_an_earlier_invocation": len(kept), "total_fits": len(_fit_order(cfg)), "failures": 0}


# ---------------------------------------------------------------------------------------------
# G33-5a / G33-5b: test scoring (single-shot)
# ---------------------------------------------------------------------------------------------

def gate_g33_5a(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    verify_protocol_lock(cfg.root)
    test = _load(cfg, deps, "test", LOAD_COLUMNS, ("test",))
    sub, keys, y = _eligible(test)
    kh = pop.key_hash(keys)
    p1 = read_json(Path(run_dir) / "population.json")
    if p1["test_key_hash"] != kh:
        raise DataIntegrityError("test population differs from the population recorded at G33-1")
    ledger = fitting.SingleShotLedger(Path(run_dir), cfg.root)
    load_model = deps.model_loader()
    sets, scored = [], []
    for c, s in _fit_order(cfg):
        name = f"{c}_{s}"
        rec = read_json(Path(run_dir) / f"fit_record_{name}.json")
        mpath = Path(run_dir) / f"model_{name}.joblib"
        if sha256_file(mpath) != rec["model_sha256"]:
            raise DataIntegrityError(f"model file for {name} changed since it was fitted")
        ledger.claim(c, s)
        model = load_model(mpath)
        score = fitting.score_rows(model, sub, rec["features"], np.ones(len(sub), dtype=bool))
        sets.append(pop.make_prediction_set(name, keys, score))
        save_npy(cfg, run_dir, f"scores_{name}.npy", score)
        scored.append(name)
    pop.assert_common_population(keys, y, sets)
    save_npy(cfg, run_dir, "test_labels.npy", y)
    save_npz(cfg, run_dir, "test_keys.npz", trajectory_id=np.asarray(keys.traj).astype(str), step=keys.step)
    anchor = None
    if cfg.phase3_dir is not None and (Path(cfg.phase3_dir) / "scores_frozen_temporal.npy").is_file():
        arr = np.load(Path(cfg.phase3_dir) / "scores_frozen_temporal.npy", allow_pickle=False)
        got = sha256_file(Path(cfg.phase3_dir) / "scores_frozen_temporal.npy")
        if got != cfg.phase3_frozen_scores_sha256:
            raise DataIntegrityError("Phase 3 frozen-model scores hash differs from the recorded value")
        if arr.shape[0] != len(keys):
            raise DataIntegrityError("Phase 3 frozen-model scores have a different length")
        save_npy(cfg, run_dir, "scores_FROZEN_phase3.npy", arr)
        anchor = {"source": "Phase 3 scores (E1)", "sha256": got}
    return {"scored": len(scored), "population_id": f"test_usable_1s:{kh[:16]}", "frozen_anchor": anchor}


def gate_g33_5b(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    verify_protocol_lock(cfg.root)
    if not cfg.dry_run and sha256_file(cfg.frozen_model_path) != FROZEN_MODEL_SHA256:
        raise DataIntegrityError("frozen model hash differs from the locked value")
    medians = read_json(Path(run_dir) / "masking_medians.json")["medians"]
    test = _load(cfg, deps, "test", LOAD_COLUMNS, ("test",))
    sub, keys, y = _eligible(test)
    if read_json(Path(run_dir) / "population.json")["test_key_hash"] != pop.key_hash(keys):
        raise DataIntegrityError("test population differs from the population recorded at G33-1")
    model = deps.model_loader()(cfg.frozen_model_path)
    feats = list(cond.C0_FEATURES)
    ledger = fitting.SingleShotLedger(Path(run_dir), cfg.root)
    allmask = np.ones(len(sub), dtype=bool)
    ledger.claim("FROZEN", 0)
    unmasked = fitting.score_rows(model, sub, feats, allmask)
    save_npy(cfg, run_dir, "scores_FROZEN_rescored.npy", unmasked)
    variants = []
    for ms in masking.MASK_SETS:
        for method in masking.METHODS:
            seeds = [None] if method == "MS1" else list(MASK_SEEDS)
            for sd in seeds:
                label = f"{ms}-{method}" + ("" if sd is None else f"-{sd}")
                ledger.claim(label, 0)
                masked = masking.apply_mask(sub, feats, ms, method, medians=medians, seed=sd)
                masked[TARGET] = sub[TARGET].to_numpy()      # get_xy reads the label column to build y; it is never a model input
                score = fitting.score_rows(model, masked, feats, allmask)
                save_npy(cfg, run_dir, f"masking_scores_{label}.npy", score)
                variants.append({"label": label, "mask_set": ms, "method": method, "seed": sd})
    W(cfg, run_dir, "masking_variants.json", {"analysis_family": masking.ANALYSIS_FAMILY, "variants": variants,
                                              "note": "perturbation of the frozen model's inputs; not retrained ablation"})
    return {"variants": len(variants)}


# ---------------------------------------------------------------------------------------------
# G33-6: analysis of the stored test scores
# ---------------------------------------------------------------------------------------------

def historical_figures(root: Path) -> Dict[str, object]:
    """Context figures read from tracked records at run time (never typed in)."""
    out: Dict[str, object] = {}
    p = Path(root) / FROZEN_METRICS_RELPATH
    if p.is_file():
        out["E0 stored frozen-model PR-AUC (original evaluation)"] = read_json(p)["test_metrics"]["pr_auc"]
    for b in sorted((Path(root) / "outputs" / "phase3").glob("run_*/bootstrap.json")):
        pm = read_json(b)["per_method"]
        for k, label in (("frozen_temporal|pr_auc", "E1 Phase 3 frozen-model PR-AUC (regenerated data)"),
                         ("instantaneous_model_a|pr_auc", "E1 Phase 3 instantaneous Model A PR-AUC (regenerated data)")):
            if k in pm:
                out[label] = pm[k]["point"]
        break
    if not out:
        out["note"] = "no tracked historical record found in this tree"
    return out


def _events_for(eligible: pd.DataFrame, score: np.ndarray, threshold: float):
    pred = fitting.apply_threshold(score, threshold)
    return events_by_trajectory(compute_event_level_results(eligible, pred, HORIZON_S))


def gate_g33_6(cfg: RunConfig, run_dir: Path, deps: Deps) -> dict:
    verify_protocol_lock(cfg.root)
    rd = Path(run_dir)
    y = np.load(rd / "test_labels.npy")
    z = np.load(rd / "test_keys.npz", allow_pickle=False)
    traj = np.asarray(z["trajectory_id"]).astype(str)
    keys = pop.RowKeys(traj=traj, step=np.asarray(z["step"]))
    kh = pop.key_hash(keys)
    order = _fit_order(cfg)
    scores = {bs.method_key(c, s): np.load(rd / f"scores_{c}_{s}.npy") for c, s in order}
    recs = {bs.method_key(c, s): read_json(rd / f"fit_record_{c}_{s}.json") for c, s in order}
    pop.assert_common_population(keys, y, [pop.make_prediction_set(k, keys, v) for k, v in scores.items()])
    strata = read_json(rd / "strata.json")["by_trajectory"]
    B = cfg.bootstrap_B
    seeds = list(cfg.seeds)
    metrics_both = ("pr_auc", "roc_auc")

    point = bs.point_estimates(y, scores, metrics_both)
    fast_check = bs.verify_fast_replicates(traj, y, scores, seed=BOOTSTRAP_SEED, n=2)     # fast path vs scikit-learn, first replicates
    reps = bs.bootstrap_replicates(traj, y, scores, B=B, seed=BOOTSTRAP_SEED, metrics=metrics_both)
    save_npz(cfg, rd, "bootstrap_replicates.npz", **{k.replace("|", "__"): v for k, v in reps.items()})

    contrast_defs = [
        ("D1", "C0", "C1", "pr_auc", "primary", True), ("D2", "C0", "C2", "pr_auc", "primary", True),
        ("SEC-2", "C1", "C2", "pr_auc", "secondary", False), ("SEC-3", "C0", "C1", "roc_auc", "secondary", False),
        ("SEC-3", "C0", "C2", "roc_auc", "secondary", False),
        ("X-a", "C0", "C3", "pr_auc", "exploratory", False), ("X-b", "C0", "X1", "pr_auc", "exploratory", False),
    ]
    contrasts = []
    for rid, ref, cmp_, metric, status, bonf in contrast_defs:
        summ = bs.contrast_summary(ref, cmp_, seeds, point, reps, metric=metric, bonferroni=bonf)
        deltas = [summ["per_seed"][s]["point"] for s in seeds]
        b = summ["bootstrap_seed_mean"]
        adj = summ.get("bootstrap_seed_mean_bonferroni", {})
        stmt = summary.evidence_statement(status, b["ci_lo"], b["ci_hi"], deltas, adj.get("ci_lo"), adj.get("ci_hi"))
        contrasts.append({"register_id": rid, "status": status, "summary": summ, "statement": stmt})
    sec1 = {}
    for rid in ("D1", "D2"):
        c = next(c for c in contrasts if c["register_id"] == rid)
        sec1[rid] = c["summary"]["per_seed"][PRIMARY_SEED]

    # SR: regime-stratified resampling for D1 and D2 (sensitivity; no decision role)
    sr_scores = {k: v for k, v in scores.items() if k.split("|")[0] in ("C0", "C1", "C2")}
    reps_sr = bs.bootstrap_replicates(traj, y, sr_scores, B=B, seed=BOOTSTRAP_SEED, strata=strata, metrics=("pr_auc",))
    sens = {}
    for rid, ref, cmp_ in (("D1", "C0", "C1"), ("D2", "C0", "C2")):
        s_sr = bs.contrast_summary(ref, cmp_, seeds, point, reps_sr, metric="pr_auc")["bootstrap_seed_mean"]
        prim = next(c for c in contrasts if c["register_id"] == rid)["summary"]["bootstrap_seed_mean"]
        sens[rid] = {"ci_lo": s_sr["ci_lo"], "ci_hi": s_sr["ci_hi"], "primary_ci_lo": prim["ci_lo"], "primary_ci_hi": prim["ci_hi"],
                     "includes_zero": s_sr["includes_zero"], "primary_includes_zero": prim["includes_zero"],
                     "agrees_on_zero_inclusion": s_sr["includes_zero"] == prim["includes_zero"],
                     "n_undefined_replicates": s_sr["n_undefined_replicates"]}

    # seed panels: A_c(s) spread, descriptive
    panels = {c: summary.seed_panel({s: point[f"{bs.method_key(c, s)}|pr_auc"] for s in seeds}) for c in cond.CONDITION_ORDER}

    # T1: reproduction diagnostic against the frozen model's scores (Phase 3 anchor, else the G33-5b re-score)
    anchor_path = next((p for p in (rd / "scores_FROZEN_phase3.npy", rd / "scores_FROZEN_rescored.npy") if p.is_file()), None)
    repro = None
    if anchor_path is not None:
        fz = np.load(anchor_path)
        c0 = scores[bs.method_key("C0", PRIMARY_SEED)]
        two = {"FROZEN|0": fz, "C0|%d" % PRIMARY_SEED: c0}
        r2 = bs.bootstrap_replicates(traj, y, two, B=B, seed=BOOTSTRAP_SEED, metrics=("pr_auc",))
        d = r2[f"C0|{PRIMARY_SEED}|pr_auc"] - r2["FROZEN|0|pr_auc"]
        lo, hi, nu = bs.percentile_interval(d)
        identical = bool(np.array_equal(fz, c0))
        level = "R0" if identical else ("R1" if (lo is not None and lo <= 0.0 <= hi) else "R2")
        pr_c0 = float(average_precision_score(y, c0)); pr_fz = float(average_precision_score(y, fz))
        thr_c0 = recs[bs.method_key("C0", PRIMARY_SEED)]["threshold"]
        repro = {"level": level, "bit_identical": identical, "max_abs_score_diff": float(np.max(np.abs(fz - c0))),
                 "threshold_diff": float(thr_c0 - FROZEN_THRESHOLD), "pr_auc_diff": pr_c0 - pr_fz, "ci_lo": lo, "ci_hi": hi,
                 "n_undefined_replicates": nu, "anchor": str(anchor_path.name)}

    # M-OP and own-threshold operating points (descriptive / exploratory)
    yv = np.load(rd / "val_labels.npy")
    mop_rows, event_files = [], {}
    test = _load(cfg, deps, "test", LOAD_COLUMNS, ("test",))
    elig, ekeys, ey = _eligible_events(test)
    pop.assert_same_keys(keys, ekeys, label="event table vs stored keys")
    for s in seeds:
        val_scores = {c: np.load(rd / f"val_scores_{c}_{s}.npy") for c in cond.CONDITION_ORDER}
        c0_thr = recs[bs.method_key("C0", s)]["threshold"]
        matched = mop.matched_thresholds(yv, val_scores, "C0", c0_thr)
        for c in cond.CONDITION_ORDER:
            k = bs.method_key(c, s)
            own_thr = recs[k]["threshold"]
            m_thr = matched[c]["threshold"]
            own = _trim_op(operating_point(elig, y, scores[k], own_thr))
            mat = _trim_op(operating_point(elig, y, scores[k], m_thr))
            event_files[f"{c}_{s}"] = {"own_threshold": own, "matched_operating_point": mat, "matched": matched[c]}
            mop_rows.append({"condition": c, "seed": s, "threshold": m_thr, "achieved_fpr": matched[c]["achieved_fpr"], "target_fpr": matched[c]["target_fpr"]})
    for name, obj in event_files.items():
        W(cfg, rd, f"event_level_{name}.json", {"analysis_family": register.FAMILY_RETRAINED, **obj})

    # event-level bootstrap intervals, seed 20260817 only
    ev_scores, ev_map = {}, {}
    for c in cond.CONDITION_ORDER:
        k = bs.method_key(c, PRIMARY_SEED)
        ev_scores[f"{c}|own"] = scores[k]
        ev_map[f"{c}|own"] = _events_for(elig, scores[k], recs[k]["threshold"])
        if c != "C0":
            ev_scores[f"{c}|matched"] = scores[k]
            ev_map[f"{c}|matched"] = _events_for(elig, scores[k], event_files[f"{c}_{PRIMARY_SEED}"]["matched"]["threshold"])
    ev_summary = bs.event_bootstrap(traj, y, ev_scores, ev_map, B=B, seed=BOOTSTRAP_SEED)

    # frozen-model masking (separate family), if scored
    masking_rows = []
    var_path = rd / "masking_variants.json"
    if var_path.is_file() and (rd / "scores_FROZEN_rescored.npy").is_file():
        unmasked = np.load(rd / "scores_FROZEN_rescored.npy")
        variants = read_json(var_path)["variants"]
        base_pr = float(average_precision_score(y, unmasked))
        first = {}
        for v in variants:
            sc = np.load(rd / f"masking_scores_{v['label']}.npy")
            pr = float(average_precision_score(y, sc))
            pred = fitting.apply_threshold(sc, FROZEN_THRESHOLD)
            tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
            masking_rows.append({"label": v["label"], "mask_set": v["mask_set"], "method": v["method"], "seed": v["seed"], "pr_auc": pr,
                                 "delta_vs_unmasked": pr - base_pr, "precision_at_frozen_threshold": tp / (tp + fp) if tp + fp else None,
                                 "recall_at_frozen_threshold": tp / (tp + fn) if tp + fn else None, "analysis_family": masking.ANALYSIS_FAMILY})
            key = (v["mask_set"], v["method"])
            if v["method"] == "MS1" or key not in first:
                first[key] = (v["label"], sc)
        mk = {"UNMASKED": unmasked, **{lbl: sc for lbl, sc in first.values()}}
        mreps = bs.bootstrap_replicates(traj, y, mk, B=B, seed=BOOTSTRAP_SEED, metrics=("pr_auc",))
        for lbl in [l for l in mk if l != "UNMASKED"]:
            d = mreps[f"{lbl}|pr_auc"] - mreps["UNMASKED|pr_auc"]
            lo, hi, nu = bs.percentile_interval(d)
            for row in masking_rows:
                if row["label"] == lbl:
                    row.update({"bootstrap_ci_lo": lo, "bootstrap_ci_hi": hi, "n_undefined_replicates": nu})
        W(cfg, rd, "masking_results.json", {"analysis_family": masking.ANALYSIS_FAMILY, "unmasked_pr_auc": base_pr, "rows": masking_rows,
                                           "note": "perturbation of the frozen model's inputs; not comparable to retrained ablation"})

    # machine-readable records
    rows = []
    for c, s in order:
        k = bs.method_key(c, s)
        for mt in metrics_both:
            rows.append(register.metric_row(analysis_family=register.FAMILY_RETRAINED, condition=c, seed=s, metric=mt, value=point[f"{k}|{mt}"],
                                            population_id=f"test_usable_1s:{kh[:16]}", register_id="EST"))
    W(cfg, rd, "metrics_primary.json", rows)
    failures = read_json(rd / "failures.json") if (rd / "failures.json").is_file() else []
    undefined = {k: int(np.isnan(v).sum()) for k, v in reps.items() if np.isnan(v).any()}
    W(cfg, rd, "bootstrap.json", {"config": {"unit": "trajectory", "B": B, "seed": BOOTSTRAP_SEED, "pct": list(BOOTSTRAP_INTERVAL_PCT),
                                             "pairing": "one draw per replicate shared by every condition and seed"},
                                  "n_trajectories": int(pd.unique(traj).size), "n_rows": int(len(y)), "undefined_replicates": undefined,
                                  "fast_path_check": fast_check,
                                  "event_level_seed_primary": ev_summary})
    W(cfg, rd, "paired_contrasts.json", {"contrasts": contrasts, "single_seed_view": sec1})
    W(cfg, rd, "seed_panel.json", panels)
    W(cfg, rd, "regime_sensitivity.json", sens)
    W(cfg, rd, "matched_operating_point.json", {"rule": "validation-only; target = C0 validation FPR at its own threshold", "rows": mop_rows})
    if repro is not None:
        W(cfg, rd, "reproduction_check.json", repro)
    pop_rec = read_json(rd / "population.json")
    bundle = {
        "run_id": rd.name, "protocol_sha256": PROTOCOL_SHA256, "dry_run": cfg.dry_run,
        "population": {"n_rows": int(len(y)), "n_trajectories": int(pd.unique(traj).size), "n_positive": int(y.sum()),
                       "n_negative": int(len(y) - y.sum()), "population_id": f"test_usable_1s:{kh[:16]}"},
        "conditions": cond.build_manifest(), "contrasts": contrasts, "seed_panels": panels, "regime_sensitivity": sens,
        "reproduction": repro, "matched_operating_point": mop_rows, "masking": masking_rows or None,
        "failures": [json.dumps(f)[:300] for f in failures] + [f"{k}: {v} undefined replicate(s)" for k, v in undefined.items()],
        "historical": historical_figures(cfg.root),
    }
    text = report.render_report(bundle)
    write_text_exclusive(rd / "REPORT.md", text, cfg.root)
    return {"contrasts": len(contrasts), "report": "REPORT.md", "reproduction_level": None if repro is None else repro["level"]}


def _eligible_events(table: pop.SplitTable):
    mask = pop.usable_mask(table.df)
    sub = table.df.loc[mask].reset_index(drop=True)
    keys = pop.row_keys(sub)
    return sub, keys, sub[TARGET].to_numpy().astype(int)


def _trim_op(op: Mapping) -> Dict[str, object]:
    """Keep the row-level and event metrics; false-alarm rates per hour belong to Item 37 and are not reported here."""
    return {"threshold": op["threshold"], "operator": op["operator"], "classification": op["classification"], "events": op["events"]}


# ---------------------------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------------------------

GATE_FUNCS: Dict[str, Callable] = {
    "G33-1": gate_g33_1, "G33-2": gate_g33_2, "G33-4a": gate_g33_4a, "G33-4b": gate_g33_4b,
    "G33-5a": gate_g33_5a, "G33-5b": gate_g33_5b, "G33-6": gate_g33_6,
}


def execute_gate(cfg: RunConfig, gate: str, confirm: Optional[str], run_dir: Optional[Path] = None,
                 deps: Optional[Deps] = None) -> Tuple[str, dict, Path]:
    """Run one gate. A confirmation, tree, lock or ordering problem raises before anything is written; a failure
    inside the gate is recorded as FAIL and is never silently retried."""
    if gate not in GATES:
        raise ValueError(f"unknown gate {gate}")
    require_confirm(gate, confirm)
    assert_no_git(cfg.root)
    verify_protocol_lock(cfg.root)
    deps = deps or Deps()
    if gate == "G33-1":
        run_dir = new_run_dir(cfg)
    else:
        if run_dir is None:
            raise GateViolation(f"gate {gate} requires --run-dir")
        run_dir = assert_output_path(Path(run_dir), cfg.root)
        for p in PREREQ[gate]:
            require_gate_pass(run_dir, p)
        if gate_file(run_dir, gate).exists():
            raise GateViolation(f"gate {gate} already ran in {run_dir}; it is single-shot")
    try:
        payload = GATE_FUNCS[gate](cfg, run_dir, deps)
        status = "PASS"
    except Exception as exc:  # recorded (including protocol violations raised inside the gate), never swallowed silently
        status = "FAIL"
        payload = {"error_type": type(exc).__name__, "error": str(exc), "trace_tail": traceback.format_exc().splitlines()[-6:]}
    record_gate(cfg, run_dir, gate, status, {"payload": payload})
    return status, payload, run_dir


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AeroGuard Item 33 gated execution. Each gate needs its own authorization.")
    p.add_argument("gate", choices=GATES)
    p.add_argument("--confirm-gate", required=True, help="must equal the gate id; pass only after that gate is authorized")
    p.add_argument("--root", required=True, help="execution tree (no .git)")
    p.add_argument("--run-dir", default=None)
    p.add_argument("--git-commit", default="unrecorded")
    p.add_argument("--phase3-dir", default=None, help="scratch Phase 3 run directory (read-only)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cfg = RunConfig(root=Path(args.root).resolve(), git_commit=args.git_commit,
                    phase3_dir=Path(args.phase3_dir).resolve() if args.phase3_dir else None)
    status, payload, run_dir = execute_gate(cfg, args.gate, args.confirm_gate, Path(args.run_dir) if args.run_dir else None)
    print(json.dumps({"gate": args.gate, "status": status, "run_dir": str(run_dir), "payload": jsonable(payload)}, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
