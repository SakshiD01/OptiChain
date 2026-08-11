"""Tests for the synthetic data generating process."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.generator import (
    DEFAULT_SEED,
    N_DESTINATIONS,
    N_SKUS,
    N_WAREHOUSES,
    N_WEEKS_HISTORY,
    ScenarioConfig,
    distance_matrix,
    generate_scenario,
    haversine_km,
)


def test_scenario_shape_and_reproducibility():
    a = generate_scenario(ScenarioConfig(seed=DEFAULT_SEED))
    b = generate_scenario(ScenarioConfig(seed=DEFAULT_SEED))

    assert len(a["skus"]) == N_SKUS
    assert len(a["warehouses"]) == N_WAREHOUSES
    assert len(a["destinations"]) == N_DESTINATIONS
    assert len(a["demand_history"]) == N_SKUS * N_WEEKS_HISTORY

    # Destination shares form a probability simplex
    share_sum = a["destinations"]["weekly_demand_share"].sum()
    assert abs(share_sum - 1.0) < 1e-9

    # Same seed → identical demand series
    pd.testing.assert_frame_equal(a["demand_history"], b["demand_history"])
    assert a["meta"]["total_demand_units"] == b["meta"]["total_demand_units"]


def test_different_seeds_differ():
    a = generate_scenario(ScenarioConfig(seed=1))
    b = generate_scenario(ScenarioConfig(seed=2))
    assert not np.allclose(
        a["demand_history"]["quantity"].to_numpy(),
        b["demand_history"]["quantity"].to_numpy(),
    )


def test_demand_positive_and_has_variation():
    scenario = generate_scenario()
    qty = scenario["demand_history"]["quantity"]
    assert (qty > 0).all()
    # Across SKUs/weeks there must be real variation (not a flat constant)
    assert qty.std() > 10.0


def test_haversine_known_distance():
    # NYC to LA ≈ 3936 km (great-circle); allow 2% tolerance
    d = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
    assert 3850 < d < 4050


def test_distance_matrix_symmetric_zero_diag():
    locs = generate_scenario()["warehouses"]
    mat = distance_matrix(locs)
    assert mat.shape == (N_WAREHOUSES, N_WAREHOUSES)
    assert np.allclose(np.diag(mat), 0.0)
    assert np.allclose(mat, mat.T)
