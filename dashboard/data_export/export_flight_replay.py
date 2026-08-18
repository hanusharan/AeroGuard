"""Read-only export of one real v0.3 TEST-split trajectory + the frozen
primary model's inference probability, for the public dashboard's flight
replay visualization.

This script does NOT modify, retrain, or recalibrate anything. It loads the
already-frozen model (outputs/ml_v03/models/primary_model_D_1s.joblib) and the
already-frozen cached feature panel (data/ml_temporal_v03/temporal_test.parquet)
and calls .predict_proba() -- the exact same inference call
ml/temporal_experiment_v03.py's own evaluate_on_test() makes -- on one held-out
trajectory. Output is a static JSON consumed by the dashboard; nothing here is
part of the research pipeline.

Run from repo root: python dashboard/data_export/export_flight_replay.py
"""
import json
import os

import joblib
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODEL_PATH = os.path.join(ROOT, "outputs", "ml_v03", "models", "primary_model_D_1s.joblib")
METRICS_PATH = os.path.join(ROOT, "outputs", "ml_v03", "metrics", "primary_model_metrics.json")
PANEL_PATH = os.path.join(ROOT, "data", "ml_temporal_v03", "temporal_test.parquet")
OUT_PATH = os.path.join(ROOT, "dashboard", "src", "data", "flightReplay.json")

STALL_BOUNDARY_DEG = 16.068034017008504  # aeroguard_dataset config, resolve_stall_boundary()
TRAJECTORY_ID = "traj_00413"  # real v0.3 TEST-split gradual_approach_v3 crossing; its model-
                                # credited lead time (4.72s) matches the reported EVENT-LEVEL
                                # MEDIAN exactly (primary_model_metrics.json), so it is
                                # representative of the headline result, not cherry-picked-best.
DOWNSAMPLE_EVERY = 10  # dt=0.01s in the raw panel -> 0.1s resolution for the chart


def main():
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    feature_columns = metrics["feature_columns"]
    threshold = metrics["threshold"]

    model = joblib.load(MODEL_PATH)
    df = pd.read_parquet(PANEL_PATH)
    traj = df[df["trajectory_id"] == TRAJECTORY_ID].sort_values("time").reset_index(drop=True)
    if traj.empty:
        raise SystemExit(f"trajectory {TRAJECTORY_ID} not found in {PANEL_PATH}")

    X = traj[feature_columns].to_numpy()
    proba = model.predict_proba(X)[:, 1]  # pure inference, frozen model, not refit

    traj = traj.iloc[::DOWNSAMPLE_EVERY].reset_index(drop=True)
    proba = proba[::DOWNSAMPLE_EVERY]

    # Trim to a presentable window: from t=0 to a few seconds past the crossing.
    alpha_deg_full = np.degrees(traj["alpha"].to_numpy())
    crossed_full = alpha_deg_full >= STALL_BOUNDARY_DEG
    if crossed_full.any():
        window_end = float(traj["time"].to_numpy()[crossed_full][0]) + 3.0
        keep = traj["time"] <= window_end
        traj = traj[keep].reset_index(drop=True)
        proba = proba[keep.to_numpy()]

    crossing_time = None
    alpha_deg = np.degrees(traj["alpha"].to_numpy())
    crossed_mask = alpha_deg >= STALL_BOUNDARY_DEG
    if crossed_mask.any():
        crossing_time = float(traj["time"].to_numpy()[crossed_mask][0])

    first_warned_time = None
    warned_mask = proba >= threshold
    if warned_mask.any():
        first_warned_time = float(traj["time"].to_numpy()[warned_mask][0])

    lead_time_s = (
        round(crossing_time - first_warned_time, 2)
        if crossing_time is not None and first_warned_time is not None
        else None
    )

    points = []
    for i in range(len(traj)):
        points.append(
            {
                "t": round(float(traj["time"].iloc[i]), 2),
                "alphaDeg": round(float(alpha_deg[i]), 3),
                "airspeed": round(float(traj["V"].iloc[i]), 2),
                "pitchDeg": round(float(np.degrees(traj["theta"].iloc[i])), 3),
                "pitchRateDeg": round(float(np.degrees(traj["pitch_rate"].iloc[i])), 3),
                "elevatorDeg": round(float(np.degrees(traj["elevator"].iloc[i])), 3),
                "gammaDeg": round(float(np.degrees(traj["gamma"].iloc[i])), 3),
                "stallMarginDeg": round(float(np.degrees(traj["stall_margin"].iloc[i])), 3),
                "warningProbability": round(float(proba[i]), 4),
            }
        )

    out = {
        "trajectoryId": TRAJECTORY_ID,
        "source": "data/ml_temporal_v03/temporal_test.parquet (frozen v0.3 TEST split, unmodified) "
        "+ outputs/ml_v03/models/primary_model_D_1s.joblib (frozen model, inference only)",
        "stallBoundaryDeg": round(STALL_BOUNDARY_DEG, 3),
        "warningThreshold": round(threshold, 4),
        "crossingTimeS": crossing_time,
        "firstWarningTimeS": first_warned_time,
        "creditedLeadTimeS": lead_time_s,
        "points": points,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    print(f"wrote {len(points)} points to {OUT_PATH}")
    print(f"crossing at t={crossing_time}s, first warning at t={first_warned_time}s, "
          f"credited lead time = {lead_time_s}s")


if __name__ == "__main__":
    main()
