# Reviewer evidence map — supplemental, November 2026

This index is a navigation aid, not a new research result. It separates evidence types to prevent archived aggregate results from being mistaken for independently reproduced results.

| Claim / question | Source | Evidence level / remaining gap |
|---|---|---|
| Original research question and limits | [README](../../README.md), [paper Markdown](../../paper/AeroGuard_Research_Paper.md) | Published simulation-only study; no real-aircraft validation |
| Reproduced frozen-model v0.3 evaluation | [Reproducibility report](../../REPRODUCIBILITY_REPORT.md) | Author/toolchain regeneration documented; not independent replication |
| First-event denominator and lead-time scope | [Reproducibility report](../../REPRODUCIBILITY_REPORT.md), [new offline audit](README.md) | Archived metadata and outcomes; excluded outcomes unknown |
| Statistical baseline comparison | [Phase 3](../../outputs/phase3/run_20261013T140820817642Z/REPORT.md) | Stored results and protocol; different thresholds must not be treated as matched |
| Phase 4 generalization | [Phase 4](../../outputs/phase4/run_20261015T152932Z/REPORT.md), [Phase A audit](../../reports/PHASE_A_FINAL_AUDIT.md) | Stored aggregates, not reconstructed from original score arrays |
| Model-defined stall boundary | [Definition](../../docs/STALL_BOUNDARY_DEFINITION.md) | Numerical surrogate; not measured aircraft behavior |
| Historical / canonical artifact distinctions | [Provenance](../../PROVENANCE.md), [baseline hashes](../../baselines/README.md) | Preserves original outputs; do not overwrite |
| AI assistance and author responsibilities | [Author statement](../../AUTHOR_STATEMENT.md) | Explicit AI assistance; author must review and defend the work |
| Proposed confirmatory evaluation | [Draft protocol](FOLLOWUP_PROTOCOL.md) | Not executed, not preregistered; no new performance claims |

## Minimal offline reproducibility check

Run from the repository root with Python 3.12 (no third-party packages needed):

```sh
python experiments/evidence_audit/audit.py
```

The command verifies the three frozen source files against their original Git blob identities and reports SHA-256 digests, exact population counts and logical uncertainty bounds. It will fail rather than silently accept altered bytes. If Git's checkout settings convert line endings, use a checkout preserving original LF bytes.

This reproduces the secondary metadata analysis only. For the broader research, use the documented [reproduction instructions](../../REPRODUCIBILITY.md); the original project data and model environments are not bundled into this supplemental check.

## Review status

The initial supplemental audit was verified by [GitHub Actions](https://github.com/hanusharan/AeroGuard/actions/runs/45532041894). The expanded four-test audit also passed [GitHub Actions run 45532652474](https://github.com/hanusharan/AeroGuard/actions/runs/45532652474): 331 passed, 24 skipped, 11 deselected. No independent reviewer has signed off. This index and supplemental audit were AI-assisted for author review.
