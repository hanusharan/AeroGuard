# Proposed amendment: scope of the event-level metrics

**Status: proposal only. Not applied.** The research paper
(`AeroGuard_Research_Paper.md`, its HTML copies and PDFs) is unchanged and is
the published record (Zenodo DOI 10.5281/zenodo.22724022). This file is for the
author to review. Applying it would change wording only; no reported number
changes. Doing so would require rebuilding the PDF and publishing a new
Zenodo version, and needs the author's approval.

## Why

The paper reports "event recall 96.1% (73/76)" and a "median credited lead time
of 4.72 s" without saying (a) which events are in the 76, (b) that the median is
over warned events only, or (c) that some test crossings are outside the
evaluated rows. Section 3 mentions "456 test trajectories" but not that the test
split has 473. The frozen v0.3 report (`outputs/ml_v03/v03_temporal_ml_report.md`)
already contains the underlying counts.

## Evidence (all from tracked artifacts)

| Statement | Source |
|---|---|
| Test split: 473 trajectories; 456 have at least one evaluated row | `primary_model_metrics.json` → `population` |
| 76 events, 73 warned, 3 missed; recall 0.9605 | same file → `event_level` |
| Median 4.72 s is the median of the 73 stored warned-event lead times (mean 3.42 s, min 0.14 s, max 5.0 s; 29 at the 5 s cap) | same file → `event_level.lead_times_s` |
| 67 test crossings, 57 in the evaluated rows (gradual 42/40, stall 25/17); 54 of the 57 first crossings warned (37/40, 17/17) | `physics_vs_ml_summary.json` |
| 76 events = 57 first crossings + 19 second episodes | v0.3 report ("19 v0.3 test trajectories re-enter") and `physics_vs_ml_summary.json` |
| The 10 other crossings are first crossings of 10 different test trajectories that fall within the last 5 s of the trajectory (8 stall, 2 gradual; 6 of them in trajectories shorter than 6 s, which have no evaluated rows) | `trajectory_metadata_v3.csv` (`time_of_first_stall`, `duration_actual_s`, `n_steps`) with `data/splits/split_manifest_v3.csv` |
| Evaluated rows need a label (last 5 s excluded) and a full 1 s feature window | `ml/temporal_features.py:usable_mask_for_window`, `ml/events.py` |

## Proposed text changes

**1. Section 2.4 (Evaluation Protocol).** After the sentence ending
"...(capped at that horizon), and **warning coverage at τ** is the fraction of
events warned at least τ s ahead.", add:

> Events are counted only within the evaluated rows, which require an available
> label (the last 5 s of each trajectory has no complete future window) and a
> full feature window. A crossing in the last 5 s of a trajectory is therefore
> outside the evaluation; it is neither warned nor missed. The median credited
> lead time is taken over warned events only, and missed events carry no lead
> time. An event is a maximal run of unsafe samples, so a trajectory that
> re-enters the unsafe region contributes more than one event.

**2. Section 3 results sentence.** Replace "(538,034 test rows, 456 test
trajectories)" with "(538,034 evaluated test rows from 456 of the 473 test
trajectories)", and "event recall **96.1% (73/76)** and a **median credited lead
time of 4.72 s**" with "event recall **96.1% (73/76 evaluated events)** and a
**median credited lead time of 4.72 s among the 73 warned events**".

**3. New sentence after that result:**

> The 76 evaluated events are 57 first crossings and 19 second episodes in
> trajectories that re-enter the unsafe region. Ten further test crossings (8
> `stall`, 2 `gradual_approach_v3`), each the first crossing of a different
> trajectory, fall in the last 5 s of their trajectories and are outside the
> evaluation. Among the 57 first crossings, 54 were warned.

**4. Table 1 caption.** Append: "Event recall and median lead time are over the
evaluated events (see §2.4); the median lead time is over warned events only."

**5. Abstract and Conclusion.** Change "96.1% event recall and a 4.72 s median
lead" to "96.1% event recall (evaluated events) and a 4.72 s median lead among
warned events".

**6. Limitations, "Small absolute event counts".** Append: "The evaluated events
exclude ten test crossings that occur in the last 5 s of their trajectories,
mostly in the `stall` regime (8 of 25 `stall` crossings versus 2 of 42
`gradual_approach_v3`); the effect of these events on recall was not measured."

## Not included on purpose

Hypothetical recall values obtained by assuming the ten excluded events were all
warned or all missed are not proposed for publication, because they would
present assumptions as results. A measured value would need predictions on the
rows outside the evaluation, which the current pipeline does not produce.

## Open points for the author

- Whether to apply any of this, and whether to republish.
- Whether to add a measured analysis of the excluded events (new work that
  needs the regenerated data).
- The same headline numbers also appear on the dashboard and in
  `dashboard/public/docs/AEROGUARD_README.md`; these were not changed.
