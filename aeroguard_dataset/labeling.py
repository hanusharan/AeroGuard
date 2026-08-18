"""Causal future-outcome labeling: future_stall_5s (Section 10).

Definition: for row i (time t_i) within a trajectory, future_stall_5s[i]
is 1.0 if is_unsafe is True for ANY sample strictly after t_i and up to
and including t_i + horizon_s, 0.0 if not, and NaN (unavailable) if the
trajectory does not have that much future data recorded (either because
it is near the nominal end of the simulation, or because the trajectory
terminated early -- see trajectory_sim.py).

The window is (t_i, t_i + horizon_s] -- i.e. it does NOT include the
current sample itself, only strictly future samples. This is computed
purely from indices, not floating-point time comparisons, since dt is
fixed and uniform within a trajectory: horizon_steps = round(horizon_s/dt).

This module never uses any information beyond the single trajectory's
own already-simulated, already-terminated array of is_unsafe flags --
it is a label computed from the real (simulated) future, never a
predictive/estimated one, and it is never itself used as a feature.
"""

from typing import Tuple

import numpy as np


def compute_future_stall_label(is_unsafe: np.ndarray, dt: float, horizon_s: float) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (labels, available).

    labels[i] in {0.0, 1.0, np.nan}; np.nan where unavailable.
    available[i] is a boolean twin of `labels[i] is not NaN`, provided
    for convenience/explicitness in the processed table.
    """
    n = len(is_unsafe)
    horizon_steps = int(round(horizon_s / dt))

    labels = np.full(n, np.nan, dtype=float)
    available = np.zeros(n, dtype=bool)

    valid_n = n - horizon_steps  # number of rows with a full future window available
    if valid_n <= 0:
        return labels, available

    is_unsafe_int = is_unsafe.astype(int)
    # cumsum[k] = sum(is_unsafe[0..k]) inclusive
    cumsum = np.cumsum(is_unsafe_int)

    idx = np.arange(valid_n)
    j_end = idx + horizon_steps
    # sum over (idx, j_end] = cumsum[j_end] - cumsum[idx]  (excludes idx itself, includes j_end)
    window_counts = cumsum[j_end] - cumsum[idx]

    labels[:valid_n] = (window_counts > 0).astype(float)
    available[:valid_n] = True

    return labels, available
