# Reproducing this Item 33 run

Git alone cannot reproduce this run: it needs the four research panels (scratch storage, gitignored), the pinned virtual environment and, for the frozen-model anchor, the Phase 3 scratch run directory. If the container is reclaimed these are lost.

## Inputs
- Repository revision `c6ad770d77d5d9ba2378aaaeb18df701bc3c0a74` plus the modified files listed in `audit.json` (`code_provenance`, entries with `committed_in_c6ad770: false`; not yet committed - G33-8).
- Panels (SHA-256 verified by G33-1): see `data_provenance.json`. The original v0.3 dataset is absent; these are the Item 26 regenerated copy.
- Environment: Python 3.12.3, scikit-learn 1.9.0, numpy 2.5.4, pandas 3.0.6, pyarrow 26.0.0, scipy 1.18.1, joblib 1.6.0; full `pip freeze` in `environment.json`.
- Hardware used: 4 CPUs, about 16 GB RAM.

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
