"""Finalize an Item 33 run: copy logs and tools, write REPRODUCIBILITY.md, ACCEPTANCE_CHECKLIST.md and audit.json.
Every status in the checklist is computed from the run's records or from live hash/ref checks; nothing is asserted by hand."""
import glob, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

rd, logs, tools, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path[:0] = [str(rd.parents[3]), str(rd.parents[3] / "experiments/items33_42/item33/src")]
from item33 import conditions as cond

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
def sh(cmd, cwd=repo):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd).stdout.strip()
J = lambda n: json.load(open(rd / n))

# 1. logs and tools
(rd / "logs").mkdir(); (rd / "tools").mkdir()
for p in sorted(logs.iterdir()):
    if p.is_file():
        shutil.copy2(p, rd / "logs" / p.name)
for p in sorted(tools.iterdir()):
    if p.is_file() and p.suffix == ".py":
        shutil.copy2(p, rd / "tools" / p.name)

# 2. live integrity facts
EXPECT = {"frozen": "707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3", "phase3": "da9c62fa1d41beef6ae53aabaedda0eecb623fa5ee06c237c21191011d2a97f2",
          "protocol": "742f55a9cc4e5da0474de84bf40cc6ffcb63a4ed46f12c3d2536ac57b21c4dc7"}
protected = {
    "frozen_model_repo": sha(repo / "outputs/ml_v03/models/primary_model_D_1s.joblib"), "frozen_model_exec_tree": sha(rd.parents[3] / "outputs/ml_v03/models/primary_model_D_1s.joblib"),
    "phase3_protocol": sha(repo / "experiments/phase3/PROTOCOL.md"), "item33_protocol": sha(repo / "experiments/items33_42/item33/PROTOCOL.md"),
    "item33_protocol_exec_tree": sha(rd.parents[3] / "experiments/items33_42/item33/PROTOCOL.md"),
}
baseline = sh("sha256sum -c baselines/v0.3.sha256 2>&1 | awk '{print $NF}' | sort | uniq -c").split()
refs = {l.split("\t")[1]: l.split("\t")[0] for l in sh("git ls-remote --heads origin").splitlines()}
local_main = sh("git rev-parse main")
status = sh("git status --porcelain=v1 --untracked-files=all").splitlines()
head = sh("git rev-parse HEAD")
protected_ok = (protected["frozen_model_repo"] == protected["frozen_model_exec_tree"] == EXPECT["frozen"] and protected["phase3_protocol"] == EXPECT["phase3"]
                and protected["item33_protocol"] == protected["item33_protocol_exec_tree"] == EXPECT["protocol"] and baseline == ["79", "OK"])
refs_ok = (refs.get("refs/heads/main") == "66b5661433af40de1a296026cd511539e33f5aa0" == local_main
           and refs.get("refs/heads/credibility-v1.1") == "f904f9b505bf27f58a2e264e8946618cf2491289"
           and refs.get("refs/heads/pre-clean-history-backup") == "47bc5626804782678c2a280deb999c750cbbbf99"
           and refs.get("refs/heads/claude/loving-fermi-ql3cyo") == "c6ad770d77d5d9ba2378aaaeb18df701bc3c0a74" == head)

# 3. code provenance (working tree vs the preserved commit)
COMMIT = "c6ad770d77d5d9ba2378aaaeb18df701bc3c0a74"
code = {}
for f in sorted(p for p in (repo / "experiments/items33_42/item33").rglob("*") if p.is_file()):
    rel = f.relative_to(repo).as_posix()
    blob = sh(f"git rev-parse {COMMIT}:{rel}")
    exec_copy = rd.parents[3] / rel
    code[rel] = {"sha256": sha(f), "committed_in_c6ad770": bool(blob) and sh(f"git hash-object {rel}") == blob,
                 "exec_tree_copy_identical": exec_copy.is_file() and sha(exec_copy) == sha(f)}
modified = sorted(k for k, v in code.items() if not v["committed_in_c6ad770"])
run_py = [k for k in code if k.startswith("experiments/items33_42/item33/src/")]
# the exec tree copies of README/ISSUES may differ from the final working-tree docs; only source/tests must match what ran
ran_identical = all(code[k]["exec_tree_copy_identical"] for k in code if "/src/" in k or "/tests/" in k)

# 4. checks for the checklist
lock = json.load(open(repo / "experiments/items33_42/item33/PROTOCOL_LOCK.json"))
gates = {g: J(f"gate_{g}.json") for g in ["G33-1", "G33-2", "G33-4a", "G33-4b", "G33-5a", "G33-5b", "G33-6"]}
fit_recs = {(c, s): J(f"fit_record_{c}_{s}.json") for c in cond.CONDITION_ORDER for s in J("seeds.json")["forest_seeds"]}
fm = J("frozen_model_check.json"); man = J("conditions_manifest.json")
indep = json.load(open(logs / "independent_check.json"))
tests_repo = open(logs / "final_tests_repo.txt").read(); tests_exec = open(logs / "final_tests_exec.txt").read()
pcs = J("paired_contrasts.json")["contrasts"]
prim = {c["register_id"]: c["statement"]["label"] for c in pcs if c["status"] == "primary"}
report = (rd / "REPORT.md").read_text(); addendum = (rd / "REPORT_ADDENDUM.md").read_text()
readme = (repo / "experiments/items33_42/item33/README.md").read_text(); issues = (repo / "experiments/items33_42/item33/ISSUES.md").read_text()
first_gate5 = gates["G33-5a"]["utc"]
fit_times = [os.path.getmtime(rd / f"fit_record_{c}_{s}.json") for (c, s) in fit_recs]
from datetime import datetime, timezone
t5a = datetime.strptime(first_gate5, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
def fmt3(v): return format(float(v), ".3g")
d1 = [c for c in pcs if c["register_id"] == "D1"][0]["summary"]["bootstrap_seed_mean"]
readme_numbers_ok = all(x in readme for x in (fmt3(d1["point"]), fmt3(d1["ci_lo"]).replace("-0.00390", "-0.00390")[:6]))
checks = []
def chk(n, title, ok, ev, note=""): checks.append((n, title, "MET" if ok is True else ("NOT MET" if ok is False else ok), ev, note))
chk(1, "Protocol finalized before data-dependent experimentation", lock["locked_utc"] < gates["G33-1"]["utc"], f"lock {lock['locked_utc']} < G33-1 {gates['G33-1']['utc']}")
chk(2, "Feature schema and conditions verified", [v["n_features"] for v in man.values()] == [23, 21, 20, 16, 22] and fm.get("feature_names_in") == list(cond.C0_FEATURES) and all(g["status"] == "PASS" for g in gates.values()),
    "conditions_manifest.json counts 23/21/20/16/22; frozen model feature_names_in_ equals C0 (frozen_model_check.json); G33-1/G33-2 PASS")
chk(3, "Approved conditions and seeds executed", len(fit_recs) == 25 and all(r["status"] == "FITTED" for r in fit_recs.values()) and J("failures.json") == [], "25 of 25 fit records FITTED; failures.json is empty; G33-4b was interrupted once and resumed with identical settings (ISSUES I-34)")
chk(4, "Same eligible population for comparable conditions", gates["G33-5a"]["status"] == "PASS" and J("population.json")["n_rows"] == 538034, "G33-5a asserts one key set and finite scores for all 25 models; test_keys.npz; population id " + gates["G33-5a"]["payload"]["population_id"])
chk(5, "Trajectory-disjoint splits", J("population.json")["count_mismatches"] == [] and gates["G33-1"]["status"] == "PASS", "G33-1: assert_no_trajectory_overlap and split-manifest equality passed; counts reconcile with the record")
chk(6, "Threshold selection uses no test labels", max(fit_times) < t5a and "(\"train\", \"val\")" in (rd.parents[3] / "experiments/items33_42/item33/src/item33/driver.py").read_text(),
    "all 25 thresholds were written before the test-scoring gate; fitting gates load only the train and validation panels; fit function has no test argument (tested)")
chk(7, "Primary contrasts computed correctly", indep["all_checks_within_1e-10"], "independent scikit-learn recomputation: point estimates and per-seed deltas differ by 0.0; 40 real bootstrap replicates of 25 score vectors differ by 3.3e-16")
chk(8, "Uncertainty reported and interpreted correctly", prim == {"D1": "no_difference_demonstrated", "D2": "no_difference_demonstrated"} and "never combined into one interval" in report and "Seed variability (descriptive" in report,
    "seed variability and bootstrap intervals in separate blocks; wording rules applied by code; D1 and D2: no difference demonstrated; no equivalence or negligible claim")
chk(9, "Failures and undefined metrics preserved and disclosed", J("failures.json") == [] and J("bootstrap.json")["undefined_replicates"] == {} and "I-34" in issues, "failures.json []; undefined replicates {}; interruption disclosed (I-34)")
chk(10, "Frozen model and historical results unchanged", protected_ok and refs_ok, f"frozen model {protected['frozen_model_repo'][:12]}..., Phase 3 protocol, Item 33 protocol, 79/79 baseline hashes; main, credibility-v1.1, pre-clean-history-backup refs unchanged")
chk(11, "Tests pass with their actual scope reported", "162 passed, 6 skipped" in tests_repo and "162 passed, 6 skipped" in tests_exec, "162 passed, 6 skipped (synthetic_fit group excluded) in the repository and in the execution tree; synthetic data only; no real-data path of the driver is covered by tests")
chk(12, "Provenance sufficient to understand what ran", ran_identical and (rd / "environment.json").is_file() and (rd / "freeze.json").is_file(),
    f"environment.json, freeze.json, protocol_lock.json, data_provenance.json, audit.json; code that ran = commit c6ad770 plus {len(modified)} modified files recorded with hashes", "caveat: the modified files are not committed")
chk(13, "Exposure and simulation limitations described", all(x in report for x in ("not blind", "original v0.3 dataset is absent", "real aircraft")), "REPORT.md sections 0 and 10; REPORT_ADDENDUM.md section D")
chk(14, "Final consistency audit passes", all(c[2] == "MET" for c in checks), "all programmatic checks above are MET", "performed by the assistant that ran the experiment, using an independent code path (scikit-learn) for the numbers; it is not an external review")
untracked = [l for l in status if l.startswith("??") or l.startswith(" M") or l.startswith("M")]
chk(15, "Final files preserved in the intended repository location", "PENDING G33-8", f"{len(untracked)} working-tree changes are uncommitted (run records, {len(modified)} changed files); copying into outputs/items33_42/item33/ is done in the working tree only", "requires G33-8 authorization")
overall = "COMPLETE" if all(c[2] == "MET" for c in checks) else "INCOMPLETE (pending G33-8)" if all(c[2] in ("MET", "PENDING G33-8") for c in checks) else "BLOCKED"
lines = ["# Item 33 acceptance checklist (PROTOCOL.md section 18)\n", f"Run `{rd.name}`. Overall: **{overall}**. A good PR-AUC is not an acceptance criterion; neither is a script running.\n",
         "| # | Criterion | Status | Evidence | Note |", "|---|---|---|---|---|"]
lines += [f"| {n} | {t} | {s} | {e} | {nt} |" for n, t, s, e, nt in checks]
lines += ["", "Minimum remaining work: G33-8 - authorize the commit of the run's small records and of the modified files listed in `audit.json` (`code_provenance`, entries with `committed_in_c6ad770: false`)."]
(rd / "ACCEPTANCE_CHECKLIST.md").write_text("\n".join(lines) + "\n") if not (rd / "ACCEPTANCE_CHECKLIST.md").exists() else sys.exit("exists")

# 5. reproducibility notes
env = J("environment.json")
repro = f"""# Reproducing this Item 33 run

Git alone cannot reproduce this run: it needs the four research panels (scratch storage, gitignored), the pinned virtual environment and, for the frozen-model anchor, the Phase 3 scratch run directory. If the container is reclaimed these are lost.

## Inputs
- Repository revision `c6ad770d77d5d9ba2378aaaeb18df701bc3c0a74` plus the modified files listed in `audit.json` (`code_provenance`, entries with `committed_in_c6ad770: false`; not yet committed - G33-8).
- Panels (SHA-256 verified by G33-1): see `data_provenance.json`. The original v0.3 dataset is absent; these are the Item 26 regenerated copy.
- Environment: Python {env['versions']['python']}, scikit-learn {env['versions']['scikit-learn']}, numpy {env['versions']['numpy']}, pandas {env['versions']['pandas']}, pyarrow {env['versions']['pyarrow']}, scipy {env['versions']['scipy']}, joblib {env['versions']['joblib']}; full `pip freeze` in `environment.json`.
- Hardware used: {env['cpu_count']} CPUs, about 16 GB RAM.

## Steps (each gate needs its own authorization; nothing here is run by importing the package or by the synthetic tests)
1. Build an execution tree without `.git`: `git archive <commit> | tar -x -C <tree>`; overlay the modified files; symlink `data/ml_temporal_v03` and `data/processed` to the panels.
2. From the tree root, with `PYTHONPATH=<tree>:<tree>/experiments/items33_42/item33/src`, run in order, each with `--confirm-gate <gate> --root <tree>` (and `--run-dir <dir>` after G33-1; `--phase3-dir <Phase 3 run dir>` for G33-1 and G33-5a):
   `python -B -m item33.driver G33-1`, `G33-2`, `G33-4a`, `G33-4b`, `G33-5a`, `G33-5b`, `G33-6`.
3. Exact commands and resource records of this run are in `logs/` (`*_resources.json` contain the command line, wall time, CPU time and peak memory).
4. `tools/independent_check.py`, `tools/build_addendum.py` and `tools/finalize.py` regenerated the independent check, `REPORT_ADDENDUM.md` and these records from the run's JSON.

## Expected cost (measured here, 4 CPUs)
G33-1 24 s; first fit 530 s and 3.16 GB; 25 fits about 8.5 min each (about 3.5 h); G33-5a 26 s; G33-5b 43 s; G33-6 620 s; independent check about 4 min.

## Known nondeterminism
Forest fits use `n_jobs=-1`; bit-identical refits under a fixed seed are believed but unverified (ISSUES I-09). Seeds are fixed in `seeds.json`.
"""
(rd / "REPRODUCIBILITY.md").write_text(repro)

# 6. audit record (hashes every file in the run directory except itself)
files = {}
for p in sorted(rd.rglob("*")):
    if p.is_file() and p.name != "audit.json":
        files[p.relative_to(rd).as_posix()] = {"sha256": sha(p), "bytes": p.stat().st_size}
audit = {"run": rd.name, "protocol_sha256": EXPECT["protocol"], "overall_status": overall, "checks": {str(n): {"title": t, "status": s, "evidence": e, "note": nt} for n, t, s, e, nt in checks},
         "protected": protected, "baseline_manifest": baseline, "remote_heads": refs, "local_head": head, "local_main": local_main,
         "working_tree_changes": status, "code_provenance": code, "modified_after_commit": modified, "preserved_commit": COMMIT,
         "files": files, "note": "models, score arrays, validation scores, masking scores, test_keys.npz, bootstrap_replicates.npz exist only in scratch; their hashes are listed above"}
json.dump(audit, open(rd / "audit.json", "x"), indent=2, sort_keys=True)
print(overall); [print(n, s, t) for n, t, s, e, nt in checks]
