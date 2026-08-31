"""Compose paper figures 2-4 from ALREADY-RECORDED experiment outputs.

No experiment, simulation, or model fit is run here. Every value plotted is
read from a file under `outputs/` that was written by an earlier, frozen
pipeline stage. Figure 1 is a compact redraw of the existing pipeline schematic at
`outputs/final/figures/01_aeroguard_pipeline.png` — same stages, same flow,
re-laid-out to stay legible at two-column width.

Run:  .venv/bin/python paper/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 6.2,
        "axes.titlesize": 6.6,
        "axes.labelsize": 6.2,
        "legend.fontsize": 5.5,
        "xtick.labelsize": 5.9,
        "ytick.labelsize": 5.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)

C_V02 = "#4C6EF5"
C_V03 = "#E03131"
C_ALT = "#F08C00"
C_EXCL = "#868E96"

BOUNDARY_DEG = 16.07  # aeroguard_dataset/events.py: numerically located CL(alpha) peak


def _load(p: str):
    f = ROOT / p
    if f.suffix == ".json":
        return json.loads(f.read_text())
    return pd.read_csv(f)


# ---------------------------------------------------------------- figure 1
def figure1() -> None:
    """Compact redraw of the pipeline schematic in outputs/final/figures/01.

    Same stages and same flow as the existing diagram; re-laid-out at a wide,
    short aspect ratio so it stays legible at two-column paper width. This is a
    documentation schematic, not a plot of experimental data.
    """
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(7.0, 1.50))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 30)
    ax.axis("off")
    ax.grid(False)

    SIM, MLC, OUTC = "#DCE6FA", "#DCF0E4", "#FAE7D8"
    SIME, MLE, OUTE = "#7A9BD4", "#6FB48A", "#D9A06A"

    row1 = [
        ("Physics engine\naeroguard/\nRK4, 5-state, emergent\n$C_L(\\alpha)$ stall", SIM, SIME),
        ("Control profiles\nv0.1 / v0.2 / v0.3 / F\ntiming only —\nphysics never modified", SIM, SIME),
        ("Trajectory generation\n+ causal labeling\nfuture_stall_5s\n(5 s horizon)", SIM, SIME),
        ("Audited datasets\n+ trajectory-level\nTRAIN / VAL / TEST\nsplits", SIM, SIME),
    ]
    row2 = [
        ("Temporal features\n23 features,\n1 s history window", MLC, MLE),
        ("RandomForest\nthreshold chosen\non VAL only", MLC, MLE),
        ("Frozen v0.3\nprimary model\n(never refit)", MLC, MLE),
        ("Transfer tests\nD$\\to$F, F$\\to$D,\nregime exclusion", OUTC, OUTE),
    ]

    w, h, gap = 21.0, 11.6, 5.0
    x0 = 1.0

    def draw(row, y):
        centres = []
        for i, (txt, fc, ec) in enumerate(row):
            x = x0 + i * (w + gap)
            ax.add_patch(
                FancyBboxPatch(
                    (x, y), w, h,
                    boxstyle="round,pad=0,rounding_size=1.2",
                    facecolor=fc, edgecolor=ec, linewidth=0.8,
                )
            )
            ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center",
                    fontsize=5.3, linespacing=1.40, color="#101418")
            centres.append((x, x + w, y + h / 2))
        for a, b in zip(centres, centres[1:]):
            ax.add_patch(FancyArrowPatch((a[1] + 0.7, a[2]), (b[0] - 0.7, b[2]),
                                         arrowstyle="-|>", mutation_scale=7,
                                         linewidth=0.8, color="#495057"))
        return centres

    top = draw(row1, 16.4)
    bot = draw(row2, 1.6)
    # elbow connector routed through the gap band between the two rows
    x_from = (top[-1][0] + top[-1][1]) / 2
    x_to = (bot[0][0] + bot[0][1]) / 2
    y_band = (1.6 + h + 16.4) / 2
    ax.plot([x_from, x_from, x_to], [16.4, y_band, y_band],
            color="#495057", linewidth=0.8, solid_capstyle="round", zorder=1)
    ax.add_patch(FancyArrowPatch((x_to, y_band), (x_to, 1.6 + h + 0.3),
                                 arrowstyle="-|>", mutation_scale=7,
                                 linewidth=0.8, color="#495057"))
    fig.tight_layout(pad=0.15)
    fig.savefig(OUT / "fig1_pipeline.png")
    plt.close(fig)


# ---------------------------------------------------------------- figure 2
def figure2() -> None:
    """v0.2 physics diagnosis (flat alpha) vs. v0.3 physical precursor coverage."""
    off = _load("outputs/precursor_diagnosis/exact_offset_summary_by_regime.csv")
    cmp_ = _load("outputs/ml_v03/metrics/v02_vs_v03_comparison.csv").set_index("metric")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.45, 1.86))

    # (a) direction-aligned median alpha in the 5s before a v0.2 crossing
    for regime, colour, marker in (
        ("near_boundary", C_V02, "o"),
        ("stall", "#0CA678", "s"),
    ):
        d = off[off["regime"] == regime].sort_values("offset_before_crossing_s")
        ax1.plot(
            d["offset_before_crossing_s"],
            np.degrees(d["alpha_median"]),
            marker=marker,
            markersize=2.6,
            linewidth=1.1,
            color=colour,
            label=f"v0.2 `{regime}`",
        )
    ax1.axhline(BOUNDARY_DEG, color="k", linestyle="--", linewidth=0.9)
    ax1.set_ylim(-1.0, 24.0)
    ax1.text(5.0, BOUNDARY_DEG + 1.0, "stall boundary  16.07°", fontsize=5.4, color="k",
             ha="left")
    ax1.invert_xaxis()
    ax1.set_xlabel("seconds before stall crossing")
    ax1.set_ylabel("median $\\alpha$ [deg]")
    ax1.set_title("(a) v0.2: $\\alpha$ is flat until the final ~1 s", loc="left")
    ax1.legend(loc="upper right", frameon=False, fontsize=5.2)

    # (b) physical precursor coverage, dataset scale
    keys = [
        (">=2s precursor coverage (physical, dataset-scale)", "$\\geq$2 s"),
        (">=3s precursor coverage (physical, dataset-scale)", "$\\geq$3 s"),
        (">=4s precursor coverage (physical, dataset-scale)", "$\\geq$4 s"),
        (">=5s precursor coverage (physical, dataset-scale)", "$\\geq$5 s"),
    ]
    v02 = [float(cmp_.loc[k, "v0.2"]) * 100 for k, _ in keys]
    v03 = [float(cmp_.loc[k, "v0.3"]) * 100 for k, _ in keys]
    x = np.arange(len(keys))
    w = 0.38
    b1 = ax2.bar(x - w / 2, v02, w, color=C_V02, label="v0.2 (median 0.54 s)")
    b2 = ax2.bar(x + w / 2, v03, w, color=C_V03, label="v0.3 (median 4.38 s)")
    for bars in (b1, b2):
        ax2.bar_label(bars, fmt="%.0f%%", fontsize=5.2, padding=1.2)
    ax2.set_xticks(x, [lbl for _, lbl in keys])
    ax2.set_ylim(0, 152)
    ax2.set_xlabel("physical precursor duration (onset $\\to$ crossing)")
    ax2.set_ylabel("% of crossings")
    ax2.set_title("(b) Physical precursor coverage, dataset scale", loc="left")
    ax2.legend(loc="upper center", ncol=2, frameon=False, fontsize=5.2, columnspacing=1.0, borderaxespad=0.1)

    fig.tight_layout(pad=0.3, h_pad=0.7)
    fig.savefig(OUT / "fig2_precursor.png")
    plt.close(fig)


# ---------------------------------------------------------------- figure 3
def figure3() -> None:
    """Temporal-ML early warning: v0.2 vs v0.3 recall by lead-time and coverage."""
    m02 = _load("outputs/ml_temporal/metrics/primary_model_metrics.json")
    m03 = _load("outputs/ml_v03/metrics/primary_model_metrics.json")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.45, 1.86))

    buckets = [b["bucket"] for b in m03["lead_time_recall_bucket"]]
    r02 = [b["recall"] * 100 for b in m02["lead_time_recall_bucket"]]
    r03 = [b["recall"] * 100 for b in m03["lead_time_recall_bucket"]]
    x = np.arange(len(buckets))
    w = 0.38
    ax1.bar(x - w / 2, r02, w, color=C_V02, label="v0.2 (median lead 0.53 s)")
    ax1.bar(x + w / 2, r03, w, color=C_V03, label="v0.3 (median lead 4.72 s)")
    ax1.set_xticks(x, buckets)
    ax1.set_ylim(0, 140)
    ax1.set_xlabel("time until the actual stall crossing")
    ax1.set_ylabel("recall [%]")
    ax1.set_title("(a) Recall by lead-time bucket", loc="left")
    ax1.legend(loc="upper center", ncol=2, frameon=False, fontsize=5.2, columnspacing=1.0, borderaxespad=0.1)

    ths = [">=1s", ">=2s", ">=3s", ">=4s", ">=5s"]
    lbls = ["$\\geq$1 s", "$\\geq$2 s", "$\\geq$3 s", "$\\geq$4 s", "$\\geq$5 s"]
    c02 = [m02["fraction_of_events_detected_at_least"][t] * 100 for t in ths]
    c03 = [m03["fraction_of_events_detected_at_least"][t] * 100 for t in ths]
    x = np.arange(len(ths))
    b1 = ax2.bar(x - w / 2, c02, w, color=C_V02, label="v0.2 (14 events)")
    b2 = ax2.bar(x + w / 2, c03, w, color=C_V03, label="v0.3 (76 events)")
    for bars in (b1, b2):
        ax2.bar_label(bars, fmt="%.0f%%", fontsize=5.2, padding=1.2)
    ax2.set_xticks(x, lbls)
    ax2.set_ylim(0, 158)
    ax2.set_xlabel("credited warning lead time")
    ax2.set_ylabel("% events warned")
    ax2.set_title("(b) Event-level warning coverage", loc="left")
    ax2.legend(loc="upper center", ncol=2, frameon=False, fontsize=5.2, columnspacing=1.0, borderaxespad=0.1)

    fig.tight_layout(pad=0.3, h_pad=0.7)
    fig.savefig(OUT / "fig3_temporal_ml.png")
    plt.close(fig)


# ---------------------------------------------------------------- figure 4
def figure4() -> None:
    """Cross-mechanism transfer vs. the zero-exposure regime-exclusion control."""
    m03 = _load("outputs/ml_v03/metrics/primary_model_metrics.json")
    excl = _load("outputs/ml_v03/metrics/generalization_check.json")
    fwd = _load(
        "outputs/ml_v03_generalization/metrics/"
        "forward_check_frozen_model_on_alt_mechanism.json"
    )
    rev = _load(
        "outputs/ml_v03_generalization/metrics/"
        "reverse_check_alt_model_on_v03_gradual.json"
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.45, 1.86))

    buckets = [b["bucket"] for b in m03["lead_time_recall_bucket"]]
    x = np.arange(len(buckets))
    w = 0.27
    series = [
        (m03, "v0.3 in-distribution (D $\\to$ D)", C_V03, -w),
        (fwd, "forward transfer: frozen model $\\to$ F", C_ALT, 0.0),
        (excl, "regime-exclusion control (zero exposure)", C_EXCL, w),
    ]
    for src, label, colour, dx in series:
        vals = [b["recall"] * 100 for b in src["lead_time_recall_bucket"]]
        ax1.bar(x + dx, vals, w, color=colour, label=label)
    ax1.set_xticks(x, buckets)
    ax1.set_ylim(0, 178)
    ax1.set_xlabel("time until the actual stall crossing")
    ax1.set_ylabel("recall [%]")
    ax1.set_title("(a) Transfer holds where zero exposure collapses", loc="left")
    ax1.legend(loc="upper center", ncol=1, frameon=False, fontsize=5.0, borderaxespad=0.1)

    rows = [
        ("v0.3\nin-distribution", m03, C_V03),
        ("forward\nD $\\to$ F", fwd, C_ALT),
        ("reverse\nF $\\to$ D", rev, "#7048E8"),
        ("regime\nexclusion", excl, C_EXCL),
    ]
    x = np.arange(len(rows))
    w = 0.26
    pr = [s["test_metrics"]["pr_auc"] * 100 for _, s, _ in rows]
    er = [s["event_level"]["event_recall"] * 100 for _, s, _ in rows]
    cv = [s["fraction_of_events_detected_at_least"][">=2s"] * 100 for _, s, _ in rows]
    for i, (vals, lbl, hatch) in enumerate(
        ((pr, "PR-AUC", ""), (er, "event recall", "//"), (cv, "coverage $\\geq$2 s", ".."))
    ):
        bars = ax2.bar(
            x + (i - 1) * w,
            vals,
            w,
            color=[c for _, _, c in rows],
            alpha=[1.0, 0.72, 0.48][i],
            hatch=hatch,
            edgecolor="white",
            linewidth=0.4,
            label=lbl,
        )
        ax2.bar_label(bars, fmt="%.0f", fontsize=4.9, padding=1.0)
    ax2.set_xticks(x, [lbl for lbl, _, _ in rows])
    ax2.set_ylim(0, 186)
    ax2.set_ylabel("value [%]")
    ax2.set_title("(b) Headline metrics across the four conditions", loc="left")
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="#495057", alpha=a, hatch=h, edgecolor="white")
        for a, h in ((1.0, ""), (0.72, "//"), (0.48, ".."))
    ]
    ax2.legend(handles, ["PR-AUC", "event recall", "coverage $\\geq$2 s"],
               loc="upper center", frameon=False, ncol=3, columnspacing=0.7,
               handlelength=1.0, fontsize=5.2, borderaxespad=0.15)

    fig.tight_layout(pad=0.3, h_pad=0.7)
    fig.savefig(OUT / "fig4_generalization.png")
    plt.close(fig)


if __name__ == "__main__":
    figure1()
    figure2()
    figure3()
    figure4()
    print("wrote:", *(p.name for p in sorted(OUT.glob("fig*.png"))))
