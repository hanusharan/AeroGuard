# Proposed follow-up study: prospective evaluation under matched alert burden

**DRAFT — not preregistered, executed, or a result.** Author and independent reviewer must approve and time-stamp the finalized protocol before fresh data are generated or examined. Simulation research only. No real-world use or aircraft-control changes.

## Hypothesis and incremental contribution

Does temporal history contribute measurable information for first-event prediction once repeated events, already-unsafe samples, outcome-dependent selection, and unequal alert burdens are explicitly accounted for? The question is narrower than claiming a new stall prediction algorithm. Prior work already studies event-level alarm evaluation and temporal stall precursors. The potential contribution is a transparent, controlled test of what information transfers under a defined synthetic benchmark.

## Design and evidence gates

- Freeze previously published results and commit hashes. Record a new immutable analysis plan, untouched data partition and seeds before observing results. Do not reuse a previously inspected test set as confirmation.
- Compare existing instantaneous and temporal baselines under identical simulated populations, feature availability and pre-event eligibility, with validation-only operating-point selection and explicit achieved alert burden. Lock all candidate definitions, target budgets, tie handling, exclusions and estimands before scoring.
- Report first-event counts, misses, exclusions, pre-event-only discrimination, coverage including missed events, and warning burden together; explicitly identify right-censored labels. Compare at matched validation-selected burdens and report any differences in achieved test burden. Do not select test thresholds or discard negative results.
- Specify uncertainty at the trajectory level and, for configuration-level claims, at the configuration level. Distinguish independent partitions, random seeds and repeated fits. Report effect sizes and intervals; no superiority claim unless the pre-specified criteria are satisfied.
- Archive split manifests, configuration, code revision, dependency lock, seed and environment, per-row scores/labels and eligibility flags, per-event records, metrics, and SHA-256 digests. Include one small deterministic fixture and exact commands for clean-machine reproduction. Record failures and deviations. Large artifacts should have an immutable public research archive identifier, not be silently omitted.
- Stop if data provenance, leakage checks, endpoint definitions or baseline comparisons are inadequate. Ask an independent reviewer to inspect the design and artifact availability, not just the headline number.

## Prior work and positioning

This is a provisional literature map, not a systematic review:
- *Causal Meta Multiple-Instance Learning for Interpretable Stall Precursor Detection*, DOI [10.1061/JAEEEZ.ASENG-7057](https://doi.org/10.1061/JAEEEZ.ASENG-7057): precursor identification and cross-aircraft generalization are already studied.
- *Technical considerations for evaluating clinical prediction indices*, [PMC8414372](https://pmc.ncbi.nlm.nih.gov/articles/PMC8414372/): event-level alarm evaluation and warning burden are established methodology in another domain.
- *REFORMS: Consensus-based Recommendations for Machine-learning-based Science*, [PMC11092361](https://pmc.ncbi.nlm.nih.gov/articles/PMC11092361/): experimental reporting and reproducibility guidance.

A defensible novelty claim requires a broader literature review and reviewer feedback. No first-ever claim is made.

## Independent review questions

1. Are the simulation-defined event and scope justified for the research question?
2. Are the denominators, censoring and operating points fair?
3. Can you rerun the small audit from a clean checkout and verify the input hashes?
4. Does the proposed confirmatory study answer a new question rather than repackage existing analyses?
5. What further evidence would be necessary before any publication or practical claim?

AI-assisted draft for author review. Not a replacement for the author's own understanding or an independent assessment.
