"""OptiChain FastAPI application entrypoint."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import forecasting, inventory, network, routing, scheduling, simulation, scenario
from app.core.forecasting.bootstrap import bootstrap_native_deps
from app.services.pipeline import start_warmup_background

bootstrap_native_deps()

app = FastAPI(
    title="OptiChain API",
    description="Supply chain intelligence and optimization platform",
    version="0.1.0",
)

_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _origins.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecasting.router, prefix="/api/forecasting", tags=["forecasting"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(network.router, prefix="/api/network", tags=["network"])
app.include_router(routing.router, prefix="/api/routing", tags=["routing"])
app.include_router(scheduling.router, prefix="/api/scheduling", tags=["scheduling"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(scenario.router, prefix="/api/scenario", tags=["scenario"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "optichain"}


@app.on_event("startup")
def _on_startup():
    start_warmup_background(seed=42)
