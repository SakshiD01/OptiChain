"""Inventory optimization core — EOQ, safety stock, reorder point.

Framework-agnostic. Uses classical inventory formulas:

  EOQ = sqrt(2 * D * S / H)
    D = annual demand, S = ordering cost, H = annual holding cost per unit

  Safety stock = z * σ_L
    z = service-level z-score, σ_L = stddev of demand over lead time
    For independent weekly demand: σ_L = σ_week * sqrt(L_weeks)

  ROP = demand_during_lead_time + safety_stock

Multi-echelon: warehouse lead time includes production replenishment lead time
from the central plant (L_wh = L_transit + L_production).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

# Common service-level targets → standard normal z
SERVICE_LEVEL_Z = {
    0.90: 1.2815515655446004,
    0.95: 1.6448536269514722,
    0.98: 2.0537489106318225,
    0.99: 2.3263478740408408,
}


def z_for_service_level(service_level: float) -> float:
    """Return one-sided normal z-score for a fill-rate / cycle-service target."""
    if service_level in SERVICE_LEVEL_Z:
        return SERVICE_LEVEL_Z[service_level]
    if not 0.5 < service_level < 1.0:
        raise ValueError(f"service_level must be in (0.5, 1), got {service_level}")
    return float(stats.norm.ppf(service_level))


@dataclass(frozen=True)
class InventoryPolicy:
    sku_id: str
    warehouse_id: str
    eoq: float
    safety_stock: float
    reorder_point: float
    avg_weekly_demand: float
    demand_std_weekly: float
    lead_time_weeks: float
    service_level: float
    z: float
    annual_demand: float
    ordering_cost: float
    unit_holding_cost: float
    annual_ordering_cost: float
    annual_holding_cost: float
    total_annual_inventory_cost: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def economic_order_quantity(annual_demand: float, ordering_cost: float, unit_holding_cost: float) -> float:
    """
    Classical Harris/Wilson EOQ.

    Q* = sqrt(2DS / H). Returns 0 if any input is non-positive (infeasible inputs).
    """
    if annual_demand <= 0 or ordering_cost <= 0 or unit_holding_cost <= 0:
        return 0.0
    return float(np.sqrt(2.0 * annual_demand * ordering_cost / unit_holding_cost))


def safety_stock(z: float, demand_std_weekly: float, lead_time_weeks: float) -> float:
    """z-score safety stock under independent weekly demand over lead time L."""
    if lead_time_weeks < 0:
        raise ValueError("lead_time_weeks must be ≥ 0")
    return float(z * demand_std_weekly * np.sqrt(lead_time_weeks))


def reorder_point(
    avg_weekly_demand: float,
    lead_time_weeks: float,
    safety_stock_units: float,
) -> float:
    """ROP = μ * L + SS."""
    return float(avg_weekly_demand * lead_time_weeks + safety_stock_units)


def annual_inventory_cost(annual_demand: float, eoq: float, ordering_cost: float, unit_holding_cost: float) -> tuple[float, float, float]:
    """Return (ordering_cost_annual, holding_cost_annual, total)."""
    if eoq <= 0:
        return 0.0, 0.0, 0.0
    n_orders = annual_demand / eoq
    order_cost = n_orders * ordering_cost
    hold_cost = (eoq / 2.0) * unit_holding_cost
    return float(order_cost), float(hold_cost), float(order_cost + hold_cost)


def compute_policy(
    sku_id: str,
    warehouse_id: str,
    weekly_demand: np.ndarray | pd.Series,
    ordering_cost: float,
    unit_cost: float,
    holding_cost_rate: float = 0.25,
    service_level: float = 0.95,
    transit_lead_weeks: float = 1.0,
    production_lead_weeks: float = 1.0,
) -> InventoryPolicy:
    """
    Compute EOQ / SS / ROP for one SKU at one warehouse.

    Multi-echelon lead time = transit (plant→warehouse) + production replenishment.
    Holding cost H = unit_cost * holding_cost_rate (annual).
    """
    y = np.asarray(weekly_demand, dtype=float)
    if y.size == 0:
        raise ValueError("weekly_demand must be non-empty")

    avg_weekly = float(np.mean(y))
    std_weekly = float(np.std(y, ddof=1)) if y.size > 1 else 0.0
    annual_demand = avg_weekly * 52.0
    unit_holding = unit_cost * holding_cost_rate
    lead = float(transit_lead_weeks + production_lead_weeks)
    z = z_for_service_level(service_level)

    eoq = economic_order_quantity(annual_demand, ordering_cost, unit_holding)
    ss = safety_stock(z, std_weekly, lead)
    rop = reorder_point(avg_weekly, lead, ss)
    order_c, hold_c, total_c = annual_inventory_cost(annual_demand, eoq, ordering_cost, unit_holding)

    return InventoryPolicy(
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        eoq=round(eoq, 2),
        safety_stock=round(ss, 2),
        reorder_point=round(rop, 2),
        avg_weekly_demand=round(avg_weekly, 2),
        demand_std_weekly=round(std_weekly, 2),
        lead_time_weeks=lead,
        service_level=service_level,
        z=round(z, 4),
        annual_demand=round(annual_demand, 2),
        ordering_cost=ordering_cost,
        unit_holding_cost=round(unit_holding, 4),
        annual_ordering_cost=round(order_c, 2),
        annual_holding_cost=round(hold_c, 2),
        total_annual_inventory_cost=round(total_c, 2),
    )


def optimize_inventory(
    demand_history: pd.DataFrame,
    skus: pd.DataFrame,
    warehouses: pd.DataFrame,
    service_level: float = 0.95,
    transit_lead_weeks: float = 1.0,
    production_lead_weeks: float = 1.0,
    demand_growth: float = 0.0,
) -> dict[str, Any]:
    """
    Compute policies for every SKU × warehouse.

    demand_growth: fractional uplift applied to historical weekly demand
    (used by the scenario dashboard).
    """
    policies: list[InventoryPolicy] = []
    sku_index = skus.set_index("id")

    for _, wh in warehouses.iterrows():
        for sku_id, hist in demand_history.groupby("sku_id"):
            sku = sku_index.loc[sku_id]
            weekly = hist.sort_values("week_start")["quantity"].to_numpy(dtype=float)
            if demand_growth:
                weekly = weekly * (1.0 + demand_growth)
            policies.append(
                compute_policy(
                    sku_id=str(sku_id),
                    warehouse_id=str(wh["id"]),
                    weekly_demand=weekly,
                    ordering_cost=float(sku["ordering_cost"]),
                    unit_cost=float(sku["unit_cost"]),
                    holding_cost_rate=float(sku["holding_cost_rate"]),
                    service_level=service_level,
                    transit_lead_weeks=transit_lead_weeks,
                    production_lead_weeks=production_lead_weeks,
                )
            )

    total_cost = float(sum(p.total_annual_inventory_cost for p in policies))
    return {
        "policies": [p.to_dict() for p in policies],
        "summary": {
            "n_policies": len(policies),
            "service_level": service_level,
            "lead_time_weeks": transit_lead_weeks + production_lead_weeks,
            "demand_growth": demand_growth,
            "total_annual_inventory_cost": round(total_cost, 2),
            "method": "EOQ + z-score safety stock (multi-echelon lead time)",
        },
    }
