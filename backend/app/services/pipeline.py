"""Scenario pipeline with in-memory + disk cache and fast interactive paths.

Interactive API defaults favor speed:
  - forecasting: parallel SKUs, fast=True (one holdout), optional quick mode (LightGBM-only)
  - scenario resolve: fewer SKUs/replications, shorter scheduling time limit
  - warmup(): precompute baseline modules so GET /results is instant
"""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.core.forecasting.engine import forecast_sku, fit_lightgbm_forecast
from app.core.inventory.optimizer import optimize_inventory
from app.core.network_design.solver import demand_by_destination, solve_network_for_scenario
from app.core.scheduling.scheduler import jobs_from_inventory_policies, solve_schedule
from app.core.simulation.monte_carlo import DisruptionConfig, run_monte_carlo
from app.core.vehicle_routing.solver import solve_routing_for_network
from app.data.generator import ScenarioConfig, generate_scenario

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {}
_CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"
_CACHE_LOCK = threading.Lock()
_WARMUP_STARTED = False


def _disk_path(key: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{key}.json"


def _save_disk(key: str, payload: dict[str, Any]) -> None:
    try:
        _disk_path(key).write_text(json.dumps(payload, default=str))
    except Exception as exc:
        logger.debug("disk cache write failed: %s", exc)


def _load_disk(key: str) -> dict[str, Any] | None:
    path = _disk_path(key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def get_cached(key: str) -> dict[str, Any] | None:
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    disk = _load_disk(key)
    if disk is not None:
        with _CACHE_LOCK:
            _CACHE[key] = disk
        return disk
    return None


def set_cached(key: str, payload: dict[str, Any], persist: bool = True) -> dict[str, Any]:
    with _CACHE_LOCK:
        _CACHE[key] = payload
    if persist:
        _save_disk(key, payload)
    return payload


def invalidate_cached(key: str) -> None:
    with _CACHE_LOCK:
        _CACHE.pop(key, None)
    path = _disk_path(key)
    try:
        if path.exists():
            path.unlink()
    except Exception as exc:
        logger.debug("disk cache invalidate failed: %s", exc)


def get_scenario(seed: int = 42, force: bool = False) -> dict[str, Any]:
    key = f"scenario_{seed}"
    if force or key not in _CACHE:
        _CACHE[key] = generate_scenario(ScenarioConfig(seed=seed))
        for k in list(_CACHE):
            if k != key and not k.startswith("scenario_"):
                # keep disk-backed module caches; only clear sibling in-memory scenario
                pass
    return _CACHE[key]


def _forecast_one(
    sku_id: str,
    hist,
    seed: int,
    mode: str,
    timeout_s: float,
) -> dict[str, Any]:
    if mode == "quick":
        # LightGBM-only — typically <1s/SKU
        y = hist.sort_values("week_start")["quantity"]
        mean, lo, hi = fit_lightgbm_forecast(y, horizon=12, seed=seed, timeout_s=timeout_s)
        last = hist.sort_values("week_start")["week_start"].iloc[-1]
        import pandas as pd

        last_ts = pd.Timestamp(last)
        rows = []
        for i in range(12):
            rows.append(
                {
                    "week_start": (last_ts + pd.Timedelta(weeks=i + 1)).date(),
                    "forecast": round(float(mean[i]), 2),
                    "lower_ci": round(float(lo[i]), 2),
                    "upper_ci": round(float(hi[i]), 2),
                }
            )
        # Tiny holdout metric
        hold = min(8, len(y) // 4)
        y_train, y_hold = y.iloc[:-hold], y.iloc[-hold:].to_numpy()
        m_h, _, _ = fit_lightgbm_forecast(y_train, horizon=hold, seed=seed, timeout_s=timeout_s)
        from app.core.forecasting.engine import _mape, _rmse

        return {
            "sku_id": sku_id,
            "forecast": rows,
            "metrics": {
                "mape": _mape(y_hold, m_h[: len(y_hold)]),
                "rmse": _rmse(y_hold, m_h[: len(y_hold)]),
                "holdout_weeks": float(hold),
                "fast": 1.0,
            },
            "weights": {"sarima": 0.0, "prophet": 0.0, "lightgbm": 1.0},
            "method": "lightgbm_quick",
            "meta": {"mode": "quick", "models": ["lightgbm"]},
        }

    weights = {"sarima": 0.4, "prophet": 0.25, "lightgbm": 0.35}
    fr = forecast_sku(
        sku_id,
        hist,
        seed=seed,
        weights=weights,
        timeout_s=timeout_s,
        fast=True,
    )
    return {
        "sku_id": fr.sku_id,
        "forecast": fr.forecast.to_dict(orient="records"),
        "metrics": fr.metrics,
        "weights": fr.weights,
        "method": fr.method,
        "meta": fr.meta,
    }


def run_forecasting(
    seed: int = 42,
    sku_limit: int | None = 5,
    demand_growth: float = 0.0,
    mode: str = "quick",
    timeout_s: float = 12.0,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    mode=quick → LightGBM only (interactive default)
    mode=standard → full ensemble with fast=True metrics
    """
    cache_key = f"forecasting_{seed}_{sku_limit}_{demand_growth}_{mode}"
    if use_cache and demand_growth == 0.0:
        hit = get_cached(cache_key)
        if hit:
            return hit

    t0 = time.perf_counter()
    scenario = get_scenario(seed)
    hist = scenario["demand_history"].copy()
    if demand_growth:
        hist["quantity"] = hist["quantity"] * (1.0 + demand_growth)

    sku_ids = sorted(hist["sku_id"].unique().tolist())
    if sku_limit:
        sku_ids = sku_ids[:sku_limit]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(sku_ids)))) as pool:
        futs = {
            pool.submit(
                _forecast_one,
                sku_id,
                hist.loc[hist["sku_id"] == sku_id, ["week_start", "quantity"]],
                seed,
                mode,
                timeout_s,
            ): sku_id
            for sku_id in sku_ids
        }
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda r: r["sku_id"])

    history = []
    for sku_id in sku_ids:
        h = hist.loc[hist["sku_id"] == sku_id].sort_values("week_start").tail(52)
        for _, row in h.iterrows():
            history.append(
                {
                    "sku_id": sku_id,
                    "week_start": row["week_start"].isoformat()
                    if hasattr(row["week_start"], "isoformat")
                    else str(row["week_start"]),
                    "quantity": float(row["quantity"]),
                }
            )

    for r in results:
        for row in r["forecast"]:
            ws = row["week_start"]
            row["week_start"] = ws.isoformat() if hasattr(ws, "isoformat") else str(ws)

    elapsed = time.perf_counter() - t0
    payload = {
        "results": results,
        "history": history,
        "summary": {
            "n_skus": len(results),
            "horizon_weeks": 12,
            "demand_growth": demand_growth,
            "mean_mape": round(
                float(sum(r["metrics"]["mape"] for r in results) / max(len(results), 1)), 4
            ),
            "solve_time_s": round(elapsed, 4),
            "method": (
                "LightGBM quick path"
                if mode == "quick"
                else "ensemble SARIMA + Prophet + LightGBM (fast metrics)"
            ),
            "mode": mode,
            "cached": False,
        },
    }
    set_cached("forecasting", payload)
    if demand_growth == 0.0:
        set_cached(cache_key, payload)
    return payload


def run_inventory(
    seed: int = 42,
    service_level: float = 0.95,
    demand_growth: float = 0.0,
    use_cache: bool = True,
) -> dict[str, Any]:
    cache_key = f"inventory_{seed}_{service_level}_{demand_growth}"
    if use_cache and demand_growth == 0.0 and service_level == 0.95:
        hit = get_cached(cache_key)
        if hit:
            return hit

    t0 = time.perf_counter()
    scenario = get_scenario(seed)
    result = optimize_inventory(
        scenario["demand_history"],
        scenario["skus"],
        scenario["warehouses"],
        service_level=service_level,
        demand_growth=demand_growth,
    )
    result["summary"]["solve_time_s"] = round(time.perf_counter() - t0, 4)
    set_cached("inventory", result)
    if demand_growth == 0.0 and service_level == 0.95:
        set_cached(cache_key, result)
    return result


def run_network(
    seed: int = 42,
    forced_open_count: int | None = None,
    demand_growth: float = 0.0,
    use_cache: bool = True,
) -> dict[str, Any]:
    cache_key = f"network_{seed}_{forced_open_count}_{demand_growth}"
    if use_cache and demand_growth == 0.0 and forced_open_count is None:
        hit = get_cached(cache_key)
        if hit:
            return hit

    scenario = get_scenario(seed)
    hist = scenario["demand_history"]
    weekly = float(hist.groupby("week_start")["quantity"].sum().mean())
    weekly *= 1.0 + demand_growth
    result = solve_network_for_scenario(
        scenario,
        forecast_weekly_total=weekly,
        forced_open_count=forced_open_count,
    )
    set_cached("network", result)
    if demand_growth == 0.0 and forced_open_count is None:
        set_cached(cache_key, result)
    return result


def run_routing(seed: int = 42, use_cache: bool = True) -> dict[str, Any]:
    if use_cache:
        hit = get_cached("routing")
        if hit and get_cached("network"):
            return hit

    scenario = get_scenario(seed)
    network = get_cached("network") or run_network(seed)
    if not network["optimized"]["feasible"]:
        return {
            "feasible": False,
            "error": "network_infeasible",
            "detail": "Cannot route without a feasible network solution",
            "warehouse_routes": [],
        }
    weekly = network["weekly_demand_total"]
    dest_demand = demand_by_destination(weekly, scenario["destinations"])
    result = solve_routing_for_network(
        scenario["warehouses"],
        scenario["destinations"],
        network["optimized"]["open_warehouses"],
        network["optimized"]["assignments"],
        dest_demand,
        time_limit_s=12,
    )
    return set_cached("routing", result)


def run_scheduling(
    seed: int = 42,
    service_level: float = 0.95,
    time_limit_s: int = 12,
    use_cache: bool = True,
) -> dict[str, Any]:
    if use_cache and service_level == 0.95:
        hit = get_cached("scheduling")
        if hit:
            return hit

    scenario = get_scenario(seed)
    inv = get_cached("inventory") or run_inventory(seed, service_level=service_level)
    jobs = jobs_from_inventory_policies(inv["policies"], scenario["skus"], due_weeks=2.0)
    for j in jobs:
        scale = 0.08
        j["qty"] = round(j["qty"] * scale, 1)
        j["proc_m1"] *= scale
        j["proc_m2"] *= scale
        j["proc_m3"] *= scale
    result = solve_schedule(
        jobs,
        list(scenario["production_facility"]["machines"]),
        scenario["setup_times"],
        time_limit_s=time_limit_s,
    )
    return set_cached("scheduling", result)


def run_simulation(
    seed: int = 42,
    n_replications: int = 60,
    disruption_prob_scale: float = 1.0,
    use_cache: bool = True,
) -> dict[str, Any]:
    cache_key = f"simulation_{seed}_{n_replications}_{disruption_prob_scale}"
    if use_cache and disruption_prob_scale == 1.0:
        hit = get_cached(cache_key)
        if hit:
            return hit

    base = DisruptionConfig()
    cfg = DisruptionConfig(
        production_delay_prob=min(1.0, base.production_delay_prob * disruption_prob_scale),
        demand_spike_prob=min(1.0, base.demand_spike_prob * disruption_prob_scale),
        warehouse_down_prob=min(1.0, base.warehouse_down_prob * disruption_prob_scale),
        vehicle_breakdown_prob=min(1.0, base.vehicle_breakdown_prob * disruption_prob_scale),
    )
    inv = get_cached("inventory")
    base_cost = float(inv["summary"]["total_annual_inventory_cost"] / 52) if inv else 10_000.0
    result = run_monte_carlo(
        n_replications=n_replications,
        seed=seed,
        n_orders=40,
        base_weekly_cost=base_cost,
        disruption=cfg,
    )
    set_cached("simulation", result)
    if disruption_prob_scale == 1.0:
        set_cached(cache_key, result)
    return result


def run_scenario_overrides(
    demand_growth: float = 0.0,
    disruption_prob_scale: float = 1.0,
    forced_open_count: int | None = None,
    service_level: float = 0.95,
    seed: int = 42,
) -> dict[str, Any]:
    """Live re-solve — uses quick forecast + parallel independent modules."""
    t0 = time.perf_counter()
    # Invalidate baseline caches when overrides change the world
    for k in ("forecasting", "inventory", "network", "routing", "scheduling", "simulation"):
        _CACHE.pop(k, None)

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_fut = pool.submit(
            run_forecasting,
            seed,
            3,
            demand_growth,
            "quick",
            10.0,
            False,
        )
        i_fut = pool.submit(
            run_inventory, seed, service_level, demand_growth, False
        )
        forecasting = f_fut.result()
        inventory = i_fut.result()

    network = run_network(
        seed=seed,
        forced_open_count=forced_open_count,
        demand_growth=demand_growth,
        use_cache=False,
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        r_fut = pool.submit(run_routing, seed, False)
        s_fut = pool.submit(run_scheduling, seed, service_level, 10, False)
        sim_fut = pool.submit(run_simulation, seed, 40, disruption_prob_scale, False)
        routing = r_fut.result()
        scheduling = s_fut.result()
        simulation = sim_fut.result()

    elapsed = time.perf_counter() - t0
    total_cost = (
        inventory["summary"]["total_annual_inventory_cost"]
        + (network["optimized"]["objective"] or 0) * 52
    )

    return {
        "overrides": {
            "demand_growth": demand_growth,
            "disruption_prob_scale": disruption_prob_scale,
            "forced_open_count": forced_open_count,
            "service_level": service_level,
            "seed": seed,
        },
        "executive": {
            "total_cost_proxy": round(total_cost, 2),
            "service_level_sim": simulation["service_level"]["mean"],
            "resilience_score": simulation["resilience_score"],
            "inventory_cost": inventory["summary"]["total_annual_inventory_cost"],
            "network_weekly_cost": network["optimized"]["objective"],
            "network_savings_vs_all_open": network["savings_vs_all_open"],
            "open_warehouses": network["optimized"]["open_warehouses"],
            "routing_distance_km": routing.get("total_distance_km"),
            "vehicles_used": routing.get("total_vehicles_used"),
            "schedule_makespan": scheduling.get("makespan"),
            "missed_due_dates": len(scheduling.get("missed_due_dates") or []),
            "forecast_mean_mape": forecasting["summary"]["mean_mape"],
            "solve_time_s": round(elapsed, 4),
        },
        "forecasting": forecasting["summary"],
        "inventory": inventory["summary"],
        "network": {
            "optimized_objective": network["optimized"]["objective"],
            "baseline_objective": network["baseline_all_open"]["objective"],
            "open_warehouses": network["optimized"]["open_warehouses"],
            "savings": network["savings_vs_all_open"],
        },
        "routing": {
            "total_distance_km": routing.get("total_distance_km"),
            "vehicles_used": routing.get("total_vehicles_used"),
            "feasible": routing.get("feasible"),
        },
        "scheduling": {
            "makespan": scheduling.get("makespan"),
            "missed_due_dates": len(scheduling.get("missed_due_dates") or []),
            "utilization": scheduling.get("machine_utilization"),
            "status": scheduling.get("status"),
        },
        "simulation": {
            "resilience_score": simulation["resilience_score"],
            "service_level": simulation["service_level"],
            "stockout_rate": simulation["stockout_rate"],
            "avg_fulfillment_delay": simulation["avg_fulfillment_delay"],
        },
        "meta": {
            "method": "parallel re-solve (quick forecast)",
            "solve_time_s": round(elapsed, 4),
        },
    }


def _assemble_from_modules(
    forecasting: dict[str, Any],
    inventory: dict[str, Any],
    network: dict[str, Any],
    routing: dict[str, Any],
    scheduling: dict[str, Any],
    simulation: dict[str, Any],
    *,
    solve_time_s: float = 0.0,
    from_cache: bool = True,
) -> dict[str, Any]:
    total_cost = (
        inventory["summary"]["total_annual_inventory_cost"]
        + (network["optimized"]["objective"] or 0) * 52
    )
    return {
        "overrides": {
            "demand_growth": 0.0,
            "disruption_prob_scale": 1.0,
            "forced_open_count": None,
            "service_level": 0.95,
            "seed": 42,
        },
        "executive": {
            "total_cost_proxy": round(total_cost, 2),
            "service_level_sim": simulation["service_level"]["mean"],
            "resilience_score": simulation["resilience_score"],
            "inventory_cost": inventory["summary"]["total_annual_inventory_cost"],
            "network_weekly_cost": network["optimized"]["objective"],
            "network_savings_vs_all_open": network["savings_vs_all_open"],
            "open_warehouses": network["optimized"]["open_warehouses"],
            "routing_distance_km": routing.get("total_distance_km"),
            "vehicles_used": routing.get("total_vehicles_used"),
            "schedule_makespan": scheduling.get("makespan"),
            "missed_due_dates": len(scheduling.get("missed_due_dates") or []),
            "forecast_mean_mape": forecasting["summary"]["mean_mape"],
            "solve_time_s": round(solve_time_s, 4),
        },
        "forecasting": forecasting["summary"],
        "inventory": inventory["summary"],
        "network": {
            "optimized_objective": network["optimized"]["objective"],
            "baseline_objective": network["baseline_all_open"]["objective"],
            "open_warehouses": network["optimized"]["open_warehouses"],
            "savings": network["savings_vs_all_open"],
        },
        "routing": {
            "total_distance_km": routing.get("total_distance_km"),
            "vehicles_used": routing.get("total_vehicles_used"),
            "feasible": routing.get("feasible"),
        },
        "scheduling": {
            "makespan": scheduling.get("makespan"),
            "missed_due_dates": len(scheduling.get("missed_due_dates") or []),
            "utilization": scheduling.get("machine_utilization"),
            "status": scheduling.get("status"),
        },
        "simulation": {
            "resilience_score": simulation["resilience_score"],
            "service_level": simulation["service_level"],
            "stockout_rate": simulation["stockout_rate"],
            "avg_fulfillment_delay": simulation["avg_fulfillment_delay"],
        },
        "meta": {
            "method": "baseline from warm cache" if from_cache else "baseline computed",
            "solve_time_s": round(solve_time_s, 4),
            "from_cache": from_cache,
        },
    }


def get_baseline_scenario(seed: int = 42) -> dict[str, Any]:
    """
    Instant scenario dashboard payload for first paint.

    Uses warm module caches when present; otherwise computes them once
    (same as warmup) and assembles the executive view — no button press.
    """
    t0 = time.perf_counter()
    cached = get_cached("scenario_baseline")
    if cached:
        return cached

    keys = ["forecasting", "inventory", "network", "routing", "scheduling", "simulation"]
    mods = {k: get_cached(k) for k in keys}
    if all(mods.values()):
        payload = _assemble_from_modules(
            mods["forecasting"],
            mods["inventory"],
            mods["network"],
            mods["routing"],
            mods["scheduling"],
            mods["simulation"],
            solve_time_s=0.0,
            from_cache=True,
        )
        return set_cached("scenario_baseline", payload)

    # Cold path — compute whatever is missing
    forecasting = mods["forecasting"] or run_forecasting(seed=seed, sku_limit=5, mode="quick")
    inventory = mods["inventory"] or run_inventory(seed=seed)
    network = mods["network"] or run_network(seed=seed)
    routing = mods["routing"] or run_routing(seed=seed)
    scheduling = mods["scheduling"] or run_scheduling(seed=seed)
    simulation = mods["simulation"] or run_simulation(seed=seed, n_replications=60)
    payload = _assemble_from_modules(
        forecasting,
        inventory,
        network,
        routing,
        scheduling,
        simulation,
        solve_time_s=time.perf_counter() - t0,
        from_cache=False,
    )
    return set_cached("scenario_baseline", payload)


def scenario_overview(seed: int = 42) -> dict[str, Any]:
    scenario = get_scenario(seed)
    return {
        "meta": scenario["meta"],
        "n_skus": len(scenario["skus"]),
        "n_warehouses": len(scenario["warehouses"]),
        "n_destinations": len(scenario["destinations"]),
        "categories": scenario["skus"]["category"].value_counts().to_dict(),
        "warehouses": scenario["warehouses"][
            ["id", "name", "lat", "lon", "fixed_cost", "capacity"]
        ].to_dict(orient="records"),
    }


def warmup(seed: int = 42) -> dict[str, Any]:
    """Precompute baseline modules so first UI visit is cache-hit fast."""
    t0 = time.perf_counter()
    get_scenario(seed)
    run_inventory(seed=seed)
    run_network(seed=seed)
    run_routing(seed=seed)
    run_scheduling(seed=seed)
    run_simulation(seed=seed, n_replications=60)
    run_forecasting(seed=seed, sku_limit=5, mode="quick")
    get_baseline_scenario(seed=seed)
    return {"status": "warm", "solve_time_s": round(time.perf_counter() - t0, 4)}


def start_warmup_background(seed: int = 42) -> None:
    global _WARMUP_STARTED
    if _WARMUP_STARTED:
        return
    _WARMUP_STARTED = True

    def _run():
        try:
            logger.info("OptiChain warmup starting…")
            result = warmup(seed=seed)
            logger.info("OptiChain warmup done in %ss", result["solve_time_s"])
        except Exception:
            logger.exception("OptiChain warmup failed")

    threading.Thread(target=_run, name="optichain-warmup", daemon=True).start()
