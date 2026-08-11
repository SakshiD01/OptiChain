"""Inventory API router."""

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline

router = APIRouter()


@router.get("/status")
def status():
    return {"module": "inventory", "status": "ready"}


@router.post("/run")
def run_inventory(
    seed: int = Query(42),
    service_level: float = Query(0.95, ge=0.8, le=0.99),
    demand_growth: float = Query(0.0, ge=-0.5, le=2.0),
):
    try:
        return pipeline.run_inventory(
            seed=seed, service_level=service_level, demand_growth=demand_growth
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "inventory_failed", "detail": str(exc)}
        ) from exc


@router.get("/results")
def results():
    cached = pipeline.get_cached("inventory")
    if cached:
        return cached
    return pipeline.run_inventory()
