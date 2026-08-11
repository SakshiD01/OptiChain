"""Scheduling API router."""

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline

router = APIRouter()


@router.get("/status")
def status():
    return {"module": "scheduling", "status": "ready"}


@router.post("/run")
def run_scheduling(seed: int = Query(42), service_level: float = Query(0.95)):
    try:
        pipeline.run_inventory(seed=seed, service_level=service_level)
        return pipeline.run_scheduling(
            seed=seed, service_level=service_level, use_cache=False
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "scheduling_failed", "detail": str(exc)}
        ) from exc


@router.get("/results")
def results():
    cached = pipeline.get_cached("scheduling")
    if cached:
        return cached
    pipeline.run_inventory()
    return pipeline.run_scheduling()
