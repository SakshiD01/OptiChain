"""Scheduling tests — tiny hand-checkable instance + scenario sanity."""

from __future__ import annotations

from app.core.inventory.optimizer import optimize_inventory
from app.core.scheduling.scheduler import jobs_from_inventory_policies, solve_schedule
from app.data.generator import CATEGORIES, ScenarioConfig, generate_scenario


def test_toy_two_jobs_one_machine_order():
    """
    Two jobs, one usable machine path.

    Job A: 10 min on M1 only-ish (M2/M3 very long), due 100
    Job B: 10 min on M1, due 100
    Setup A→B = 5. Makespan should be 10+5+10 = 25 when both on M1.
    """
    jobs = [
        {
            "id": "A",
            "sku_id": "A",
            "category": "Beverages",
            "qty": 1,
            "due_minutes": 100,
            "proc_m1": 10,
            "proc_m2": 1000,
            "proc_m3": 1000,
        },
        {
            "id": "B",
            "sku_id": "B",
            "category": "Snacks",
            "qty": 1,
            "due_minutes": 100,
            "proc_m1": 10,
            "proc_m2": 1000,
            "proc_m3": 1000,
        },
    ]
    setups = {
        ("Beverages", "Beverages"): 0,
        ("Snacks", "Snacks"): 0,
        ("Beverages", "Snacks"): 5,
        ("Snacks", "Beverages"): 5,
        ("Beverages", "Personal Care"): 5,
        ("Personal Care", "Beverages"): 5,
        ("Snacks", "Personal Care"): 5,
        ("Personal Care", "Snacks"): 5,
        ("Personal Care", "Personal Care"): 0,
    }
    result = solve_schedule(jobs, ["M1", "M2", "M3"], setups, time_limit_s=10)
    assert result["feasible"]
    assert result["makespan"] == 25
    assert result["missed_due_dates"] == []
    assert all(t["machine"] == "M1" for t in result["tasks"])


def test_full_scenario_schedule_sanity():
    scenario = generate_scenario(ScenarioConfig(seed=42))
    inv = optimize_inventory(
        scenario["demand_history"],
        scenario["skus"],
        scenario["warehouses"].head(1),
        service_level=0.95,
    )
    jobs = jobs_from_inventory_policies(inv["policies"], scenario["skus"], due_weeks=2.0)
    # Scale down processing for test speed / horizon fit: use EOQ/10 as qty proxy
    for j in jobs:
        scale = 0.05
        j["qty"] *= scale
        j["proc_m1"] *= scale
        j["proc_m2"] *= scale
        j["proc_m3"] *= scale

    result = solve_schedule(
        jobs,
        list(scenario["production_facility"]["machines"]),
        scenario["setup_times"],
        time_limit_s=20,
    )
    assert result["feasible"]
    assert result["makespan"] > 0
    assert len(result["tasks"]) == len(jobs)
    assert set(result["machine_utilization"]) == {"M1", "M2", "M3"}
    for u in result["machine_utilization"].values():
        assert 0 <= u <= 1.0 + 1e-6
