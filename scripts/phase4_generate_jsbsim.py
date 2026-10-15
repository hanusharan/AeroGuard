"""Phase 4 JSBSim data (PROTOCOL.md section 11 with DEVIATIONS.md P4-D1..D4).

usage: python scripts/phase4_generate_jsbsim.py <data_dir>
Writes <data_dir>/JSB/c172p.parquet (usable rows), c172p_meta.csv, envelope.json and feasibility.json.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from phase4 import jsbsim_sim as J  # noqa: E402
from phase4.panel import build_usable_panel  # noqa: E402

SEED = 20261017
COUNTS = {"normal": 267, "stall": 200, "gradual_approach_v3": 533}

out = Path(sys.argv[1]) / "JSB"
out.mkdir(parents=True, exist_ok=True)
json.dump({m: J.feasibility(m) for m in J.CANDIDATES}, open(out / "feasibility.json", "w"), indent=1, default=str)
frames, meta, env = J.generate("c172p", SEED, 1.0, counts=COUNTS)
panel = build_usable_panel(frames)
panel.insert(1, "config_id", "JSB_c172p")
panel.to_parquet(out / "c172p.parquet", index=False)
meta.to_csv(out / "c172p_meta.csv", index=False)
env["n_usable_rows"] = int(len(panel)); env["seed"] = SEED; env["counts"] = COUNTS
json.dump(env, open(out / "envelope.json", "w"), indent=1, default=float)
print(json.dumps(env, default=float))
print(meta.groupby("generation_mode")["whether_stall_occurred"].mean().to_dict())
