"""Offline audit of frozen v0.3 metadata. Does not train or operate any system."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    "data/metadata/trajectory_metadata_v3.csv": "dd3a7f64cb35558b91b39041f407c3352bb28d48",
    "data/splits/split_manifest_v3.csv": "528ca9f50f1cc3b08c6d764f932f767ca4cb8a69",
    "outputs/ml_v03/metrics/physics_vs_ml_lead_time.csv": "361e522c5daba57ac44d3f0baeb2d0e5178a44d9",
}
SOURCE_COMMIT = "6896587a86354e1337e2583ecd62734ee8415319"


def read_verified(root, path):
    raw = (root / path).read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if git_blob != INPUTS[path]:
        raise ValueError(f"Frozen input mismatch: {path}")
    return list(csv.DictReader(raw.decode("utf-8").splitlines())), {
        "git_blob_sha1": git_blob, "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def unique(rows):
    result = {}
    for row in rows:
        key = row["trajectory_id"]
        if key in result:
            raise ValueError(f"Duplicate trajectory: {key}")
        result[key] = row
    return result


def boolean(value):
    if value not in ("True", "False"):
        raise ValueError(f"Unexpected boolean: {value}")
    return value == "True"


def bounds(total, observed, warned):
    """Partial identification, not a confidence interval."""
    if not 0 <= warned <= observed <= total:
        raise ValueError("Inconsistent counts")
    return {
        "total_first_crossings": total,
        "evaluated_first_crossings": observed,
        "warned_evaluated_first_crossings": warned,
        "unknown_first_crossings": total - observed,
        "conditional_recall": warned / observed if observed else None,
        "lower_bound": warned / total if total else None,
        "upper_bound": (warned + total - observed) / total if total else None,
    }


def audit(root=ROOT):
    inputs, hashes = {}, {}
    for path in INPUTS:
        inputs[path], hashes[path] = read_verified(root, path)
    meta, split, events = (unique(inputs[p]) for p in INPUTS)
    if meta.keys() != split.keys():
        raise ValueError("Split and metadata IDs differ")
    groups = defaultdict(lambda: dict(trajectories=0, rows=0, usable_rows=0,
                                       first_crossings=0, excluded_start=0,
                                       excluded_end=0, eligible_first_crossings=0))
    test_first = {}
    for key, row in meta.items():
        partition = split[key]["split"]
        if partition not in ("train", "val", "test"):
            raise ValueError("Invalid partition")
        regime = row["generation_mode"]
        g = groups[partition + "/" + regime]
        n = int(row["n_steps"])
        if n <= 0:
            raise ValueError("Nonpositive trajectory size")
        g["trajectories"] += 1
        g["rows"] += n
        g["usable_rows"] += max(0, n - 600)
        if not boolean(row["whether_stall_occurred"]):
            continue
        g["first_crossings"] += 1
        steps = float(row["time_of_first_stall"]) / 0.01
        index = round(steps)
        if not 0 <= index < n or abs(steps - index) > 1e-6:
            raise ValueError("Invalid crossing index")
        if index < 100:
            g["excluded_start"] += 1
            eligible = False
        elif index >= n - 500:
            g["excluded_end"] += 1
            eligible = False
        else:
            g["eligible_first_crossings"] += 1
            eligible = True
        if partition == "test":
            test_first[key] = (regime, eligible)
    if events.keys() != test_first.keys():
        raise ValueError("Archived first-crossing records do not match test metadata")
    counts = defaultdict(lambda: [0, 0, 0])
    leads = defaultdict(list)
    for key, (regime, eligible) in test_first.items():
        row = events[key]
        if row["split"] != "test" or row["regime"] != regime:
            raise ValueError("Archived event group mismatch")
        if boolean(row["ml_row_population_available"]) != eligible:
            raise ValueError("Archived eligibility differs from metadata")
        warned = boolean(row["ml_warned"])
        if warned and not eligible:
            raise ValueError("Warning credited to unavailable population")
        if warned:
            lead = float(row["ml_credited_lead_time_s"])
            if not math.isfinite(lead) or not 0 <= lead <= 5.0 + 1e-9:
                raise ValueError("Invalid archived warning lead")
        for name in (regime, "all"):
            c = counts[name]
            c[0] += 1
            c[1] += int(eligible)
            c[2] += int(warned and eligible)
            if warned:
                leads[name].append(lead)
    coverage = {}
    for name, (total, observed, warned) in sorted(counts.items()):
        times = leads[name]
        coverage[name] = {
            "median_credited_lead_warned_s": statistics.median(times) if times else None,
            "coverage_at_least_2s": bounds(total, observed, sum(t >= 2 for t in times)),
            "coverage_at_least_4s": bounds(total, observed, sum(t >= 4 for t in times)),
        }
    return {
        "source_commit": SOURCE_COMMIT,
        "inputs": hashes,
        "scope": "Frozen v0.3 metadata and archived first-crossing outcomes only",
        "groups": dict(sorted(groups.items())),
        "first_event_coverage": coverage,
        "test_first_event_identification_bounds": {
            k: bounds(*v) for k, v in sorted(counts.items())
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path, help="New path only; never overwrite an archive")
    args = p.parse_args()
    result = json.dumps(audit(args.root), indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(result)
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
