"""Loading and split-integrity verification for the frozen Dataset v0.2.

Does not regenerate or modify any data/*_v2.* file. Only reads them.
"""

import json
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

from . import config


class SplitIntegrityError(Exception):
    """Raised when the train/validation/test trajectory sets overlap."""


def verify_split_integrity(manifest: pd.DataFrame) -> None:
    """Fails loudly (Section 4) if any trajectory_id appears in more than
    one split, or if a trajectory_id is duplicated within the manifest."""
    dup = manifest["trajectory_id"][manifest["trajectory_id"].duplicated()]
    if len(dup) > 0:
        raise SplitIntegrityError(f"Duplicate trajectory_id(s) in split manifest: {sorted(set(dup))}")

    ids_by_split = {s: set(g["trajectory_id"]) for s, g in manifest.groupby("split")}
    splits = list(ids_by_split.keys())
    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            overlap = ids_by_split[splits[i]] & ids_by_split[splits[j]]
            if overlap:
                raise SplitIntegrityError(
                    f"trajectory_id overlap between splits '{splits[i]}' and '{splits[j]}': {sorted(overlap)}"
                )


@dataclass
class Dataset:
    """The full processed table plus per-split trajectory_id sets and the
    frozen generation configuration, for reference/reporting."""

    processed: pd.DataFrame  # all rows, all splits, with a 'split' column merged in
    manifest: pd.DataFrame
    metadata: pd.DataFrame
    generation_config: dict

    def split_df(self, split_name: str) -> pd.DataFrame:
        return self.processed[self.processed["split"] == split_name]

    def trajectory_ids(self, split_name: str):
        return set(self.manifest.loc[self.manifest["split"] == split_name, "trajectory_id"])


def load_dataset() -> Dataset:
    """Load the frozen v0.2 processed dataset, split manifest, and metadata;
    verify split integrity (raises SplitIntegrityError on any overlap);
    merge the split assignment into the processed table.
    """
    processed = pd.read_parquet(config.PROCESSED_DATASET_PATH)
    manifest = pd.read_csv(config.SPLIT_MANIFEST_PATH)
    metadata = pd.read_csv(config.METADATA_PATH)

    verify_split_integrity(manifest)

    n_before = len(processed)
    processed = processed.merge(manifest, on="trajectory_id", how="left", validate="many_to_one")
    if len(processed) != n_before:
        raise SplitIntegrityError("merge with split manifest changed row count -- manifest does not cover all trajectory_ids 1:1")
    if processed["split"].isna().any():
        missing = processed.loc[processed["split"].isna(), "trajectory_id"].unique()
        raise SplitIntegrityError(f"trajectory_id(s) present in processed data but missing from split manifest: {sorted(missing)}")

    with open(config.GENERATION_CONFIG_PATH) as f:
        generation_config = json.load(f)

    return Dataset(processed=processed, manifest=manifest, metadata=metadata, generation_config=generation_config)


def report_split_sizes(dataset: Dataset) -> Dict[str, dict]:
    out = {}
    for split_name in ["train", "val", "test"]:
        ids = dataset.trajectory_ids(split_name)
        rows = dataset.split_df(split_name)
        out[split_name] = {"n_trajectories": len(ids), "n_rows": len(rows)}
    return out
