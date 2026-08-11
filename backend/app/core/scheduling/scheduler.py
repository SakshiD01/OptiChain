"""Job-shop production scheduling with sequence-dependent setups (OR-Tools CP-SAT).

Each SKU is a job that must be assigned to exactly one of 3 machines.
Processing time depends on (SKU, machine). Sequence-dependent setup times
depend on consecutive job categories on the same machine.

Objective: minimize makespan, subject to meeting due dates when feasible.
Timeout: 30s — returns best feasible solution found (honest status).
"""

from __future__ import annotations

import time
from typing import Any

from ortools.sat.python import cp_model

SOLVER_TIME_LIMIT_S = 30
HORIZON_MINUTES = 14 * 24 * 60  # 2-week planning horizon


def solve_schedule(
    jobs: list[dict[str, Any]],
    machines: list[str],
    setup_times: dict[tuple[str, str], float],
    time_limit_s: int = SOLVER_TIME_LIMIT_S,
    horizon_minutes: int = HORIZON_MINUTES,
) -> dict[str, Any]:
    """
    Parameters
    ----------
    jobs : list of dicts with keys:
        id, category, due_minutes, qty,
        proc_m1, proc_m2, proc_m3  (minutes for the full batch on each machine)
    machines : e.g. ["M1","M2","M3"]
    setup_times : (category_a, category_b) → setup minutes
    """
    model = cp_model.CpModel()
    n = len(jobs)
    m = len(machines)
    if n == 0:
        return {
            "status": "Optimal",
            "feasible": True,
            "makespan": 0,
            "tasks": [],
            "machine_utilization": {},
            "missed_due_dates": [],
            "solve_time_s": 0.0,
            "meta": {"method": "OR-Tools CP-SAT job-shop", "n_jobs": 0},
        }

    # task[j][k] exists only if we assign job j to machine k
    # We model: assign binary + interval on chosen machine
    assign = {}
    starts = {}
    ends = {}
    intervals = {}
    proc = {}

    for j, job in enumerate(jobs):
        durations = [
            max(1, int(round(job["proc_m1"]))),
            max(1, int(round(job["proc_m2"]))),
            max(1, int(round(job["proc_m3"]))),
        ]
        for k in range(m):
            assign[j, k] = model.NewBoolVar(f"assign_{j}_{k}")
            proc[j, k] = durations[k]
            starts[j, k] = model.NewIntVar(0, horizon_minutes, f"start_{j}_{k}")
            ends[j, k] = model.NewIntVar(0, horizon_minutes, f"end_{j}_{k}")
            intervals[j, k] = model.NewOptionalIntervalVar(
                starts[j, k],
                durations[k],
                ends[j, k],
                assign[j, k],
                f"interval_{j}_{k}",
            )
        model.AddExactlyOne(assign[j, k] for k in range(m))

    # No-overlap per machine + sequence-dependent setups via pairwise precedence
    for k in range(m):
        model.AddNoOverlap([intervals[j, k] for j in range(n)])

        for j1 in range(n):
            for j2 in range(j1 + 1, n):
                setup_12 = int(
                    round(setup_times.get((jobs[j1]["category"], jobs[j2]["category"]), 15))
                )
                setup_21 = int(
                    round(setup_times.get((jobs[j2]["category"], jobs[j1]["category"]), 15))
                )
                # If both on machine k: either j1 before j2 with setup, or vice versa
                both = model.NewBoolVar(f"both_{j1}_{j2}_{k}")
                model.AddBoolAnd([assign[j1, k], assign[j2, k]]).OnlyEnforceIf(both)
                model.AddBoolOr([assign[j1, k].Not(), assign[j2, k].Not(), both])

                b_12 = model.NewBoolVar(f"prec_{j1}_before_{j2}_{k}")
                # j1 before j2
                model.Add(starts[j2, k] >= ends[j1, k] + setup_12).OnlyEnforceIf([both, b_12])
                # j2 before j1
                model.Add(starts[j1, k] >= ends[j2, k] + setup_21).OnlyEnforceIf(
                    [both, b_12.Not()]
                )

    # Makespan
    makespan = model.NewIntVar(0, horizon_minutes, "makespan")
    for j in range(n):
        for k in range(m):
            model.Add(makespan >= ends[j, k]).OnlyEnforceIf(assign[j, k])

    # Soft due dates: minimize tardiness (and makespan as secondary via weighted sum)
    tardiness_vars = []
    for j, job in enumerate(jobs):
        due = int(job["due_minutes"])
        job_end = model.NewIntVar(0, horizon_minutes, f"job_end_{j}")
        for k in range(m):
            model.Add(job_end == ends[j, k]).OnlyEnforceIf(assign[j, k])
        tard = model.NewIntVar(0, horizon_minutes, f"tard_{j}")
        model.Add(tard >= job_end - due)
        tardiness_vars.append(tard)

    total_tard = model.NewIntVar(0, horizon_minutes * max(n, 1), "total_tard")
    model.Add(total_tard == sum(tardiness_vars))
    # Lexicographic-ish: heavy weight on tardiness, then makespan
    model.Minimize(total_tard * (horizon_minutes + 1) + makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    t0 = time.perf_counter()
    status = solver.Solve(model)
    solve_time = time.perf_counter() - t0

    status_name = solver.StatusName(status)
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    if not feasible:
        return {
            "status": status_name,
            "feasible": False,
            "makespan": None,
            "tasks": [],
            "machine_utilization": {},
            "missed_due_dates": [],
            "solve_time_s": round(solve_time, 4),
            "meta": {
                "method": "OR-Tools CP-SAT job-shop",
                "time_limit_s": time_limit_s,
                "fallback": "none — no schedule fabricated",
            },
        }

    tasks = []
    missed = []
    machine_busy = {mid: 0 for mid in machines}
    for j, job in enumerate(jobs):
        for k, mid in enumerate(machines):
            if solver.Value(assign[j, k]):
                st = solver.Value(starts[j, k])
                en = solver.Value(ends[j, k])
                tasks.append(
                    {
                        "job_id": job["id"],
                        "sku_id": job.get("sku_id", job["id"]),
                        "machine": mid,
                        "category": job["category"],
                        "start_min": st,
                        "end_min": en,
                        "duration_min": en - st,
                        "due_min": int(job["due_minutes"]),
                        "qty": job.get("qty", 0),
                    }
                )
                machine_busy[mid] += en - st
                if en > int(job["due_minutes"]):
                    missed.append(
                        {
                            "job_id": job["id"],
                            "due_min": int(job["due_minutes"]),
                            "end_min": en,
                            "tardiness_min": en - int(job["due_minutes"]),
                        }
                    )
                break

    ms = solver.Value(makespan)
    utilization = {
        mid: round(machine_busy[mid] / ms, 4) if ms > 0 else 0.0 for mid in machines
    }

    return {
        "status": status_name,
        "feasible": True,
        "makespan": ms,
        "total_tardiness": solver.Value(total_tard),
        "tasks": sorted(tasks, key=lambda t: (t["machine"], t["start_min"])),
        "machine_utilization": utilization,
        "missed_due_dates": missed,
        "solve_time_s": round(solve_time, 4),
        "meta": {
            "method": "OR-Tools CP-SAT job-shop with sequence-dependent setups",
            "time_limit_s": time_limit_s,
            "n_jobs": n,
            "n_machines": m,
            "horizon_minutes": horizon_minutes,
        },
    }


def jobs_from_inventory_policies(
    policies: list[dict[str, Any]],
    skus: Any,
    due_weeks: float = 2.0,
) -> list[dict[str, Any]]:
    """
    Build production jobs from inventory EOQs (Module 2 output).

    One job per SKU: produce EOQ units (averaged across warehouses) by due date.
    """
    import pandas as pd

    sku_df = skus if isinstance(skus, pd.DataFrame) else pd.DataFrame(skus)
    sku_index = sku_df.set_index("id")
    # Average EOQ across warehouses per SKU
    by_sku: dict[str, list[float]] = {}
    for p in policies:
        by_sku.setdefault(p["sku_id"], []).append(float(p["eoq"]))

    due_minutes = int(due_weeks * 7 * 24 * 60)
    jobs = []
    for sku_id, eoqs in sorted(by_sku.items()):
        qty = float(sum(eoqs) / len(eoqs))
        sku = sku_index.loc[sku_id]
        # Batch processing time = per-unit minutes * quantity
        jobs.append(
            {
                "id": f"JOB-{sku_id}",
                "sku_id": sku_id,
                "category": str(sku["category"]),
                "qty": round(qty, 1),
                "due_minutes": due_minutes,
                "proc_m1": float(sku["processing_time_m1"]) * qty,
                "proc_m2": float(sku["processing_time_m2"]) * qty,
                "proc_m3": float(sku["processing_time_m3"]) * qty,
            }
        )
    return jobs
