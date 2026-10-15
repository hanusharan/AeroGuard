"""EXCLUDED GROUP (marker ``synthetic_fit``): tiny real forests fitted on random in-memory data.

These tests are NOT authorized at G33-3 and are skipped unless the environment variable ITEM33_ALLOW_SYNTHETIC_FIT=1
is set, which must only be done after the researcher approves them. They were written but have NOT been executed.
They fit nothing from research data, persist no model, and use only fixed-seed random arrays.
"""

import os

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("ITEM33_ALLOW_SYNTHETIC_FIT") != "1",
                                reason="synthetic_fit group excluded at G33-3 (not authorized)")

from item33 import SEEDS, conditions as cond, fitting


def data(n=300, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({f: rng.standard_normal(n) for f in cond.C0_FEATURES})
    y = (X["alpha"] + 0.3 * rng.standard_normal(n) > 0).astype(int)
    return X, y


@pytest.mark.parametrize("c", cond.CONDITION_ORDER)
def test_the_seed_reaches_the_forest_and_max_features_is_four_for_every_condition(c):
    X, y = data()
    m = fitting.build_forest(SEEDS[2])
    m.fit(X[cond.features_for(c)], y)
    assert m.random_state == SEEDS[2] and int(m.estimators_[0].max_features_) == 4


def test_conditions_at_one_seed_share_their_row_bootstraps_and_other_seeds_do_not():
    X, y = data()
    a = fitting.build_forest(SEEDS[1]).fit(X[cond.features_for("C0")], y)
    b = fitting.build_forest(SEEDS[1]).fit(X[cond.features_for("C2")], y)
    c = fitting.build_forest(SEEDS[2]).fit(X[cond.features_for("C0")], y)
    assert all(np.array_equal(s1, s2) for s1, s2 in zip(a.estimators_samples_, b.estimators_samples_))
    assert any(not np.array_equal(s1, s2) for s1, s2 in zip(a.estimators_samples_, c.estimators_samples_))
