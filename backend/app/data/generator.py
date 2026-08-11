"""Synthetic data generating process for the OptiChain FMCG/D2C scenario.

Produces a fully reproducible fixed scenario:
  - 25 SKUs across 3 categories
  - 4 candidate regional warehouses
  - 40 retail/delivery destinations
  - 1 production facility with 3 machines (processing times per SKU)
  - Weekly demand history with trend, seasonality, noise, and occasional shocks

All randomness is seeded (default SEED=42) so ground truth is known and every
downstream module can be validated against the same world.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_SEED = 42
N_SKUS = 25
N_WAREHOUSES = 4
N_DESTINATIONS = 40
N_WEEKS_HISTORY = 104  # 2 years of weekly demand
CATEGORIES = ("Beverages", "Snacks", "Personal Care")

# Approximate US regional warehouse candidate sites (lat, lon)
WAREHOUSE_SITES = (
    ("WH-NE", "Northeast DC", 40.7128, -74.0060, 420_000.0, 50_000.0),
    ("WH-SE", "Southeast DC", 33.7490, -84.3880, 380_000.0, 45_000.0),
    ("WH-MW", "Midwest DC", 41.8781, -87.6298, 350_000.0, 55_000.0),
    ("WH-W", "West Coast DC", 34.0522, -118.2437, 480_000.0, 48_000.0),
)

# Production facility (fixed) — used by scheduling / simulation modules
PRODUCTION_FACILITY = {
    "id": "PLANT-1",
    "name": "Central Production Plant",
    "lat": 39.0997,
    "lon": -94.5786,  # Kansas City area
    "machines": ("M1", "M2", "M3"),
}


@dataclass(frozen=True)
class ScenarioConfig:
    """Tunable knobs for the data-generating process."""

    seed: int = DEFAULT_SEED
    n_skus: int = N_SKUS
    n_destinations: int = N_DESTINATIONS
    n_weeks: int = N_WEEKS_HISTORY
    history_end: date = date(2025, 12, 29)  # last Monday of history window
    base_weekly_demand: float = 120.0
    annual_trend: float = 0.08  # ~8% YoY growth embedded in weekly series
    seasonality_amplitude: float = 0.18
    shock_probability: float = 0.03  # chance of a demand shock any given week
    shock_magnitude: tuple[float, float] = (1.4, 2.2)  # multiplicative spike range
    noise_cv: float = 0.12  # coefficient of variation for weekly noise


def _sku_catalog(rng: np.random.Generator, n_skus: int) -> pd.DataFrame:
    """Build the 25-SKU master with costs and machine processing times (minutes/unit)."""
    rows = []
    for i in range(1, n_skus + 1):
        category = CATEGORIES[(i - 1) % len(CATEGORIES)]
        # Different demand bases / costs by category — realistic FMCG spread
        cat_mult = {"Beverages": 1.2, "Snacks": 1.0, "Personal Care": 0.75}[category]
        unit_cost = float(rng.uniform(1.5, 12.0) * (1.1 if category == "Personal Care" else 1.0))
        rows.append(
            {
                "id": f"SKU-{i:03d}",
                "name": f"{category} Item {i:02d}",
                "category": category,
                "unit_cost": round(unit_cost, 2),
                "holding_cost_rate": 0.25,  # classic 25% annual holding rate
                "ordering_cost": float(rng.choice([35.0, 50.0, 75.0, 100.0])),
                # Minutes per unit on each machine — scheduling module uses these
                "processing_time_m1": round(float(rng.uniform(0.8, 3.5) / cat_mult), 2),
                "processing_time_m2": round(float(rng.uniform(0.8, 3.5) / cat_mult), 2),
                "processing_time_m3": round(float(rng.uniform(0.8, 3.5) / cat_mult), 2),
                "demand_scale": float(cat_mult * rng.uniform(0.6, 1.6)),
                "seasonality_phase": float(rng.uniform(0, 2 * np.pi)),
            }
        )
    return pd.DataFrame(rows)


def _warehouses() -> pd.DataFrame:
    rows = [
        {
            "id": wid,
            "name": name,
            "lat": lat,
            "lon": lon,
            "fixed_cost": fixed,
            "capacity": cap,
            "is_open_baseline": True,
        }
        for wid, name, lat, lon, fixed, cap in WAREHOUSE_SITES
    ]
    return pd.DataFrame(rows)


def _destinations(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Scatter 40 delivery points around the warehouse regions with demand shares."""
    # Cluster centers roughly near the four warehouses
    centers = [(40.7, -74.0), (33.7, -84.4), (41.9, -87.6), (34.1, -118.2)]
    rows = []
    raw_shares = rng.dirichlet(np.ones(n) * 2.0)  # mild concentration, sums to 1
    for i in range(n):
        c_lat, c_lon = centers[i % len(centers)]
        lat = float(c_lat + rng.normal(0, 1.8))
        lon = float(c_lon + rng.normal(0, 2.2))
        rows.append(
            {
                "id": f"DST-{i + 1:03d}",
                "name": f"Retail Node {i + 1:02d}",
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "weekly_demand_share": float(raw_shares[i]),
            }
        )
    return pd.DataFrame(rows)


def _week_starts(history_end: date, n_weeks: int) -> list[date]:
    """Return ascending list of Mondays ending at history_end."""
    # Snap to Monday
    end = history_end - timedelta(days=history_end.weekday())
    return [end - timedelta(weeks=(n_weeks - 1 - i)) for i in range(n_weeks)]


def generate_demand_series(
    sku_row: pd.Series,
    weeks: list[date],
    cfg: ScenarioConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Data-generating process for one SKU.

    q_t = base * scale * (1 + trend)^t * (1 + A*sin(2π t/52 + φ)) * ε_t * shock_t

    where ε_t ~ LogNormal calibrated to noise_cv, and shock_t is occasional spikes.

    Note: demand_scale and seasonality_phase are generator-only helper columns and
    are dropped from the public SKU table returned by generate_scenario — the
    observed series is the ground truth for downstream modules, not the latent
    components (those stay internal to this function).
    """
    t = np.arange(len(weeks), dtype=float)
    weekly_trend = (1 + cfg.annual_trend) ** (t / 52.0)
    seasonality = 1.0 + cfg.seasonality_amplitude * np.sin(
        2 * np.pi * t / 52.0 + sku_row["seasonality_phase"]
    )
    # Log-normal noise with approximate CV = noise_cv
    sigma = np.sqrt(np.log(1 + cfg.noise_cv**2))
    epsilon = rng.lognormal(mean=-(sigma**2) / 2, sigma=sigma, size=len(weeks))

    shocks = np.ones(len(weeks))
    shock_hits = rng.random(len(weeks)) < cfg.shock_probability
    n_shocks = int(shock_hits.sum())
    if n_shocks:
        shocks[shock_hits] = rng.uniform(*cfg.shock_magnitude, size=n_shocks)

    base = cfg.base_weekly_demand * float(sku_row["demand_scale"])
    qty = base * weekly_trend * seasonality * epsilon * shocks
    return np.maximum(qty, 1.0).round(1)  # demand is at least 1 unit


def generate_scenario(config: ScenarioConfig | None = None) -> dict[str, Any]:
    """
    Generate the full fixed scenario as in-memory DataFrames / dicts.

    Returns
    -------
    dict with keys:
      config, skus, warehouses, destinations, demand_history,
      production_facility, setup_times, meta
    """
    cfg = config or ScenarioConfig()
    rng = np.random.default_rng(cfg.seed)

    skus = _sku_catalog(rng, cfg.n_skus)
    warehouses = _warehouses()
    destinations = _destinations(rng, cfg.n_destinations)
    weeks = _week_starts(cfg.history_end, cfg.n_weeks)

    demand_rows = []
    for _, sku in skus.iterrows():
        series = generate_demand_series(sku, weeks, cfg, rng)
        for w, q in zip(weeks, series):
            demand_rows.append({"sku_id": sku["id"], "week_start": w, "quantity": float(q)})
    demand_history = pd.DataFrame(demand_rows)

    # Sequence-dependent setup times (minutes) between categories on any machine
    # Diagonal = small changeover within category; off-diagonal = larger
    setup_times = {}
    for a in CATEGORIES:
        for b in CATEGORIES:
            setup_times[(a, b)] = 5.0 if a == b else float(rng.uniform(20.0, 45.0))

    # Drop generator-only helper columns from the SKU master exposed downstream
    sku_public = skus.drop(columns=["demand_scale", "seasonality_phase"])

    return {
        "config": asdict(cfg),
        "skus": sku_public,
        "warehouses": warehouses,
        "destinations": destinations,
        "demand_history": demand_history,
        "production_facility": PRODUCTION_FACILITY,
        "setup_times": setup_times,
        "meta": {
            "seed": cfg.seed,
            "n_skus": len(sku_public),
            "n_warehouses": len(warehouses),
            "n_destinations": len(destinations),
            "n_weeks": len(weeks),
            "history_start": weeks[0].isoformat(),
            "history_end": weeks[-1].isoformat(),
            "total_demand_units": float(demand_history["quantity"].sum()),
        },
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km — used by network design and VRP (no Maps API)."""
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def distance_matrix(locations: pd.DataFrame) -> np.ndarray:
    """NxN km distance matrix from a frame with lat/lon columns."""
    n = len(locations)
    mat = np.zeros((n, n))
    lats = locations["lat"].to_numpy()
    lons = locations["lon"].to_numpy()
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_km(lats[i], lons[i], lats[j], lons[j])
            mat[i, j] = mat[j, i] = d
    return mat
