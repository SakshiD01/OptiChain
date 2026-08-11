"""Inventory optimization tests — hand-checkable toy case + full-scenario sanity."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.inventory.optimizer import (
    compute_policy,
    economic_order_quantity,
    optimize_inventory,
    reorder_point,
    safety_stock,
    z_for_service_level,
)
from app.data.generator import ScenarioConfig, generate_scenario


def test_eoq_harris_wilson_toy_case():
    """
    Classic textbook EOQ (hand-checkable):
      D = 1000 units/year, S = $10/order, H = $0.50/unit/year
      Q* = sqrt(2DS/H) = sqrt(40000) = 200
    """
    eoq = economic_order_quantity(annual_demand=1000, ordering_cost=10, unit_holding_cost=0.5)
    assert abs(eoq - 200.0) < 1e-9


def test_safety_stock_and_rop_toy_case():
    """
    Hand check: σ_week = 10, L = 4 weeks, z(95%) ≈ 1.64485
      SS = 1.64485 * 10 * sqrt(4) = 32.897
      μ = 50/week → ROP = 50*4 + 32.897 = 232.897
    """
    z = z_for_service_level(0.95)
    ss = safety_stock(z, demand_std_weekly=10.0, lead_time_weeks=4.0)
    assert abs(ss - z * 10.0 * 2.0) < 1e-9
    rop = reorder_point(avg_weekly_demand=50.0, lead_time_weeks=4.0, safety_stock_units=ss)
    assert abs(rop - (200.0 + ss)) < 1e-9


def test_compute_policy_multi_echelon_lead_time():
    # Constant demand → SS driven only by zero std ≈ 0; lead = transit + production
    weekly = np.full(52, 40.0)
    policy = compute_policy(
        sku_id="TOY",
        warehouse_id="WH-1",
        weekly_demand=weekly,
        ordering_cost=50.0,
        unit_cost=8.0,
        holding_cost_rate=0.25,
        service_level=0.95,
        transit_lead_weeks=1.0,
        production_lead_weeks=2.0,
    )
    assert policy.lead_time_weeks == 3.0
    assert policy.safety_stock == 0.0  # zero variance
    assert policy.reorder_point == pytest.approx(40.0 * 3.0, rel=1e-6)
    assert policy.eoq > 0
    assert policy.total_annual_inventory_cost > 0


def test_full_scenario_inventory_sanity():
    scenario = generate_scenario(ScenarioConfig(seed=42))
    # Use two warehouses to keep the test light but multi-location
    result = optimize_inventory(
        demand_history=scenario["demand_history"],
        skus=scenario["skus"],
        warehouses=scenario["warehouses"].head(2),
        service_level=0.95,
    )
    assert result["summary"]["n_policies"] == 25 * 2
    assert result["summary"]["total_annual_inventory_cost"] > 0
    for p in result["policies"]:
        assert p["eoq"] > 0
        assert p["reorder_point"] >= p["safety_stock"]
        assert 0 < p["service_level"] <= 1


def test_invalid_service_level_raises():
    with pytest.raises(ValueError):
        z_for_service_level(1.5)
