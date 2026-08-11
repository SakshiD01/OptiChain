"""Scenario dashboard API — live re-solve with override parameters."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import pipeline

router = APIRouter()


class ScenarioOverrides(BaseModel):
    demand_growth: float = Field(0.0, ge=-0.5, le=2.0)
    disruption_prob_scale: float = Field(1.0, ge=0.0, le=5.0)
    forced_open_count: Optional[int] = Field(None, ge=1, le=4)
    service_level: float = Field(0.95, ge=0.8, le=0.99)
    seed: int = 42


@router.get("/status")
def status():
    return {"module": "scenario", "status": "ready"}


@router.get("/overview")
def overview(seed: int = 42):
    return pipeline.scenario_overview(seed=seed)


@router.post("/warmup")
def warmup(seed: int = 42):
    """Precompute baseline modules (also started automatically on API boot)."""
    try:
        return pipeline.warmup(seed=seed)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "warmup_failed", "detail": str(exc)}
        ) from exc


@router.get("/warmup/status")
def warmup_status():
    keys = ["forecasting", "inventory", "network", "routing", "scheduling", "simulation"]
    ready = {k: pipeline.get_cached(k) is not None for k in keys}
    return {"ready": ready, "all_ready": all(ready.values())}


@router.get("/baseline")
def baseline(seed: int = 42):
    """Auto-load scenario executive view from warm cache (no button press)."""
    try:
        return pipeline.get_baseline_scenario(seed=seed)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "baseline_failed", "detail": str(exc)}
        ) from exc


@router.post("/resolve")
def resolve(overrides: ScenarioOverrides):
    """Re-solve affected modules with live overrides."""
    try:
        pipeline.invalidate_cached("scenario_baseline")
        return pipeline.run_scenario_overrides(
            demand_growth=overrides.demand_growth,
            disruption_prob_scale=overrides.disruption_prob_scale,
            forced_open_count=overrides.forced_open_count,
            service_level=overrides.service_level,
            seed=overrides.seed,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "scenario_resolve_failed", "detail": str(exc)},
        ) from exc
