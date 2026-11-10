"""Causal sensor-observation models for isolated robustness studies.

This module does not alter the AeroGuard flight-dynamics engine. It maps a
simulated truth signal into a sampled, delayed, noisy observation channel.
All parameters are explicit and deterministic under a fixed random seed.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SensorConfig:
    """Parameters for one scalar sensor channel.

    Units follow the supplied signal (e.g. radians for angle of attack).
    bias is a constant offset; drift_per_s is linear bias drift.
    sample_period_s and latency_s are seconds. Noise is independent Gaussian
    noise applied once per acquired sample, not once per held row.
    A dropped acquisition is represented as NaN until the next acquisition.
    """

    sample_period_s: float
    latency_s: float = 0.0
    noise_std: float = 0.0
    bias: float = 0.0
    drift_per_s: float = 0.0
    dropout_probability: float = 0.0
    seed: int = 0


@dataclass(frozen=True)
class ObservedSignal:
    """Observed values and availability mask aligned to the input time grid."""

    time_s: np.ndarray
    value: np.ndarray
    available: np.ndarray


def apply_sensor_model(time_s, truth, config: SensorConfig) -> ObservedSignal:
    """Apply sampling, latency, bias, drift, noise and dropout causally.

    Samples are acquired on a regular schedule anchored at time_s[0].
    At an acquisition time between simulator steps, the latest truth sample
    at or before that time is used (never a future sample). At each output
    time, only an acquisition whose timestamp is <= output_time-latency is
    visible. The most recent visible acquisition is held until the next one.
    If that acquisition was dropped, the output is NaN until another sample
    arrives; no hidden-state interpolation or imputation is performed.
    """
    t = np.asarray(time_s, dtype=float)
    x = np.asarray(truth, dtype=float)

    if t.ndim != 1 or x.ndim != 1 or t.size != x.size or t.size < 2:
        raise ValueError("time_s and truth must be 1D arrays of equal length >= 2")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(x)):
        raise ValueError("time_s and truth must contain only finite values")
    steps = np.diff(t)
    if np.any(steps <= 0):
        raise ValueError("time_s must be strictly increasing")
    if not np.isfinite(config.sample_period_s) or config.sample_period_s <= 0:
        raise ValueError("sample_period_s must be finite and > 0")
    if config.sample_period_s + 1e-12 < float(np.max(steps)):
        raise ValueError("sample_period_s must be >= the largest simulation time step")
    if not np.isfinite(config.latency_s) or config.latency_s < 0:
        raise ValueError("latency_s must be finite and >= 0")
    if not np.isfinite(config.noise_std) or config.noise_std < 0:
        raise ValueError("noise_std must be finite and >= 0")
    if not np.isfinite(config.bias) or not np.isfinite(config.drift_per_s):
        raise ValueError("bias and drift_per_s must be finite")
    if not 0 <= config.dropout_probability <= 1:
        raise ValueError("dropout_probability must be in [0, 1]")

    t0 = float(t[0])
    count = int(np.floor((float(t[-1]) - t0) / config.sample_period_s + 1e-12)) + 1
    scheduled_times = t0 + np.arange(count, dtype=float) * config.sample_period_s
    acquired_indices = np.searchsorted(t, scheduled_times, side="right") - 1
    acquired_indices = np.clip(acquired_indices, 0, t.size - 1)

    rng = np.random.default_rng(config.seed)
    measurements = (
        x[acquired_indices]
        + config.bias
        + config.drift_per_s * (scheduled_times - t0)
        + rng.normal(0.0, config.noise_std, size=count)
    )
    dropped = rng.random(count) < config.dropout_probability

    # Protect exact-grid comparisons from subtraction roundoff (e.g.
    # 0.3 - 0.2 evaluating to 0.09999999999999998 instead of 0.1).
    time_tolerance = min(
        0.01 * config.sample_period_s,
        8.0 * np.finfo(float).eps * max(1.0, float(np.max(np.abs(t)))),
    )
    visible_sample = np.searchsorted(
        scheduled_times, t - config.latency_s + time_tolerance, side="right"
    ) - 1
    output = np.full(t.shape, np.nan, dtype=float)
    has_visible_sample = visible_sample >= 0
    rows = np.flatnonzero(has_visible_sample)
    if rows.size:
        sample_ids = visible_sample[rows]
        valid = ~dropped[sample_ids]
        output[rows[valid]] = measurements[sample_ids[valid]]

    return ObservedSignal(time_s=t.copy(), value=output, available=np.isfinite(output))


def causal_backward_difference(time_s, observed):
    """Compute a backward difference from observations only.

    The first value and any difference touching a missing observation are NaN.
    No future samples, interpolation, or hidden truth values are used.
    """
    t = np.asarray(time_s, dtype=float)
    x = np.asarray(observed, dtype=float)
    if t.ndim != 1 or x.ndim != 1 or t.size != x.size or t.size < 2:
        raise ValueError("time_s and observed must be 1D arrays of equal length >= 2")
    if not np.all(np.isfinite(t)) or np.any(np.diff(t) <= 0):
        raise ValueError("time_s must be finite and strictly increasing")
    out = np.full(x.shape, np.nan, dtype=float)
    valid = np.isfinite(x[1:]) & np.isfinite(x[:-1])
    differences = np.diff(x) / np.diff(t)
    valid_rows = np.flatnonzero(valid) + 1
    out[valid_rows] = differences[valid]
    return out
