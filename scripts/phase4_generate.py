"""Phase 4 data generation (PROTOCOL.md section 1): every configuration, one data seed.

usage: python scripts/phase4_generate.py <data_dir> <D0|D1> [n_workers]

Writes, per configuration, <data_dir>/<seed_name>/<config_id>.parquet (usable rows only,
section-2 feature columns) and <config_id>_meta.csv, plus configs.json and
envelopes.json. Data directories are outside Git.
"""

import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from phase4 import DATA_SEEDS  # noqa: E402
from phase4.configs import design  # noqa: E402


def work(args):
    cfg, idx, seed, out_dir = args
    from phase4.panel import build_usable_panel
    from phase4.sim import generate_config
    t0 = time.time()
    frames, meta, env = generate_config(cfg, idx, seed)
    panel = build_usable_panel(frames)
    panel.insert(1, "config_id", cfg["config_id"])
    panel.to_parquet(out_dir / f"{cfg['config_id']}.parquet", index=False)
    meta.to_csv(out_dir / f"{cfg['config_id']}_meta.csv", index=False)
    env["n_usable_rows"] = int(len(panel))
    env["seconds"] = time.time() - t0
    return cfg["config_id"], env


def main():
    data_dir, seed_name = Path(sys.argv[1]), sys.argv[2]
    n_workers = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
    out = data_dir / seed_name
    out.mkdir(parents=True, exist_ok=True)
    cfgs = design()
    json.dump(cfgs, open(out / "configs.json", "w"), indent=1)
    jobs = [(c, i, DATA_SEEDS[seed_name], out) for i, c in enumerate(cfgs)]
    envs = {}
    with Pool(n_workers) as pool:
        for cid, env in pool.imap_unordered(work, jobs):
            envs[cid] = env
            print(f"{seed_name} {cid}: {env['n_usable_rows']} usable rows, {env['seconds']:.0f}s", flush=True)
    json.dump(envs, open(out / "envelopes.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
