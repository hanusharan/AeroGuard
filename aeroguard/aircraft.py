"""Aircraft parameters.

All numeric defaults describe a *generic* small fixed-wing aircraft.
They are picked to be physically plausible (right order of magnitude)
so that the simulator produces sensible trajectories, but they are
NOT taken from, or validated against, any real aircraft type.
"""

from dataclasses import dataclass


@dataclass
class Aircraft:
    """Physical and aerodynamic parameters of a generic aircraft.

    Parameters
    ----------
    mass : float
        Aircraft mass [kg].
    wing_area : float
        Reference wing area S [m^2].
    Iyy : float
        Pitch-axis moment of inertia [kg*m^2]. Used only by the
        simplified pitch-rate response model (see dynamics.py).

    Drag polar: CD = CD0 + k * CL^2
        CD0 : zero-lift drag coefficient.
        k   : induced-drag factor.

    Lift-curve (pre-stall, linear region): CL = CL0 + CL_alpha * alpha
        CL0      : lift coefficient at zero angle of attack.
        CL_alpha : lift-curve slope [1/rad].
        alpha_stall : angle of attack [rad] at which stall onset begins.
        stall_transition_rate : dimensionless sharpness of the blend
            between the linear pre-stall curve and the post-stall
            (decaying) curve. Larger = sharper stall break.
        post_stall_decay_rate : rate [1/rad] at which CL decays past
            alpha_stall in the post-stall branch. Larger = faster drop-off.

    Propulsion:
        thrust_max : thrust produced at full throttle [N].

    Pitch / elevator response (simplified short-period model):
        elevator_effectiveness : moment gain from elevator deflection.
        pitch_damping          : moment gain opposing pitch rate q.
        alpha_stiffness         : moment gain opposing angle of attack
                                   (weathercock-type restoring effect).
    """

    mass: float = 1200.0
    wing_area: float = 16.2
    Iyy: float = 1285.0

    CD0: float = 0.028
    k: float = 0.045

    CL0: float = 0.2
    CL_alpha: float = 5.5
    alpha_stall: float = 0.2793  # ~16 degrees, in radians
    stall_transition_rate: float = 25.0
    post_stall_decay_rate: float = 3.0

    thrust_max: float = 2600.0

    elevator_effectiveness: float = 3.2e4
    pitch_damping: float = 6.0e3
    alpha_stiffness: float = 1.0e4
