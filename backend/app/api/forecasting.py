"""Forecasting API router."""

from fastapi import APIRouter, HTTPException, Query

from app.services import pipeline

router = APIRouter()


@router.get("/status")
def status():
    return {"module": "forecasting", "status": "ready"}


@router.post("/run")
def run_forecast(
    seed: int = Query(42),
    sku_limit: int = Query(5, ge=1, le=25),
    demand_growth: float = Query(0.0, ge=-0.5, le=2.0),
    mode: str = Query("quick", pattern="^(quick|standard)$"),
):
    try:
        return pipeline.run_forecasting(
            seed=seed,
            sku_limit=sku_limit,
            demand_growth=demand_growth,
            mode=mode,
            use_cache=demand_growth == 0.0,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": "forecast_failed", "detail": str(exc)}
        ) from exc


@router.get("/results")
def results(
    seed: int = Query(42),
    sku_limit: int = Query(5, ge=1, le=25),
    mode: str = Query("quick"),
):
    cached = pipeline.get_cached("forecasting")
    if cached:
        return cached
    return pipeline.run_forecasting(seed=seed, sku_limit=sku_limit, mode=mode)
