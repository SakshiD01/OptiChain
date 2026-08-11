"""Network design API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline

router = APIRouter()


@router.get("/status")
def status():
    return {"module": "network", "status": "ready"}


@router.post("/run")
def run_network(
    seed: int = Query(42),
    forced_open_count: Optional[int] = Query(None, ge=1, le=4),
    demand_growth: float = Query(0.0, ge=-0.5, le=2.0),
):
    try:
        return pipeline.run_network(
            seed=seed,
            forced_open_count=forced_open_count,
            demand_growth=demand_growth,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "network_failed", "detail": str(exc)}
        ) from exc


@router.get("/results")
def results():
    cached = pipeline.get_cached("network")
    if cached:
        return cached
    return pipeline.run_network()
