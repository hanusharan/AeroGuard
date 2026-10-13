"""Declarative feature-ablation conditions (PROTOCOL.md sections 3 and 4).

Everything is written out literally and then cross-checked, so a drift in the upstream
feature definitions fails closed instead of silently changing a condition. No data is read.
"""

from typing import Dict, Iterable, List, Mapping, Sequence

import pandas as pd

# The frozen model's 23 features, in the frozen order (outputs/ml_v03/metrics/primary_model_metrics.json,
# verified equal to ml.temporal_config_v03.model_d_features(1.0) during protocol preparation).
C0_FEATURES = (
    "V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin",
    "dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt", "d2alpha_dt2",
    "alpha_mean_1s", "alpha_min_1s", "alpha_max_1s", "alpha_range_1s", "alpha_slope_1s", "alpha_trend_1s",
    "V_slope_1s", "gamma_slope_1s", "pitch_rate_slope_1s", "elevator_change_1s",
)

_C1 = ("elevator", "throttle")
_C2 = _C1 + ("elevator_change_1s",)
_C3 = _C2 + ("dq_dt", "dV_dt", "pitch_rate_slope_1s", "V_slope_1s")

REMOVALS: Dict[str, tuple] = {
    "C0": (),
    "C1": _C1,
    "C2": _C2,
    "C3": _C3,
    "X1": ("elevator_change_1s",),
}
CONDITION_ORDER = ("C0", "C1", "C2", "C3", "X1")
EXPECTED_N_FEATURES = {"C0": 23, "C1": 21, "C2": 20, "C3": 16, "X1": 22}
STATUS = {"C0": "baseline", "C1": "primary", "C2": "primary", "C3": "exploratory", "X1": "exploratory"}

# Never admitted to any predictor matrix (PROTOCOL.md 3.4).
FORBIDDEN_COLUMNS = frozenset({
    "future_stall_5s", "future_stall_5s_available", "is_unsafe", "time_to_stall",
    "trajectory_id", "time", "split", "thrust", "theta", "vertical_speed",
})


class ManifestError(ValueError):
    """A condition manifest or a table's columns violate the protocol; the run must stop."""


def features_for(condition: str) -> List[str]:
    """C0's order with the condition's removed names deleted."""
    if condition not in REMOVALS:
        raise ManifestError(f"unknown condition {condition!r}")
    removed = set(REMOVALS[condition])
    return [f for f in C0_FEATURES if f not in removed]


def build_manifest() -> Dict[str, Dict[str, object]]:
    return {
        c: {"features": features_for(c), "n_features": len(features_for(c)), "removed": list(REMOVALS[c]), "status": STATUS[c]}
        for c in CONDITION_ORDER
    }


def assert_no_forbidden(features: Iterable[str]) -> None:
    bad = sorted(set(features) & FORBIDDEN_COLUMNS)
    if bad:
        raise ManifestError(f"forbidden column(s) in a feature list: {bad}")


def validate_manifest(manifest: Mapping[str, Mapping[str, object]] = None) -> Dict[str, Dict[str, object]]:
    """Fail closed unless the manifest equals the protocol: counts, order, uniqueness, nesting, no forbidden column."""
    manifest = build_manifest() if manifest is None else manifest
    if list(manifest) != list(CONDITION_ORDER):
        raise ManifestError(f"conditions must be exactly {list(CONDITION_ORDER)}, got {list(manifest)}")
    c0 = list(C0_FEATURES)
    if len(c0) != 23 or len(set(c0)) != 23:
        raise ManifestError("C0 must have 23 unique features")
    for name, entry in manifest.items():
        feats = list(entry["features"])
        if len(set(feats)) != len(feats):
            raise ManifestError(f"{name}: duplicate feature(s)")
        if len(feats) != EXPECTED_N_FEATURES[name] or entry.get("n_features") != EXPECTED_N_FEATURES[name]:
            raise ManifestError(f"{name}: expected {EXPECTED_N_FEATURES[name]} features, got {len(feats)}")
        assert_no_forbidden(feats)
        if feats != [f for f in c0 if f in set(feats)]:
            raise ManifestError(f"{name}: feature order differs from C0's order")
        if set(feats) | set(entry["removed"]) != set(c0) or set(feats) & set(entry["removed"]):
            raise ManifestError(f"{name}: features plus removed names must partition C0")
        if feats != features_for(name):
            raise ManifestError(f"{name}: differs from the literal protocol manifest")
    sets = {k: set(v["features"]) for k, v in manifest.items()}
    if not (sets["C3"] < sets["C2"] < sets["C1"] < sets["C0"]):
        raise ManifestError("nesting C3 < C2 < C1 < C0 is violated")
    if not (sets["C2"] < sets["X1"] < sets["C0"]):
        raise ManifestError("nesting C2 < X1 < C0 is violated")
    return dict(manifest)


def verify_against_source() -> bool:
    """C0 must equal ``ml.temporal_config_v03.model_d_features(1.0)`` (existing source), in order."""
    from ml import temporal_config_v03 as v3cfg

    src = list(v3cfg.model_d_features(1.0))
    if src != list(C0_FEATURES):
        raise ManifestError("C0 differs from ml.temporal_config_v03.model_d_features(1.0)")
    return True


def verify_against_stored_record(feature_columns: Sequence[str]) -> bool:
    """C0 must equal the feature list stored with the frozen model's metrics (caller reads the tracked JSON)."""
    if list(feature_columns) != list(C0_FEATURES):
        raise ManifestError("C0 differs from the stored frozen-model feature list")
    return True


def select_columns(df: pd.DataFrame, condition: str) -> pd.DataFrame:
    """Return ``df`` restricted to the condition's features in order. Fails closed on a missing or
    duplicated column; never substitutes a feature."""
    feats = features_for(condition)
    assert_no_forbidden(feats)
    cols = list(df.columns)
    dup = sorted({c for c in feats if cols.count(c) > 1})
    if dup:
        raise ManifestError(f"duplicated column(s) in the table: {dup}")
    missing = [f for f in feats if f not in cols]
    if missing:
        raise ManifestError(f"{condition}: missing feature column(s): {missing}")
    return df[feats]
