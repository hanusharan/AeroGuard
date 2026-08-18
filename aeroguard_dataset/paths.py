"""Path bootstrapping shared by every module in this package.

The core physics (aeroguard/) is a proper package, but the trim solver
lives in scripts/simulate.py, which is a standalone script, not a
package member (this mirrors how tests/test_trim.py and
scripts/validate_physics.py already import it). Importing this module
first makes both `aeroguard.*` and `simulate` importable everywhere
else in aeroguard_dataset/ without repeating the sys.path setup.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")

for _p in (PROJECT_ROOT, SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Re-exported so callers can do `from aeroguard_dataset.paths import trim_level_flight`
# instead of repeating the sys.path dance.
from simulate import trim_level_flight  # noqa: E402
from validate_physics import cl_max_of, stall_speed  # noqa: E402

DATA_RAW_DIR = os.path.join(DATA_DIR, "raw")
DATA_PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
DATA_METADATA_DIR = os.path.join(DATA_DIR, "metadata")
DATA_SPLITS_DIR = os.path.join(DATA_DIR, "splits")
AUDIT_DIR = os.path.join(OUTPUTS_DIR, "dataset_audit")
AUDIT_PLOTS_DIR = os.path.join(AUDIT_DIR, "plots")

# v0.2 dataset outputs are kept in separate files/directories from v0.1's
# (never overwritten) so the two datasets can always be compared directly.
AUDIT_DIR_V2 = os.path.join(OUTPUTS_DIR, "dataset_audit_v2")
AUDIT_PLOTS_DIR_V2 = os.path.join(AUDIT_DIR_V2, "plots")


def ensure_data_dirs() -> None:
    for d in (DATA_RAW_DIR, DATA_PROCESSED_DIR, DATA_METADATA_DIR, DATA_SPLITS_DIR, AUDIT_PLOTS_DIR, AUDIT_PLOTS_DIR_V2):
        os.makedirs(d, exist_ok=True)
