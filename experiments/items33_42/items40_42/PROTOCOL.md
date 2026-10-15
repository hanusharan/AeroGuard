# AeroGuard Items 40, 41, 42 — Fair comparison, comparison report, tests of the conclusions

| | |
|---|---|
| **Status** | Pre-specified before any Item 40–42 number was computed. Committed before the analysis runs. |
| **Scope** | Item 40: the rules for a fair comparison, plus a comparison at operating points matched on validation data. Item 41: one generated report with tables and figures that brings together Phase 3, Item 33, Items 37–39 and Item 40. Item 42: automated checks for leakage, invalid metrics and over-stated conclusions. |
| **Evidence** | E2 on previously exposed test data (regenerated v0.3 copy, Item 26). Not blind and not independent replication. Simulation only. No model is trained. The frozen model and the Phase 3 instantaneous model are only *used* (read-only, hash-checked) to score the validation split. |

## 1. Item 40 — fairness rules (every comparison must satisfy all of them; Item 42 checks them)

F1. Same rows: the common 1 s usable population of each split (test: 538,034 rows, 456 trajectories; key hash `806ab81b786ec704…`). Same labels (`future_stall_5s`).
F2. Same split: the tracked trajectory-level manifest; no trajectory appears in two splits.
F3. No test information in any choice: thresholds, candidate grids and target rates are fixed here or computed from training/validation data only.
F4. Same decision rule (`score > threshold`, strict) and the same event, episode and lead-time definitions (Items 37–38 protocol).
F5. Paired uncertainty: method contrasts use the same trajectory bootstrap draws for every method (B = 1000, seed 20261013, percentile 95%).
F6. Threshold-free metrics (PR-AUC, ROC-AUC) may be compared directly. Threshold-dependent metrics are compared **only** at matched operating points (section 2). At each method's own threshold they are reported side by side but not ranked.
F7. Every method and every pre-specified metric is reported, including unfavourable ones; no result is dropped.

## 2. Item 40 — comparison at matched operating points

- **Methods compared:** M1 `frozen_temporal`, M2 `instantaneous_model_a`, M3 `aoa_signed` (Phase 3 run `run_20261013T140820817642Z`). `aoa_two_sided` makes the same decisions as `aoa_signed` on these data at its own threshold and is reported only. Item 33 retrained models are compared within Item 33 and are not included here.
- **Validation scores:** M3 = `alpha`; M2 = the stored Phase 3 instantaneous model (hash checked against its fit record); M1 = the frozen model (hash `707d4c61…f3f3`, read-only). Each is scored once on the validation population.
- **Matching criterion:** the validation false-warning-episode rate (Item 37 primary definition: FALSE episodes per eligible span hour, no merging). Target rates R ∈ {10, 20, 40} per simulated hour. These are comparison points on a grid, **not** acceptable rates.
- **Threshold rule:** candidate thresholds are the method's validation score quantiles at the 1,001 levels 0.500, 0.0005 apart, up to 1.000. Scanning in increasing order, the selected threshold is the first candidate whose validation false-episode rate is ≤ R. The maximum (level 1.000) always qualifies, so a threshold always exists. The test split is not read during selection.
- **Test metrics at each matched point:**
  - false-episode rate per simulated hour;
  - coverage at 2 s and 4 s (existing lead-time definition, all events, with the eligibility rule of Items 37–39);
  - sustained-warning coverage at 2 s and 4 s;
  - row precision and recall.
- **Contrasts:** M1 − M2 and M1 − M3 for test coverage at 2 s, coverage at 4 s and false-episode rate, at each R. That is 2 × 3 × 3 = 18 contrasts, all with paired percentile intervals.
  - No multiplicity adjustment is made. The contrasts are descriptive, the number of contrasts is stated next to them, and no single contrast is presented as decisive.
  - "Interval excludes 0" is reported as such and is not a p-value.
  - The validation-matched rates will not be equal on test. The test rates are reported next to every coverage contrast.

## 3. Item 41 — comparison report

`REPORT.md` is generated from the machine-readable results only. It lists every source file with its SHA-256.
- **Tables:**
  - Phase 3 threshold-free metrics and paired contrasts.
  - Item 33 primary and exploratory contrasts, and the masking range.
  - Items 37–39 counts, false-warning rates and coverage.
  - Item 40 matched operating points and contrasts.
- **Figures (PNG):**
  - (a) test precision–recall curves of M1–M3, with the prevalence line;
  - (b) coverage against lead time (0.5–5 s) at each method's own threshold;
  - (c) test false-episode rate against coverage at 4 s over each method's validation threshold grid. This curve is descriptive and is drawn from test data: it is not used for any choice.
  - (d) Item 33 contrasts with intervals;
  - (e) Item 40 matched-point coverage contrasts with intervals.
- Every figure caption carries the evidence label.

## 4. Item 42 — tests of the conclusions (each recorded PASS / FAIL / FLAG with its evidence)

**Leakage**
- L1. No trajectory in two splits (panels and manifest).
- L2. No model's feature list contains a label, target-derived, key or excluded column: `future_stall_5s`, `future_stall_5s_available`, `is_unsafe`, `time_to_stall`, `trajectory_id`, `time`, `split`. This applies to the frozen model, the instantaneous model and the Item 33 conditions.
- L3. Single-feature screen on test. For each frozen-model feature, compute the PR-AUC of the feature and of its negation, and keep the larger. FLAG if any single feature reaches ≥ 0.95 or ≥ the full model's PR-AUC, because that pattern suggests leakage. The largest values are reported.
- L4. The AoA threshold is reproduced from training and validation data alone: re-running `phase3.rules.fit_signed_aoa` on the train and validation populations gives the stored threshold exactly.
- L5. The Item 40 thresholds are computed by a function that receives validation arrays only. This is a code check, and a synthetic test also covers it.

**Invalid metrics**
- M1. PR-AUC and ROC-AUC recomputed from the stored test scores equal the values stored by Phase 3 and Item 33 (absolute tolerance 1e-12).
- M2. PR-AUC is average precision (step interpolation). The trapezoidal value is reported for information only.
- M3. The prevalence (positive-row fraction) is reported. Every PR-AUC is compared with it.
- M4. Bootstrap records are consistent: undefined replicates are counted, and intervals have lower ≤ upper. A point estimate outside its percentile interval is reported as FLAG, not FAIL.
- M5. Items 37–39 are internally consistent:
  - episodes = TRUE + ONGOING + FALSE;
  - covered ≤ eligible ≤ events;
  - lead times are in (0, 5] s;
  - counts per regime sum to the totals.

**Conclusions**
- C1. Every headline statement in the Item 41 report is re-derived independently from the source JSON: the sign of each estimate and whether its interval includes 0.
- C2. A wording scan of the Items 33–42 reports and the Phase 3 report covers the terms blind, independent, confirm, real aircraft, operational, equivalen, negligible, caus, prove and significan. A line is FLAGGED if it contains no negation or qualification. Every flagged line is listed for manual review, and the reviewer's verdict on each line is recorded.

## 5. Reporting rules

Rates are per simulated hour of eligible evaluation time. No acceptable false-alarm rate, required coverage or meaningful-effect margin is defined, and none is invented. No result is called blind, independent, confirmatory or evidence about real aircraft, and no causal claim is made. If a check fails, the run stops before the report is written, unless the check is defined as a FLAG.
