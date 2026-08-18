"""Deterministic, trajectory-level train/validation/test splitting.

CRITICAL (Section 13): splitting is done by trajectory_id, never by
individual timestep -- every row belonging to a given trajectory_id goes
to exactly one split. Timesteps within a trajectory are highly
correlated (they are one continuous physical flight), so splitting them
individually would leak information between train and test.
"""

from typing import List

import numpy as np
import pandas as pd

TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
TEST_FRACTION = 0.15


def split_trajectory_ids(trajectory_ids: List[str], seed: int) -> pd.DataFrame:
    """Deterministically shuffle and split trajectory IDs 70/15/15.

    Uses a Generator seeded with the SAME dataset seed used for
    generation, but as an independently-constructed Generator instance
    (splitting is a separate, later step from generation, and should be
    reproducible on its own from the manifest of IDs plus the seed,
    without re-running generation).

    Returns a DataFrame with columns [trajectory_id, split].
    """
    ids = np.array(sorted(trajectory_ids))  # sort first so the shuffle is the only source of order
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)

    n = len(ids)
    n_train = int(round(TRAIN_FRACTION * n))
    n_val = int(round(VAL_FRACTION * n))
    # test gets the remainder, so rounding never drops or duplicates an id
    n_test = n - n_train - n_val

    splits = np.array(["train"] * n_train + ["val"] * n_val + ["test"] * n_test)
    assert len(splits) == n

    manifest = pd.DataFrame({"trajectory_id": ids, "split": splits})
    return manifest.sort_values("trajectory_id").reset_index(drop=True)


def verify_no_overlap(manifest: pd.DataFrame) -> None:
    """Raises AssertionError if any trajectory_id appears in more than
    one split, or if the manifest has duplicate trajectory_ids."""
    counts = manifest["trajectory_id"].value_counts()
    duplicated = counts[counts > 1]
    if len(duplicated) > 0:
        raise AssertionError(f"trajectory_id(s) appear more than once in split manifest: {list(duplicated.index)}")

    splits_per_id = manifest.groupby("trajectory_id")["split"].nunique()
    bad = splits_per_id[splits_per_id > 1]
    if len(bad) > 0:
        raise AssertionError(f"trajectory_id(s) assigned to multiple splits: {list(bad.index)}")
