"""Routing API router."""

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline

router = APIRouter()


@router.get("/status")
def status():
    return {"module": "routing", "status": "ready"}


@router.post("/run")
def run_routing(seed: int = Query(42)):
    try:
        pipeline.run_network(seed=seed)
        return pipeline.run_routing(seed=seed, use_cache=False)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "routing_failed", "detail": str(exc)}
        ) from exc


@router.get("/results")
def results():
    cached = pipeline.get_cached("routing")
    if cached:
        return cached
    pipeline.run_network()
    return pipeline.run_routing()
