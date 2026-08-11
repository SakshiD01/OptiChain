"""Capacitated Vehicle Routing Problem with Time Windows (CVRPTW).

Solved with Google OR-Tools Routing library. Distances are Haversine km
converted to travel minutes at an assumed average speed (no Maps API).

For each open warehouse, routes its assigned destinations minimizing total
travel distance subject to vehicle capacity and delivery time windows.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.data.generator import haversine_km

SOLVER_TIME_LIMIT_S = 30
AVG_SPEED_KMH = 50.0  # synthetic urban/regional average
SERVICE_TIME_MIN = 15  # minutes per stop
VEHICLE_CAPACITY = 500.0  # demand units per vehicle (must exceed largest stop)
DEFAULT_TW_START = 0  # minutes from planning origin
DEFAULT_TW_END = 7 * 24 * 60  # weekly planning horizon (minutes)


def _travel_minutes(km: float) -> int:
    return int(np.ceil(km / AVG_SPEED_KMH * 60.0))


def solve_cvrptw_for_depot(
    depot: dict[str, Any],
    stops: pd.DataFrame,
    demands: dict[str, float],
    vehicle_capacity: float = VEHICLE_CAPACITY,
    time_limit_s: int = SOLVER_TIME_LIMIT_S,
    max_vehicles: int | None = None,
) -> dict[str, Any]:
    """
    Solve CVRPTW for one depot.

    stops: DataFrame with id, lat, lon (and optional tw_start, tw_end in minutes)
    demands: stop_id → demand
    """
    if stops.empty:
        return {
            "warehouse_id": depot["id"],
            "status": "Optimal",
            "feasible": True,
            "routes": [],
            "total_distance_km": 0.0,
            "vehicles_used": 0,
            "utilization": 0.0,
            "solve_time_s": 0.0,
            "meta": {"method": "OR-Tools Routing CVRPTW", "note": "no stops assigned"},
        }

    stop_ids = stops["id"].tolist()
    # index 0 = depot
    locations = [{"id": depot["id"], "lat": depot["lat"], "lon": depot["lon"]}] + [
        {"id": r["id"], "lat": float(r["lat"]), "lon": float(r["lon"])}
        for _, r in stops.iterrows()
    ]
    n = len(locations)
    demand_vec = [0.0] + [float(demands[sid]) for sid in stop_ids]

    # Distance (meters-equivalent scaled) and time matrices
    dist_km = np.zeros((n, n))
    time_mat = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = haversine_km(locations[i]["lat"], locations[i]["lon"],
                             locations[j]["lat"], locations[j]["lon"])
            dist_km[i, j] = d
            time_mat[i, j] = _travel_minutes(d)

    total_demand = float(sum(demand_vec))
    # Capacity must cover the largest single stop
    peak = max(demand_vec) if demand_vec else 0.0
    if peak > vehicle_capacity:
        vehicle_capacity = float(np.ceil(peak))
    if max_vehicles is None:
        max_vehicles = max(1, int(np.ceil(total_demand / vehicle_capacity)) + 3)

    manager = pywrapcp.RoutingIndexManager(n, max_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        # OR-Tools wants ints — use meters
        return int(dist_km[f, t] * 1000)

    dist_cb_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(dist_cb_idx)

    def demand_callback(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        return int(np.ceil(demand_vec[node]))

    demand_cb_idx = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb_idx,
        0,
        [int(vehicle_capacity)] * max_vehicles,
        True,
        "Capacity",
    )

    def time_callback(from_index: int, to_index: int) -> int:
        f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        service = 0 if f == 0 else SERVICE_TIME_MIN
        return int(time_mat[f, t] + service)

    time_cb_idx = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(
        time_cb_idx,
        60,  # allow waiting
        DEFAULT_TW_END + 60,
        False,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    for i, sid in enumerate(stop_ids, start=1):
        index = manager.NodeToIndex(i)
        row = stops.loc[stops["id"] == sid].iloc[0]
        tw_start = int(row["tw_start"]) if "tw_start" in stops.columns else DEFAULT_TW_START
        tw_end = int(row["tw_end"]) if "tw_end" in stops.columns else DEFAULT_TW_END
        time_dim.CumulVar(index).SetRange(tw_start, tw_end)

    for v in range(max_vehicles):
        time_dim.CumulVar(routing.Start(v)).SetRange(DEFAULT_TW_START, DEFAULT_TW_END)
        time_dim.CumulVar(routing.End(v)).SetRange(DEFAULT_TW_START, DEFAULT_TW_END + 60)

    params = pywrapcp.DefaultRoutingSearchParameters()
    # Integer enum values (OR-Tools): PATH_CHEAPEST_ARC=3, GUIDED_LOCAL_SEARCH=2
    params.first_solution_strategy = 3
    params.local_search_metaheuristic = 2
    params.time_limit.FromSeconds(time_limit_s)

    t0 = time.perf_counter()
    solution = routing.SolveWithParameters(params)
    solve_time = time.perf_counter() - t0

    if solution is None:
        return {
            "warehouse_id": depot["id"],
            "status": "InfeasibleOrTimeout",
            "feasible": False,
            "routes": [],
            "total_distance_km": None,
            "vehicles_used": 0,
            "utilization": None,
            "solve_time_s": round(solve_time, 4),
            "meta": {
                "method": "OR-Tools Routing CVRPTW",
                "time_limit_s": time_limit_s,
                "fallback": "none — no solution; not fabricating routes",
                "max_vehicles": max_vehicles,
            },
        }

    routes = []
    total_dist = 0.0
    vehicles_used = 0
    load_sum = 0.0
    for v in range(max_vehicles):
        index = routing.Start(v)
        if routing.IsEnd(solution.Value(routing.NextVar(index))):
            continue  # unused vehicle
        vehicles_used += 1
        seq = [depot["id"]]
        route_load = 0.0
        route_dist = 0.0
        prev = 0
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                seq.append(locations[node]["id"])
                route_load += demand_vec[node]
            prev_index = index
            index = solution.Value(routing.NextVar(index))
            nxt = manager.IndexToNode(index)
            # When End is reached, nxt maps back via manager — use ArcCost
            route_dist += routing.GetArcCostForVehicle(prev_index, index, v) / 1000.0
            prev = nxt
        seq.append(depot["id"])
        total_dist += route_dist
        load_sum += route_load
        routes.append(
            {
                "vehicle": v,
                "sequence": seq,
                "load": round(route_load, 2),
                "distance_km": round(route_dist, 2),
                "capacity": vehicle_capacity,
                "utilization": round(route_load / vehicle_capacity, 4),
            }
        )

    utilization = (load_sum / (vehicles_used * vehicle_capacity)) if vehicles_used else 0.0

    return {
        "warehouse_id": depot["id"],
        "status": "OptimalOrFeasible",
        "feasible": True,
        "routes": routes,
        "total_distance_km": round(total_dist, 2),
        "vehicles_used": vehicles_used,
        "utilization": round(utilization, 4),
        "solve_time_s": round(solve_time, 4),
        "meta": {
            "method": "OR-Tools Routing CVRPTW",
            "time_limit_s": time_limit_s,
            "vehicle_capacity": vehicle_capacity,
            "avg_speed_kmh": AVG_SPEED_KMH,
            "n_stops": len(stop_ids),
            "max_vehicles": max_vehicles,
        },
    }


def solve_routing_for_network(
    warehouses: pd.DataFrame,
    destinations: pd.DataFrame,
    open_warehouse_ids: list[str],
    assignments: list[dict[str, Any]],
    destination_demand: dict[str, float],
    vehicle_capacity: float = VEHICLE_CAPACITY,
    time_limit_s: int = SOLVER_TIME_LIMIT_S,
) -> dict[str, Any]:
    """Solve CVRPTW per open warehouse using network-design assignments."""
    wh = warehouses.set_index("id")
    results = []
    for wid in open_warehouse_ids:
        assigned_dst = [
            a["destination_id"]
            for a in assignments
            if a["warehouse_id"] == wid and a.get("fraction", 0) > 0.5
        ]
        # Also include partial assignments scaled
        stop_demand = {}
        for a in assignments:
            if a["warehouse_id"] != wid:
                continue
            did = a["destination_id"]
            stop_demand[did] = float(destination_demand[did]) * float(a["fraction"])

        stops = destinations[destinations["id"].isin(stop_demand.keys())].copy()
        depot = {
            "id": wid,
            "lat": float(wh.loc[wid, "lat"]),
            "lon": float(wh.loc[wid, "lon"]),
        }
        results.append(
            solve_cvrptw_for_depot(
                depot,
                stops,
                stop_demand,
                vehicle_capacity=vehicle_capacity,
                time_limit_s=time_limit_s,
            )
        )

    feasible = all(r["feasible"] for r in results)
    total_dist = sum(r["total_distance_km"] or 0 for r in results)
    vehicles = sum(r["vehicles_used"] for r in results)

    return {
        "feasible": feasible,
        "warehouse_routes": results,
        "total_distance_km": round(total_dist, 2),
        "total_vehicles_used": vehicles,
        "meta": {"method": "OR-Tools CVRPTW per open warehouse", "time_limit_s": time_limit_s},
    }
