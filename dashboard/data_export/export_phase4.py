"""Export the Phase 4 numbers shown on the dashboard.

Reads the committed Phase 4 run (Items 43-53) and copies values verbatim into
dashboard/src/data/phase4.json. Nothing is computed, estimated or adjusted;
rounding happens only at display time in the React component.

    python dashboard/data_export/export_phase4.py   # from the repository root

Standard library only; no research environment needed.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "outputs/phase4/run_20261015T152932Z"
SRC = ROOT / RUN
OUT = ROOT / "dashboard" / "src" / "data" / "phase4.json"

PRIMARY_SEED = "20260817"


def load(name: str) -> dict:
    return json.loads((SRC / name).read_text())


def group(block: dict) -> dict:
    return {
        "nTrajectories": block["n_trajectories"],
        "prAuc": block["row"]["pr_auc"],
        "prAucCi": block["ci95"]["pr_auc"],
        "nEvents": block["event"]["n_events"],
        "nWarned": block["event"]["n_warned"],
        "medianLeadS": block["event"]["median_lead_s"],
        "medianLeadCi": block["ci95"]["median_lead_s"],
        "ece": block["row"]["ece"],
    }


def main() -> None:
    primary = load("primary.json")
    jsb = load("jsbsim.json")["results"]
    robust = load("robustness.json")
    gm = primary["group_metrics"]

    regime = primary["item52"]["ALL"]["regime"]
    out = {
        "source": RUN,
        "protocol": "experiments/phase4/PROTOCOL.md",
        "nConfigurations": sum(len(v) for v in primary["partition"].values()),
        "groups": {g: group(gm[g]["M_D"]) for g in ("SEEN", "IDH", "OOD", "C00")},
        "frozenZeroShotOOD": {"prAuc": gm["OOD"]["F_v03"]["row"]["pr_auc"], "ece": gm["OOD"]["F_v03"]["row"]["ece"]},
        "item44": {"delta": primary["item44"]["pr_auc"]["delta"], "ci": primary["item44"]["pr_auc"]["ci95"]},
        "item45": {
            "rho": primary["item45"]["spearman_pr_auc_drop_vs_d_ood"]["rho"],
            "p": primary["item45"]["spearman_pr_auc_drop_vs_d_ood"]["p"],
        },
        "regimes": {
            name: {"nEvents": regime[key]["M_D"]["event"]["n_events"], "medianLeadS": regime[key]["M_D"]["event"]["median_lead_s"]}
            for name, key in (("gradual", "gradual_approach_v3"), ("abrupt", "stall"))
        },
        "jsbsim": {
            "cross": group(jsb[f"cross|X_D|{PRIMARY_SEED}|JSB_test"]),
            "native": group(jsb[f"native|X_D|{PRIMARY_SEED}|JSB_test"]),
        },
        "robustness": {
            key: {
                "signHolds": round(v["sign_holds_fraction"] * v["n_runs"]),
                "nRuns": v["n_runs"],
                "diff": v["primary_diff"],
                "ci": v["primary_ci95"],
                "verdict": v["verdict"],
            }
            for key, v in robust.items()
        },
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
