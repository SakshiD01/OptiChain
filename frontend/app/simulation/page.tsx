"use client";

import { useModuleData } from "@/lib/useModuleData";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnimatedMetrics } from "@/components/AnimatedMetrics";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/Skeleton";
import { RunButton } from "@/components/RunButton";

type Dist = { mean: number; p50: number; p90: number; p95: number; min: number; max: number };

type SimResponse = {
  n_replications: number;
  resilience_score: number;
  stockout_rate: Dist;
  avg_fulfillment_delay: Dist;
  cost_overrun: Dist;
  service_level: Dist;
  meta: { method: string };
};

export default function SimulationPage() {
  const { data, loading, refreshing, error, run } = useModuleData<SimResponse>({
    resultsPath: "/api/simulation/results",
    runPath: "/api/simulation/run?n_replications=60",
  });

  if (loading && !data) return <PageSkeleton />;

  const distChart = data
    ? [
        { name: "Service", mean: data.service_level.mean, p90: data.service_level.p90 },
        { name: "Stockout", mean: data.stockout_rate.mean, p90: data.stockout_rate.p90 },
        {
          name: "Delay (days)",
          mean: data.avg_fulfillment_delay.mean,
          p90: data.avg_fulfillment_delay.p90,
        },
        { name: "Cost overrun", mean: data.cost_overrun.mean, p90: data.cost_overrun.p90 },
      ]
    : [];

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader
        title="Disruption Simulation"
        subtitle="SimPy discrete-event Monte Carlo — production delay, demand spikes, warehouse downtime, vehicle breakdowns."
        action={<RunButton onClick={run} loading={refreshing} label="Refresh Monte Carlo" />}
      />
      {error && (
        <p className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
          {error}
        </p>
      )}
      {!data ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-[14px] text-slate-500 shadow-panel">
          {error
            ? "Couldn’t load simulation — check the API is running, then use Refresh."
            : "Loading Monte Carlo results…"}
        </div>
      ) : (
        <>
          <AnimatedMetrics>
            <div data-metric>
              <MetricCard
                label="Resilience score"
                value={data.resilience_score.toFixed(1)}
                hint="/ 100"
                tone={data.resilience_score >= 70 ? "success" : "warning"}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Service level (mean)"
                value={`${(data.service_level.mean * 100).toFixed(1)}%`}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Stockout rate (mean)"
                value={`${(data.stockout_rate.mean * 100).toFixed(1)}%`}
                tone={data.stockout_rate.mean > 0.1 ? "warning" : "default"}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Replications"
                value={String(data.n_replications)}
                hint={data.meta.method}
              />
            </div>
          </AnimatedMetrics>

          <div className="mt-8 rounded-2xl border border-slate-200 bg-white shadow-panel p-5">
            <h2 className="mb-4 text-sm font-semibold">Outcome distributions (mean vs p90)</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar dataKey="mean" fill="#0f766e" name="Mean" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="p90" fill="#99f6e4" name="P90" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
