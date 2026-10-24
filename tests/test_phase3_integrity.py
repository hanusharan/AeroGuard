"""Phase 3 tests: protected artifacts, gate discipline and an end-to-end DRY RUN of gates
G4-G8 on SYNTHETIC data in a temporary tree (PROTOCOL.md sections 11, 13, 14, 15, 16).

What this file does NOT do: it never opens, hashes or reads the regenerated v0.3 dataset (the
synthetic tree has its own tiny stand-in files), it never loads or scores with the real frozen
model (a small stand-in forest is trained on synthetic data), and nothing is enabled by an
environment variable. The only real artifacts it touches are the tracked frozen-model file and
the tracked baseline manifest, whose SHA-256 values it checks.

The dry run proves the driver's plumbing and its gate rules (ordering, single-shot, exclusive
writes, no test access before G5/G7, no writes outside outputs/phase3/). It says nothing about
scientific results.
"""

import ast
import dataclasses
import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_phase3 as drv
from test_phase3_population import make_panel

from ml.temporal_config import model_d_features
from phase3 import (
    BOOTSTRAP_B,
    BOOTSTRAP_SEED,
    FROZEN_MODEL_RELPATH,
    FROZEN_MODEL_SHA256,
    PROTOCOL_RELPATH,
    PROTOCOL_SHA256,
)
from phase3 import population as pop

# ---------------------------------------------------------------------------------------
# Protected artifacts (real tracked files; hashes only)
# ---------------------------------------------------------------------------------------


def test_the_frozen_model_hash_constant_matches_the_tracked_artifact():
    assert pop.sha256_file(ROOT / FROZEN_MODEL_RELPATH) == FROZEN_MODEL_SHA256


BASELINE_MANIFEST_SHA256 = "d4d9447c538416e354e8e1a7006318383aadf5521ac7c59470147186d97b1255"
PAPER_PDF_RELPATH = "paper/AeroGuard_Research_Paper.pdf"
HISTORICAL_PDF_RELPATH = "paper/archive/AeroGuard_Research_Paper_baseline_v0.3.pdf"
PAPER_PDF_MANIFEST_RELPATH = "baselines/paper_pdf_v1.1.0.sha256"


def _manifest_digests(relpath):
    out = {}
    for line in (ROOT / relpath).read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            digest, _, rel = line.strip().partition("  ")
            out[rel.strip().lstrip("*")] = digest
    return out


def test_all_79_baseline_hashes_pass():
    """Every digest in the frozen v0.3 manifest is verified against real bytes.

    Commit 30e7732 rebuilt the paper PDF (see baselines/README.md). The frozen manifest is not
    regenerated: its own hash is pinned, the other 78 files are checked in place, and the PDF's
    historical digest is checked against the byte-identical copy recovered from Git, kept at
    HISTORICAL_PDF_RELPATH. The current PDF is checked against its own digest in
    baselines/paper_pdf_v1.1.0.sha256. Any other mismatch fails."""
    assert pop.sha256_file(ROOT / "baselines/v0.3.sha256") == BASELINE_MANIFEST_SHA256
    frozen = _manifest_digests("baselines/v0.3.sha256")
    assert len(frozen) == 79
    result = pop.verify_baseline_manifest(ROOT)
    assert result["n_ok"] == 78 and result["failures"] == [PAPER_PDF_RELPATH]
    assert pop.sha256_file(ROOT / HISTORICAL_PDF_RELPATH) == frozen[PAPER_PDF_RELPATH]
    current = _manifest_digests(PAPER_PDF_MANIFEST_RELPATH)
    assert current == {HISTORICAL_PDF_RELPATH: frozen[PAPER_PDF_RELPATH], PAPER_PDF_RELPATH: current[PAPER_PDF_RELPATH]}
    assert pop.sha256_file(ROOT / PAPER_PDF_RELPATH) == current[PAPER_PDF_RELPATH] != frozen[PAPER_PDF_RELPATH]


def test_the_protocol_hash_constant_matches_the_locked_file():
    path = ROOT / PROTOCOL_RELPATH
    if not path.is_file():
        pytest.skip("experiments/phase3/PROTOCOL.md is not present in this tree (it is untracked at this commit)")
    assert pop.sha256_file(path) == PROTOCOL_SHA256


# ---------------------------------------------------------------------------------------
# Synthetic execution tree
# ---------------------------------------------------------------------------------------

TRAIN_KINDS = ["normal"] * 5 + ["pos"] * 3 + ["neg"] * 2 + ["double", "mixed"]
VAL_KINDS = ["normal"] * 3 + ["pos", "pos", "neg", "double", "mixed"]
TEST_KINDS = ["normal"] * 3 + ["pos", "pos", "neg", "neg", "double", "mixed"]


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _eligible_by_position(df):
    """Independent of ml.temporal_features.usable_mask_for_window: rows 100 .. n-501 of each trajectory."""
    pos = df.groupby("trajectory_id").cumcount().to_numpy()
    n = df.groupby("trajectory_id")["time"].transform("size").to_numpy()
    return (pos >= 100) & (pos < n - 500)


def _independent_counts(panels):
    c = {}
    for s, df in panels.items():
        elig = _eligible_by_position(df)
        c[f"trajectories_{s}"] = int(df["trajectory_id"].nunique())
        c[f"panel_rows_{s}"] = int(len(df))
        c[f"usable_rows_{s}"] = int(elig.sum())
    te = panels["test"]
    elig = _eligible_by_position(te)
    lab = te["future_stall_5s"].to_numpy()
    c["test_trajectories_with_usable_rows"] = int(te.loc[elig, "trajectory_id"].nunique())
    c["test_positive_rows"] = int((elig & (lab == 1.0)).sum())
    c["test_negative_rows"] = int((elig & (lab == 0.0)).sum())
    c["test_trajectories_with_any_unsafe_run"] = int(te.loc[te["is_unsafe"], "trajectory_id"].nunique())
    first = later = trajs = 0
    for _, g in te.loc[elig].groupby("trajectory_id"):
        u = g["is_unsafe"].to_numpy().astype(int)
        starts = int((np.diff(np.concatenate([[0], u])) == 1).sum())
        if starts:
            trajs += 1
            first += 1
            later += starts - 1
    c.update({"test_events": first + later, "test_first_events": first, "test_later_events": later, "test_trajectories_with_events": trajs})
    c["dataset_rows"] = sum(c[f"panel_rows_{s}"] for s in panels)
    c["dataset_trajectories"] = sum(c[f"trajectories_{s}"] for s in panels)
    return c


def build_tree(root, train_kinds=TRAIN_KINDS, val_kinds=VAL_KINDS, test_kinds=TEST_KINDS):
    root = Path(root)
    panels = {"train": make_panel("tr", train_kinds, seed=31), "val": make_panel("va", val_kinds, seed=32), "test": make_panel("te", test_kinds, seed=33)}
    for d in ("data/ml_temporal_v03", "data/processed", "data/splits", "experiments/phase3", "outputs/ml_v03/models", "outputs/ml_v03/metrics",
              "baselines", "item26/audit_out/gen_diag", "item26/audit_out/score"):
        (root / d).mkdir(parents=True, exist_ok=True)
    for s, df in panels.items():
        df.to_parquet(root / "data" / "ml_temporal_v03" / f"temporal_{s}.parquet", index=False)
    (root / "data" / "processed" / "processed_dataset_v3.parquet").write_bytes(b"synthetic placeholder, not a dataset")
    pd.DataFrame([(t, s) for s, df in panels.items() for t in df["trajectory_id"].unique()], columns=["trajectory_id", "split"]).to_csv(
        root / "data" / "splits" / "split_manifest_v3.csv", index=False)
    (root / PROTOCOL_RELPATH).write_text("synthetic stand-in for the locked protocol\n")
    # stand-in for the frozen model: a small forest on the real feature NAMES, trained on synthetic rows
    feats = list(model_d_features(1.0))
    tr = panels["train"].loc[_eligible_by_position(panels["train"])]
    standin = RandomForestClassifier(n_estimators=25, max_depth=6, random_state=0).fit(tr[feats], tr["future_stall_5s"].astype(int))
    joblib.dump(standin, root / FROZEN_MODEL_RELPATH)
    (root / "outputs/ml_v03/metrics/primary_model_metrics.json").write_text(json.dumps({"threshold": 0.5, "feature_columns": feats}))
    te = panels["test"]
    per_traj = te.loc[_eligible_by_position(te)].groupby("trajectory_id").size()
    (root / "outputs/ml_v03/metrics/false_alarm_analysis.json").write_text(json.dumps({"total_test_trajectory_seconds": float((per_traj - 1).sum() * 0.01)}))
    (root / "baselines" / "README.md").write_text("stand-in\n")
    (root / "baselines" / "v0.3.sha256").write_text(f"{_sha(root / 'baselines' / 'README.md')}  baselines/README.md\n")
    elig_te = te.loc[_eligible_by_position(te)]
    steps = elig_te.groupby("trajectory_id").cumcount().to_numpy() + 100
    pd.DataFrame({"trajectory_id": elig_te["trajectory_id"].to_numpy(), "step": steps}).to_parquet(root / "item26/audit_out/score/row_keys.parquet", index=False)
    np.save(root / "item26/audit_out/score/labels.npy", elig_te["future_stall_5s"].to_numpy().astype(int))
    counts = _independent_counts(panels)
    (root / "item26/audit_out/gen_diag/gate_A.json").write_text(json.dumps({"all_gate_A_pass": True, "processed_rows": counts["dataset_rows"],
                                                                           "processed_trajectories": counts["dataset_trajectories"],
                                                                           "metadata_max_relative_difference": 0.0}))
    (root / "item26/audit_out/gate_B.json").write_text(json.dumps({"all_gate_B_pass": True, "usable_test": counts["usable_rows_test"]}))
    data_hashes = {rel: _sha(root / "data" / rel) for rel in ("processed/processed_dataset_v3.parquet", "ml_temporal_v03/temporal_train.parquet",
                                                              "ml_temporal_v03/temporal_val.parquet", "ml_temporal_v03/temporal_test.parquet")}
    cfg = drv.RunConfig(root=root, item26_dir=root / "item26", git_commit="synthetic-test", protocol_sha256=_sha(root / PROTOCOL_RELPATH),
                        frozen_model_sha256=_sha(root / FROZEN_MODEL_RELPATH), data_hashes=data_hashes, expected_counts=counts)
    return cfg, panels, counts


def snapshot(root, skip_prefix="outputs/phase3"):
    snap = {}
    for base, _dirs, files in os.walk(root):
        for f in files:
            p = Path(base) / f
            rel = p.relative_to(root).as_posix()
            if not rel.startswith(skip_prefix):
                snap[rel] = _sha(p)
    return snap


@pytest.fixture(scope="module")
def e2e(tmp_path_factory):
    root = tmp_path_factory.mktemp("tree")
    cfg, panels, counts = build_tree(root)
    before = snapshot(root)
    out = {"cfg": cfg, "counts": counts, "before": before, "panels": panels, "root": root}
    def spy_reads(gate, run=None):
        """Run one gate while recording every Parquet file pandas is asked to read."""
        calls, real = [], pd.read_parquet

        def spy(path, *a, **k):
            calls.append(str(path))
            return real(path, *a, **k)

        mp = pytest.MonkeyPatch()
        mp.setattr(pd, "read_parquet", spy)
        try:
            return drv.execute_gate(cfg, gate, gate, run), calls
        finally:
            mp.undo()

    (status, payload, run_dir), out["g4_reads"] = spy_reads("G4")
    out["G4"], out["run_dir"] = (status, payload), run_dir
    out["G5"] = drv.execute_gate(cfg, "G5", "G5", run_dir)[:2]
    (st6, pay6, _), out["g6_reads"] = spy_reads("G6", run_dir)
    out["G6"] = (st6, pay6)
    out["G7"] = drv.execute_gate(cfg, "G7", "G7", run_dir)[:2]
    out["G8"] = drv.execute_gate(cfg, "G8", "G8", run_dir)[:2]
    out["after"] = snapshot(root)
    return out


def _read(e2e, name):
    return json.loads((e2e["run_dir"] / name).read_text())


# ---------------------------------------------------------------------------------------
# End-to-end dry run (synthetic)
# ---------------------------------------------------------------------------------------

def test_all_five_gates_pass_in_order_on_synthetic_data(e2e):
    for g in ("G4", "G5", "G6", "G7", "G8"):
        assert e2e[g][0] == "PASS", (g, e2e[g][1])
        assert (e2e["run_dir"] / f"gate_{g}.json").is_file()


def test_nothing_outside_the_phase3_output_directory_changed(e2e):
    assert e2e["before"] == e2e["after"]  # data, protocol, frozen stand-in, metrics, manifests: byte-identical
    run = e2e["run_dir"]
    assert run.parent == e2e["root"] / "outputs" / "phase3" and run.name.startswith("run_")
    assert {p.name for p in (e2e["root"] / "outputs").iterdir()} == {"ml_v03", "phase3"}


def test_g4_records_the_lock_provenance_and_the_q3_decision(e2e):
    lock, prov = _read(e2e, "protocol_lock.json"), _read(e2e, "data_provenance.json")
    assert lock["protocol"]["sha256"] == e2e["cfg"].protocol_sha256 and lock["seeds"] == {"forest_random_state": 20260817, "bootstrap_seed": 20261013, "bootstrap_B": 1000}
    assert lock["git_commit_of_execution_tree"] == "synthetic-test" and any(x.startswith("numpy==") for x in lock["environment"]["pip_freeze"])
    assert all(f["ok"] for f in prov["data_files"]) and "Not independent replication" in prov["banner"]
    q = _read(e2e, "negative_alpha_train.json")
    assert q["split"] == "train" and q["q3_negative_only_positive_rows"] > 0 and q["run_two_sided"] is True
    assert e2e["G4"][1]["run_two_sided"] is True


def test_g5_reconciles_every_count_against_independently_computed_values(e2e):
    pop_json = _read(e2e, "population.json")
    assert pop_json["problems"] == [] and pop_json["count_mismatches"] == []
    assert pop_json["observed_counts"] == e2e["counts"]
    assert pop_json["item26_cross_check"]["keys_equal"] and pop_json["item26_cross_check"]["labels_equal"]
    assert pop_json["eligible_span_matches_stored"] and pop_json["split_manifest_matches"]
    t = pop_json["eligible_time_test"]
    assert t["rows_times_dt_seconds"] - t["span_seconds"] == pytest.approx(t["n_trajectories"] * 0.01)


def test_g4_and_g6_read_only_the_train_and_validation_panels(e2e):
    assert e2e["g4_reads"] and all("temporal_train" in c for c in e2e["g4_reads"]), e2e["g4_reads"]
    assert e2e["g6_reads"] and all(("temporal_train" in c or "temporal_val" in c) for c in e2e["g6_reads"]), e2e["g6_reads"]
    assert not [c for c in e2e["g4_reads"] + e2e["g6_reads"] if "temporal_test" in c or "processed_dataset" in c]


def test_g6_saved_separate_artifacts_and_left_the_frozen_model_alone(e2e):
    run = e2e["run_dir"]
    for name in ("aoa_rule.json", "model_a_config.json", "model_a_fit_record.json", "feature_manifest.json", "instantaneous_model_a.joblib",
                 "aoa_two_sided_rule.json", "negative_alpha_q4.json"):
        assert (run / name).is_file(), name
    rule, cfgm, fit = _read(e2e, "aoa_rule.json"), _read(e2e, "model_a_config.json"), _read(e2e, "model_a_fit_record.json")
    assert rule["operator"] == "strict >" and len(rule["calibration_info"]["candidate_thresholds_rad"]) == 10
    assert cfgm["random_state"] == 20260817 and cfgm["preprocessing"] == "none" and cfgm["model_sha256"] == _sha(run / "instantaneous_model_a.joblib")
    assert fit["fit_seconds"] > 0 and _read(e2e, "feature_manifest.json")["features"] == ["V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin"]
    assert _read(e2e, "negative_alpha_q4.json")["influences_q3_decision"] is False
    assert not (e2e["root"] / FROZEN_MODEL_RELPATH).samefile(run / "instantaneous_model_a.joblib")


def test_g7_scores_all_methods_on_one_common_population_with_the_stored_thresholds(e2e):
    m = _read(e2e, "metrics_primary.json")
    assert list(m["methods"]) == ["aoa_signed", "instantaneous_model_a", "frozen_temporal", "aoa_two_sided"]
    n = e2e["counts"]["usable_rows_test"]
    assert m["population"]["n_rows"] == n and m["population"]["n_positive"] == e2e["counts"]["test_positive_rows"]
    assert m["thresholds"]["aoa_signed"] == _read(e2e, "aoa_rule.json")["threshold_rad"]
    assert m["thresholds"]["instantaneous_model_a"] == _read(e2e, "model_a_fit_record.json")["threshold"]
    assert m["thresholds"]["frozen_temporal"] == 0.5
    run = e2e["run_dir"]
    labels = np.load(run / "labels.npy")
    keys = np.load(run / "row_keys.npz")
    for name in m["methods"]:
        s = np.load(run / f"scores_{name}.npy")
        assert s.shape == (n,) and np.isfinite(s).all() and labels.shape == (n,)
        assert m["methods"][name]["operating_point"]["events"]["n_events"] == e2e["counts"]["test_events"]  # same events for every method
        assert m["methods"][name]["operating_point"]["operator"] == "strict >"
    assert keys["step"].shape == (n,) and len(set(zip(keys["trajectory_id"], keys["step"]))) == n


def test_g7_item30_is_a_decision_count_only(e2e):
    eq = _read(e2e, "equivalence_check.json")
    assert set(eq["by_split"]) == {"train", "val", "test"}
    for r in eq["by_split"].values():
        assert r["n_disagree"] == r["n_disagree_exactly_at_threshold"] + r["n_disagree_elsewhere"] and "pr_auc" not in r
    assert "not evaluated as a separate method" in eq["note"]
    assert "stall" not in " ".join(_read(e2e, "metrics_primary.json")["methods"])


def test_g7_is_single_shot_and_gates_cannot_be_rerun_or_skipped(e2e):
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(e2e["cfg"], "G7", "G7", e2e["run_dir"])
    assert (e2e["run_dir"] / "g7_started.lock").is_file()
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(e2e["cfg"], "G8", "G8", e2e["run_dir"])  # G8 has already run in this directory


def test_g8_uses_the_approved_bootstrap_and_writes_a_non_promotional_report(e2e):
    boot = _read(e2e, "bootstrap.json")
    assert boot["config"]["B"] == BOOTSTRAP_B == 1000 and boot["config"]["seed"] == BOOTSTRAP_SEED == 20261013 and boot["config"]["unit"] == "trajectory"
    primary = boot["paired_differences"]["frozen_temporal - instantaneous_model_a | pr_auc"]
    assert set(primary) >= {"point", "ci_lo", "ci_hi", "ci_includes_zero", "n_undefined_replicates"}
    report = (e2e["run_dir"] / "REPORT.md").read_text()
    assert "Not independent replication" in report and "no claim of practical superiority" in report
    assert "NOT MATCHED across methods; do not rank" in report and "mathematically equivalent to item 28" in report.lower()
    for banned in ("outperform", "proves", "better than", "is superior"):
        assert banned not in report.lower()
    audit = _read(e2e, "audit.json")
    assert audit["frozen_model_unchanged"] is True and audit["baseline_manifest"]["n_failed"] == 0 and all(f["ok"] for f in audit["data_files"])
    assert set(audit["run_files"]) >= {"bootstrap.json", "REPORT.md", "metrics_primary.json", "gate_G7.json"}


# ---------------------------------------------------------------------------------------
# Gate discipline (each on its own small tree)
# ---------------------------------------------------------------------------------------

@pytest.fixture()
def small_tree(tmp_path):
    cfg, _, _ = build_tree(tmp_path, ["normal", "normal", "pos", "neg"], ["normal", "pos", "neg"], ["normal", "pos", "neg"])
    return cfg


def test_a_gate_refuses_to_run_without_its_own_confirmation_and_writes_nothing(small_tree):
    for bad in (None, "", "G5", "g4", "G4 "):
        with pytest.raises(pop.GateViolation):
            drv.execute_gate(small_tree, "G4", bad)
    assert not (small_tree.root / "outputs" / "phase3").exists()


def test_gates_cannot_run_out_of_order_or_without_a_run_directory(small_tree):
    status, _, run = drv.execute_gate(small_tree, "G4", "G4")
    assert status == "PASS"
    for gate in ("G6", "G7", "G8"):
        with pytest.raises(pop.GateViolation):
            drv.execute_gate(small_tree, gate, gate, run)
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(small_tree, "G5", "G5", None)
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(small_tree, "G5", "G5", small_tree.root / "elsewhere")  # a run directory outside outputs/phase3/


def test_the_driver_refuses_to_run_inside_a_git_checkout(small_tree):
    (small_tree.root / ".git").mkdir()
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(small_tree, "G4", "G4")
    assert not (small_tree.root / "outputs" / "phase3").exists()


def test_a_changed_protocol_or_data_file_makes_g4_fail_and_blocks_everything_after(small_tree):
    bad_protocol = dataclasses.replace(small_tree, protocol_sha256="0" * 64)
    status, payload, run = drv.execute_gate(bad_protocol, "G4", "G4")
    assert status == "FAIL" and "protocol hash differs" in payload["error"]
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(small_tree, "G5", "G5", run)
    first = next(iter(small_tree.data_hashes))
    bad_data = dataclasses.replace(small_tree, data_hashes={**small_tree.data_hashes, first: "f" * 64})
    status, payload, _ = drv.execute_gate(bad_data, "G4", "G4")
    assert status == "FAIL" and "hash differs" in payload["error"]


def test_a_changed_frozen_model_makes_the_gate_fail(small_tree):
    bad = dataclasses.replace(small_tree, frozen_model_sha256="1" * 64)
    status, payload, _ = drv.execute_gate(bad, "G4", "G4")
    assert status == "FAIL" and "frozen model hash differs" in payload["error"]


def test_a_count_mismatch_at_g5_fails_the_gate_and_blocks_g6(small_tree):
    status, _, run = drv.execute_gate(small_tree, "G4", "G4")
    assert status == "PASS"
    wrong = dict(small_tree.counts)
    wrong["usable_rows_test"] += 1
    status, payload, _ = drv.execute_gate(dataclasses.replace(small_tree, expected_counts=wrong), "G5", "G5", run)
    assert status == "FAIL" and "usable_rows_test" in payload["error"]
    with pytest.raises(pop.GateViolation):
        drv.execute_gate(small_tree, "G6", "G6", run)


def test_outputs_are_created_exclusively_and_only_below_the_phase3_directory(small_tree):
    run = drv.new_run_dir(small_tree)
    path = drv.write_json(small_tree, run, "x.json", {"a": 1})
    assert json.loads(path.read_text()) == {"a": 1}
    with pytest.raises(FileExistsError):
        drv.write_json(small_tree, run, "x.json", {"a": 2})
    drv.write_npy(small_tree, run, "a.npy", np.zeros(2))
    with pytest.raises(FileExistsError):
        drv.write_npy(small_tree, run, "a.npy", np.zeros(2))
    for bad in ("../x.json", "../../ml_v03/x.json"):
        with pytest.raises(pop.GateViolation):
            drv.write_json(small_tree, run, bad, {})


def test_g4_skips_the_two_sided_analysis_when_q3_is_zero(tmp_path):
    cfg, _, _ = build_tree(tmp_path, ["normal", "normal", "pos", "double"], ["normal", "pos"], ["normal", "pos"])
    status, payload, run = drv.execute_gate(cfg, "G4", "G4")
    assert status == "PASS" and payload["run_two_sided"] is False and payload["q3"] == 0


def test_the_parser_requires_a_confirmation_flag_and_a_run_directory_after_g4():
    parser = drv.build_parser()
    for gate in ("g4", "g5", "g6", "g7", "g8"):
        with pytest.raises(SystemExit):
            parser.parse_args([gate])
    for gate in ("g5", "g6", "g7", "g8"):
        with pytest.raises(SystemExit):
            parser.parse_args([gate, "--confirm-gate", gate.upper(), "--item26-dir", "x"] if gate == "g5" else [gate, "--confirm-gate", gate.upper()])
    ns = parser.parse_args(["g6", "--confirm-gate", "G6", "--run-dir", "r"])
    assert ns.confirm_gate == "G6" and ns.run_dir == "r"


def _names_and_strings(fn):
    tree = ast.parse(inspect.getsource(fn))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return names, strings


def test_gates_g4_and_g6_cannot_even_name_the_test_split_in_their_code():
    for fn in (drv.gate_g4, drv.gate_g6):
        names, strings = _names_and_strings(fn)
        assert "test" not in strings and "SPLITS" not in names, fn.__name__
    _, g6_strings = _names_and_strings(drv.gate_g6)
    assert "train" in g6_strings and "val" in g6_strings
    assert pop.SPLITS == ("train", "val", "test")


def test_every_file_open_in_the_driver_is_an_exclusive_create():
    """No read-open, no overwrite-open: reads go through Path.read_text / pandas / numpy / joblib,
    and every open() call creates a new file exclusively ('x' / 'xb')."""
    tree = ast.parse(inspect.getsource(drv))
    modes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "mode"), None)
            modes.append(mode.value if isinstance(mode, ast.Constant) else None)
    assert modes and set(modes) <= {"x", "xb"}, modes
