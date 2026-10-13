"""Report generated ONLY from machine-readable results (PROTOCOL.md section 13).

Every number printed comes from the ``bundle`` dictionary passed in; nothing is typed in by hand and nothing
is computed here. A missing required entry raises ``ReportError``: the report is never filled with placeholders.
Static text contains the fixed limitations. Generated sentences go through ``summary.assert_wording_clean``.
"""

from typing import Dict, List, Mapping, Sequence

from .summary import assert_wording_clean

BANNER = (
    "Computed on a regenerated copy of the v0.3 data (Item 26); the original v0.3 dataset is absent. The test split "
    "was exposed by earlier analyses. These results are a controlled re-evaluation of previously exposed data: they "
    "are not blind, not independent replication, and say nothing about real aircraft. Ablation shows dependence of "
    "predictive information, not causal effects."
)
REQUIRED_KEYS = ("run_id", "protocol_sha256", "dry_run", "population", "conditions", "contrasts", "seed_panels", "failures", "historical")


class ReportError(ValueError):
    """The bundle lacks something the report must print; no placeholder is invented."""


def num(v) -> str:
    if v is None:
        return "undefined"
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    return format(float(v), ".10g")


def _need(mapping: Mapping, key: str, where: str):
    if key not in mapping:
        raise ReportError(f"missing '{key}' in {where}")
    return mapping[key]


def _contrast_lines(c: Mapping) -> List[str]:
    rid = _need(c, "register_id", "contrast")
    summ = _need(c, "summary", f"contrast {rid}")
    stmt = _need(c, "statement", f"contrast {rid}")
    assert_wording_clean(_need(stmt, "text", f"statement of {rid}"))
    bs = _need(summ, "bootstrap_seed_mean", f"summary of {rid}")
    se = _need(summ, "seed_estimates", f"summary of {rid}")
    lines = [
        f"### {rid}: {summ['reference']} - {summ['comparison']} ({summ['metric']}; status: {c['status']})",
        "",
        f"- Estimate (mean over seeds {summ['seeds']}): {num(bs['point'])}; median {num(se['median'])}.",
        f"- Trajectory-bootstrap interval for the seed mean (percentile {bs['pct']}): [{num(bs['ci_lo'])}, {num(bs['ci_hi'])}]; "
        f"undefined replicates: {bs['n_undefined_replicates']}. {bs['note']}.",
    ]
    if "bootstrap_seed_mean_bonferroni" in summ:
        b = summ["bootstrap_seed_mean_bonferroni"]
        lines.append(f"- Bonferroni-adjusted sensitivity interval (m = {b['m']}, percentile {b['pct']}): [{num(b['ci_lo'])}, {num(b['ci_hi'])}].")
    lines += [
        f"- Seed variability (descriptive, not an interval): min {num(se['min'])}, max {num(se['max'])}, SD {num(se['sd_ddof1'])}; "
        f"all per-seed deltas share one sign: {se['sign_consistent']}.",
        "- Per-seed deltas (point; trajectory-bootstrap interval):",
    ]
    for s, v in summ["per_seed"].items():
        lines.append(f"  - seed {s}: {num(v['point'])}; [{num(v['ci_lo'])}, {num(v['ci_hi'])}]")
    lines += ["", f"**Statement:** {stmt['text']}", ""]
    return lines


def render_report(bundle: Mapping) -> str:
    for k in REQUIRED_KEYS:
        _need(bundle, k, "bundle")
    out: List[str] = []
    a = out.append
    a(f"# AeroGuard Item 33: control-input ablation report (run {bundle['run_id']})")
    a("")
    if bundle["dry_run"]:
        a("**DRY RUN ON SYNTHETIC DATA. Nothing below is a research result.**")
        a("")
    a(f"> {BANNER}")
    a("")
    a(f"Protocol: `experiments/items33_42/item33/PROTOCOL.md`, SHA-256 `{bundle['protocol_sha256']}` (locked).")
    a("")
    a("## 1. Evaluated population")
    pop = bundle["population"]
    for k in ("n_rows", "n_trajectories", "n_positive", "n_negative", "population_id"):
        a(f"- {k}: {num(_need(pop, k, 'population'))}")
    a("")
    a("## 2. Conditions")
    a("")
    a("| Condition | Features | Status |")
    a("|---|---|---|")
    for name, entry in bundle["conditions"].items():
        a(f"| {name} | {entry['n_features']} | {entry['status']} |")
    a("")
    a("## 3. Retrained feature ablation (analysis family: retrained_ablation)")
    a("")
    a("Seed variability and trajectory-bootstrap uncertainty are different sources of variation and are reported separately. "
      "They are never combined into one interval.")
    a("")
    for c in bundle["contrasts"]:
        a_lines = _contrast_lines(c)
        out.extend(a_lines)
    a("### PR-AUC by condition and seed (descriptive spread across seeds)")
    a("")
    for cond, panel in bundle["seed_panels"].items():
        a(f"- {cond}: mean {num(panel['mean'])}, median {num(panel['median'])}, min {num(panel['min'])}, max {num(panel['max'])}, SD {num(panel['sd_ddof1'])}")
    a("")
    sens = bundle.get("regime_sensitivity")
    if sens:
        a("## 4. Regime-stratified sensitivity (SR; no decision role)")
        a("")
        for rid, s in sens.items():
            a(f"- {rid}: stratified interval [{num(s['ci_lo'])}, {num(s['ci_hi'])}] versus primary [{num(s['primary_ci_lo'])}, {num(s['primary_ci_hi'])}]; "
              f"zero-inclusion agrees: {s['agrees_on_zero_inclusion']}.")
        a("")
    rep = bundle.get("reproduction")
    a("## 5. Reproduction diagnostic (C0 at seed 20260817 versus the frozen model)")
    a("")
    if rep is None:
        a("Not computed: the frozen-model reference scores were not available (a missing artifact, not a failed experiment).")
    else:
        a(f"- Level: {rep['level']}; scores bit-identical: {rep['bit_identical']}; max absolute score difference {num(rep['max_abs_score_diff'])}; "
          f"threshold difference {num(rep['threshold_diff'])}.")
        a(f"- PR-AUC(C0) - PR-AUC(frozen): {num(rep['pr_auc_diff'])}, interval [{num(rep['ci_lo'])}, {num(rep['ci_hi'])}].")
    a("")
    mop = bundle.get("matched_operating_point")
    if mop:
        a("## 6. Matched operating point (exploratory, validation-defined)")
        a("")
        for row in mop:
            a(f"- {row['condition']} (seed {row['seed']}): threshold {num(row['threshold'])}, achieved validation FPR {num(row['achieved_fpr'])} "
              f"(target {num(row['target_fpr'])}).")
        a("")
    mask = bundle.get("masking")
    a("## 7. Frozen-model input masking (analysis family: frozen_model_masking)")
    a("")
    a("This is a perturbation of the frozen model's inputs. It is a separate, descriptive analysis and does not measure the same "
      "quantity as the retrained ablation above. Replaced values can be out-of-distribution.")
    a("")
    if not mask:
        a("Not run.")
    else:
        for m in mask:
            a(f"- {m['label']}: PR-AUC {num(m['pr_auc'])}; change versus unmasked frozen model {num(m['delta_vs_unmasked'])}.")
    a("")
    a("## 8. Failures and undefined results")
    a("")
    fails = bundle["failures"]
    if not fails:
        a("No failed fit or undefined replicate was recorded.")
    else:
        for f in fails:
            a(f"- {f}")
    a("")
    a("## 9. Historical figures (context only; not recomputed here)")
    a("")
    for k, v in bundle["historical"].items():
        a(f"- {k}: {num(v) if not isinstance(v, str) else v}")
    a("")
    a("## 10. Limitations")
    a("")
    for line in (
        "The original v0.3 dataset is absent; the regenerated copy is not shown to be byte-identical to it.",
        "The test split was previously exposed; nothing here is blind or independent.",
        "Controls are scripted and open-loop; state-derived features can carry control information, so no condition is control-free.",
        "The trajectory bootstrap treats test trajectories as exchangeable and may understate uncertainty if trajectories sharing a regime are dependent.",
        "Five training seeds sample one randomness source and do not establish generalisation across training randomness.",
        "No meaningful-effect margin was specified, so no difference is declared equivalent or negligible.",
        "Simulation only: nothing here establishes performance on real aircraft.",
    ):
        a(f"- {line}")
    a("")
    return "\n".join(out)
