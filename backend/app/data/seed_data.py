"""Persist the synthetic scenario into the database.

Idempotent: clears scenario tables and re-seeds when called with replace=True.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.data.generator import ScenarioConfig, generate_scenario
from app.db import models


def seed_database(
    db: Session,
    config: ScenarioConfig | None = None,
    replace: bool = True,
) -> dict[str, Any]:
    """
    Generate the fixed scenario and write SKUs, warehouses, destinations,
    demand history, and metadata into the DB.
    """
    scenario = generate_scenario(config)

    if replace:
        db.query(models.DemandForecast).delete()
        db.query(models.DemandHistory).delete()
        db.query(models.Destination).delete()
        db.query(models.Warehouse).delete()
        db.query(models.SKU).delete()
        db.query(models.ScenarioMeta).delete()
        db.flush()

    for _, row in scenario["skus"].iterrows():
        db.add(
            models.SKU(
                id=row["id"],
                name=row["name"],
                category=row["category"],
                unit_cost=float(row["unit_cost"]),
                holding_cost_rate=float(row["holding_cost_rate"]),
                ordering_cost=float(row["ordering_cost"]),
                processing_time_m1=float(row["processing_time_m1"]),
                processing_time_m2=float(row["processing_time_m2"]),
                processing_time_m3=float(row["processing_time_m3"]),
            )
        )

    for _, row in scenario["warehouses"].iterrows():
        db.add(
            models.Warehouse(
                id=row["id"],
                name=row["name"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                fixed_cost=float(row["fixed_cost"]),
                capacity=float(row["capacity"]),
                is_open_baseline=bool(row["is_open_baseline"]),
            )
        )

    for _, row in scenario["destinations"].iterrows():
        db.add(
            models.Destination(
                id=row["id"],
                name=row["name"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                weekly_demand_share=float(row["weekly_demand_share"]),
            )
        )

    for _, row in scenario["demand_history"].iterrows():
        db.add(
            models.DemandHistory(
                sku_id=row["sku_id"],
                week_start=row["week_start"],
                quantity=float(row["quantity"]),
            )
        )

    meta_payload = {
        **scenario["meta"],
        "config": scenario["config"],
        "production_facility": scenario["production_facility"],
        # setup_times keys are tuples — serialize as "A|B"
        "setup_times": {
            f"{a}|{b}": v for (a, b), v in scenario["setup_times"].items()
        },
    }
    db.add(models.ScenarioMeta(key="scenario", value=json.dumps(meta_payload, default=str)))
    db.add(models.ScenarioMeta(key="seed", value=str(scenario["meta"]["seed"])))
    db.commit()

    return scenario["meta"]
