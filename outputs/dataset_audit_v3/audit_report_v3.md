# AeroGuard Stage 2 -- Dataset Audit Report

Dataset version: `stage2-v0.3-full`  
Seed: `20260823`

## A. Trajectory counts
- total_trajectories: 3150
- valid_trajectories: 3150
- invalid_trajectories: 0
- terminated_early_trajectories: 877
- completed_full_duration_trajectories: 2273

## B. Generation-mode distribution
- gradual_approach_v3: 2400 (76.2%), target 76%
- normal: 500 (15.9%), target 16%
- stall: 250 (7.9%), target 8%

## C. Actual event distribution
- trajectories_with_stall: 470
- trajectories_without_stall: 2680
- fraction_with_stall: 0.1492063492063492

## D. Supervised label distribution
- future_stall_5s_negative_0: 3467445
- future_stall_5s_positive_1: 310404
- future_stall_5s_unavailable_NaN: 1563016
- positive_fraction_of_available: 0.08216421566875753
- total_rows: 5340865

## E. Physical ranges
- V_m_s: min=13.7180, max=132.4658
- alpha_deg: min=-41.2203, max=76.1928
- altitude_m: min=0.0199, max=2205.7104
- gamma_deg: min=-45.4507, max=45.3978
- thrust_N: min=408.7715, max=1958.8259
- elevator_rad: min=-0.3153, max=0.3659

## F. Validity-envelope events
- n_exceeded_low_airspeed: 0
- n_exceeded_gamma: 858
- n_ground_contact: 19
- n_numerical_instability: 0
- n_invalid_control: 0
- termination_reason_counts: {'completed_normally': 2273, 'validity_envelope_gamma_exceeded': 858, 'ground_contact': 19}
- v_stall_m_s: 26.140289984056395
- v_floor_m_s: 13.070144992028197
- gamma_max_deg: 45.0

## G. Data integrity
- raw_missing_values_per_column: {}
- raw_infinite_values_per_column: {}
- processed_missing_values_per_column: {'dV_dt': 3150, 'dalpha_dt': 3150, 'future_stall_5s': 1563016}
- processed_missing_values_note: dV_dt/dalpha_dt are NaN on the first row of every trajectory by design (no prior sample for a causal derivative). future_stall_5s and future_stall_5s_available are NaN/False on the final 5.0s of every trajectory by design (insufficient future data within the simulated trajectory -- see Section 10).
- duplicate_rows_raw: 0
- duplicate_rows_processed: 0
- duplicate_trajectory_ids_in_metadata: 0
- duplicate_trajectory_ids_in_split_manifest: 0
- trajectory_ids_in_multiple_splits: 0
- metadata_manifest_id_set_equal: True
- future_label_leakage_check: {'n_trajectories_checked': 25, 'mismatches': [], 'passed': True}
- causal_derivative_check: {'n_trajectories_checked': 25, 'mismatches': [], 'passed': True}

## H. Temporal correctness
- monotonic_timestamps_check: {'n_trajectories_checked': 3150, 'non_monotonic_trajectory_ids': [], 'passed': True}
- causal_derivative_check: {'n_trajectories_checked': 25, 'mismatches': [], 'passed': True}
- future_label_check: {'n_trajectories_checked': 25, 'mismatches': [], 'passed': True}

## V0 range validation (Section 4)
- v_stall_m_s: 26.140289984056395
- v_floor_m_s: 13.070144992028197
- requested_v0_min: 30.0
- requested_v0_max: 75.0
- v0_min_margin_over_vstall: 1.1476536801350612
- v0_max_margin_over_vstall: 2.869134200337653
- v0_min_above_vstall: True
- v0_min_above_v_floor: True