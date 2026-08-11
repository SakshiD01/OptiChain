# OptiChain Architecture

```
┌─────────────┐     REST/JSON      ┌──────────────────────────────────┐
│  Next.js UI │ ◄────────────────► │  FastAPI                         │
│  (Vercel)   │                    │  /api/{forecasting,inventory,…}  │
└─────────────┘                    └──────────────┬───────────────────┘
                                                  │
                                       ┌──────────▼──────────┐
                                       │  core/ algorithms   │
                                       │  (framework-free)   │
                                       └──────────┬──────────┘
                                                  │
                                       ┌──────────▼──────────┐
                                       │  Postgres (Neon) /  │
                                       │  SQLite (local)     │
                                       └─────────────────────┘

Data flow:
  generator → demand_history → forecasting → forecasts
           → inventory / network / routing / scheduling
           → simulation (Monte Carlo)
           → scenario API (partial re-solve on overrides)
```

Modules stay independent in `backend/app/core/*` so pytest can validate toy cases
without spinning up HTTP.
