"""Comparison register and the machine-readable row schema (PROTOCOL.md sections 9.5 and 13)."""

import math
from typing import Dict, List, Mapping

from . import conditions as cond
from .summary import STATUSES

FAMILY_RETRAINED = "retrained_ablation"
FAMILY_MASKING = "frozen_model_masking"
FAMILIES = (FAMILY_RETRAINED, FAMILY_MASKING)
EVIDENCE_CATEGORY = "E2"
EXPOSURE_LABEL = "previously exposed test data; regenerated copy; not blind; not independent replication"

ROW_FIELDS = (
    "analysis_family", "condition", "seed", "metric", "value", "population_id", "evidence_category",
    "register_id", "status", "exposure_label",
)

# (id, comparison, status, estimand, interval, adjustment)  -- identical to PROTOCOL.md section 9.5
REGISTER: List[Dict[str, str]] = [
    {"id": "D1", "comparison": "C0 - C1", "status": "primary", "estimand": "seed-mean delta", "interval": "percentile 95%", "adjustment": "Bonferroni sensitivity (m=2)"},
    {"id": "D2", "comparison": "C0 - C2", "status": "primary", "estimand": "seed-mean delta", "interval": "percentile 95%", "adjustment": "Bonferroni sensitivity (m=2)"},
    {"id": "SEC-1", "comparison": "D1, D2 at seed 20260817", "status": "secondary", "estimand": "single-seed delta", "interval": "percentile 95%", "adjustment": "none"},
    {"id": "SEC-2", "comparison": "C1 - C2", "status": "secondary", "estimand": "seed-mean delta", "interval": "percentile 95%", "adjustment": "none"},
    {"id": "SEC-3", "comparison": "ROC-AUC analogues of D1, D2", "status": "secondary", "estimand": "seed-mean delta", "interval": "percentile 95%", "adjustment": "none"},
    {"id": "T1", "comparison": "C0(seed 20260817) vs frozen model", "status": "technical", "estimand": "reproduction level R0/R1/R2", "interval": "percentile 95%", "adjustment": "none"},
    {"id": "SR", "comparison": "D1, D2 under regime-stratified resampling", "status": "sensitivity", "estimand": "seed-mean delta", "interval": "stratified percentile 95%", "adjustment": "none"},
    {"id": "X-a", "comparison": "C0 - C3", "status": "exploratory", "estimand": "seed-mean delta", "interval": "percentile 95%", "adjustment": "none"},
    {"id": "X-b", "comparison": "C0 - X1", "status": "exploratory", "estimand": "seed-mean delta", "interval": "percentile 95%", "adjustment": "none"},
    {"id": "X-c", "comparison": "matched operating point (validation-defined)", "status": "exploratory", "estimand": "descriptive differences", "interval": "seed by seed", "adjustment": "none"},
    {"id": "X-d", "comparison": "own-threshold and event metrics", "status": "descriptive", "estimand": "descriptive", "interval": "none", "adjustment": "none"},
    {"id": "EST", "comparison": "per-condition per-seed point estimates (not a comparison)", "status": "descriptive", "estimand": "A_c(s)", "interval": "none", "adjustment": "none"},
    {"id": "M", "comparison": "frozen-model masking (separate family)", "status": "descriptive", "estimand": "PR-AUC change of the frozen model", "interval": "bootstrap for 9 variants", "adjustment": "none"},
]
PRIMARY_IDS = tuple(r["id"] for r in REGISTER if r["status"] == "primary")


def register_by_id() -> Dict[str, Dict[str, str]]:
    return {r["id"]: r for r in REGISTER}


def validate_register() -> bool:
    ids = [r["id"] for r in REGISTER]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate register ids")
    if PRIMARY_IDS != ("D1", "D2"):
        raise ValueError("the primary contrasts must be exactly D1 and D2")
    for r in REGISTER:
        if r["status"] not in STATUSES:
            raise ValueError(f"register row {r['id']}: unknown status {r['status']!r}")
    return True


def metric_row(*, analysis_family: str, condition: str, seed, metric: str, value, population_id: str, register_id: str) -> Dict[str, object]:
    """One long-format row. Retrained rows use the condition labels C0..X1; masking rows never do."""
    if register_id not in register_by_id():
        raise ValueError(f"unknown register id {register_id!r}")
    row = {
        "analysis_family": analysis_family, "condition": condition, "seed": seed, "metric": metric,
        "value": None if (isinstance(value, float) and not math.isfinite(value)) else value,
        "population_id": population_id, "evidence_category": EVIDENCE_CATEGORY, "register_id": register_id,
        "status": register_by_id()[register_id]["status"], "exposure_label": EXPOSURE_LABEL,
    }
    validate_row(row)
    return row


def validate_row(row: Mapping[str, object]) -> bool:
    missing = [f for f in ROW_FIELDS if f not in row]
    extra = [k for k in row if k not in ROW_FIELDS]
    if missing or extra:
        raise ValueError(f"row fields differ from the schema: missing {missing}, extra {extra}")
    if row["analysis_family"] not in FAMILIES:
        raise ValueError(f"unknown analysis family {row['analysis_family']!r}")
    if row["evidence_category"] != EVIDENCE_CATEGORY:
        raise ValueError("new results must carry evidence category E2")
    if row["register_id"] not in register_by_id():
        raise ValueError(f"unknown register id {row['register_id']!r}")
    labels = set(cond.CONDITION_ORDER)
    if row["analysis_family"] == FAMILY_RETRAINED and row["condition"] not in labels | {"FROZEN"}:
        raise ValueError(f"retrained row with unknown condition {row['condition']!r}")
    if row["analysis_family"] == FAMILY_MASKING and row["condition"] in labels:
        raise ValueError("masking rows must not use the retrained condition labels")
    if row["status"] not in STATUSES:
        raise ValueError(f"unknown status {row['status']!r}")
    return True
