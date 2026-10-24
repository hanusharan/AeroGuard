# AeroGuard Phase 4 report — Items 43–53 (run `run_20261015T152932Z`)

> **Scope.** Simulation only. Every number describes simulated aircraft: the AeroGuard 2D longitudinal model with varied parameters, or the community JSBSim `c172p` model. Nothing here is evidence about a real aircraft, an operational false-alarm rate or certified performance. Same author and code base as Phases 1–3, so this is not independent replication. False-warning rates are per **simulated** hour of eligible evaluation time.

Protocol: [`experiments/phase4/PROTOCOL.md`](../../../experiments/phase4/PROTOCOL.md) (SHA-256 `54fd8d54…035f2f`, committed before any data were generated). Deviations P4-D1 to P4-D5: [`DEVIATIONS.md`](../../../experiments/phase4/DEVIATIONS.md), all written before the data they affect were scored. Machine-readable results in this directory: `primary.json`, `per_config.csv`, `jsbsim.json`, `robustness.json`, `robustness_runs.csv`, `item50.json`. Intervals are 95% trajectory-bootstrap percentile intervals (B = 1000, seed 20261015) unless stated.

## 1. Data (Item 43)

23 configurations: the v0.3 aircraft (C00), 12 training configurations (T01–T12), 4 held-out configurations inside the training envelope (H01–H04) and 6 unfamiliar configurations (O01–O06), 300 trajectories each, data seed D0 (D1 used only for item 53). All configurations trimmed over their full start-speed range; no speed cap was needed. Fitting used 2,323 training and 502 validation trajectories (TRAIN configurations, every 5th usable row). Evaluation populations at full 0.01 s resolution:

| Group | Trajectories | Usable rows | Stall events |
|---|---|---|---|
| SEEN (TRAIN configs, test split) | 505 | 597,794 | 105 |
| IDH (H01–H04, all trajectories) | 1,107 | 1,318,736 | 202 |
| OOD (O01–O06, all trajectories) | 1,650 | 1,901,346 | 276 |
| C00 (v0.3 aircraft) | 268 | 320,415 | 54 |

Each IDH and OOD configuration and C00 passed the evaluability gate (≥ 15 events). Only one TRAIN configuration (T09) did so on its own (3–21 events per test split), so SEEN is interpreted only pooled. A note made before results: with 12 Sobol points in 15 dimensions, the IDH configurations already lie 0–3 parameters outside the TRAIN per-parameter range, so "inside the envelope" means inside the core box, not inside the convex hull.

## 2. Headline table (primary model seed 20260817; each model at its own validation-selected threshold)

| Group | Model | PR-AUC | Event recall | Median lead (s) | Coverage ≥ 2 s / ≥ 4 s | False warnings / sim. h | ECE |
|---|---|---|---|---|---|---|---|
| SEEN | `M_D` | 0.880 [0.847, 0.906] | 0.990 (104/105) | 2.35 [1.74, 4.64] | 0.58 / 0.60 | 31.3 [16.7, 51.1] | 0.071 |
| IDH | `M_D` | 0.891 [0.869, 0.909] | 0.995 (201/202) | 1.98 [1.53, 2.43] | 0.57 / 0.61 | 36.9 [22.3, 53.4] | 0.075 |
| OOD | `M_D` | 0.863 [0.842, 0.883] | 0.982 (271/276) | 1.38 [0.93, 1.88] | 0.50 / 0.54 | 23.3 [14.1, 34.5] | 0.084 |
| C00 | `M_D` | 0.905 [0.857, 0.940] | 0.963 (52/54) | 4.01 [1.83, 4.84] | 0.71 / 0.72 | 31.5 [12.3, 56.1] | 0.072 |
| OOD | `M_D_noSM` | 0.858 [0.836, 0.878] | 0.978 | 1.68 | 0.52 / 0.55 | 30.9 | 0.082 |
| OOD | `M_A` | 0.818 [0.794, 0.839] | 0.993 | 2.20 | 0.60 / 0.69 | 96.8 [80.0, 112.8] | 0.111 |
| OOD | `R_AoA` | 0.722 [0.695, 0.746] | 1.000 | 0.67 | 0.45 / 0.28 | 20.8 | — |
| OOD | `F_v03` (frozen, zero-shot) | 0.871 [0.852, 0.888] | 0.971 (268/276) | 0.80 [0.72, 0.98] | 0.44 / 0.40 | 9.5 [5.5, 14.3] | 0.054 |

Across the five model seeds `M_D` PR-AUC varies by at most 0.003 within any group (e.g. OOD 0.863–0.866), so seed variation is negligible next to the bootstrap intervals. All models and groups are in `primary.json`.

**Reading lead time and false warnings.** Each model runs at its own threshold. `M_A` warns earlier than `M_D` but raises 3–4 times as many false-warning episodes, and `F_v03` raises the fewest but warns latest, so lead time and false-warning rate are not comparable across models at these operating points. PR-AUC is threshold-free and is the fair ranking metric here. A validation-matched comparison like Items 40–42 was not part of this protocol.

## 3. Item 44 — held-out configurations inside the training envelope

`M_D`: Δ(IDH − SEEN) PR-AUC = +0.010 [−0.022, +0.048]; Δ event recall = +0.005 [−0.014, +0.030]. Per IDH configuration, PR-AUC minus SEEN: H01 +0.021, H02 +0.037, H03 −0.019, H04 +0.004.

**Outcome (pre-specified rule): generalises within the training envelope.** No loss was detected; the intervals are wide enough that a loss of about 0.02 PR-AUC cannot be excluded. H1 is supported.

## 4. Item 45 — unfamiliar configurations

Pooled OOD PR-AUC is 0.863 against 0.880 SEEN and 0.891 IDH; event recall stays at 0.98, but median lead falls to 1.38 s and ECE rises to 0.084. Per configuration (`M_D` PR-AUC): O01 0.882, O02 0.856, O03 0.894, O04 0.904, O05 0.847, O06 0.833 (median 0.869 versus 0.893 for IDH). The all-parameters-extreme O06 and the sluggish-pitch O05 are the hardest. Spearman correlation between per-configuration PR-AUC and the distance `d_OOD` over all 23 configurations: ρ = −0.09 (p = 0.68). With TRAIN configurations at distance 0, this is weak and descriptive; no monotone relation with distance was detected.

Pre-specified expectation (O03/O04 hurt `M_D_noSM` and `R_AoA` more than `M_D` and `R_SM`):
- `M_D` versus `M_D_noSM`: in the expected direction on O03 (0.894 vs 0.882) and O04 (0.904 vs 0.894). Pooled OOD paired difference +0.006 [+0.001, +0.010]. Small.
- `R_SM` versus `R_AoA`: **not testable with PR-AUC as specified.** Within one configuration, stall margin is a constant shift of α, so the two rules rank rows identically and have identical PR-AUC (0.721 on O04, 0.756 on O03). They differ only through their single threshold. This was an error in the protocol's expectation, not a result.

H2 is **partly supported**: there is a modest loss on unfamiliar configurations, mostly in lead time, but it does not grow detectably with distance, and the stall-AoA configurations O03/O04 were among the easiest rather than the hardest.

**Unexpected observation.** The frozen v0.3 model, trained on one aircraft and never refitted, ranks rows on OOD as well as the family-trained `M_D` (PR-AUC 0.871 vs 0.863; on O06 0.904 vs 0.833) and is better calibrated (ECE 0.054). It operates at a far more conservative point: fewer false warnings, later warnings. A plausible but untested explanation is that its `stall_margin` input already encodes each configuration's own stall angle. Retraining on the configuration family did not improve ranking on unfamiliar aircraft in this simulator.

## 5. Item 46 — abstention (τ set for 5% abstention on TRAIN validation rows)

| Score | Abstention SEEN / IDH / OOD / C00 | Row error all → retained (OOD) | Error AUROC (SEEN / OOD) | Protocol verdict |
|---|---|---|---|---|
| `U_amb` (p(1−p)) | 4.6% / 5.1% / 4.6% / 6.1% | 3.22% → 2.72% | 0.886 / 0.868 | retained error lower everywhere; **does not** abstain more on OOD → *not useful* by the rule |
| `U_ens` (seed spread) | 4.7% / 5.2% / 8.5% / 3.7% | 3.22% → 2.08% | 0.851 / 0.855 | **useful** (both parts pass) |
| `U_nov` (kNN novelty) | 5.2% / 4.9% / 7.2% / 5.5% | 3.22% → 2.85% | 0.332 / 0.502 | abstains more on OOD, but retained error is *higher* on SEEN (3.84% vs 3.82%) → *not useful* |

The novelty score does detect unfamiliar inputs (more abstention on OOD, and 19–21% on JSBSim data, §8), but it does not detect errors. Its error AUROC is at or below chance, because the model's mistakes occur in ordinary-looking states near the stall boundary, not in unusual ones. Only the seed-ensemble spread both concentrates on errors and rises under shift. H3's first part (novelty abstains more under shift) holds; "abstention is useful" holds only for `U_ens`.

## 6. Item 47 — uncertainty under distribution shift

- Error AUROC stays at 0.85–0.89 for `U_amb` and `U_ens` in every group → **remains informative under shift** for both; not for `U_nov`.
- Split conformal (target 90%, calibrated on TRAIN validation rows): marginal coverage 0.908 SEEN, 0.912 IDH, 0.918 OOD, 0.905 C00 → **no coverage failure on OOD**. Positive-class coverage, however, is 0.77–0.83 in every group, including SEEN. The prediction sets under-cover pre-stall rows regardless of shift, a known property of marginal (not class-conditional) conformal prediction under class imbalance.
- Calibration degrades mildly under shift: `M_D` ECE 0.071 (SEEN) → 0.084 (OOD); Brier scores in `primary.json`.

H3's second part (probability uncertainty less informative under shift, conformal coverage drops) is **not supported** at this degree of shift.

## 7. Item 52 — operating conditions (`M_D`; all groups pooled; cells with < 10 events marked)

| Slice | Events | PR-AUC | Recall | Median lead (s) | False warnings / h |
|---|---|---|---|---|---|
| regime: gradual approach | 331 | 0.901 | 0.973 | 4.56 | 39.9 |
| regime: abrupt stall entry | 304 | 0.962 | 1.000 | 0.70 | 31.8 |
| regime: normal | 2 (insufficient) | — | — | — | 12.0 |
| V0/V_stall 1.15–1.6 | 423 | 0.923 | 0.995 | 4.27 | 84.5 |
| V0/V_stall 1.6–2.2 | 148 | 0.785 | 0.953 | 0.71 | 8.7 |
| V0/V_stall 2.2–2.87 | 66 | 0.764 | 1.000 | 0.80 | 1.6 |
| ρ 0.905–1.012 / 1.012–1.118 / 1.118–1.225 | 217 / 195 / 225 | 0.878 / 0.888 / 0.871 | 0.995 / 0.995 / 0.969 | 1.84 / 2.02 / 1.82 | 38.8 / 30.8 / 18.5 |
| wing loading tertile 1 / 2 / 3 | 210 / 148 / 279 | 0.861 / 0.884 / 0.890 | 0.976 / 0.986 / 0.993 | 1.20 / 2.21 / 2.19 | 11.7 / 42.3 / 37.9 |
| entry rate < 2°/s / 2–5°/s / ≥ 5°/s | 20 / 97 / 520 | — | 1.000 / 0.918 / 0.998 | 2.41 / 2.37 / 1.33 | — |

The aggregate hides large differences. Multi-second warning exists for gradual approaches from low speed; abrupt high-rate entries get well under a second; entries at 2–5°/s have the lowest recall (0.92). Air density and wing loading make little difference. Most false warnings come from low-speed starts. The same pattern holds within OOD alone (`primary.json` → `item52.OOD`).

## 8. Items 48–49 — JSBSim

**Feasibility (Item 48).** `c172p` passed F1–F4: lift-table peak at α = 0.28 rad (CLmax 1.47); trim over 1.3–2.0 V_stall; a full nose-up ramp reaches α ≈ 0.73 rad; all states readable. With this harness, `c172x` and `c182` failed F3 and `pa28` and `c310` failed F2; not investigated further.

**Cross-simulator test (Item 49, with P4-D1 to P4-D5).** 1,000 c172p trajectories (seed 20261017), 906 with usable rows. Crossing rates: stall regime 32%, gradual 29%, normal 1.9% (AeroGuard v0.3: 61%, 13%, 0%). Test split: 128 trajectories, **30 stall events**, so event metrics are coarse.

| Model (seed 20260817) | Trained on | PR-AUC (JSB test) | Recall | Median lead (s) | False warnings / h | ECE |
|---|---|---|---|---|---|---|
| `X_D` | AeroGuard only | 0.780 [0.708, 0.827] | 30/30 | 1.20 [0.94, 3.62] | 48.0 | 0.024 |
| `X_D_noSM` | AeroGuard only | 0.783 [0.702, 0.833] | 30/30 | 1.20 | 41.1 | 0.018 |
| `R_AoA` | AeroGuard threshold | 0.750 [0.654, 0.828] | 30/30 | 0.44 | 6.9 | — |
| `X_D` native reference | JSBSim train split | 0.937 [0.894, 0.965] | 30/30 | 4.79 [3.78, 5.00] | 95.9 | 0.058 |
| `X_D` on AeroGuard IDH | AeroGuard only | 0.887 | 201/202 | 3.11 | 45.9 | 0.077 |

On all 906 JSBSim trajectories (secondary, 256 events) `X_D` gives PR-AUC 0.826 [0.804, 0.844] against 0.778 [0.751, 0.805] for `R_AoA`. Across five seeds the cross-simulator PR-AUC is 0.774–0.788 and the native 0.936–0.937. Novelty-based abstention rises from the designed 5% to 19% (test) and 21% (all) on JSBSim inputs.

**Interpretation.** A warning learned only in AeroGuard keeps skill in a second, more detailed simulator model: every test stall was warned, and on the larger population it ranks better than the angle-of-attack rule. It loses a large part of what is achievable there: PR-AUC 0.78 versus 0.94 natively, median lead 1.2 s versus 4.8 s. **H5 is supported.** The c172p is itself an approximation (assumptions audit), so this is model-to-model transfer, not validation against flight data.

## 9. Item 50 — published evidence (`item50.json`)

| Quantity | AeroGuard | Reference | Difference | Band | Level | Result |
|---|---|---|---|---|---|---|
| lift slope, α 0–12° | 5.76 /rad | 4.97 /rad (c172p table) | +15.9% | ±15% | J | outside |
| CLmax | 1.736 | 1.47 (c172p table) | +18.1% | ±10% | J | outside |
| α at CLmax | 16.07° | 16.04° (c172p table) | +0.03° | ±2° | J | within |
| CLmax implied by C172R 51 KCAS at 2,450 lb | 1.736 | 1.596 | +8.8% | ±10% | S | within |
| 1 g stall speed at 2,450 lb, sea level | 25.2 m/s | 26.2 m/s | −4.1% | ±10% | S | within |

No primary experimental source (NACA TR-824, POH) could be opened from the research environment, so none of these is agreement or disagreement with experimental evidence. Against the c172p model, AeroGuard's lift curve is steeper and peaks higher at the same stall angle; against the secondary C172R stall speed it is within the bands. Correction: an earlier status note (`experiments/phase4/STATUS.md`, superseded) gave AeroGuard's stall speed at 1,111 kg as 24.7 m/s; the correct value is 25.2 m/s.

## 10. Item 51 — assumptions

See [`SIMULATOR_ASSUMPTIONS.md`](../../../experiments/phase4/SIMULATOR_ASSUMPTIONS.md) (A1–A14). The JSBSim result is consistent with the audit's warning: the linear pitch surrogate (A2) gives AeroGuard about five times the c172p's static angle-of-attack response per unit elevator (P4-D2), which is one reason AeroGuard inputs had to be converted and why the stall-entry dynamics differ.

## 11. Item 53 — robustness

20 runs: partitions P0/P1/P2 × data seeds D0/D1 × model seeds (5 for P0-D0 at 0.01 s resolution, 3 for the other five combinations at the pre-specified 0.05 s evaluation stride). Verdict rule (pre-specified): **persists** if the sign holds in ≥ 90% of runs and the primary paired 95% interval lies entirely in favour; **fragile** if the sign holds in 50–90%; otherwise **not supported**.

| Claim | Group | Sign holds | Primary paired difference [95% CI] | Verdict |
|---|---|---|---|---|
| K1 `M_D` PR-AUC > `M_A` | IDH | 20/20 | +0.036 [+0.026, +0.046] | **persists** |
| K1 | OOD | 20/20 | +0.046 [+0.033, +0.059] | **persists** |
| K2 `M_D` median lead > `M_A` | IDH | 9/20 | −1.68 s [−2.42, −0.45] | **not supported** |
| K2 | OOD | 9/20 | −0.82 s [−2.24, −0.34] | **not supported** |
| K3 `M_D` recall ≥ `R_AoA` | IDH | 14/20 | −0.005 [−0.016, 0.000] | **fragile** |
| K3 | OOD | 2/20 | −0.018 [−0.036, −0.004] | **not supported** |
| K4 `M_D` PR-AUC ≥ `M_D_noSM` | OOD | 20/20 | +0.006 [+0.001, +0.010] | **persists** (small) |

Median `M_D` PR-AUC per combination ranges 0.874–0.892 on IDH and 0.865–0.874 on OOD (`robustness_runs.csv`), so the item 44–45 picture does not depend on the partition or data seed.

**Interpretation.** The temporal model's ranking advantage over the instantaneous model persists everywhere. Its lead-time and recall "advantages" do not, but both comparisons are made at each model's own validation-selected threshold. `M_A` and `R_AoA` reach their recall and lead by warning much more often (`M_A` 3–4× the false-warning rate on OOD) or very close to the boundary (`R_AoA` median lead 0.7 s). K2 and K3 therefore compare operating points, not models. H4 is **supported for PR-AUC and not supported for lead time** as pre-specified. A threshold-matched lead-time comparison (as in Items 40–42) would be needed to separate model from operating point.

## 12. Summary of pre-specified outcomes

| Item | Outcome |
|---|---|
| 44 | Generalises within the training envelope (no loss detected; CI ±0.03–0.05) |
| 45 | Modest loss on unfamiliar configurations, mainly lead time; no detectable trend with distance; part of the expectation was untestable as specified |
| 46 | Ensemble spread is useful for abstention; ambiguity and novelty are not by the pre-specified rule; novelty detects shift but not errors |
| 47 | Ambiguity and ensemble uncertainty stay informative; no conformal coverage failure under this shift; positive-class under-coverage everywhere |
| 48 | JSBSim c172p suitable |
| 49 | Cross-simulator transfer keeps partial skill (PR-AUC 0.78 vs native 0.94; lead 1.2 s vs 4.8 s) |
| 50 | Within bands against secondary C172R data; outside bands against the c172p model; no primary source checked |
| 51 | Audit complete |
| 52 | Large regime differences hidden by aggregates (gradual 4.6 s vs abrupt 0.7 s lead) |
| 53 | PR-AUC advantage over the instantaneous model persists; lead-time and recall advantages at own thresholds are not supported (operating-point confounded); stall-margin input gives a small persistent gain on unfamiliar configurations |

## 13. Reproduction

Environment: CPython 3.13, `requirements-pinned.txt` plus `jsbsim==1.3.2`. Datasets, fitted models and score arrays are written to `<data_dir>` (not committed; about 3 GB).

```
python scripts/phase4_generate.py <data_dir> D0 4
python scripts/phase4_generate.py <data_dir> D1 4
python scripts/phase4_generate_jsbsim.py <data_dir>
python scripts/run_phase4.py <data_dir> <run_dir> primary     # ~2 h on 4 cores
python scripts/run_phase4.py <data_dir> <run_dir> jsbsim      # ~10 min
python scripts/run_phase4.py <data_dir> <run_dir> robust      # ~70 min
python scripts/phase4_item50.py <run_dir>/item50.json
python -m pytest tests/test_phase4_core.py
```
