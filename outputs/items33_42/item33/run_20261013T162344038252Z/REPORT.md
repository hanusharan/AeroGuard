# AeroGuard Item 33: control-input ablation report (run run_20261013T162344038252Z)

> Computed on a regenerated copy of the v0.3 data (Item 26); the original v0.3 dataset is absent. The test split was exposed by earlier analyses. These results are a controlled re-evaluation of previously exposed data: they are not blind, not independent replication, and say nothing about real aircraft. Ablation shows dependence of predictive information, not causal effects.

Protocol: `experiments/items33_42/item33/PROTOCOL.md`, SHA-256 `742f55a9cc4e5da0474de84bf40cc6ffcb63a4ed46f12c3d2536ac57b21c4dc7` (locked).

## 1. Evaluated population
- n_rows: 538034
- n_trajectories: 456
- n_positive: 46169
- n_negative: 491865
- population_id: test_usable_1s:806ab81b786ec704

## 2. Conditions

| Condition | Features | Status |
|---|---|---|
| C0 | 23 | baseline |
| C1 | 21 | primary |
| C2 | 20 | primary |
| C3 | 16 | exploratory |
| X1 | 22 | exploratory |

## 3. Retrained feature ablation (analysis family: retrained_ablation)

Seed variability and trajectory-bootstrap uncertainty are different sources of variation and are reported separately. They are never combined into one interval.

### D1: C0 - C1 (pr_auc; status: primary)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.0001929202616; median -9.210981333e-05.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.003899565522, 0.003553888524]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Bonferroni-adjusted sensitivity interval (m = 2, percentile [1.25, 98.75]): [-0.004556313295, 0.004002953847].
- Seed variability (descriptive, not an interval): min -0.0007268279139, max 0.001008946446, SD 0.0007605017224; all per-seed deltas share one sign: False.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: -0.0007268279139; [-0.004822431536, 0.002474210267]
  - seed 20261101: 0.001008946446; [-0.002859264443, 0.004648875684]
  - seed 20261102: 0.0009551033972; [-0.002954036908, 0.004331246708]
  - seed 20261103: -9.210981333e-05; [-0.005929189917, 0.004586247904]
  - seed 20261104: -0.0001805108076; [-0.004332429521, 0.003401369457]

**Statement:** No difference was demonstrated under this protocol (the interval includes 0). This does not show that the two conditions perform alike.

### D2: C0 - C2 (pr_auc; status: primary)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.0005192492632; median 0.0005237846253.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.003604356635, 0.004087314845]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Bonferroni-adjusted sensitivity interval (m = 2, percentile [1.25, 98.75]): [-0.004352144396, 0.004577598626].
- Seed variability (descriptive, not an interval): min -0.0006034811267, max 0.001936417361, SD 0.0009272272645; all per-seed deltas share one sign: False.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: 0.0006201620459; [-0.003837952145, 0.004222961985]
  - seed 20261101: 0.001936417361; [-0.002610984725, 0.006212658733]
  - seed 20261102: 0.0005237846253; [-0.00274633005, 0.003842531183]
  - seed 20261103: 0.0001193634105; [-0.005315780576, 0.004597290531]
  - seed 20261104: -0.0006034811267; [-0.00457483688, 0.002800057815]

**Statement:** No difference was demonstrated under this protocol (the interval includes 0). This does not show that the two conditions perform alike.

### SEC-2: C1 - C2 (pr_auc; status: secondary)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.0003263290016; median 0.0002114732238.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.0003743266886, 0.0009728611717]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Seed variability (descriptive, not an interval): min -0.0004313187719, max 0.00134698996, SD 0.0007987164487; all per-seed deltas share one sign: False.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: 0.00134698996; [-0.0005584948431, 0.003553042746]
  - seed 20261101: 0.000927470915; [-0.0007340676238, 0.002642914152]
  - seed 20261102: -0.0004313187719; [-0.002426012754, 0.001429088442]
  - seed 20261103: 0.0002114732238; [-0.001470043905, 0.001824185332]
  - seed 20261104: -0.000422970319; [-0.001993227276, 0.0009836300085]

**Statement:** No difference was observed (secondary, unadjusted; the interval includes 0).

### SEC-3: C0 - C1 (roc_auc; status: secondary)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.0006317461527; median 0.000563906197.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.001226836423, 0.003052193171]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Seed variability (descriptive, not an interval): min 8.727109965e-05, max 0.001358658208, SD 0.0004881349234; all per-seed deltas share one sign: True.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: 8.727109965e-05; [-0.001434613571, 0.001624618717]
  - seed 20261101: 0.000563906197; [-0.001044660479, 0.002701659734]
  - seed 20261102: 0.001358658208; [-0.0006362690237, 0.004337229831]
  - seed 20261103: 0.0008163981348; [-0.00244691865, 0.005066183655]
  - seed 20261104: 0.0003324971245; [-0.001494168692, 0.002219030245]

**Statement:** No difference was observed (secondary, unadjusted; the interval includes 0).

### SEC-3: C0 - C2 (roc_auc; status: secondary)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.0006931732966; median 0.0007973372727.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.00112393182, 0.003056891669]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Seed variability (descriptive, not an interval): min -5.822175957e-05, max 0.001495179788, SD 0.000570950978; all per-seed deltas share one sign: False.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: 0.0007973372727; [-0.0008878427457, 0.002786723043]
  - seed 20261101: 0.001495179788; [-0.001056285055, 0.005277932786]
  - seed 20261102: 0.0004243394025; [-0.0008964965698, 0.002169352695]
  - seed 20261103: 0.0008072317788; [-0.002134030372, 0.004553443528]
  - seed 20261104: -5.822175957e-05; [-0.001641480193, 0.001352405735]

**Statement:** No difference was observed (secondary, unadjusted; the interval includes 0).

### X-a: C0 - C3 (pr_auc; status: exploratory)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.002116047217; median 0.002011883229.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.001803489507, 0.005729537624]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Seed variability (descriptive, not an interval): min 0.0008490561782, max 0.004216554688, SD 0.001282084976; all per-seed deltas share one sign: True.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: 0.001376709825; [-0.003266702297, 0.005648515601]
  - seed 20261101: 0.004216554688; [0.0002377580725, 0.008018883807]
  - seed 20261102: 0.002011883229; [-0.001619303362, 0.005623834978]
  - seed 20261103: 0.002126032163; [-0.002528737686, 0.006423241499]
  - seed 20261104: 0.0008490561782; [-0.003398021038, 0.004742632185]

**Statement:** No difference was observed (exploratory, unadjusted; the interval includes 0).

### X-b: C0 - X1 (pr_auc; status: exploratory)

- Estimate (mean over seeds [20260817, 20261101, 20261102, 20261103, 20261104]): 0.0001020924374; median -0.0001302909058.
- Trajectory-bootstrap interval for the seed mean (percentile [2.5, 97.5]): [-0.001005131019, 0.001047618292]; undefined replicates: 0. test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability.
- Seed variability (descriptive, not an interval): min -0.0003648383578, max 0.0007118617167, SD 0.0005054693918; all per-seed deltas share one sign: False.
- Per-seed deltas (point; trajectory-bootstrap interval):
  - seed 20260817: -0.0002856528342; [-0.001988015206, 0.001527425836]
  - seed 20261101: -0.0003648383578; [-0.002541047699, 0.001623543412]
  - seed 20261102: -0.0001302909058; [-0.001756119595, 0.001294664561]
  - seed 20261103: 0.0005793825679; [-0.002498056272, 0.003140226565]
  - seed 20261104: 0.0007118617167; [-0.0006664588505, 0.001963512531]

**Statement:** No difference was observed (exploratory, unadjusted; the interval includes 0).

### PR-AUC by condition and seed (descriptive spread across seeds)

- C0: mean 0.8909057454, median 0.8907133797, min 0.8904915379, max 0.8916254385, SD 0.0004443821567
- C1: mean 0.8907128251, median 0.8906720487, min 0.890062862, max 0.8914402076, SD 0.0004914374221
- C2: mean 0.8903864961, median 0.8904941808, min 0.8896890211, max 0.8910950191, SD 0.0005283347995
- C3: mean 0.8887896982, median 0.8890060822, min 0.8874088838, max 0.8896424818, SD 0.0008711007415
- X1: mean 0.8908036529, median 0.8909990325, min 0.8897796762, max 0.8919902769, SD 0.0008813651863

## 4. Regime-stratified sensitivity (SR; no decision role)

- D1: stratified interval [-0.003991234488, 0.003373060968] versus primary [-0.003899565522, 0.003553888524]; zero-inclusion agrees: True.
- D2: stratified interval [-0.003816473183, 0.00375815625] versus primary [-0.003604356635, 0.004087314845]; zero-inclusion agrees: True.

## 5. Reproduction diagnostic (C0 at seed 20260817 versus the frozen model)

- Level: R1; scores bit-identical: False; max absolute score difference 0.07029479268; threshold difference 0.002445897901.
- PR-AUC(C0) - PR-AUC(frozen): 0.0004359019497, interval [-0.0004179436582, 0.001589583694].

## 6. Matched operating point (exploratory, validation-defined)

- C0 (seed 20260817): threshold 0.8605622675, achieved validation FPR 0.006579870244 (target 0.006579870244).
- C1 (seed 20260817): threshold 0.8532364351, achieved validation FPR 0.006448360512 (target 0.006579870244).
- C2 (seed 20260817): threshold 0.8602902734, achieved validation FPR 0.006251095914 (target 0.006579870244).
- C3 (seed 20260817): threshold 0.8590697669, achieved validation FPR 0.006134928985 (target 0.006579870244).
- X1 (seed 20260817): threshold 0.8605531348, achieved validation FPR 0.006281781518 (target 0.006579870244).
- C0 (seed 20261101): threshold 0.8610225727, achieved validation FPR 0.006323426267 (target 0.006323426267).
- C1 (seed 20261101): threshold 0.8569272447, achieved validation FPR 0.006229177626 (target 0.006323426267).
- C2 (seed 20261101): threshold 0.859680847, achieved validation FPR 0.006268630545 (target 0.006323426267).
- C3 (seed 20261101): threshold 0.8612767406, achieved validation FPR 0.005988076451 (target 0.006323426267).
- X1 (seed 20261101): threshold 0.8628425859, achieved validation FPR 0.006323426267 (target 0.006323426267).
- C0 (seed 20261102): threshold 0.8570144471, achieved validation FPR 0.006091092408 (target 0.006091092408).
- C1 (seed 20261102): threshold 0.8640587441, achieved validation FPR 0.006091092408 (target 0.006091092408).
- C2 (seed 20261102): threshold 0.8637454167, achieved validation FPR 0.006091092408 (target 0.006091092408).
- C3 (seed 20261102): threshold 0.8614118313, achieved validation FPR 0.006031913028 (target 0.006091092408).
- X1 (seed 20261102): threshold 0.8690972818, achieved validation FPR 0.005959582676 (target 0.006091092408).
- C0 (seed 20261103): threshold 0.864403236, achieved validation FPR 0.006165614589 (target 0.006165614589).
- C1 (seed 20261103): threshold 0.8601412232, achieved validation FPR 0.006060406803 (target 0.006165614589).
- C2 (seed 20261103): threshold 0.863853243, achieved validation FPR 0.006165614589 (target 0.006165614589).
- C3 (seed 20261103): threshold 0.8611567604, achieved validation FPR 0.006099859723 (target 0.006165614589).
- X1 (seed 20261103): threshold 0.8681462617, achieved validation FPR 0.006165614589 (target 0.006165614589).
- C0 (seed 20261104): threshold 0.8689972772, achieved validation FPR 0.006042872173 (target 0.006042872173).
- C1 (seed 20261104): threshold 0.8636036046, achieved validation FPR 0.006042872173 (target 0.006042872173).
- C2 (seed 20261104): threshold 0.8669287444, achieved validation FPR 0.006038488515 (target 0.006042872173).
- C3 (seed 20261104): threshold 0.86444239, achieved validation FPR 0.00599026828 (target 0.006042872173).
- X1 (seed 20261104): threshold 0.8712371725, achieved validation FPR 0.006027529371 (target 0.006042872173).

## 7. Frozen-model input masking (analysis family: frozen_model_masking)

This is a perturbation of the frozen model's inputs. It is a separate, descriptive analysis and does not measure the same quantity as the retrained ablation above. Replaced values can be out-of-distribution.

- M-A-MS1: PR-AUC 0.8438502535; change versus unmasked frozen model -0.04642722425.
- M-A-MS2-20261201: PR-AUC 0.8089911624; change versus unmasked frozen model -0.08128631528.
- M-A-MS2-20261202: PR-AUC 0.8085235803; change versus unmasked frozen model -0.08175389738.
- M-A-MS2-20261203: PR-AUC 0.8085603211; change versus unmasked frozen model -0.08171715662.
- M-A-MS2-20261204: PR-AUC 0.8087150348; change versus unmasked frozen model -0.08156244291.
- M-A-MS2-20261205: PR-AUC 0.8079981375; change versus unmasked frozen model -0.08227934025.
- M-A-MS3-20261201: PR-AUC 0.8744085886; change versus unmasked frozen model -0.0158688891.
- M-A-MS3-20261202: PR-AUC 0.8746412555; change versus unmasked frozen model -0.01563622218.
- M-A-MS3-20261203: PR-AUC 0.8747655033; change versus unmasked frozen model -0.01551197438.
- M-A-MS3-20261204: PR-AUC 0.8743205443; change versus unmasked frozen model -0.01595693342.
- M-A-MS3-20261205: PR-AUC 0.8750496257; change versus unmasked frozen model -0.01522785199.
- M-B-MS1: PR-AUC 0.8741672126; change versus unmasked frozen model -0.01611026511.
- M-B-MS2-20261201: PR-AUC 0.87672292; change versus unmasked frozen model -0.01355455772.
- M-B-MS2-20261202: PR-AUC 0.8767316898; change versus unmasked frozen model -0.01354578792.
- M-B-MS2-20261203: PR-AUC 0.8764114174; change versus unmasked frozen model -0.01386606035.
- M-B-MS2-20261204: PR-AUC 0.876623439; change versus unmasked frozen model -0.0136540387.
- M-B-MS2-20261205: PR-AUC 0.8765271681; change versus unmasked frozen model -0.01375030961.
- M-B-MS3-20261201: PR-AUC 0.8795209107; change versus unmasked frozen model -0.010756567.
- M-B-MS3-20261202: PR-AUC 0.879694779; change versus unmasked frozen model -0.01058269865.
- M-B-MS3-20261203: PR-AUC 0.8797947167; change versus unmasked frozen model -0.01048276104.
- M-B-MS3-20261204: PR-AUC 0.8793360841; change versus unmasked frozen model -0.01094139365.
- M-B-MS3-20261205: PR-AUC 0.8796455966; change versus unmasked frozen model -0.01063188106.
- M-C-MS1: PR-AUC 0.8180190727; change versus unmasked frozen model -0.07225840499.
- M-C-MS2-20261201: PR-AUC 0.7863155586; change versus unmasked frozen model -0.1039619191.
- M-C-MS2-20261202: PR-AUC 0.7856411469; change versus unmasked frozen model -0.1046363308.
- M-C-MS2-20261203: PR-AUC 0.7852896432; change versus unmasked frozen model -0.1049878345.
- M-C-MS2-20261204: PR-AUC 0.7852583039; change versus unmasked frozen model -0.1050191738.
- M-C-MS2-20261205: PR-AUC 0.784958107; change versus unmasked frozen model -0.1053193707.
- M-C-MS3-20261201: PR-AUC 0.864119452; change versus unmasked frozen model -0.02615802572.
- M-C-MS3-20261202: PR-AUC 0.86427501; change versus unmasked frozen model -0.02600246769.
- M-C-MS3-20261203: PR-AUC 0.8647633449; change versus unmasked frozen model -0.02551413283.
- M-C-MS3-20261204: PR-AUC 0.8638931142; change versus unmasked frozen model -0.02638436351.
- M-C-MS3-20261205: PR-AUC 0.8647709536; change versus unmasked frozen model -0.02550652411.

## 8. Failures and undefined results

No failed fit or undefined replicate was recorded.

## 9. Historical figures (context only; not recomputed here)

- E0 stored frozen-model PR-AUC (original evaluation): 0.8902774777
- E1 Phase 3 frozen-model PR-AUC (regenerated data): 0.8902774777
- E1 Phase 3 instantaneous Model A PR-AUC (regenerated data): 0.8754338391

## 10. Limitations

- The original v0.3 dataset is absent; the regenerated copy is not shown to be byte-identical to it.
- The test split was previously exposed; nothing here is blind or independent.
- Controls are scripted and open-loop; state-derived features can carry control information, so no condition is control-free.
- The trajectory bootstrap treats test trajectories as exchangeable and may understate uncertainty if trajectories sharing a regime are dependent.
- Five training seeds sample one randomness source and do not establish generalisation across training randomness.
- No meaningful-effect margin was specified, so no difference is declared equivalent or negligible.
- Simulation only: nothing here establishes performance on real aircraft.
