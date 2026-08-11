# OptiChain

Prescriptive **supply chain intelligence and optimization** platform.

Not a historical dashboard — it forecasts demand, solves inventory / network / routing / production decisions, stress-tests the plan with Monte Carlo disruptions, and lets you change assumptions on a live scenario dashboard that re-solves for real.

## Architecture

```
Frontend (Next.js 14) ──REST──► FastAPI
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              core/ algorithms   services/     data/generator
              (framework-free)   pipeline      (seeded scenario)
```

See [docs/architecture.md](docs/architecture.md).

## Modules

| Module | Method | Validation |
|--------|--------|------------|
| Demand forecasting | SARIMA + Prophet + LightGBM ensemble | Toy seasonal series + MAPE bounds |
| Inventory | EOQ + z-score safety stock + multi-echelon ROP | Harris EOQ Q*=200 hand check |
| Network design | PuLP CBC MILP facility location | 2-WH toy: opens cheap warehouse only |
| Vehicle routing | OR-Tools CVRPTW | 2-stop TSP capacity cases |
| Production scheduling | OR-Tools CP-SAT job-shop | 2-job makespan=25 with setups |
| Disruption simulation | SimPy Monte Carlo | Zero-disruption service=1; downtime hurts |
| Scenario dashboard | Partial re-solve on overrides | Live API `/api/scenario/resolve` |

## Fixed business scenario

- 25 SKUs · 3 categories · 4 candidate warehouses · 40 destinations · 3 machines
- Synthetic DGP with trend, seasonality, noise, shocks — **seed=42** by default

## Stack (100% free tier)

- Python: FastAPI, statsmodels, Prophet, LightGBM, PuLP, OR-Tools, SimPy
- Frontend: Next.js 14 App Router, Tailwind, Recharts, GSAP
- DB: Neon Postgres when `DATABASE_URL` set; otherwise in-memory pipeline + optional SQLite

## Local run

### Native deps (macOS, once)

```bash
cd backend
bash scripts/bootstrap_native_deps.sh   # vendors libomp for LightGBM
# CmdStan for Prophet (once):
source .venv/bin/activate
python -c "from cmdstanpy import install_cmdstan; install_cmdstan()"
```

### Backend

```bash
cd backend
cp .env.example .env   # optional; edit DATABASE_URL / CORS_ORIGINS for deploy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)
export CMDSTAN=$HOME/.cmdstan/cmdstan-2.39.0   # if installed
export DYLD_LIBRARY_PATH=$(pwd)/.deps/lib:$DYLD_LIBRARY_PATH
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local   # optional; defaults to http://127.0.0.1:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — start with **Scenario** for the flagship view.

### Tests

```bash
cd backend && source .venv/bin/activate
export PYTHONPATH=$(pwd) CMDSTAN=$HOME/.cmdstan/cmdstan-2.39.0
export DYLD_LIBRARY_PATH=$(pwd)/.deps/lib:$DYLD_LIBRARY_PATH
pytest -v
```

## API sketch

- `POST /api/forecasting/run`
- `POST /api/inventory/run`
- `POST /api/network/run`
- `POST /api/routing/run`
- `POST /api/scheduling/run`
- `POST /api/simulation/run`
- `POST /api/scenario/resolve` — body: `{ demand_growth, disruption_prob_scale, forced_open_count, service_level }`

Every response includes method metadata / solve time. Infeasible or timed-out solvers are reported honestly — never fabricated.
