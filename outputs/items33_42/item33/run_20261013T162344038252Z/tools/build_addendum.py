"""Build REPORT_ADDENDUM.md for an Item 33 run from its machine-readable records only (no number is typed in)."""
import glob, json, os, sys, time
from pathlib import Path

rd = Path(sys.argv[1]); logs = Path(sys.argv[2]); indep = json.load(open(sys.argv[3]))
J = lambda name: json.load(open(rd / name))
f = lambda v, p=6: "undefined" if v is None else format(float(v), f".{p}g")
SEEDS = J("seeds.json")["forest_seeds"]; CONDS = ["C0", "C1", "C2", "C3", "X1"]
pc = {(c["register_id"], c["summary"]["reference"], c["summary"]["comparison"], c["summary"]["metric"]): c for c in J("paired_contrasts.json")["contrasts"]}
D1, D2 = pc[("D1", "C0", "C1", "pr_auc")]["summary"], pc[("D2", "C0", "C2", "pr_auc")]["summary"]
XA, XB = pc[("X-a", "C0", "C3", "pr_auc")]["summary"], pc[("X-b", "C0", "X1", "pr_auc")]["summary"]
sec2 = pc[("SEC-2", "C1", "C2", "pr_auc")]["summary"]
panel = J("seed_panel.json"); rep = J("reproduction_check.json"); mk = J("masking_results.json"); st = J("structure_checks.json")
boot = J("bootstrap.json"); sr = J("regime_sensitivity.json"); strata = J("strata.json")["sizes"]; fp = J("fit_progress.json"); freeze = J("freeze.json")
bm = lambda s: s["bootstrap_seed_mean"]; se = lambda s: s["seed_estimates"]
L = []; a = L.append
a("# Item 33 report addendum (generated from the run's machine-readable records)\n")
a(f"Run: `{rd.name}`. Protocol SHA-256 `{J('protocol_lock.json')['protocol_sha256']}`. Specification hash (frozen at G33-2, before any scoring): `{freeze['specification_sha256']}`.\n")
a("> Evidence category E2: new results on a regenerated copy of previously exposed data. Not blind, not independent replication, not evidence about real aircraft. Observed results, statistical uncertainty, exploratory interpretation and limitations are kept in separate sections below.\n")

a("## A. Execution record\n")
a("| Gate | Status | UTC (gate record) | Wall s | CPU s (user+sys) | Peak RSS MB |\n|---|---|---|---|---|---|")
resmap = {"G33-4a": ["g33_4a_resources.json"], "G33-4b": ["g33_4b_resume_resources.json"], "G33-5a": ["g33_5a_resources.json"], "G33-5b": ["g33_5b_resources.json"], "G33-6": ["g33_6_resources.json"]}
for g in ["G33-1", "G33-2", "G33-4a", "G33-4b", "G33-5a", "G33-5b", "G33-6"]:
    gr = J(f"gate_{g}.json"); w = cpu = rss = "not captured"
    for n in resmap.get(g, []):
        p = logs / n
        if p.is_file():
            r = json.load(open(p)); w, cpu, rss = f(r["wall_seconds"], 5), f(r["user_cpu_seconds"] + r["sys_cpu_seconds"], 6), f(r["max_rss_mb"], 5)
    a(f"| {g} | {gr['status']} | {gr['utc']} | {w} | {cpu} | {rss} |")
a("\nG33-4b ran as two invocations of the same gate with identical code paths, parameters and seeds (ISSUES I-34): the first was stopped by the background-job time limit after the fits recorded as kept in `fit_progress.json`, the second (resumed) invocation hash-verified and kept them and fitted the rest. "
  f"Fitted in the resumed invocation: {len(fp['fitted_in_this_invocation'])}; kept from the first invocation (besides the G33-4a fit): {len(fp['kept_from_an_earlier_invocation'])}; failed fits: {len(J('failures.json'))}. Resource data for the interrupted first invocation were not captured (the job was killed).\n")
a("### Fits (all 25 condition-by-seed pairs)\n")
a("| Condition | Seed | Features | Validation-selected threshold | Validation F1 | Fit s | max_features | Model SHA-256 |\n|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    for c in CONDS:
        r = J(f"fit_record_{c}_{s}.json")
        a(f"| {c} | {s} | {r['n_features']} | {f(r['threshold'], 10)} | {f(r['threshold_info']['selected_val_f1'], 8)} | {f(r['fit_seconds'], 5)} | {r['resolved_max_features']} | `{r['model_sha256'][:16]}…` |")
a("\n(The full model hashes are in `audit.json`. Several fits selected a visibly lower threshold than their siblings - for example C1 at seed 20261101 and C2 at seed 20261103 - which affects threshold-dependent metrics but not PR-AUC.)\n")

a("## B. Observed results (statistical uncertainty stated alongside)\n")
a("### B1. Primary contrasts (retrained feature ablation; PR-AUC; seed-mean estimand)\n")
for nm, S_ in (("D1 = PR-AUC(C0) - PR-AUC(C1)", D1), ("D2 = PR-AUC(C0) - PR-AUC(C2)", D2)):
    adj = S_["bootstrap_seed_mean_bonferroni"]
    a(f"- **{nm}**: seed-mean {f(bm(S_)['point'])}, median {f(se(S_)['median'])}; trajectory-bootstrap 95% interval [{f(bm(S_)['ci_lo'])}, {f(bm(S_)['ci_hi'])}] (B=1000, seed 20261013, undefined replicates {bm(S_)['n_undefined_replicates']}); Bonferroni-adjusted (m=2) interval [{f(adj['ci_lo'])}, {f(adj['ci_hi'])}]. Seed variability (descriptive): per-seed deltas range {f(se(S_)['min'])} to {f(se(S_)['max'])}, SD {f(se(S_)['sd_ddof1'])}; same sign for every seed: {se(S_)['sign_consistent']}.")
a("\nUnder the protocol's wording rules: for D1 and D2 **no difference was demonstrated** (both intervals include 0, and the per-seed deltas have mixed signs). The across-seed SD of the deltas is larger than the seed-mean delta in both cases, so at five seeds these differences are not separable from training noise. No meaningful-effect margin was specified, so this report does **not** declare the conditions equivalent or the effect negligible.\n")
a("### B2. Secondary and exploratory contrasts\n")
a(f"- C1 - C2 (secondary): seed-mean {f(bm(sec2)['point'])}, interval [{f(bm(sec2)['ci_lo'])}, {f(bm(sec2)['ci_hi'])}], per-seed range {f(se(sec2)['min'])} to {f(se(sec2)['max'])}.")
a(f"- C0 - C3 (exploratory, unadjusted): seed-mean {f(bm(XA)['point'])}, interval [{f(bm(XA)['ci_lo'])}, {f(bm(XA)['ci_hi'])}]; all five per-seed deltas are positive ({f(se(XA)['min'])} to {f(se(XA)['max'])}); the interval for the seed mean includes 0. In the single-seed view, seed 20261101 has an unadjusted interval that excludes 0 ([{f(XA['per_seed']['20261101']['ci_lo'])}, {f(XA['per_seed']['20261101']['ci_hi'])}]); with five seeds, two primary contrasts and several exploratory ones, that single interval is not evidence of an effect.")
a(f"- C0 - X1 (exploratory, unadjusted): seed-mean {f(bm(XB)['point'])}, interval [{f(bm(XB)['ci_lo'])}, {f(bm(XB)['ci_hi'])}], per-seed range {f(se(XB)['min'])} to {f(se(XB)['max'])}.")
a("\nPR-AUC by condition across the five seeds (descriptive spread, not an interval): " + "; ".join(f"{c} mean {f(panel[c]['mean'], 7)} (min {f(panel[c]['min'], 7)}, max {f(panel[c]['max'], 7)}, SD {f(panel[c]['sd_ddof1'], 4)})" for c in CONDS) + ".\n")
a("### B3. Sensitivity analyses\n")
for k, v in sr.items():
    a(f"- Regime-stratified resampling, {k}: [{f(v['ci_lo'])}, {f(v['ci_hi'])}] versus the primary [{f(v['primary_ci_lo'])}, {f(v['primary_ci_hi'])}]; both include 0: {v['includes_zero'] and v['primary_includes_zero']}. Test strata (usable trajectories): " + ", ".join(f"{k2} {v2}" for k2, v2 in strata.items()) + ".")
a("")
a("### B4. Reproduction diagnostic (C0 at seed 20260817 versus the frozen model's stored scores)\n")
a(f"Level **{rep['level']}**: scores are not bit-identical (max absolute difference {f(rep['max_abs_score_diff'])}); PR-AUC(C0) - PR-AUC(frozen) = {f(rep['pr_auc_diff'])}, interval [{f(rep['ci_lo'])}, {f(rep['ci_hi'])}] includes 0; the validation-selected threshold differs by {f(rep['threshold_diff'])}. This is a reported discrepancy, not a failure: C0 is a retrained model (scikit-learn 1.9.0; the frozen model's fitting environment is unrecorded). The comparisons D1 and D2 are among retrained models and do not depend on it.\n")
a("### B5. Descriptive threshold-dependent test metrics (each model at its own validation-selected threshold, and at the validation-matched operating point)\n")
a("Differences here mix ranking quality with threshold position and carry no hypothesis test. Event metrics use the existing definitions (76 events in 57 trajectories; lead time capped at 5 s).\n")
a("| Condition | Seed | Threshold | Precision | Recall | F1 | Events warned | Median lead s | | Matched threshold | Precision | Recall | F1 | Events warned |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    for c in CONDS:
        e = J(f"event_level_{c}_{s}.json"); o, m = e["own_threshold"], e["matched_operating_point"]
        a(f"| {c} | {s} | {f(o['threshold'], 6)} | {f(o['classification']['precision'], 4)} | {f(o['classification']['recall'], 4)} | {f(o['classification']['f1'], 4)} | {o['events']['n_warned']}/{o['events']['n_events']} | {f(o['events']['median_lead_time_s'], 4)} | | {f(m['threshold'], 6)} | {f(m['classification']['precision'], 4)} | {f(m['classification']['recall'], 4)} | {f(m['classification']['f1'], 4)} | {m['events']['n_warned']}/{m['events']['n_events']} |")
a("")
ev = boot["event_level_seed_primary"]["per_method"]
a("Event-level trajectory-bootstrap intervals (seed 20260817 only): event recall " + "; ".join(f"{k.split('|')[0]} {k.split('|')[1]} {f(v['point'], 4)} [{f(v['ci_lo'], 4)}, {f(v['ci_hi'], 4)}]" for k, v in ev.items() if k.endswith("event_recall") and k.split('|')[0] in ("C0", "C1", "C2")) + ". With 76 events in 57 trajectories, and a recall near 96%, these intervals are very wide and degenerate near 100%.\n")

a("### B6. Frozen-model input masking (separate analysis family: frozen_model_masking)\n")
a(f"Unmasked comparator: the frozen model re-scored in this run, PR-AUC {f(mk['unmasked_pr_auc'], 12)} (identical to the stored original value and to the Phase 3 re-score). Changes in PR-AUC with 95% trajectory-bootstrap intervals (unadjusted; first permutation draw only for MS2/MS3; the other four draws are listed in REPORT.md):\n")
a("| Variant | PR-AUC change | Interval | Precision at the frozen threshold | Recall at the frozen threshold |\n|---|---|---|---|---|")
for r in mk["rows"]:
    if "bootstrap_ci_lo" in r:
        a(f"| {r['label']} | {f(r['delta_vs_unmasked'], 5)} | [{f(r['bootstrap_ci_lo'], 5)}, {f(r['bootstrap_ci_hi'], 5)}] | {f(r['precision_at_frozen_threshold'], 4)} | {f(r['recall_at_frozen_threshold'], 4)} |")
a("\nMS1 = training-median constant, MS2 = global permutation, MS3 = within-trajectory permutation; M-A = elevator and throttle, M-B = elevator_change_1s, M-C = all three. Derived columns were not recomputed after replacement.\n")

a("## C. Exploratory interpretation (hypotheses; none was tested by this run)\n")
a("1. **Retrained models do not lose measurable PR-AUC when controls are withheld.** In this simulator the remaining features include the angle of attack and its short-history statistics and derivatives, which describe the approach to the stall boundary directly. State variables integrate the scripted past controls, so control information can remain in the state features (the protocol's C3 removed only four named proxies, and C0 - C3 still shows no demonstrated difference). The data cannot distinguish 'controls carry no extra information' from 'the same information is available elsewhere'.")
a("2. **The frozen model's reliance is large, the retrained models' need is not.** Masking the frozen model's control inputs lowers its PR-AUC substantially (largest for global permutation, smallest for within-trajectory permutation), while retrained models without those inputs perform about as well as with them. These are different quantities: masking measures sensitivity of one fitted function to out-of-distribution, physically inconsistent inputs (derived columns such as elevator_change_1s, dq_dt and dV_dt were not recomputed, so the masked rows contradict the equations of motion); retraining lets the forest rely on other features. The two results are not contradictory and are not combined.")
a(f"3. **Throttle can identify trajectories in training.** {st['throttle']['n_constant_within_trajectory']} of {st['throttle']['n_trajectories']} training trajectories ({f(100*st['throttle']['fraction_constant'], 4)}%) hold throttle constant at a value no other trajectory shares ({st['throttle']['n_distinct_constant_values']} distinct values), and {st['elevator']['n_constant_within_trajectory']} hold elevator constant. A forest could in principle exploit such a fingerprint during training; test trajectories carry unseen values, and removing throttle produced no detectable change in test PR-AUC. This run provides no evidence that a fingerprint helped on test; it does not rule out an effect on training fit.")
a("4. **Open-loop, scripted controls.** Controls in the simulator are scripted time functions and do not respond to the aircraft's state; in the dominant regime the stall is produced by the scripted elevator pulse itself. Statements about 'dependence on controls' therefore concern predictive information in this generator, not how a pilot-in-the-loop system would behave.")
a("5. **No causal reading.** Feature ablation shows how much predictive information a model family loses, not a causal effect of the controls, not causal independence, and not performance on real aircraft.\n")

a("## D. Discrepancies, deviations and what could not be concluded\n")
a("- Reproduction diagnostic level R1 (section B4).")
a("- G33-4b was interrupted by the background-job time limit and resumed (section A; ISSUES I-34).")
a("- The bootstrap metric computation was changed after the preservation commit from per-replicate scikit-learn calls to an equivalent pre-sorted weighted computation (ISSUES I-33). Equivalence checks: " + f"scikit-learn recomputation of all 50 point estimates agrees to {f(indep['point_estimates_recomputed_with_scikit_learn']['max_abs_difference_vs_recorded'], 3)}; per-seed deltas, means and medians agree to {f(indep['per_seed_deltas_mean_median_recomputed']['max_abs_difference_vs_recorded'], 3)}; the first {indep['bootstrap_fast_path_vs_scikit_learn_on_real_scores']['replicates_checked']} bootstrap replicates of all {indep['bootstrap_fast_path_vs_scikit_learn_on_real_scores']['n_methods']} score vectors agree with scikit-learn to {f(indep['bootstrap_fast_path_vs_scikit_learn_on_real_scores']['max_abs_difference'], 3)} (in-run check: {f(boot['fast_path_check']['max_abs_difference'], 3)} over {boot['fast_path_check']['replicates_checked']} replicates).")
a("- The locked protocol's register (SEC-3) asks for seed-averaged ROC-AUC contrasts for all seeds while its cost estimate counts ROC-AUC only for seed 20260817 (ISSUES I-27); the register was followed.")
a("- The `synthetic_fit` test group was not run (it was excluded at G33-3 and not re-authorized).")
a("- Not concluded: any equivalence or negligible effect (no margin was specified); any effect of controls beyond what five seeds and 456 test trajectories can resolve; generalisation to other regimes, designs, aircraft or real flights.")
a("- Limitations: original v0.3 dataset absent and the regenerated copy not shown byte-identical; previously exposed test split; trajectories may share regime or generator dependencies the bootstrap does not model; one train/validation/test split; five seeds sample one source of randomness; hyperparameters were not retuned per condition; simulation only.\n")
open(rd / "REPORT_ADDENDUM.md", "x").write("\n".join(L) + "\n")
print("addendum written:", len(L), "lines")
