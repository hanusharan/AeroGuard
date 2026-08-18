"""Smooth, bounded, temporally coherent control-perturbation generation.

Every perturbation is a smooth trapezoid (raised via a cubic smoothstep,
not a hard step): it ramps up from 0, optionally holds at a plateau,
then ramps back down to 0 -- there is no discontinuity, no high-frequency
noise, and no independent per-timestep randomness. This is the "ramps /
smooth pulses / piecewise-smooth profile" the pilot/autopilot analogy in
the spec asks for.

Perturbations are always ADDED on top of the trim throttle/elevator
returned by trim_level_flight() -- they never replace it (Section 5).

Regime calibration note: the magnitude ranges in config.py were checked
against Stage-1's own validated behaviour (a 0.02 rad elevator pulse from
trim produced a mild ~2 deg alpha rise; a 0.15 rad pulse produced a ~24
deg excursion well past the ~16 deg stall boundary) and then adjusted
with a small pilot batch (see scripts/generate_dataset.py generation
log / the Stage-2 report) so that "boundary" mode plausibly produces a
mix of near-boundary and boundary-crossing outcomes rather than
reliably doing (or not doing) either.
"""

from dataclasses import dataclass
from typing import Callable, List

import numpy as np

from aeroguard.dynamics import Controls
from .config import ControlRangeSpec, RegimeControlConfig


def _smoothstep_scalar(x: float) -> float:
    """Cubic Hermite smoothstep, clamped to [0, 1]. C1-continuous: zero
    slope at both x=0 and x=1, so pulses have no kinks at their edges."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x * x * (3.0 - 2.0 * x)


@dataclass(frozen=True)
class Pulse:
    start: float
    rise: float
    hold: float
    fall: float
    magnitude: float

    def value_at(self, t: float) -> float:
        if t < self.start:
            return 0.0
        end_rise = self.start + self.rise
        if t < end_rise:
            frac = (t - self.start) / self.rise if self.rise > 0 else 1.0
            return self.magnitude * _smoothstep_scalar(frac)
        end_hold = end_rise + self.hold
        if t < end_hold:
            return self.magnitude
        end_fall = end_hold + self.fall
        if t < end_fall:
            frac = (t - end_hold) / self.fall if self.fall > 0 else 1.0
            return self.magnitude * (1.0 - _smoothstep_scalar(frac))
        return 0.0

    def as_dict(self) -> dict:
        return {
            "start": self.start, "rise": self.rise, "hold": self.hold,
            "fall": self.fall, "magnitude": self.magnitude,
        }


def sample_pulses(rng: np.random.Generator, spec: ControlRangeSpec, n_pulses: int, duration_s: float) -> List[Pulse]:
    """Sample up to n_pulses non-overlapping trapezoid pulses spread across
    [0, duration_s]. If there isn't enough room for all n_pulses (short
    duration, long pulses), fewer are returned -- silently reducing count
    is fine here since it only affects perturbation richness, not physics
    correctness."""
    pulses: List[Pulse] = []
    # First pulse starts somewhere in the first third of the window so
    # there is always room for the trajectory to show pre-perturbation
    # (trimmed) behaviour first.
    t_cursor = rng.uniform(0.5, max(0.6, duration_s * 0.3))
    for _ in range(n_pulses):
        if t_cursor >= duration_s - 0.5:
            break
        rise = rng.uniform(spec.rise_s_min, spec.rise_s_max)
        hold = rng.uniform(spec.hold_s_min, spec.hold_s_max)
        fall = rng.uniform(spec.fall_s_min, spec.fall_s_max)
        mag_abs = rng.uniform(spec.magnitude_min, spec.magnitude_max)
        sign = rng.choice([-1.0, 1.0])
        magnitude = float(sign * mag_abs)
        pulse = Pulse(start=float(t_cursor), rise=float(rise), hold=float(hold), fall=float(fall), magnitude=magnitude)
        pulses.append(pulse)
        t_cursor = t_cursor + rise + hold + fall + rng.uniform(0.3, 1.5)
    return pulses


def _sample_active_channels(rng: np.random.Generator, regime_cfg: RegimeControlConfig):
    """Decide whether elevator, throttle, or both are perturbed this
    trajectory (Section 5: "whether elevator, throttle, or both")."""
    if rng.random() < regime_cfg.both_channels_prob:
        return True, True
    if rng.random() < regime_cfg.elevator_prob_if_single:
        return True, False
    return False, True


@dataclass
class ControlProfile:
    """A fully-specified control law for one trajectory, plus a record of
    exactly how it was generated (for metadata/auditing)."""

    elevator_trim: float
    throttle_trim: float
    elevator_pulses: List[Pulse]
    throttle_pulses: List[Pulse]

    def __call__(self, t: float) -> Controls:
        elevator = self.elevator_trim + sum(p.value_at(t) for p in self.elevator_pulses)
        throttle = self.throttle_trim + sum(p.value_at(t) for p in self.throttle_pulses)
        return Controls(throttle=throttle, elevator=elevator)

    def summary(self) -> dict:
        return {
            "n_elevator_pulses": len(self.elevator_pulses),
            "n_throttle_pulses": len(self.throttle_pulses),
            "elevator_pulses": [p.as_dict() for p in self.elevator_pulses],
            "throttle_pulses": [p.as_dict() for p in self.throttle_pulses],
        }


def build_control_profile(
    rng: np.random.Generator,
    regime_cfg: RegimeControlConfig,
    alpha_trim: float,
    throttle_trim: float,
    elevator_trim: float,
    duration_s: float,
) -> ControlProfile:
    """Sample a full control profile for one trajectory under one regime."""
    elevator_active, throttle_active = _sample_active_channels(rng, regime_cfg)

    elevator_pulses: List[Pulse] = []
    if elevator_active:
        n = int(rng.choice(regime_cfg.n_pulses_choices))
        elevator_pulses = sample_pulses(rng, regime_cfg.elevator, n, duration_s)

    throttle_pulses: List[Pulse] = []
    if throttle_active:
        n = int(rng.choice(regime_cfg.n_pulses_choices))
        throttle_pulses = sample_pulses(rng, regime_cfg.throttle, n, duration_s)

    return ControlProfile(
        elevator_trim=elevator_trim,
        throttle_trim=throttle_trim,
        elevator_pulses=elevator_pulses,
        throttle_pulses=throttle_pulses,
    )
