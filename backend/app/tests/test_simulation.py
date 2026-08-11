"""Simulation tests — toy case with known disruption behaviour + sanity bounds."""

from __future__ import annotations

import numpy as np

from app.core.simulation.monte_carlo import DisruptionConfig, run_monte_carlo


def test_toy_zero_disruption_high_service():
    """
    With all disruption probabilities at 0, every order fulfills on time.
    Stockout rate must be 0; service level must be 1; delay ≈ 0.
    """
    cfg = DisruptionConfig(
        production_delay_prob=0.0,
        demand_spike_prob=0.0,
        warehouse_down_prob=0.0,
        vehicle_breakdown_prob=0.0,
    )
    result = run_monte_carlo(
        n_replications=30,
        seed=0,
        n_orders=20,
        disruption=cfg,
    )
    assert result["stockout_rate"]["mean"] == 0.0
    assert result["service_level"]["mean"] == 1.0
    assert result["avg_fulfillment_delay"]["mean"] == 0.0
    assert result["resilience_score"] > 80


def test_toy_guaranteed_warehouse_down_hurts_service():
    """Warehouse always down periodically → service level must drop below 1."""
    cfg = DisruptionConfig(
        production_delay_prob=0.0,
        demand_spike_prob=0.0,
        warehouse_down_prob=1.0,
        warehouse_down_days=(3.0, 3.0),
        vehicle_breakdown_prob=0.0,
    )
    result = run_monte_carlo(n_replications=20, seed=1, n_orders=15, disruption=cfg)
    assert result["service_level"]["mean"] < 1.0
    assert result["avg_fulfillment_delay"]["mean"] > 0.0


def test_reproducibility_same_seed():
    a = run_monte_carlo(n_replications=10, seed=123, n_orders=10)
    b = run_monte_carlo(n_replications=10, seed=123, n_orders=10)
    assert a["stockout_rate"] == b["stockout_rate"]
    assert a["resilience_score"] == b["resilience_score"]


def test_sanity_bounds_default_config():
    result = run_monte_carlo(n_replications=50, seed=42, n_orders=30)
    assert 0 <= result["stockout_rate"]["mean"] <= 1
    assert 0 <= result["service_level"]["mean"] <= 1
    assert result["avg_fulfillment_delay"]["mean"] >= 0
    assert result["cost_overrun"]["mean"] >= 0
    assert 0 <= result["resilience_score"] <= 100
