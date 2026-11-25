# Evidence audit: first-event selection and partial identification (2026-11-25)

**Status:** exploratory secondary analysis of frozen simulation records. No retraining, new flight simulation, physical validation, or change to published results. AI-assisted code and analysis generated for author review. No independent replication is claimed.

## Question

How much does selecting only crossings within the original feature/label eligibility window change the interpretation of reported first-event recall? The earlier reproducibility report already identified excluded crossings and the first-event vs pooled distinction. This addendum quantifies regime-specific selection and logical bounds without inventing outcomes for excluded crossings.

## Source and reproducibility

Frozen main commit `6896587a86354e1337e2583ecd62734ee8415319`. Three tracked CSV inputs, with Git blob IDs hard-coded in the audit, are joined by trajectory ID. The command also emits SHA-256 hashes for the inputs. It uses Python standard library only; no parquet, model loading, or network needed.

From repository root:

```sh
python experiments/evidence_audit/audit.py
python -m pytest tests/test_evidence_audit.py -q
```

To archive a new report without overwriting existing files: `python experiments/evidence_audit/audit.py --output evidence-audit.json`.

Eligibility is defined using the existing 100-row history requirement and 500-row unavailable-label tail; the first crossing time is converted to the original 0.01 s index. Archived first-crossing outcomes are checked against metadata and split manifests. This is a metadata reconstruction, not re-scoring individual predictions.

## Results

The following counts were calculated directly from the three tracked CSVs through an independent in-memory table join during creation of this addendum. The initial audit and all three initial regression tests passed [GitHub Actions run 45532041894](https://github.com/hanusharan/AeroGuard/actions/runs/45532041894) (330 passed, 24 skipped, 11 deselected). This is automated reproduction from archived metadata, not independent scientific validation.

| Test regime | All first crossings | Eligible | Excluded | Warned among eligible | Excluded fraction |
|---|---:|---:|---:|---:|---:|
| Gradual approach | 42 | 40 | 2 | 37 | 4.8% |
| Abrupt stall | 25 | 17 | 8 | 17 | 32.0% |
| All | 67 | 57 | 10 | 54 | 14.9% |

Across the train, validation and test partitions, the corresponding first-crossing eligibility counts are 283/342, 44/61 and 57/67. Selection is especially pronounced in the abrupt-stall regime: 54/102 train, 16/26 validation and 8/25 test first crossings are excluded. No first crossing is excluded solely by the initial history window in these metadata.

| Population | Conditional recall | Logical lower bound | Logical upper bound |
|---|---:|---:|---:|
| Gradual approach | 92.5% | 88.1% | 92.9% |
| Abrupt stall | 100% | 68.0% | 100% |
| All first crossings | 94.7% | 80.6% | 95.5% |

The lower bound assigns no warnings to unknown crossings; the upper bound assigns warnings to all unknown crossings. These are **partial-identification bounds on a hypothetical complete first-crossing evaluation**, not measured recall, confidence intervals, predictions, or estimates of real aircraft performance. They assume the archived observed outcomes remain fixed. A changed evaluation protocol could also alter observed outcomes. Excluded events are not classified as misses by the published protocol.

The exclusion rate differs substantially by regime; missingness cannot simply be assumed representative. Even 100% conditional recall in the abrupt-stall subset leaves substantial uncertainty about the complete population. No conclusion about a causal effect of selection is established. Do not combine these bounds with the historical pooled 73/76 metric, which includes repeat episodes.

## Contribution and limits

The new artifact is a small, independently runnable selection-bias audit with a fail-closed provenance check, transparent denominator accounting and exact assumption-free outcome bounds conditional on observed records. The underlying bound is elementary and not a new statistical algorithm. This strengthens the study's interpretation, not its physical validity or the model's demonstrated performance. It does not close missing Phase 4 artifacts, establish novelty relative to the literature, or replace a fresh held-out comparison.

## Review links

- [Original reproducibility report](../../REPRODUCIBILITY_REPORT.md), especially section 11.
- [Scientific audit](../../reports/PHASE_A_FINAL_AUDIT.md).
- [REFORMS reporting guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC11092361/).
- [NeurIPS paper checklist](https://neurips.cc/public/guides/PaperChecklist).

## Additional first-event warning coverage

A separate join of the archived first-crossing records gives the following counts. Conditional coverage uses all eligible first crossings, including misses; lead-time medians use warned first crossings only. Logical bounds use all metadata first crossings and allow unknown outcomes to vary, holding the recorded outcomes fixed.

| Regime | Median credited lead among warned | Eligible coverage ≥2 s | Eligible coverage ≥4 s | Complete-population ≥2 s bounds | Complete-population ≥4 s bounds |
|---|---:|---:|---:|---:|---:|
| Gradual approach | 4.83 s | 30/40 | 25/40 | 30/42–32/42 | 25/42–27/42 |
| Abrupt stall | 0.66 s | 0/17 | 0/17 | 0/25–8/25 | 0/25–8/25 |
| All | 3.15 s | 30/57 | 25/57 | 30/67–40/67 | 25/67–35/67 |

No evaluated abrupt first crossing had a credited warning at least two seconds in advance. The result describes this archived synthetic dataset only; it is not an operational safety assessment. The updated audit and all four regression tests passed [GitHub Actions run 45532652474](https://github.com/hanusharan/AeroGuard/actions/runs/45532652474) (331 passed, 24 skipped, 11 deselected). The generic bounds fields named `conditional_recall` and `warned_evaluated_first_crossings` represent conditional coverage and count meeting the specified lead-time criterion when nested under a coverage metric.
