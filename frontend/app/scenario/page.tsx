"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MetricCard } from "@/components/MetricCard";
import { PageSkeleton } from "@/components/Skeleton";
import { AnimatedGridPattern } from "@/components/ui/animated-grid-pattern";
import { BlurFade } from "@/components/ui/blur-fade";
import { BorderBeam } from "@/components/ui/border-beam";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { apiGet, apiPost } from "@/lib/api";

type ScenarioResult = {
  executive: {
    total_cost_proxy: number;
    service_level_sim: number;
    resilience_score: number;
    inventory_cost: number;
    network_weekly_cost: number | null;
    network_savings_vs_all_open: number | null;
    open_warehouses: string[];
    routing_distance_km: number | null;
    vehicles_used: number | null;
    schedule_makespan: number | null;
    missed_due_dates: number;
    forecast_mean_mape: number;
    solve_time_s: number;
  };
  network: {
    optimized_objective: number | null;
    baseline_objective: number | null;
    open_warehouses: string[];
    savings: number | null;
  };
  simulation: {
    resilience_score: number;
    service_level: { mean: number; p90: number };
    stockout_rate: { mean: number };
  };
  meta: { solve_time_s: number; from_cache?: boolean; method?: string };
};

export default function ScenarioPage() {
  const [demandGrowth, setDemandGrowth] = useState(0);
  const [disruptionScale, setDisruptionScale] = useState(1);
  const [forcedOpen, setForcedOpen] = useState<number | "auto">("auto");
  const [serviceLevel, setServiceLevel] = useState(0.95);
  const [data, setData] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiGet<ScenarioResult>("/api/scenario/baseline");
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load baseline");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const resolve = useCallback(async () => {
    setResolving(true);
    setError(null);
    try {
      const res = await apiPost<ScenarioResult>("/api/scenario/resolve", {
        demand_growth: demandGrowth,
        disruption_prob_scale: disruptionScale,
        forced_open_count: forcedOpen === "auto" ? null : forcedOpen,
        service_level: serviceLevel,
        seed: 42,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Re-solve failed");
    } finally {
      setResolving(false);
    }
  }, [demandGrowth, disruptionScale, forcedOpen, serviceLevel]);

  const comparison = data
    ? [
        {
          name: "Network weekly",
          optimized: data.network.optimized_objective ?? 0,
          baseline: data.network.baseline_objective ?? 0,
        },
      ]
    : [];

  if (loading && !data) {
    return (
      <div className="mx-auto max-w-6xl px-8 py-10">
        <PageSkeleton />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <AnimatedGridPattern
        numSquares={24}
        maxOpacity={0.14}
        duration={3.5}
        className="inset-x-0 top-0 h-[32rem] [mask-image:radial-gradient(520px_circle_at_center,white,transparent)]"
      />

      <div className="relative z-10 mx-auto max-w-6xl px-8 py-10">
        <BlurFade>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">
            Flagship
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            OptiChain Scenario
          </h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-slate-500">
            Baseline loads automatically. Adjust assumptions below and re-solve
            only when you want a what-if.
          </p>
        </BlurFade>

        <BlurFade delay={0.12}>
          <div className="relative mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-panel">
            <BorderBeam size={70} duration={9} colorFrom="#14b8a6" colorTo="#38bdf8" />
            <div className="relative z-10 grid gap-6 md:grid-cols-2">
              <label className="block">
                <div className="mb-2 flex justify-between text-[12px]">
                  <span className="font-medium text-slate-800">Demand growth</span>
                  <span className="tabular-nums text-slate-500">
                    {(demandGrowth * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={-0.2}
                  max={0.5}
                  step={0.05}
                  value={demandGrowth}
                  onChange={(e) => setDemandGrowth(Number(e.target.value))}
                  className="w-full accent-teal-700"
                />
              </label>
              <label className="block">
                <div className="mb-2 flex justify-between text-[12px]">
                  <span className="font-medium text-slate-800">Disruption intensity</span>
                  <span className="tabular-nums text-slate-500">
                    {disruptionScale.toFixed(1)}×
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={3}
                  step={0.1}
                  value={disruptionScale}
                  onChange={(e) => setDisruptionScale(Number(e.target.value))}
                  className="w-full accent-teal-700"
                />
              </label>
              <label className="block">
                <div className="mb-2 flex justify-between text-[12px]">
                  <span className="font-medium text-slate-800">Service level target</span>
                  <span className="tabular-nums text-slate-500">
                    {(serviceLevel * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0.9}
                  max={0.99}
                  step={0.01}
                  value={serviceLevel}
                  onChange={(e) => setServiceLevel(Number(e.target.value))}
                  className="w-full accent-teal-700"
                />
              </label>
              <label className="block">
                <div className="mb-2 text-[12px] font-medium text-slate-800">
                  Forced open warehouses
                </div>
                <select
                  value={forcedOpen === "auto" ? "auto" : String(forcedOpen)}
                  onChange={(e) =>
                    setForcedOpen(
                      e.target.value === "auto" ? "auto" : Number(e.target.value)
                    )
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-[13px]"
                >
                  <option value="auto">Auto (optimize)</option>
                  <option value="1">Force 1</option>
                  <option value="2">Force 2</option>
                  <option value="3">Force 3</option>
                  <option value="4">Force 4 (all open)</option>
                </select>
              </label>
            </div>

            <div className="relative z-10 mt-6 flex flex-wrap items-center gap-3">
              <ShimmerButton onClick={resolve} disabled={resolving} background="#0f766e">
                {resolving ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Re-solving…
                  </span>
                ) : (
                  "Apply overrides"
                )}
              </ShimmerButton>
              {data && !resolving && (
                <p className="text-[12px] text-slate-500">
                  {data.meta.from_cache
                    ? "Loaded from warm cache"
                    : `Last solve ${data.meta.solve_time_s.toFixed(1)}s`}
                </p>
              )}
            </div>
          </div>
        </BlurFade>

        {error && (
          <p className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
            {error}
          </p>
        )}

        {data && (
          <>
            <BlurFade delay={0.18}>
              <h2 className="mb-4 mt-10 text-sm font-semibold uppercase tracking-[0.12em] text-slate-400">
                Executive summary
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  label="Cost proxy (annualized)"
                  value={`$${Math.round(data.executive.total_cost_proxy).toLocaleString()}`}
                />
                <MetricCard
                  label="Simulated service level"
                  value={`${(data.executive.service_level_sim * 100).toFixed(1)}%`}
                  tone="success"
                />
                <MetricCard
                  label="Resilience score"
                  value={data.executive.resilience_score.toFixed(1)}
                  hint="/ 100"
                />
                <MetricCard
                  label="Open warehouses"
                  value={data.executive.open_warehouses.join(", ") || "—"}
                  hint={`Savings $${(data.executive.network_savings_vs_all_open ?? 0).toLocaleString()}/wk`}
                />
              </div>
            </BlurFade>

            <BlurFade delay={0.24}>
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                {[
                  {
                    label: "Routing",
                    value: `${data.executive.routing_distance_km?.toLocaleString() ?? "—"} km`,
                    hint: `${data.executive.vehicles_used ?? "—"} vehicles`,
                  },
                  {
                    label: "Schedule",
                    value: data.executive.schedule_makespan
                      ? `${(data.executive.schedule_makespan / 60).toFixed(1)} h`
                      : "—",
                    hint: `${data.executive.missed_due_dates} missed due dates`,
                  },
                  {
                    label: "Forecast MAPE",
                    value: `${(data.executive.forecast_mean_mape * 100).toFixed(1)}%`,
                    hint: `Stockout mean ${(data.simulation.stockout_rate.mean * 100).toFixed(1)}%`,
                  },
                ].map((card) => (
                  <MagicCard key={card.label} className="rounded-2xl">
                    <div className="p-5">
                      <p className="text-[11px] uppercase tracking-wider text-slate-400">
                        {card.label}
                      </p>
                      <p className="mt-2 font-display text-xl font-semibold tabular-nums text-slate-900">
                        {card.value}
                      </p>
                      <p className="mt-1 text-[12px] text-slate-500">{card.hint}</p>
                    </div>
                  </MagicCard>
                ))}
              </div>
            </BlurFade>

            <BlurFade delay={0.3}>
              <MagicCard className="mt-6 rounded-2xl">
                <div className="p-5">
                  <h3 className="mb-4 text-sm font-semibold text-slate-900">
                    Network before / after
                  </h3>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={comparison}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                        <Bar
                          dataKey="baseline"
                          fill="#cbd5e1"
                          name="All open"
                          radius={[4, 4, 0, 0]}
                        />
                        <Bar
                          dataKey="optimized"
                          fill="#0f766e"
                          name="Optimized"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </MagicCard>
            </BlurFade>
          </>
        )}
      </div>
    </div>
  );
}
