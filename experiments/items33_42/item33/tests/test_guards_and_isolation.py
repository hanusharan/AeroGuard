"""Protocol lock, output-path protection, exclusive writes and the test-isolation guard (PROTOCOL.md sections 11, 13, 14)."""

import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

import item33
from conftest import ResearchDataAccess
from item33 import FROZEN_MODEL_RELPATH, LOCK_RELPATH, OUTPUT_ROOT_RELPATH, PROTOCOL_RELPATH, PROTOCOL_SHA256
from item33 import guards


def _tree(tmp_path, repo_root):
    """A throwaway tree holding copies of the two lock documents only."""
    for rel in (PROTOCOL_RELPATH, LOCK_RELPATH):
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / rel, dst)
    return tmp_path


# --- protocol lock ---------------------------------------------------------------------------

def test_the_tracked_protocol_still_matches_the_locked_hash(repo_root):
    assert guards.verify_protocol_lock(repo_root) == PROTOCOL_SHA256


def test_the_lock_record_agrees_with_the_package_constant(repo_root):
    lock = json.loads((repo_root / LOCK_RELPATH).read_text())
    assert lock["protocol_sha256"] == PROTOCOL_SHA256
    assert lock["authorizations_granted_with_this_lock"]["G33-3"]["granted"] is True
    assert "G33-1 (data-dependent checks; panel reads; frozen-model load)" in lock["authorizations_not_granted"]


def test_a_changed_protocol_fails_the_lock(tmp_path, repo_root):
    tree = _tree(tmp_path, repo_root)
    (tree / PROTOCOL_RELPATH).write_text((tree / PROTOCOL_RELPATH).read_text() + "\nedited\n")
    with pytest.raises(guards.DataIntegrityError):
        guards.verify_protocol_lock(tree)


def test_a_lock_record_with_another_hash_fails(tmp_path, repo_root):
    tree = _tree(tmp_path, repo_root)
    lock = json.loads((tree / LOCK_RELPATH).read_text())
    lock["protocol_sha256"] = "0" * 64
    (tree / LOCK_RELPATH).write_text(json.dumps(lock))
    with pytest.raises(guards.DataIntegrityError):
        guards.verify_protocol_lock(tree)


def test_the_protocol_text_agrees_with_the_package_constants(repo_root):
    text = (repo_root / PROTOCOL_RELPATH).read_text()
    for s in item33.SEEDS:
        assert str(s) in text
    assert item33.MASK_SEEDS == tuple(range(20261201, 20261206))         # the protocol states the range 20261201-20261205
    assert "20261201" in text and "20261205" in text
    assert str(item33.BOOTSTRAP_SEED) in text and "B = 1000" in text
    assert str(item33.FROZEN_THRESHOLD) in text
    for h in item33.DATA_FILE_SHA256.values():
        assert h in text
    assert item33.PRIMARY_SEED == item33.SEEDS[0] == 20260817
    assert item33.BONFERRONI_INTERVAL_PCT == (1.25, 98.75)


def test_constants_match_the_existing_phase3_records():
    import phase3
    assert item33.FROZEN_MODEL_SHA256 == phase3.FROZEN_MODEL_SHA256
    assert item33.DATA_FILE_SHA256 == phase3.DATA_FILE_SHA256
    assert item33.PHASE3_PROTOCOL_SHA256 == phase3.PROTOCOL_SHA256
    assert item33.BOOTSTRAP_B == phase3.BOOTSTRAP_B and item33.BOOTSTRAP_SEED == phase3.BOOTSTRAP_SEED
    assert item33.BOOTSTRAP_INTERVAL_PCT == phase3.BOOTSTRAP_INTERVAL_PCT


# --- output paths -------------------------------------------------------------------------------

def test_outputs_are_allowed_only_inside_a_per_run_directory(tmp_path):
    ok = tmp_path / OUTPUT_ROOT_RELPATH / "run_20260101T000000Z" / "x.json"
    assert guards.assert_output_path(ok, tmp_path) == ok.resolve()


@pytest.mark.parametrize("rel", [
    "outputs/ml_v03/metrics/x.json", "outputs/phase3/run_1/x.json", FROZEN_MODEL_RELPATH, "outputs/ml_v03/models/anything.joblib",
    "experiments/phase3/PROTOCOL.md", "data/processed/x.parquet", "paper/x.md", "baselines/v0.3.sha256", "ml/models.py", "phase3/analysis.py",
    "outputs/items33_42/item33/x.json",                         # not inside a run_ directory
    "outputs/items33_42/item33/notrun/x.json",
    "outputs/items33_42/item33/run_1/../../../ml_v03/x.json",   # escape
    "elsewhere/x.json",
])
def test_protected_and_unrelated_locations_are_refused(tmp_path, rel):
    with pytest.raises(guards.GateViolation):
        guards.assert_output_path(tmp_path / rel, tmp_path)


def test_the_frozen_model_path_can_never_be_written(tmp_path):
    with pytest.raises(guards.GateViolation):
        guards.write_text_exclusive(tmp_path / FROZEN_MODEL_RELPATH, "x", tmp_path)


def test_exclusive_write_never_overwrites(tmp_path):
    p = tmp_path / OUTPUT_ROOT_RELPATH / "run_1" / "a.json"
    guards.write_json_exclusive(p, {"a": 1}, tmp_path)
    with pytest.raises(FileExistsError):
        guards.write_json_exclusive(p, {"a": 2}, tmp_path)
    assert json.loads(p.read_text()) == {"a": 1}


def test_json_output_is_deterministic_and_never_contains_nan(tmp_path):
    obj = {"b": float("nan"), "a": np.float64(0.5), "c": np.arange(3), "d": float("inf"), "e": (1, 2)}
    p = guards.write_json_exclusive(tmp_path / OUTPUT_ROOT_RELPATH / "run_1" / "o.json", obj, tmp_path)
    text = p.read_text()
    assert "NaN" not in text and "Infinity" not in text
    assert json.loads(text) == {"a": 0.5, "b": None, "c": [0, 1, 2], "d": None, "e": [1, 2]}
    assert list(json.loads(text)) == sorted(json.loads(text))


def test_a_git_checkout_is_refused_as_an_execution_tree(tmp_path):
    guards.assert_no_git(tmp_path)
    (tmp_path / ".git").mkdir()
    with pytest.raises(guards.GateViolation):
        guards.assert_no_git(tmp_path)


# --- the isolation guard itself ---------------------------------------------------------------------

def test_opening_the_frozen_model_path_raises(repo_root):
    with pytest.raises(ResearchDataAccess):
        open(repo_root / FROZEN_MODEL_RELPATH, "rb")


def test_joblib_load_of_the_frozen_model_raises(repo_root):
    with pytest.raises(ResearchDataAccess):
        joblib.load(repo_root / FROZEN_MODEL_RELPATH)


def test_read_parquet_of_the_research_panels_raises(repo_root):
    with pytest.raises(ResearchDataAccess):
        pd.read_parquet(repo_root / "data" / "ml_temporal_v03" / "temporal_test.parquet")
    with pytest.raises(ResearchDataAccess):
        pd.read_parquet("/anywhere/else/file.parquet")


def test_phase3_outputs_and_historical_metrics_cannot_be_opened(repo_root):
    with pytest.raises(ResearchDataAccess):
        open(repo_root / "outputs" / "ml_v03" / "metrics" / "primary_model_metrics.json")
    with pytest.raises(ResearchDataAccess):
        np.load(repo_root / "outputs" / "phase3" / "run_x" / "scores.npy")


def test_scratch_research_directories_are_blocked_by_name():
    with pytest.raises(ResearchDataAccess):
        open("/tmp/some/item26x/aeroguard-eval/data/processed/x.csv")


def test_ordinary_temporary_files_remain_usable(tmp_path):
    p = tmp_path / "ok.txt"
    p.write_text("hello")
    assert p.read_text() == "hello"
