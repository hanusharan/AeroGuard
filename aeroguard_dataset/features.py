"""Causal feature computation.

Distinguishes RAW PHYSICS OBSERVATIONS (recorded directly from the
simulation: V, alpha, theta, gamma, altitude, pitch_rate, vertical_speed,
thrust, elevator, throttle -- see trajectory_sim.TrajectoryResult) from
DERIVED FEATURES computed here (dV_dt, dalpha_dt, stall_margin, and the
is_unsafe event flag). See data/metadata/feature_schema.json (written by
dataset_builder) for the authoritative list.

All derived quantities here use ONLY the current and past samples of a
single trajectory -- never a centered window, never a future sample.
"""

from typing import Dict

import numpy as np

from .events import StallBoundary
from .trajectory_sim import TrajectoryResult


def causal_backward_difference(x: np.ndarray, dt: float) -> np.ndarray:
    """d/dt via a one-sided backward difference: out[i] = (x[i]-x[i-1])/dt.

    out[0] is NaN (no prior sample exists for the first row of a
    trajectory) -- this is intentional, not a bug: there is nothing else
    a *causal* derivative could legitimately use at i=0.
    """
    out = np.full(x.shape, np.nan, dtype=float)
    out[1:] = (x[1:] - x[:-1]) / dt
    return out


def compute_features_for_trajectory(result: TrajectoryResult, boundary: StallBoundary, dt: float) -> Dict[str, np.ndarray]:
    """Compute derived features and the ground-truth event flag for one
    already-simulated trajectory.

    stall_margin follows the exact formula specified for Stage 2:
        stall_margin = alpha_at_cl_peak - alpha
    (alpha_at_cl_peak is the model's own, numerically-located CL(alpha)
    peak -- see events.resolve_stall_boundary -- used in place of the
    literal aircraft.alpha_stall parameter so this stays tied to the
    actual model rather than an assumed-equal constant.)

    Note this formula is signed relative to the POSITIVE boundary only;
    for a negative-alpha excursion past -alpha_at_cl_peak (also a valid,
    symmetric stall event under is_unsafe()), stall_margin does not read
    as a symmetric "distance to event" the way it does for positive
    alpha. This is the formula as specified for Stage 2 and is used
    as-is; it is documented here rather than silently generalized.
    """
    dV_dt = causal_backward_difference(result.V, dt)
    dalpha_dt = causal_backward_difference(result.alpha, dt)
    stall_margin = boundary.alpha_at_cl_peak - result.alpha
    is_unsafe = boundary.is_unsafe(result.alpha)

    return {
        "dV_dt": dV_dt,
        "dalpha_dt": dalpha_dt,
        "stall_margin": stall_margin,
        "is_unsafe": is_unsafe,
    }
