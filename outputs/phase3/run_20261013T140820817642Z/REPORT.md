# AeroGuard Phase 3 results (run_20261013T140820817642Z)

> Computed on regenerated v0.3 data (Item 26 copy; hashes in the protocol lock). Not independent replication. Simulation only: nothing here establishes real-aircraft safety.

Generated from the machine-readable results of this run. No practical-significance criterion is defined (D10); no claim of practical superiority is made.

## Population
538034 rows, 456 trajectories, 46169 positive / 491865 negative rows (rows, trajectories and events are distinct units).

## Threshold-free metrics with paired trajectory-bootstrap 95% intervals
B = 1000, seed 20261013, unit = trajectory, percentile 2.5/97.5.

| method | PR-AUC | 95% interval | ROC-AUC | 95% interval |
|---|---|---|---|---|
| aoa_signed | 0.7095 | [0.6670, 0.7448] | 0.9050 | [0.8762, 0.9310] |
| instantaneous_model_a | 0.8754 | [0.8345, 0.9114] | 0.9714 | [0.9589, 0.9822] |
| frozen_temporal | 0.8903 | [0.8535, 0.9224] | 0.9775 | [0.9690, 0.9857] |
| aoa_two_sided | 0.7089 | [0.6664, 0.7445] | 0.9013 | [0.8709, 0.9297] |

## Paired differences (PR-AUC primary contrast first)

| difference | point | 95% interval | interval includes 0 | undefined replicates |
|---|---|---|---|---|
| frozen_temporal - instantaneous_model_a | pr_auc | 0.0148 | [0.0079, 0.0230] | False | 0 |
| frozen_temporal - instantaneous_model_a | roc_auc | 0.0061 | [0.0023, 0.0109] | False | 0 |
| frozen_temporal - aoa_signed | pr_auc | 0.1808 | [0.1505, 0.2192] | False | 0 |
| frozen_temporal - aoa_signed | roc_auc | 0.0725 | [0.0512, 0.0946] | False | 0 |
| instantaneous_model_a - aoa_signed | pr_auc | 0.1660 | [0.1341, 0.2047] | False | 0 |
| instantaneous_model_a - aoa_signed | roc_auc | 0.0664 | [0.0464, 0.0864] | False | 0 |

## Reading of the primary contrast (rules fixed in the protocol, section 9.4)
The paired interval for the primary contrast excludes 0: statistical evidence of a difference under this resampling model (not a p-value; not evidence of cause; practical significance not assessed).
A higher score for one model is not proof that temporal reasoning caused it.

## Threshold-dependent metrics: NOT MATCHED across methods; do not rank
Each method is at its own validation-selected operating point (strict >).

| method | threshold | precision | recall | F1 | events warned / events | median lead (s) | false-alarm episodes / eligible hour |
|---|---|---|---|---|---|---|---|
| aoa_signed | 0.217239 | 0.7764 | 0.5257 | 0.6269 | 76 / 76 | 2.080 | 23.438 |
| instantaneous_model_a | 0.819487 | 0.8716 | 0.7471 | 0.8046 | 75 / 76 | 4.650 | 29.465 |
| frozen_temporal | 0.858553 | 0.9348 | 0.7361 | 0.8236 | 73 / 76 | 4.720 | 18.751 |
| aoa_two_sided | 0.217239 | 0.7764 | 0.5257 | 0.6269 | 76 / 76 | 2.080 | 23.438 |

Event-level numbers come from few independent trajectories; see the protocol (section 9.3).

## Item 30 (stall margin)
Mathematically equivalent to Item 28; not evaluated as a separate method. Decision counts only:

- train: 1 disagreeing rows of 2443881 (1 exactly at the threshold)
- val: 0 disagreeing rows of 491322 (0 exactly at the threshold)
- test: 0 disagreeing rows of 538034 (0 exactly at the threshold)

## Limitations
See PROTOCOL.md sections 10, 12 and 20: prior test exposure, regenerated data, one simulated aircraft, few independent event trajectories.
