"""Generic fixed-step RK4 integrator.

Kept independent of the flight-dynamics model so it can be unit
tested against a problem with a known analytical solution.
"""

from typing import Callable

import numpy as np


def rk4_step(
    f: Callable[..., np.ndarray],
    t: float,
    y: np.ndarray,
    dt: float,
    *args,
) -> np.ndarray:
    """Advance y(t) to y(t+dt) by one classical 4th-order Runge-Kutta step.

    f has signature f(t, y, *args) -> dy/dt
    """
    k1 = f(t, y, *args)
    k2 = f(t + dt / 2.0, y + dt / 2.0 * k1, *args)
    k3 = f(t + dt / 2.0, y + dt / 2.0 * k2, *args)
    k4 = f(t + dt, y + dt * k3, *args)
    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def integrate(
    f: Callable[..., np.ndarray],
    y0: np.ndarray,
    t_span,
    dt: float,
    *args,
):
    """Integrate f from t_span[0] to t_span[1] with fixed step dt.

    Returns (t_array, y_array) where y_array has shape (n_steps+1, len(y0)).
    """
    t0, t1 = t_span
    n_steps = int(round((t1 - t0) / dt))
    t_array = t0 + dt * np.arange(n_steps + 1)

    y_array = np.zeros((n_steps + 1, len(y0)))
    y_array[0] = y0

    y = np.array(y0, dtype=float)
    for i in range(n_steps):
        y = rk4_step(f, t_array[i], y, dt, *args)
        y_array[i + 1] = y

    return t_array, y_array
