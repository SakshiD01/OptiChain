"""VRP tests — tiny hand-checkable instance + scenario sanity."""

from __future__ import annotations

import pandas as pd

from app.core.network_design.solver import solve_network_for_scenario
from app.core.vehicle_routing.solver import solve_cvrptw_for_depot, solve_routing_for_network
from app.data.generator import ScenarioConfig, generate_scenario, haversine_km


def test_toy_cvrptw_two_stops():
    """
    Depot at (0,0), two nearby stops with demand 10 each, capacity 25.
    One vehicle must visit both; total distance ≥ depot→A + A→B + B→depot (TSP).
    """
    depot = {"id": "DEPOT", "lat": 0.0, "lon": 0.0}
    stops = pd.DataFrame(
        [
            {"id": "S1", "lat": 0.05, "lon": 0.0},
            {"id": "S2", "lat": 0.0, "lon": 0.05},
        ]
    )
    demands = {"S1": 10.0, "S2": 10.0}
    result = solve_cvrptw_for_depot(depot, stops, demands, vehicle_capacity=25.0, time_limit_s=10)

    assert result["feasible"] is True
    assert result["vehicles_used"] == 1
    assert len(result["routes"]) == 1
    seq = result["routes"][0]["sequence"]
    assert seq[0] == "DEPOT" and seq[-1] == "DEPOT"
    assert set(seq[1:-1]) == {"S1", "S2"}

    # Lower bound: visit both — distance at least the MST-ish star bound
    d1 = haversine_km(0, 0, 0.05, 0)
    d2 = haversine_km(0, 0, 0, 0.05)
    assert result["total_distance_km"] >= min(d1, d2) * 2 - 1e-6
    assert result["routes"][0]["load"] == 20.0


def test_capacity_forces_two_vehicles():
    depot = {"id": "DEPOT", "lat": 0.0, "lon": 0.0}
    stops = pd.DataFrame(
        [
            {"id": "S1", "lat": 0.02, "lon": 0.0},
            {"id": "S2", "lat": -0.02, "lon": 0.0},
        ]
    )
    demands = {"S1": 60.0, "S2": 60.0}
    result = solve_cvrptw_for_depot(depot, stops, demands, vehicle_capacity=70.0, time_limit_s=10)
    assert result["feasible"]
    assert result["vehicles_used"] == 2


def test_full_scenario_routing_sanity():
    scenario = generate_scenario(ScenarioConfig(seed=42))
    network = solve_network_for_scenario(scenario)
    assert network["optimized"]["feasible"]
    dest_demand = {
        row["id"]: float(network["weekly_demand_total"] * row["weekly_demand_share"])
        for _, row in scenario["destinations"].iterrows()
    }
    routing = solve_routing_for_network(
        scenario["warehouses"],
        scenario["destinations"],
        network["optimized"]["open_warehouses"],
        network["optimized"]["assignments"],
        dest_demand,
        time_limit_s=15,
    )
    assert routing["feasible"]
    assert routing["total_distance_km"] > 0
    assert routing["total_vehicles_used"] >= 1
