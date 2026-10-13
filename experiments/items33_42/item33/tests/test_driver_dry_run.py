"""Gate discipline and an end-to-end DRY RUN of every gate on synthetic data (PROTOCOL.md sections 11, 14, 17).

Everything runs in pytest's tmp_path with an injected reader (no file is read), a stand-in forest (no learning) and a
stand-in "frozen model" (never the real artifact; the autouse guard blocks the real one). A dry run is labelled in every
record. Passing these tests passes no gate of the real experiment.
"""

import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pytest

from item33 import FROZEN_MODEL_RELPATH, LOCK_RELPATH, OUTPUT_ROOT_RELPATH, PROTOCOL_RELPATH, SEEDS
from item33 import conditions as cond, driver, population as pop, register
from item33.guards import GateViolation
from synth import StubForest, StubFrozen, make_manifest, make_metadata, make_splits

B = 16


@pytest.fixture(scope="module")
def splits():
    return make_splits()


@pytest.fixture
def tree(tmp_path, repo_root):
    for rel in (PROTOCOL_RELPATH, LOCK_RELPATH):
        dst = tmp_path / "tree" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / rel, dst)
    return tmp_path / "tree"


def expected_counts(splits):
    t = {s: pop.summarize_population(df) for s, df in splits.items()}
    ev = pop.count_events(splits["test"], pop.usable_mask(splits["test"]))
    return driver.observed_counts(t, ev)


def make_deps(splits, builder=StubForest):
    def reader(path, columns):
        return splits[Path(path).stem.replace("temporal_", "")][list(columns)].copy()

    def loader(p):
        return StubFrozen() if "primary_model_D_1s" in str(p) else joblib.load(p)

    return driver.Deps(reader=reader, builder=builder, verify_hashes=lambda d, e: [{"path": k, "ok": True} for k in e],
                       schema_missing=lambda p, r: [], load_model=loader, metadata=lambda: make_metadata(splits),
                       split_manifest=lambda: make_manifest(splits), pip_freeze=lambda: ["stub==0"])


def cfg_for(tree, splits, **kw):
    return driver.RunConfig(root=tree, dry_run=True, bootstrap_B=B, expected_counts=expected_counts(splits), git_commit="synthetic", **kw)


def go(cfg, deps, gate, run_dir=None):
    return driver.execute_gate(cfg, gate, gate, run_dir, deps)


# --- gate discipline ------------------------------------------------------------------------------------------------------

def test_each_gate_needs_its_own_exact_confirmation_and_nothing_is_written_otherwise(tree, splits):
    cfg, deps = cfg_for(tree, splits), make_deps(splits)
    for given in (None, "", "G33-2", "g33-1", "G33-1 "):
        with pytest.raises(GateViolation):
            driver.execute_gate(cfg, "G33-1", given, None, deps)
    assert not (tree / "outputs").exists()


def test_gates_cannot_run_out_of_order(tree, splits):
    cfg, deps = cfg_for(tree, splits), make_deps(splits)
    status, _, rd = go(cfg, deps, "G33-1")
    assert status == "PASS"
    for later in ("G33-4a", "G33-4b", "G33-5a", "G33-6"):
        with pytest.raises(GateViolation):
            go(cfg, deps, later, rd)
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-2")                                                 # a non-first gate needs a run directory


def test_a_git_checkout_and_an_edited_protocol_are_refused(tree, splits):
    cfg, deps = cfg_for(tree, splits), make_deps(splits)
    (tree / ".git").mkdir()
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-1")
    (tree / ".git").rmdir()
    p = tree / PROTOCOL_RELPATH
    p.write_text(p.read_text() + "\nedit\n")
    with pytest.raises(Exception) as e:
        go(cfg, deps, "G33-1")
    assert "protocol hash differs" in str(e.value)
    assert not (tree / "outputs").exists()


def test_a_real_run_cannot_override_the_protocol_constants(tree):
    with pytest.raises(GateViolation):
        driver.RunConfig(root=tree, bootstrap_B=20)
    with pytest.raises(GateViolation):
        driver.RunConfig(root=tree, seeds=SEEDS[:2])
    with pytest.raises(GateViolation):
        driver.RunConfig(root=tree, expected_counts={"usable_rows_test": 1})
    assert driver.RunConfig(root=tree).bootstrap_B == 1000


def test_a_count_that_does_not_reconcile_is_recorded_as_a_failure_and_blocks_the_next_gate(tree, splits):
    cfg = driver.RunConfig(root=tree, dry_run=True, bootstrap_B=B, expected_counts={**expected_counts(splits), "usable_rows_test": 1})
    deps = make_deps(splits)
    status, payload, rd = go(cfg, deps, "G33-1")
    assert status == "FAIL" and "usable_rows_test" in payload["error"]
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-2", rd)


def test_the_run_directory_name_and_location_are_fixed(tree, splits):
    _, _, rd = go(cfg_for(tree, splits), make_deps(splits), "G33-1")
    assert rd.parent == (tree / OUTPUT_ROOT_RELPATH).resolve() and rd.name.startswith("run_")


# --- end-to-end dry run -------------------------------------------------------------------------------------------------------

@pytest.fixture
def dry_run(tree, splits):
    cfg, deps = cfg_for(tree, splits), make_deps(splits)
    out = {"cfg": cfg, "deps": deps, "tree": tree}
    st, payload, rd = go(cfg, deps, "G33-1"); assert st == "PASS", payload
    out["rd"] = rd
    st, payload, _ = go(cfg, deps, "G33-2", rd); assert st == "PASS", payload
    return out


def test_g33_1_records_the_population_provenance_and_structure(dry_run, splits):
    rd = dry_run["rd"]
    pop_rec = json.loads((rd / "population.json").read_text())
    assert pop_rec["count_mismatches"] == [] and pop_rec["n_rows"] == int(pop.usable_mask(splits["test"]).sum())
    prov = json.loads((rd / "data_provenance.json").read_text())
    assert "absent" in prov["original_dataset"] and "not shown to be byte-identical" in prov["original_dataset"]
    assert set(json.loads((rd / "masking_medians.json").read_text())["medians"]) == {"elevator", "throttle", "elevator_change_1s"}
    assert sum(json.loads((rd / "strata.json").read_text())["sizes"].values()) == pop_rec["n_trajectories"]
    assert json.loads((rd / "gate_G33-1.json").read_text())["dry_run"] is True


def test_g33_2_freezes_the_specification_before_any_fit(dry_run):
    rd = dry_run["rd"]
    fr = json.loads((rd / "freeze.json").read_text())
    assert fr["frozen_before_any_scoring"] is True and len(fr["specification_sha256"]) == 64
    assert fr["specification"]["seeds"] == list(SEEDS) and fr["specification"]["bootstrap"]["seed"] == 20261013
    assert not list(rd.glob("fit_record_*")) and not list(rd.glob("scores_*"))


def test_the_first_fit_runs_alone_and_the_remaining_fits_need_their_own_gate(dry_run):
    cfg, deps, rd = dry_run["cfg"], dry_run["deps"], dry_run["rd"]
    st, payload, _ = go(cfg, deps, "G33-4a", rd)
    assert st == "PASS" and payload["stopped_for_cost_reconfirmation"] is True
    assert [p.name for p in sorted(rd.glob("fit_record_*"))] == ["fit_record_C0_20260817.json"]
    assert not list(rd.glob("scores_*")) and not (rd / "gate_G33-4b.json").exists()
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-5a", rd)                                            # scoring is blocked until every fit exists
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-4a", rd)                                            # single-shot gate


def test_a_failed_fit_is_recorded_not_retried_and_blocks_scoring(tree, splits):
    cfg = cfg_for(tree, splits)
    calls = []
    def flaky(seed):
        calls.append(seed)
        if len(calls) == 7:
            raise RuntimeError("synthetic failure")
        return StubForest(seed)
    deps = make_deps(splits, builder=flaky)
    _, _, rd = go(cfg, deps, "G33-1"); go(cfg, deps, "G33-2", rd); go(cfg, deps, "G33-4a", rd)
    st, payload, _ = go(cfg, deps, "G33-4b", rd)
    assert st == "FAIL" and "failures.json" in payload["error"]
    assert len(calls) == 25                                                    # every (condition, seed) attempted exactly once
    fails = json.loads((rd / "failures.json").read_text())
    assert len(fails) == 1 and fails[0]["status"] == "FAILED" and "synthetic failure" in fails[0]["error"]
    assert len(list(rd.glob("fit_record_*"))) == 24
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-5a", rd)


def test_full_dry_run_of_every_gate(dry_run, splits):
    cfg, deps, rd, tree = dry_run["cfg"], dry_run["deps"], dry_run["rd"], dry_run["tree"]
    for gate in ("G33-4a", "G33-4b", "G33-5a", "G33-5b", "G33-6"):
        st, payload, _ = go(cfg, deps, gate, rd)
        assert st == "PASS", (gate, payload)
    assert len(list(rd.glob("fit_record_*"))) == len(list(rd.glob("threshold_*"))) == 25 == len(list(rd.glob("scores_[CX]*")))
    assert json.loads((rd / "failures.json").read_text()) == []
    # identical populations: one label vector, one key set
    n = int(pop.usable_mask(splits["test"]).sum())
    assert np.load(rd / "test_labels.npy").shape == (n,) and all(np.load(p).shape == (n,) for p in rd.glob("scores_[CX]*.npy"))
    # single-shot ledger: one marker per model and per masking variant
    assert len(list(rd.glob("test_scored_C*"))) + len(list(rd.glob("test_scored_X*"))) == 25
    assert len(list(rd.glob("masking_scores_*"))) == 33 and len(list(rd.glob("test_scored_M-*"))) == 33
    # the primary contrasts and the register
    pc = json.loads((rd / "paired_contrasts.json").read_text())["contrasts"]
    assert [c["register_id"] for c in pc if c["status"] == "primary"] == ["D1", "D2"]
    assert all("bootstrap_seed_mean_bonferroni" in c["summary"] for c in pc if c["status"] == "primary")
    assert all("bootstrap_seed_mean_bonferroni" not in c["summary"] for c in pc if c["status"] != "primary")
    assert {c["register_id"] for c in pc} == {"D1", "D2", "SEC-2", "SEC-3", "X-a", "X-b"}
    for c in pc:
        assert c["summary"]["bootstrap_seed_mean"]["note"].startswith("test-trajectory sampling")
        assert "ci_lo" not in c["summary"]["seed_estimates"]
        if c["status"] != "primary":
            assert "demonstrated" not in c["statement"]["text"]
    # bootstrap configuration as recorded (B is the dry-run override only)
    boot = json.loads((rd / "bootstrap.json").read_text())
    assert boot["config"]["seed"] == 20261013 and boot["config"]["B"] == B and boot["config"]["unit"] == "trajectory"
    # rows follow the schema
    rows = json.loads((rd / "metrics_primary.json").read_text())
    assert len(rows) == 25 * 2 and all(register.validate_row(r) for r in rows)
    assert all(r["analysis_family"] == "retrained_ablation" for r in rows)
    # reproduction diagnostic ran against the stand-in frozen scores, masking stayed in its own family
    rep = json.loads((rd / "reproduction_check.json").read_text())
    assert rep["level"] in ("R0", "R1", "R2")
    mk = json.loads((rd / "masking_results.json").read_text())
    assert mk["analysis_family"] == "frozen_model_masking" and len(mk["rows"]) == 33
    assert sum("bootstrap_ci_lo" in r for r in mk["rows"]) == 9              # intervals for MS1 and the first MS2/MS3 draw per set
    # regime sensitivity, matched operating point, seed panels
    assert set(json.loads((rd / "regime_sensitivity.json").read_text())) == {"D1", "D2"}
    mop = json.loads((rd / "matched_operating_point.json").read_text())["rows"]
    assert len(mop) == 25 and all(r["achieved_fpr"] <= r["target_fpr"] + 1e-12 for r in mop)
    assert set(json.loads((rd / "seed_panel.json").read_text())) == set(cond.CONDITION_ORDER)
    # event files exist for every model and contain no per-hour false-alarm rate (Items 37/38)
    ev = json.loads((rd / "event_level_C0_20260817.json").read_text())
    assert "own_threshold" in ev and "matched_operating_point" in ev and "false_alarm" not in json.dumps(ev)
    # the report is generated from the records and says it is a dry run
    text = (rd / "REPORT.md").read_text()
    assert "DRY RUN ON SYNTHETIC DATA" in text and "Frozen-model input masking" in text
    # nothing was written outside the run directory (apart from the two copied lock documents)
    written = {p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file()}
    assert all(w.startswith(OUTPUT_ROOT_RELPATH + "/run_") or w in (PROTOCOL_RELPATH, LOCK_RELPATH) for w in written)
    assert not (tree / "outputs" / "ml_v03").exists() and not (tree / FROZEN_MODEL_RELPATH).exists()
    # a completed gate cannot run again, and a second scoring pass is refused by the ledger as well
    for gate in ("G33-5a", "G33-5b", "G33-6"):
        with pytest.raises(GateViolation):
            go(cfg, deps, gate, rd)


def test_masking_scoring_can_be_declined_without_affecting_the_rest(dry_run):
    cfg, deps, rd = dry_run["cfg"], dry_run["deps"], dry_run["rd"]
    for gate in ("G33-4a", "G33-4b", "G33-5a", "G33-6"):
        st, payload, _ = go(cfg, deps, gate, rd)
        assert st == "PASS", (gate, payload)
    assert not (rd / "masking_results.json").exists() and not list(rd.glob("masking_scores_*"))
    assert not (rd / "reproduction_check.json").exists()                     # missing artifact (no frozen scores), not a failure
    assert "Not run." in (rd / "REPORT.md").read_text() and "Not computed" in (rd / "REPORT.md").read_text()


# --- the Phase 3 anchor branch (fake Phase 3 directory built in tmp_path) ----------------------------------------------------------

def _fake_phase3(tmp_path, splits):
    p3 = tmp_path / "phase3_fake"; p3.mkdir()
    sub = splits["test"].loc[pop.usable_mask(splits["test"])].reset_index(drop=True)
    keys = pop.row_keys(sub)
    np.savez(p3 / "row_keys.npz", trajectory_id=np.asarray(keys.traj).astype(str), step=keys.step)
    np.save(p3 / "scores_frozen_temporal.npy", StubFrozen().predict_proba(sub[list(cond.C0_FEATURES)])[:, 1])
    return p3


def test_the_phase3_anchor_is_hash_checked_copied_and_used_for_the_reproduction_diagnostic(tree, splits, tmp_path):
    p3 = _fake_phase3(tmp_path, splits)
    from item33.guards import sha256_file
    cfg = driver.RunConfig(root=tree, dry_run=True, bootstrap_B=B, expected_counts=expected_counts(splits), phase3_dir=p3,
                           phase3_frozen_scores_sha256=sha256_file(p3 / "scores_frozen_temporal.npy"))
    deps = make_deps(splits)
    _, _, rd = go(cfg, deps, "G33-1")
    assert json.loads((rd / "data_provenance.json").read_text())["phase3_row_keys"] == "equal"
    for gate in ("G33-2", "G33-4a", "G33-4b", "G33-5a", "G33-6"):
        st, payload, _ = go(cfg, deps, gate, rd)
        assert st == "PASS", (gate, payload)
    assert (rd / "scores_FROZEN_phase3.npy").is_file()
    assert json.loads((rd / "reproduction_check.json").read_text())["anchor"] == "scores_FROZEN_phase3.npy"


def test_a_phase3_anchor_with_the_wrong_hash_fails_the_scoring_gate(tree, splits, tmp_path):
    p3 = _fake_phase3(tmp_path, splits)
    cfg = driver.RunConfig(root=tree, dry_run=True, bootstrap_B=B, expected_counts=expected_counts(splits), phase3_dir=p3,
                           phase3_frozen_scores_sha256="0" * 64)
    deps = make_deps(splits)
    _, _, rd = go(cfg, deps, "G33-1")
    for gate in ("G33-2", "G33-4a", "G33-4b"):
        assert go(cfg, deps, gate, rd)[0] == "PASS"
    st, payload, _ = go(cfg, deps, "G33-5a", rd)
    assert st == "FAIL" and "hash differs" in payload["error"]
    with pytest.raises(GateViolation):
        go(cfg, deps, "G33-6", rd)


def test_phase3_row_keys_that_differ_from_the_panel_stop_g33_1(tree, splits, tmp_path):
    p3 = _fake_phase3(tmp_path, splits)
    z = np.load(p3 / "row_keys.npz"); traj, step = z["trajectory_id"].copy(), z["step"].copy()
    (p3 / "row_keys.npz").unlink()
    np.savez(p3 / "row_keys.npz", trajectory_id=traj[:-1], step=step[:-1])
    cfg = driver.RunConfig(root=tree, dry_run=True, bootstrap_B=B, expected_counts=expected_counts(splits), phase3_dir=p3)
    st, payload, _ = go(cfg, make_deps(splits), "G33-1")
    assert st == "FAIL" and ("differ" in payload["error"] or "different number of rows" in payload["error"])
