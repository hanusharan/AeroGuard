"""Item 33 test configuration.

SYNTHETIC ONLY. Every fixture is generated in memory (or in pytest's tmp_path) with fixed seeds. This file installs an
autouse guard that makes any attempt to read the research panels, the frozen model, the Phase 3 outputs or any
``.parquet`` file raise ``ResearchDataAccess``, so a test cannot touch research data even by mistake. Tests that
need the tracked protocol or lock record read only those two documents.

Run only this directory:  python -B -m pytest -p no:cacheprovider experiments/items33_42/item33/tests
The historical test suite is never run from here.
"""

import builtins
import io
import os
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
ITEM_DIR = TESTS_DIR.parent
REPO = ITEM_DIR.parents[2]
for p in (str(TESTS_DIR), str(ITEM_DIR / "src"), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

FORBIDDEN_DIRS = [
    REPO / "data" / "processed", REPO / "data" / "ml_temporal_v03", REPO / "data" / "ml_temporal", REPO / "data" / "ml",
    REPO / "data" / "raw", REPO / "outputs" / "ml_v03", REPO / "outputs" / "phase3", REPO / "outputs" / "analysis_v11",
    REPO / "outputs" / "ml_temporal", REPO / "outputs" / "ml_baseline",
]
FORBIDDEN_FILES = [REPO / "outputs" / "ml_v03" / "models" / "primary_model_D_1s.joblib"]
FORBIDDEN_FRAGMENTS = ("item26x", "phase3-final", "ml_temporal_v03", "processed_dataset")


class ResearchDataAccess(Exception):
    """A test tried to read research data, the frozen model or a parquet file."""


def is_blocked(path) -> bool:
    try:
        raw = os.fspath(path)
    except TypeError:
        return False
    if isinstance(raw, bytes):
        raw = raw.decode(errors="ignore")
    resolved = Path(raw).resolve()
    if resolved.suffix == ".parquet":
        return True
    if resolved in FORBIDDEN_FILES or any(d == resolved or d in resolved.parents for d in FORBIDDEN_DIRS):
        return True
    text = str(resolved)
    return any(f in text for f in FORBIDDEN_FRAGMENTS)


def _wrap(real, name):
    def guarded(file, *args, **kwargs):
        if not isinstance(file, int) and is_blocked(file):
            raise ResearchDataAccess(f"test attempted {name}({file!s})")
        return real(file, *args, **kwargs)
    guarded.__name__ = getattr(real, "__name__", name)
    return guarded


@pytest.fixture(autouse=True)
def forbid_research_data(monkeypatch):
    import joblib
    import numpy as np
    import pandas as pd

    monkeypatch.setattr(builtins, "open", _wrap(builtins.open, "open"))
    monkeypatch.setattr(io, "open", _wrap(io.open, "io.open"))
    monkeypatch.setattr(pd, "read_parquet", _wrap(pd.read_parquet, "pandas.read_parquet"))
    monkeypatch.setattr(joblib, "load", _wrap(joblib.load, "joblib.load"))
    monkeypatch.setattr(np, "load", _wrap(np.load, "numpy.load"))
    yield


@pytest.fixture
def repo_root():
    return REPO
