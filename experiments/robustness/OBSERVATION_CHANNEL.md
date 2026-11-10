# Sensor observation channel — implementation note

**Scope:** software component for a future simulation-robustness study. This is not a completed robustness experiment and does not change the v0.3 simulator, trajectories, labels, model, paper, or stored results.

## Implemented observation effects

The aeroguard_robustness.observations module provides a scalar sensor transformation with explicit parameters:

- sample-and-hold acquisition at sample_period_s;
- transport/processing latency at latency_s;
- additive Gaussian noise, sampled once per acquisition at noise_std;
- constant bias and linear drift (bias, drift_per_s);
- acquisition dropout, represented as NaN until the next successful sample;
- a causal backward difference computed only from the observed channel.

A fixed random seed makes the noise/dropout realization reproducible. Acquisition between simulation steps uses the latest truth sample at or before the acquisition timestamp; future truth is never interpolated into a measurement. The delayed output only exposes acquisitions whose timestamps are no later than the current output time minus the configured latency.

## Validation performed by unit tests

Tests cover zero-effect identity, latency, sample-and-hold, deterministic noise, explicit dropout, bias/drift, missing-aware causal derivatives, and invalid configurations. These are software-contract tests, not empirical sensor calibration.

## Parameters and evidence boundary

The implementation is parameterized; it does not prescribe aircraft sensor noise, bias, drift, latency, or dropout values. No numeric values should be described as representative of a real aircraft without a specific sensor datasheet, installation context, sampling chain, and source. Any first experiment using assumed levels must label them as engineering stress-test assumptions and pre-register them before model evaluation.

## Not implemented here

This component does not implement dynamic stall, aerodynamic gust coupling, nonlinear pitching moments, aircraft-specific trim, or an end-to-end robustness ML experiment. Those require a documented model and configuration-specific validation evidence. The existing aeroguard equations remain untouched.
