"""Network design — capacitated warehouse location + assignment MILP.

Decision variables:
  y_w ∈ {0,1}  — open warehouse w
  x_{w,d} ≥ 0  — fraction of destination d demand served by warehouse w

Objective:
  minimize Σ_w fixed_cost_w * y_w + Σ_{w,d} cost_per_unit_km * dist_{w,d} * demand_d * x_{w,d}

Constraints:
  Σ_w x_{w,d} = 1                          ∀d  (100% coverage)
  Σ_d demand_d * x_{w,d} ≤ capacity_w * y_w ∀w  (capacity only if open)
  x_{w,d} ≤ y_w                             ∀w,d (cannot assign to closed WH)
  Optional: Σ_w y_w = forced_open_count     (scenario dashboard override)

Solved with PuLP CBC, timeLimit=30s. On timeout, returns best feasible found
(status documented honestly — never a fabricated objective).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
import pulp

from app.data.generator import haversine_km

SOLVER_TIME_LIMIT_S = 30
# $/unit-km — synthetic but order-of-magnitude realistic for road freight
DEFAULT_COST_PER_UNIT_KM = 0.02


def build_and_solve(
    warehouses: pd.DataFrame,
    destinations: pd.DataFrame,
    destination_demand: dict[str, float],
    cost_per_unit_km: float = DEFAULT_COST_PER_UNIT_KM,
    forced_open_count: int | None = None,
    time_limit_s: int = SOLVER_TIME_LIMIT_S,
) -> dict[str, Any]:
    """
    Solve the facility-location MILP.

    destination_demand maps destination_id → weekly (or planning-horizon) demand units.
    """
    wh_ids = warehouses["id"].tolist()
    dst_ids = destinations["id"].tolist()
    wh = warehouses.set_index("id")
    dst = destinations.set_index("id")

    # Distance & transport cost matrices
    dist = {
        (w, d): haversine_km(float(wh.loc[w, "lat"]), float(wh.loc[w, "lon"]),
                             float(dst.loc[d, "lat"]), float(dst.loc[d, "lon"]))
        for w in wh_ids
        for d in dst_ids
    }
    demand = {d: float(destination_demand[d]) for d in dst_ids}

    prob = pulp.LpProblem("optichain_network_design", pulp.LpMinimize)
    y = pulp.LpVariable.dicts("open", wh_ids, cat=pulp.LpBinary)
    x = pulp.LpVariable.dicts("assign", [(w, d) for w in wh_ids for d in dst_ids], lowBound=0, upBound=1)

    # Objective
    fixed = pulp.lpSum(float(wh.loc[w, "fixed_cost"]) * y[w] for w in wh_ids)
    transport = pulp.lpSum(
        cost_per_unit_km * dist[w, d] * demand[d] * x[w, d]
        for w in wh_ids
        for d in dst_ids
    )
    prob += fixed + transport

    # Coverage
    for d in dst_ids:
        prob += pulp.lpSum(x[w, d] for w in wh_ids) == 1, f"cover_{d}"

    # Capacity + linking
    for w in wh_ids:
        cap = float(wh.loc[w, "capacity"])
        prob += (
            pulp.lpSum(demand[d] * x[w, d] for d in dst_ids) <= cap * y[w],
            f"cap_{w}",
        )
        for d in dst_ids:
            prob += x[w, d] <= y[w], f"link_{w}_{d}"

    if forced_open_count is not None:
        if not 1 <= forced_open_count <= len(wh_ids):
            raise ValueError(f"forced_open_count must be in [1, {len(wh_ids)}]")
        prob += pulp.lpSum(y[w] for w in wh_ids) == forced_open_count, "forced_count"

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit_s)
    t0 = time.perf_counter()
    status_code = prob.solve(solver)
    solve_time = time.perf_counter() - t0
    status = pulp.LpStatus[status_code]

    if status not in ("Optimal", "Feasible"):
        return {
            "status": status,
            "feasible": False,
            "objective": None,
            "solve_time_s": round(solve_time, 4),
            "open_warehouses": [],
            "assignments": [],
            "fixed_cost": None,
            "transport_cost": None,
            "meta": {
                "method": "PuLP CBC MILP",
                "time_limit_s": time_limit_s,
                "fallback": "none — infeasible or not solved; no fabricated objective",
            },
        }

    open_wh = [w for w in wh_ids if y[w].value() and y[w].value() > 0.5]
    assignments = []
    for w in wh_ids:
        for d in dst_ids:
            val = x[w, d].value() or 0.0
            if val > 1e-6:
                assignments.append(
                    {
                        "warehouse_id": w,
                        "destination_id": d,
                        "fraction": round(float(val), 4),
                        "demand": demand[d],
                        "distance_km": round(dist[w, d], 2),
                        "transport_cost": round(
                            cost_per_unit_km * dist[w, d] * demand[d] * float(val), 2
                        ),
                    }
                )

    fixed_val = float(sum(float(wh.loc[w, "fixed_cost"]) for w in open_wh))
    transport_val = float(sum(a["transport_cost"] for a in assignments))
    obj = float(pulp.value(prob.objective))

    return {
        "status": status,
        "feasible": True,
        "objective": round(obj, 2),
        "solve_time_s": round(solve_time, 4),
        "open_warehouses": open_wh,
        "assignments": assignments,
        "fixed_cost": round(fixed_val, 2),
        "transport_cost": round(transport_val, 2),
        "meta": {
            "method": "PuLP CBC MILP",
            "time_limit_s": time_limit_s,
            "cost_per_unit_km": cost_per_unit_km,
            "n_warehouses_candidate": len(wh_ids),
            "n_destinations": len(dst_ids),
            "forced_open_count": forced_open_count,
        },
    }


def baseline_all_open(
    warehouses: pd.DataFrame,
    destinations: pd.DataFrame,
    destination_demand: dict[str, float],
    cost_per_unit_km: float = DEFAULT_COST_PER_UNIT_KM,
) -> dict[str, Any]:
    """Force all warehouses open — before/after comparison baseline."""
    return build_and_solve(
        warehouses,
        destinations,
        destination_demand,
        cost_per_unit_km=cost_per_unit_km,
        forced_open_count=len(warehouses),
    )


def demand_by_destination(
    total_weekly_demand: float,
    destinations: pd.DataFrame,
) -> dict[str, float]:
    """Allocate aggregate demand across destinations by weekly_demand_share."""
    return {
        row["id"]: float(total_weekly_demand * row["weekly_demand_share"])
        for _, row in destinations.iterrows()
    }


def solve_network_for_scenario(
    scenario: dict[str, Any],
    forecast_weekly_total: float | None = None,
    forced_open_count: int | None = None,
    cost_per_unit_km: float = DEFAULT_COST_PER_UNIT_KM,
) -> dict[str, Any]:
    """
    High-level entry: optimized network + all-open baseline comparison.
    """
    warehouses = scenario["warehouses"]
    destinations = scenario["destinations"]
    if forecast_weekly_total is None:
        # Mean weekly total from history
        hist = scenario["demand_history"]
        forecast_weekly_total = float(hist.groupby("week_start")["quantity"].sum().mean())

    dest_demand = demand_by_destination(forecast_weekly_total, destinations)
    optimized = build_and_solve(
        warehouses,
        destinations,
        dest_demand,
        cost_per_unit_km=cost_per_unit_km,
        forced_open_count=forced_open_count,
    )
    baseline = baseline_all_open(warehouses, destinations, dest_demand, cost_per_unit_km)

    savings = None
    if optimized["feasible"] and baseline["feasible"]:
        savings = round(baseline["objective"] - optimized["objective"], 2)

    return {
        "optimized": optimized,
        "baseline_all_open": baseline,
        "savings_vs_all_open": savings,
        "weekly_demand_total": round(forecast_weekly_total, 2),
    }
