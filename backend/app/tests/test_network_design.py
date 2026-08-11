"""Network design tests — brute-forceable toy MILP + full-scenario sanity."""

from __future__ import annotations

import pandas as pd

from app.core.network_design.solver import build_and_solve, solve_network_for_scenario
from app.data.generator import ScenarioConfig, generate_scenario


def _toy_instance():
    """
    2 warehouses, 3 destinations — small enough to verify by enumeration.

    WH-A at (0,0): fixed=100, capacity=100
    WH-B at (0,1): fixed=1000, capacity=100   (expensive — should stay closed)

    Destinations all near A with modest demand. Optimal: open only A.
    """
    warehouses = pd.DataFrame(
        [
            {"id": "A", "name": "A", "lat": 0.0, "lon": 0.0, "fixed_cost": 100.0, "capacity": 100.0},
            {"id": "B", "name": "B", "lat": 0.0, "lon": 1.0, "fixed_cost": 1000.0, "capacity": 100.0},
        ]
    )
    destinations = pd.DataFrame(
        [
            {"id": "D1", "name": "D1", "lat": 0.01, "lon": 0.01, "weekly_demand_share": 0.4},
            {"id": "D2", "name": "D2", "lat": -0.01, "lon": 0.0, "weekly_demand_share": 0.3},
            {"id": "D3", "name": "D3", "lat": 0.0, "lon": -0.01, "weekly_demand_share": 0.3},
        ]
    )
    demand = {"D1": 20.0, "D2": 15.0, "D3": 15.0}  # total 50 < capacity 100
    return warehouses, destinations, demand


def test_toy_milp_opens_cheap_warehouse_only():
    warehouses, destinations, demand = _toy_instance()
    result = build_and_solve(warehouses, destinations, demand, cost_per_unit_km=0.01)

    assert result["feasible"] is True
    assert result["status"] == "Optimal"
    assert result["open_warehouses"] == ["A"]
    assert "B" not in result["open_warehouses"]
    # All demand assigned
    assert abs(sum(a["fraction"] for a in result["assignments"]) - 3.0) < 1e-6
    # Objective = fixed(A) + transport > 100, and less than opening both
    assert result["objective"] >= 100.0
    assert result["fixed_cost"] == 100.0


def test_toy_forced_both_open_costs_more():
    warehouses, destinations, demand = _toy_instance()
    opt = build_and_solve(warehouses, destinations, demand, cost_per_unit_km=0.01)
    both = build_and_solve(
        warehouses, destinations, demand, cost_per_unit_km=0.01, forced_open_count=2
    )
    assert both["feasible"]
    assert set(both["open_warehouses"]) == {"A", "B"}
    assert both["objective"] > opt["objective"]
    assert both["fixed_cost"] == 1100.0


def test_full_scenario_network_sanity():
    scenario = generate_scenario(ScenarioConfig(seed=42))
    result = solve_network_for_scenario(scenario)
    assert result["optimized"]["feasible"]
    assert result["baseline_all_open"]["feasible"]
    assert result["optimized"]["objective"] > 0
    assert result["baseline_all_open"]["objective"] > 0
    # Optimized should be ≤ all-open (same or better)
    assert result["optimized"]["objective"] <= result["baseline_all_open"]["objective"] + 1e-6
    assert result["savings_vs_all_open"] is not None
    assert result["savings_vs_all_open"] >= -1e-6
    assert 1 <= len(result["optimized"]["open_warehouses"]) <= 4
