# AeroGuard Stage 2 -- Dataset Audit Report

Dataset version: `stage2-v0.2-calibration`  
Seed: `20260817`

## A. Trajectory counts
- total_trajectories: 1000
- valid_trajectories: 1000
- invalid_trajectories: 0
- terminated_early_trajectories: 177
- completed_full_duration_trajectories: 823

## B. Generation-mode distribution
- normal: 500 (50.0%), target 50%
- stall: 250 (25.0%), target 25%
- near_boundary: 250 (25.0%), target 25%

## C. Actual event distribution
- trajectories_with_stall: 192
- trajectories_without_stall: 808
- fraction_with_stall: 0.192

## D. Supervised label distribution
- future_stall_5s_negative_0: 1176887
- future_stall_5s_positive_1: 87886
- future_stall_5s_unavailable_NaN: 488842
- positive_fraction_of_available: 0.069487568124873
- total_rows: 1753615

## E. Physical ranges
- V_m_s: min=17.5300, max=129.9861
- alpha_deg: min=-41.5664, max=73.9318
- altitude_m: min=0.1354, max=2125.6554
- gamma_deg: min=-45.5372, max=45.4600
- thrust_N: min=331.5069, max=1954.4226
- elevator_rad: min=-0.3154, max=0.3582

## F. Validity-envelope events
- n_exceeded_low_airspeed: 0
- n_exceeded_gamma: 175
- n_ground_contact: 2
- n_numerical_instability: 0
- n_invalid_control: 0
- termination_reason_counts: {'completed_normally': 823, 'validity_envelope_gamma_exceeded': 175, 'ground_contact': 2}
- v_stall_m_s: 26.140289984056395
- v_floor_m_s: 13.070144992028197
- gamma_max_deg: 45.0

## G. Data integrity
- raw_missing_values_per_column: {}
- raw_infinite_values_per_column: {}
- processed_missing_values_per_column: {'dV_dt': 1000, 'dalpha_dt': 1000, 'future_stall_5s': 488842}
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