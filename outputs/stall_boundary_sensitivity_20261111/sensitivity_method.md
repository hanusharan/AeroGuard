# Reproduction method

The calculation evaluates the existing `Aircraft` defaults and the `_stall_blend` / `lift_coefficient` functions.

Angle grid: 0–40° inclusive, 400,001 samples (0.0001° spacing). Peak and peak CL refined with three-point parabolic interpolation.

OAT: nine equally spaced values per range:
- `alpha_stall`: 14–18° (stored as radians)
- `stall_transition_rate`: 15–35
- `post_stall_decay_rate`: 2.0–4.5 rad^-1
- `CL0`: 0.15–0.30
- `CL_alpha`: 4.5–5.8 rad^-1

Factorial: seven equally spaced values for each of `alpha_stall`, `stall_transition_rate`, and `post_stall_decay_rate` (343 combinations). `CL0` and `CL_alpha` held at defaults.

No trajectory, label, model, or frozen output is read or modified.
