# AeroGuard Stage 2 -- Dataset Audit Report

Dataset version: `stage2-initial-1000-v1`  
Seed: `20260817`

## A. Trajectory counts
- total_trajectories: 1000
- valid_trajectories: 1000
- invalid_trajectories: 0
- terminated_early_trajectories: 320
- completed_full_duration_trajectories: 680

## B. Generation-mode distribution
- normal: 500 (50.0%), target 50%
- stall: 250 (25.0%), target 25%
- boundary: 250 (25.0%), target 25%

## C. Actual event distribution
- trajectories_with_stall: 187
- trajectories_without_stall: 813
- fraction_with_stall: 0.187

## D. Supervised label distribution
- future_stall_5s_negative_0: 981982
- future_stall_5s_positive_1: 96848
- future_stall_5s_unavailable_NaN: 486450
- positive_fraction_of_available: 0.08977132634428038
- total_rows: 1565280

## E. Physical ranges
- V_m_s: min=13.0675, max=117.3075
- alpha_deg: min=-43.9911, max=78.4692
- altitude_m: min=51.0605, max=2139.7592
- gamma_deg: min=-45.5040, max=45.4168
- thrust_N: min=358.7550, max=2022.0569
- elevator_rad: min=-0.3152, max=0.3778

## F. Validity-envelope events
- n_exceeded_low_airspeed: 1
- n_exceeded_gamma: 319
- n_numerical_instability: 0
- n_invalid_control: 0
- termination_reason_counts: {'completed_normally': 680, 'validity_envelope_gamma_exceeded': 319, 'validity_envelope_low_airspeed': 1}
- v_stall_m_s: 26.140289984056395
- v_floor_m_s: 13.070144992028197
- gamma_max_deg: 45.0

## G. Data integrity
- raw_missing_values_per_column: {}
- raw_infinite_values_per_column: {}
- processed_missing_values_per_column: {'dV_dt': 1000, 'dalpha_dt': 1000, 'future_stall_5s': 486450}
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
- monotonic_timestamps_check: {'n_trajectories_checked': 1000, 'non_monotonic_trajectory_ids': [], 'passed': True}
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