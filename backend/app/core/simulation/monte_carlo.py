"""Discrete-event disruption simulation (SimPy) with Monte Carlo replications.

Simulates production → warehouse → delivery under the optimized plan, injecting:
  - supplier/production delay
  - demand spike
  - warehouse temporary unavailability
  - vehicle breakdown

Each disruption has configurable probability and severity. N replications with
a fixed seed for reproducibility; reports distribution of stockout rate,
fulfillment delay, cost overrun, and service level.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import simpy

DEFAULT_REPLICATIONS = 200
DEFAULT_SEED = 42
HORIZON_DAYS = 28


@dataclass
class DisruptionConfig:
    production_delay_prob: float = 0.08
    production_delay_days: tuple[float, float] = (1.0, 5.0)
    demand_spike_prob: float = 0.06
    demand_spike_factor: tuple[float, float] = (1.3, 2.0)
    warehouse_down_prob: float = 0.04
    warehouse_down_days: tuple[float, float] = (1.0, 4.0)
    vehicle_breakdown_prob: float = 0.07
    vehicle_breakdown_days: tuple[float, float] = (0.5, 2.0)
    base_fulfillment_days: float = 2.0
    cost_per_delay_day: float = 50.0
    stockout_penalty: float = 200.0


@dataclass
class ReplicationResult:
    stockout_rate: float
    avg_fulfillment_delay: float
    cost_overrun: float
    service_level: float
    n_orders: int
    n_stockouts: int


def _run_one(
    env: simpy.Environment,
    rng: np.random.Generator,
    n_orders: int,
    cfg: DisruptionConfig,
    base_cost: float,
) -> ReplicationResult:
    """Single replication of order fulfillment under random disruptions."""
    stockouts = 0
    delays: list[float] = []
    extra_cost = 0.0

    # Warehouse availability as a resource that can be interrupted
    warehouse_up = {"available": True}
    vehicles_up = {"available": True}
    production_lag = {"extra_days": 0.0}

    def disruption_process():
        while True:
            # Check daily for disruption events
            yield env.timeout(1.0)
            if rng.random() < cfg.warehouse_down_prob:
                warehouse_up["available"] = False
                down = float(rng.uniform(*cfg.warehouse_down_days))
                yield env.timeout(down)
                warehouse_up["available"] = True
            if rng.random() < cfg.vehicle_breakdown_prob:
                vehicles_up["available"] = False
                down = float(rng.uniform(*cfg.vehicle_breakdown_days))
                yield env.timeout(down)
                vehicles_up["available"] = True
            if rng.random() < cfg.production_delay_prob:
                production_lag["extra_days"] = float(rng.uniform(*cfg.production_delay_days))

    def order_process(order_id: int, release_day: float, demand_units: float):
        nonlocal stockouts, extra_cost
        yield env.timeout(release_day)

        demand = demand_units
        if rng.random() < cfg.demand_spike_prob:
            demand *= float(rng.uniform(*cfg.demand_spike_factor))

        wait = 0.0
        # Wait until warehouse and vehicles are available
        while not warehouse_up["available"] or not vehicles_up["available"]:
            yield env.timeout(0.25)
            wait += 0.25
            if wait > HORIZON_DAYS:
                stockouts += 1
                extra_cost += cfg.stockout_penalty
                delays.append(HORIZON_DAYS)
                return

        fulfillment = cfg.base_fulfillment_days + production_lag["extra_days"] + wait
        # Decay production lag after use
        production_lag["extra_days"] *= 0.5

        delay = max(0.0, fulfillment - cfg.base_fulfillment_days)
        delays.append(delay)
        extra_cost += delay * cfg.cost_per_delay_day
        # Service failure: long wait/delay, extreme spike, or horizon breach
        if wait > 2.0 or fulfillment > 6.0 or demand > demand_units * 1.8:
            stockouts += 1
            extra_cost += cfg.stockout_penalty
        yield env.timeout(min(fulfillment, HORIZON_DAYS))

    env.process(disruption_process())
    # Spread orders across the horizon
    for i in range(n_orders):
        release = float(i * (HORIZON_DAYS / max(n_orders, 1)))
        env.process(order_process(i, release, demand_units=100.0))

    env.run(until=HORIZON_DAYS + 10)

    n_stockouts = stockouts
    stockout_rate = n_stockouts / max(n_orders, 1)
    avg_delay = float(np.mean(delays)) if delays else 0.0
    service_level = 1.0 - stockout_rate
    cost_overrun = extra_cost / max(base_cost, 1.0)

    return ReplicationResult(
        stockout_rate=stockout_rate,
        avg_fulfillment_delay=avg_delay,
        cost_overrun=cost_overrun,
        service_level=service_level,
        n_orders=n_orders,
        n_stockouts=n_stockouts,
    )


def run_monte_carlo(
    n_replications: int = DEFAULT_REPLICATIONS,
    seed: int = DEFAULT_SEED,
    n_orders: int = 40,
    base_weekly_cost: float = 10_000.0,
    disruption: DisruptionConfig | None = None,
) -> dict[str, Any]:
    """
    Run N independent SimPy replications and aggregate outcome distributions.
    """
    cfg = disruption or DisruptionConfig()
    rng = np.random.default_rng(seed)
    results: list[ReplicationResult] = []

    for r in range(n_replications):
        # Child seed per replication for reproducibility
        child_seed = int(rng.integers(0, 2**31 - 1))
        child_rng = np.random.default_rng(child_seed)
        env = simpy.Environment()
        results.append(_run_one(env, child_rng, n_orders, cfg, base_weekly_cost))

    def dist(values: np.ndarray) -> dict[str, float]:
        return {
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
            "p50": round(float(np.percentile(values, 50)), 4),
            "p90": round(float(np.percentile(values, 90)), 4),
            "p95": round(float(np.percentile(values, 95)), 4),
            "min": round(float(np.min(values)), 4),
            "max": round(float(np.max(values)), 4),
        }

    stockout = np.array([r.stockout_rate for r in results])
    delay = np.array([r.avg_fulfillment_delay for r in results])
    overrun = np.array([r.cost_overrun for r in results])
    service = np.array([r.service_level for r in results])

    # Resilience score: high service, low delay, low overrun (0–100)
    resilience = float(
        np.clip(
            100
            * (
                0.5 * np.mean(service)
                + 0.3 * (1 / (1 + np.mean(delay)))
                + 0.2 * (1 / (1 + np.mean(overrun)))
            ),
            0,
            100,
        )
    )

    return {
        "n_replications": n_replications,
        "seed": seed,
        "horizon_days": HORIZON_DAYS,
        "disruption_config": asdict(cfg),
        "stockout_rate": dist(stockout),
        "avg_fulfillment_delay": dist(delay),
        "cost_overrun": dist(overrun),
        "service_level": dist(service),
        "resilience_score": round(resilience, 2),
        "meta": {
            "method": "SimPy discrete-event + Monte Carlo",
            "n_orders_per_replication": n_orders,
        },
    }
