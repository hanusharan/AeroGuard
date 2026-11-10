import numpy as np
import pytest

from aeroguard_robustness.observations import (
    SensorConfig,
    apply_sensor_model,
    causal_backward_difference,
)


def grid(n=6, dt=0.1):
    t = np.arange(n, dtype=float) * dt
    return t, 2.0 * t + 1.0


def test_zero_effect_sensor_reproduces_truth_at_full_rate():
    t, truth = grid()
    observed = apply_sensor_model(t, truth, SensorConfig(sample_period_s=0.1))
    np.testing.assert_allclose(observed.value, truth)
    assert observed.available.all()


def test_latency_exposes_only_past_measurements():
    t, truth = grid()
    observed = apply_sensor_model(
        t, truth, SensorConfig(sample_period_s=0.1, latency_s=0.2)
    )
    assert np.isnan(observed.value[:2]).all()
    np.testing.assert_allclose(observed.value[2:], truth[:-2])


def test_sample_and_hold_does_not_update_between_acquisitions():
    t, truth = grid()
    observed = apply_sensor_model(t, truth, SensorConfig(sample_period_s=0.2))
    np.testing.assert_allclose(
        observed.value, [truth[0], truth[0], truth[2], truth[2], truth[4], truth[4]]
    )


def test_noise_is_reproducible_for_fixed_seed():
    t, truth = grid(n=20)
    config = SensorConfig(sample_period_s=0.1, noise_std=0.05, seed=73)
    first = apply_sensor_model(t, truth, config)
    second = apply_sensor_model(t, truth, config)
    np.testing.assert_array_equal(first.value, second.value)


def test_dropout_is_explicitly_missing_until_next_acquisition():
    t, truth = grid()
    observed = apply_sensor_model(
        t, truth, SensorConfig(sample_period_s=0.1, dropout_probability=1.0)
    )
    assert np.isnan(observed.value).all()
    assert not observed.available.any()


def test_bias_and_drift_are_applied_at_acquisition_time():
    t, truth = grid()
    observed = apply_sensor_model(
        t, truth, SensorConfig(sample_period_s=0.1, bias=0.5, drift_per_s=0.2)
    )
    np.testing.assert_allclose(observed.value, truth + 0.5 + 0.2 * t)


def test_causal_derivative_uses_observed_values_and_respects_missingness():
    t = np.array([0.0, 0.1, 0.2, 0.3])
    observed = np.array([np.nan, 1.0, 1.2, np.nan])
    derivative = causal_backward_difference(t, observed)
    assert np.isnan(derivative[0])
    assert np.isnan(derivative[1])
    assert derivative[2] == pytest.approx(2.0)
    assert np.isnan(derivative[3])


def test_rejects_noncausal_or_invalid_sensor_configuration():
    t, truth = grid()
    with pytest.raises(ValueError, match="latency_s"):
        apply_sensor_model(t, truth, SensorConfig(sample_period_s=0.1, latency_s=-0.1))
    with pytest.raises(ValueError, match="largest simulation time step"):
        apply_sensor_model(t, truth, SensorConfig(sample_period_s=0.05))


def test_between_step_acquisition_uses_previous_not_future_truth():
    t = np.array([0.0, 0.1, 0.2, 0.3])
    truth = np.array([0.0, 1.0, 2.0, 3.0])
    observed = apply_sensor_model(
        t, truth, SensorConfig(sample_period_s=0.15, latency_s=0.0)
    )
    # The acquisition scheduled at 0.15 s sees the 0.10 s truth sample.
    assert observed.value[2] == pytest.approx(1.0)
    assert observed.value[2] != pytest.approx(2.0)
