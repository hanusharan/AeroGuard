"""Protocol-lock, output-path and exclusive-write guards (PROTOCOL.md sections 11 and 13)."""

import json
import math
import os
from pathlib import Path
from typing import Mapping

from phase3.population import DataIntegrityError, GateViolation, sha256_file  # reused unchanged

from . import (
    FROZEN_MODEL_RELPATH, LOCK_RELPATH, OUTPUT_ROOT_RELPATH, PROTECTED_RELPATHS, PROTOCOL_RELPATH, PROTOCOL_SHA256,
)

__all__ = [
    "DataIntegrityError", "GateViolation", "sha256_file", "verify_protocol_lock", "assert_output_path",
    "assert_no_git", "jsonable", "write_json_exclusive", "write_text_exclusive",
]


def verify_protocol_lock(root) -> str:
    """The protocol on disk must hash to the locked value and the lock record must agree."""
    root = Path(root)
    got = sha256_file(root / PROTOCOL_RELPATH)
    if got != PROTOCOL_SHA256:
        raise DataIntegrityError(f"protocol hash differs: expected {PROTOCOL_SHA256}, observed {got}")
    lock = json.loads((root / LOCK_RELPATH).read_text())
    if lock.get("protocol_sha256") != PROTOCOL_SHA256:
        raise DataIntegrityError("PROTOCOL_LOCK.json records a different protocol hash")
    return got


def assert_no_git(root) -> None:
    """Execution trees must not be git checkouts: a gate that writes must not be able to run
    inside the repository by accident."""
    if (Path(root) / ".git").exists():
        raise GateViolation(f"refusing to run gates inside a git checkout: {root}")


def assert_output_path(path, root) -> Path:
    """Item 33 may write only below ``<root>/outputs/items33_42/item33/run_<UTC>/`` and never to a protected location."""
    root_p = Path(root).resolve()
    target = Path(path).resolve()
    allowed = root_p / OUTPUT_ROOT_RELPATH
    for rel in PROTECTED_RELPATHS:
        bad = root_p / rel
        if target == bad or bad in target.parents:
            raise GateViolation(f"refusing to write to protected location {bad}")
    if allowed not in target.parents:
        raise GateViolation(f"outputs must be below {allowed}, got {target}")
    run_part = target.relative_to(allowed).parts[0]
    if not run_part.startswith("run_"):
        raise GateViolation(f"outputs must be inside a per-run directory {OUTPUT_ROOT_RELPATH}/run_<UTC>/, got {target}")
    return target


def jsonable(obj):
    """Deterministic JSON-safe conversion: numpy scalars and arrays become Python values and
    non-finite floats become null (never the invalid tokens NaN / Infinity)."""
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        np = None
    if np is not None:
        if isinstance(obj, np.generic):
            obj = obj.item()
        elif isinstance(obj, np.ndarray):
            return [jsonable(v) for v in obj.tolist()]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, Mapping):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        seq = sorted(obj) if isinstance(obj, (set, frozenset)) else obj
        return [jsonable(v) for v in seq]
    return obj


def write_text_exclusive(path, text: str, root) -> Path:
    target = assert_output_path(path, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "x", encoding="utf-8") as f:   # 'x': an existing file is an error, never overwritten
        f.write(text)
    return target


def write_json_exclusive(path, obj, root) -> Path:
    return write_text_exclusive(path, json.dumps(jsonable(obj), indent=2, sort_keys=True) + "\n", root)
