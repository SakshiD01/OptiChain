"use client";

import { useModuleData } from "@/lib/useModuleData";
import { AnimatedMetrics } from "@/components/AnimatedMetrics";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/Skeleton";
import { RunButton } from "@/components/RunButton";

type RoutingResponse = {
  feasible: boolean;
  total_distance_km: number;
  total_vehicles_used: number;
  warehouse_routes: Array<{
    warehouse_id: string;
    vehicles_used: number;
    total_distance_km: number;
    utilization: number;
    routes: Array<{
      vehicle: number;
      sequence: string[];
      load: number;
      distance_km: number;
      utilization: number;
    }>;
  }>;
};

export default function RoutingPage() {
  const { data, loading, refreshing, error, run } = useModuleData<RoutingResponse>({
    resultsPath: "/api/routing/results",
    runPath: "/api/routing/run",
  });

  if (loading && !data) return <PageSkeleton />;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader
        title="Vehicle Routing"
        subtitle="Capacitated VRP with time windows per open warehouse — OR-Tools routing, Haversine distances."
        action={<RunButton onClick={run} loading={refreshing} label="Refresh VRP" />}
      />
      {error && (
        <p className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
          {error}
        </p>
      )}
      {!data ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-[14px] text-slate-500 shadow-panel">
          {error
            ? "Couldn’t load routes — check the API is running, then use Refresh."
            : "Loading vehicle routes…"}
        </div>
      ) : (
        <>
          <AnimatedMetrics>
            <div data-metric>
              <MetricCard
                label="Total distance"
                value={`${data.total_distance_km.toLocaleString()} km`}
              />
            </div>
            <div data-metric>
              <MetricCard label="Vehicles used" value={String(data.total_vehicles_used)} />
            </div>
            <div data-metric>
              <MetricCard
                label="Depots routed"
                value={String(data.warehouse_routes.length)}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Feasible"
                value={data.feasible ? "Yes" : "No"}
                tone={data.feasible ? "success" : "danger"}
              />
            </div>
          </AnimatedMetrics>

          <div className="mt-8 space-y-4">
            {data.warehouse_routes.map((wr) => (
              <div
                key={wr.warehouse_id}
                className="rounded-2xl border border-slate-200 bg-white shadow-panel p-5"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-sm font-semibold">{wr.warehouse_id}</h2>
                  <p className="text-[12px] text-neutral-500">
                    {wr.vehicles_used} vehicles · {wr.total_distance_km} km ·{" "}
                    {(wr.utilization * 100).toFixed(0)}% util
                  </p>
                </div>
                <div className="mt-4 space-y-2">
                  {wr.routes.map((r) => (
                    <div
                      key={r.vehicle}
                      className="rounded-md bg-neutral-50 px-3 py-2 text-[12px] leading-relaxed text-neutral-700"
                    >
                      <span className="font-medium text-neutral-900">V{r.vehicle}</span>
                      <span className="mx-2 text-neutral-300">·</span>
                      {r.sequence.join(" → ")}
                      <span className="mx-2 text-neutral-300">·</span>
                      <span className="tabular-nums">
                        load {r.load} · {r.distance_km} km
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
