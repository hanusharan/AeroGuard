"""Stall / post-stall event detection.

Ground-truth event definition (Section 9): the aircraft enters the
"post-peak side" of the modeled CL(alpha) curve -- the side where CL is
decreasing as |alpha| grows, i.e. the physics model's own aerodynamic
stall boundary.

This module does NOT reimplement or approximate the CL(alpha) formula.
It calls the actual aeroguard.aerodynamics.lift_coefficient() function
(the same one used by the equations of motion) and numerically locates
its peak by direct sampling -- the same technique already used and
validated in scripts/validate_physics.py's cl_max_of(). The peak
location is, by construction of the Stage-1 post-stall correction,
equal to aircraft.alpha_stall (verified there to within ~0.1 deg), but
we compute it from the live model rather than assuming that equality,
so this stays correct even if aircraft parameters change later.
"""

from dataclasses import dataclass

import numpy as np

from .paths import cl_max_of
from aeroguard.aircraft import Aircraft


@dataclass(frozen=True)
class StallBoundary:
    """The aircraft's CL(alpha)-peak-derived stall boundary, resolved once
    per aircraft from the actual model."""

    alpha_at_cl_peak: float  # rad; the boundary itself
    cl_max: float

    def is_unsafe(self, alpha) -> np.ndarray:
        """True where |alpha| is past the CL peak (post-stall side).

        Works elementwise on scalars or numpy arrays.
        """
        return np.abs(alpha) > self.alpha_at_cl_peak


def resolve_stall_boundary(aircraft: Aircraft) -> StallBoundary:
    """Numerically locate the actual CL(alpha) peak for this aircraft."""
    cl_max, alpha_at_peak = cl_max_of(aircraft)
    return StallBoundary(alpha_at_cl_peak=float(alpha_at_peak), cl_max=float(cl_max))


def first_unsafe_index(alpha: np.ndarray, boundary: StallBoundary):
    """Index of the first timestep where the post-stall event occurs, or
    None if it never occurs in the given array."""
    unsafe = boundary.is_unsafe(alpha)
    idx = np.argmax(unsafe) if np.any(unsafe) else None
    return int(idx) if idx is not None else None
