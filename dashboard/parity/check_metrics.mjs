// Checks every number in src/data/metrics.json against the frozen research
// outputs it was exported from (see data_export/export_metrics.py), and the
// eligible-event coverage figures hard-coded in the Evaluation section against
// the Item 38 output. Read-only; no Python environment needed.
//
//   node parity/check_metrics.mjs        (from dashboard/)
//
// Exit status is non-zero on any mismatch.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = join(here, "..", "..");
const json = (p) => JSON.parse(readFileSync(join(ROOT, p), "utf8").replace(/\bNaN\b/g, "null"));

const site = JSON.parse(readFileSync(join(here, "..", "src", "data", "metrics.json"), "utf8"));
const v02 = json("outputs/ml_temporal/metrics/primary_model_metrics.json");
const v03 = json("outputs/ml_v03/metrics/primary_model_metrics.json");
const zero = json("outputs/ml_v03/metrics/generalization_check.json");
const gen = "outputs/ml_v03_generalization/metrics/";
const fwd = json(gen + "forward_check_frozen_model_on_alt_mechanism.json");
const rev = json(gen + "reverse_check_alt_model_on_v03_gradual.json");
const summary = json(gen + "experiment_summary.json");
const item38 = json("outputs/items33_42/items37_39/run_20261015T143215846532Z/coverage_item38.json");

let failed = 0;
let checked = 0;
// metrics.json stores values rounded to 4 decimals (2 for some lead times).
function eq(label, shown, source, tol = 5e-5) {
  checked++;
  const ok = typeof source === "number" ? Math.abs(shown - source) <= tol : shown === source;
  if (!ok) {
    failed++;
    console.log(`MISMATCH ${label}: site=${shown} source=${source}`);
  }
}

function eventBlock(label, s, src, { prAuc = true } = {}) {
  if (prAuc) eq(`${label}.prAuc`, s.prAuc, src.test_metrics.pr_auc);
  eq(`${label}.eventRecall`, s.eventRecall, src.event_level.event_recall);
  if ("nEvents" in s) eq(`${label}.nEvents`, s.nEvents, src.event_level.n_events);
  if ("nWarned" in s) eq(`${label}.nWarned`, s.nWarned, src.event_level.n_warned);
  eq(`${label}.medianLeadTimeS`, s.medianLeadTimeS, src.event_level.median_lead_time_s, 5e-3);
  if ("meanLeadTimeS" in s) eq(`${label}.meanLeadTimeS`, s.meanLeadTimeS, src.event_level.mean_lead_time_s);
  for (const [k, v] of Object.entries(s.warningCoverage ?? {}))
    eq(`${label}.warningCoverage[${k}]`, v, src.fraction_of_events_detected_at_least[k]);
  // Displayed recall must agree with the counts it is shown next to.
  if ("nEvents" in s) eq(`${label} recall vs counts`, s.eventRecall, s.nWarned / s.nEvents);
}

eventBlock("v02", site.v02, v02);
eventBlock("v03", site.v03, v03);
eq("v03.rocAuc", site.v03.rocAuc, v03.test_metrics.roc_auc);
eq("v03.precision", site.v03.precision, v03.test_metrics.precision);
eq("v03.recall", site.v03.recall, v03.test_metrics.recall);
eq("v03.threshold", site.v03.threshold, v03.threshold);
site.v03.leadTimeRecallBuckets.forEach((b, i) => {
  const src = v03.lead_time_recall_bucket[i];
  for (const k of ["bucket", "n_positive_rows", "n_warned", "n_missed"]) eq(`v03.bucket[${i}].${k}`, b[k], src[k]);
  eq(`v03.bucket[${i}].recall`, b.recall, src.recall);
});

eventBlock("generalization.forward", site.generalization.forward, fwd);
eventBlock("generalization.reverse", site.generalization.reverse, rev);
eq("zeroExposure.prAuc", site.generalization.zeroExposureExclusion.prAuc, zero.test_metrics.pr_auc);
eq("zeroExposure.eventRecall", site.generalization.zeroExposureExclusion.eventRecall, zero.event_level.event_recall);
eq("zeroExposure.medianLeadTimeS", site.generalization.zeroExposureExclusion.medianLeadTimeS, zero.event_level.median_lead_time_s, 5e-3);
for (const [k, v] of Object.entries(site.generalization.forwardPopulation))
  eq(`forwardPopulation.${k}`, v, summary.forward_check_holdout_population[k]);
for (const [k, v] of Object.entries(site.generalization.reverseTrainPopulation))
  eq(`reverseTrainPopulation.${k}`, v, summary.reverse_check_train_population[k]);

// Split sizes against the committed manifest.
const split = readFileSync(join(ROOT, "data/splits/split_manifest_v3.csv"), "utf8").trim().split("\n").slice(1);
const count = (s) => split.filter((l) => l.endsWith("," + s)).length;
eq("dataset.trajectories", site.dataset.trajectories, split.length);
eq("dataset.trainTrajectories", site.dataset.trainTrajectories, count("train"));
eq("dataset.valTrajectories", site.dataset.valTrajectories, count("val"));
eq("dataset.testTrajectories", site.dataset.testTrajectories, count("test"));

// Evaluation section: "Warned >= 2 s / 4 s" for the frozen temporal model and
// the eligible-event denominators quoted beneath the table.
const ft = item38.methods.frozen_temporal.coverage;
eq("evaluation frozen ≥2s (shown 0.66)", 0.66, ft["2s"].primary_all_events.point, 5e-3);
eq("evaluation frozen ≥4s (shown 0.63)", 0.63, ft["4s"].primary_all_events.point, 5e-3);
eq("evaluation eligible events at 2s (shown 74)", 74, ft["2s"].primary_all_events.denominator);
eq("evaluation eligible events at 4s (shown 67)", 67, ft["4s"].primary_all_events.denominator);
// Same warned events as Key Results' all-event coverage, different denominator.
eq("≥2s numerator matches Key Results", ft["2s"].primary_all_events.numerator, Math.round(site.v03.warningCoverage[">=2s"] * site.v03.nEvents));
eq("≥4s numerator matches Key Results", ft["4s"].primary_all_events.numerator, Math.round(site.v03.warningCoverage[">=4s"] * site.v03.nEvents));

console.log(`${checked - failed}/${checked} checks passed`);
process.exit(failed ? 1 : 0);
