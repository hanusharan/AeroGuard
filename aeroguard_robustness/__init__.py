"""AeroGuard robustness-study components, isolated from the frozen simulator."""

from .observations import (
    ObservedSignal,
    SensorConfig,
    apply_sensor_model,
    causal_backward_difference,
)

__all__ = [
    "ObservedSignal",
    "SensorConfig",
    "apply_sensor_model",
    "causal_backward_difference",
]
