# Phase A status summary (2026-10-24)

Full report: [`PHASE_A_FINAL_AUDIT.md`](PHASE_A_FINAL_AUDIT.md).

**Is Phase A complete?**
Yes, against its definition of done:
- All accessible artifacts are inventoried.
- Issues A–E were investigated as far as the evidence allows.
- Safe corrections are applied, and the rest are written out as exact proposed changes.
- Nothing unverified is presented as verified.

It does not mean every uncertainty is resolved. The data-dependent questions remain open because the Phase 4 data were never archived.

**Which claims are verified from underlying data?**
- Only the Phase 4 configuration design: 23 configurations split 12/4/6/1, with the unfamiliarity table. It regenerates exactly from the committed code.
- No Phase 4 performance metric could be recomputed from data.

**Which claims rest only on stored aggregates or documentation?**
All Phase 4 performance numbers:
- SEEN 0.880 / 2.35 s, IDH 0.891 / 1.98 s, OOD 0.863 / 1.38 s, JSBSim 0.780 / 1.20 s
- the robustness verdicts and false-warning rates
- the Item 50 comparison.

These agree with the stored outputs (parity 176/176), and the metric code is verified. But they have not been reproduced from data, and nothing has been independently validated.

**Which issues remain unverifiable?**
- How much rows already inside a stall contribute to PR-AUC.
- How many crossings were excluded from the event metrics (stalls followed by less than 5 s of trajectory, and trajectories with no usable rows), and how many left-censored events there are.
- How much lead time is credited through warnings that were also counted as false.
- The per-trajectory reasons behind the count gaps (SEEN 505/540, IDH 1,107/1,200, OOD 1,650/1,800, C00 268/300, JSBSim 906/1,000).
- Dataset checksums and determinism.
- The final Item 50 report.

**Can the study be released honestly with qualified claims?**
Yes, with the wording now in the README and on the website: simulation only, one author and code base, intervals that describe flights within the tested configurations, JSBSim as transfer to one second simulator model, the lead-time question open, and the scope of PR-AUC and the event population stated.

**What MUST be done before release?**
1. ~~Fix the red CI.~~ **Resolved** in commit `be0716b`. The baseline PDF was recovered from Git into `paper/archive/`; `baselines/paper_pdf_v1.1.0.sha256` records both PDFs; the test verifies all 79 historical digests plus the current PDF. GitHub Actions Tests run #12 succeeded on `be0716b`.
2. ~~Commit the reviewed documentation changes.~~ **Done** in `be0716b` (branch `claude/gallant-babbage-m4l0wa`; not yet merged to `main`).
3. In the release phase: create the v1.1.0 tag, then restore `version` and `date-released` in `CITATION.cff`. The docs no longer claim a tag exists.

**What can safely be deferred?**
- A threshold-matched lead-time comparison (new protocol, fresh data seed).
- Configuration-level evaluation across many training splits.
- PR-AUC without post-crossing rows, and first-event recall.
- More JSBSim aircraft models.
- Primary-source values for Item 50.
- Archiving or regenerating the Phase 4 data with checksums.
- Independent replication.
