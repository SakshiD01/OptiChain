"""Simulation API router."""

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline

router = APIRouter()


@router.get("/status")
def status():
    return {"module": "simulation", "status": "ready"}


@router.post("/run")
def run_simulation(
    seed: int = Query(42),
    n_replications: int = Query(60, ge=10, le=500),
    disruption_prob_scale: float = Query(1.0, ge=0.0, le=5.0),
):
    try:
        return pipeline.run_simulation(
            seed=seed,
            n_replications=n_replications,
            disruption_prob_scale=disruption_prob_scale,
            use_cache=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "simulation_failed", "detail": str(exc)}
        ) from exc


@router.get("/results")
def results():
    cached = pipeline.get_cached("simulation")
    if cached:
        return cached
    return pipeline.run_simulation()
