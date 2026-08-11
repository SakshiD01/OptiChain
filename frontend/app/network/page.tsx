"use client";

import { useModuleData } from "@/lib/useModuleData";
import { AnimatedMetrics } from "@/components/AnimatedMetrics";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/Skeleton";
import { RunButton } from "@/components/RunButton";

type NetworkResponse = {
  optimized: {
    feasible: boolean;
    status: string;
    objective: number;
    solve_time_s: number;
    open_warehouses: string[];
    fixed_cost: number;
    transport_cost: number;
    assignments: Array<{
      warehouse_id: string;
      destination_id: string;
      distance_km: number;
      transport_cost: number;
    }>;
  };
  baseline_all_open: { objective: number; open_warehouses: string[] };
  savings_vs_all_open: number;
  weekly_demand_total: number;
};

export default function NetworkPage() {
  const { data, loading, refreshing, error, run } = useModuleData<NetworkResponse>({
    resultsPath: "/api/network/results",
    runPath: "/api/network/run",
  });

  if (loading && !data) return <PageSkeleton />;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader
        title="Network Design"
        subtitle="MILP facility location — choose which warehouses to open and which destinations they serve."
        action={<RunButton onClick={run} loading={refreshing} label="Refresh MILP" />}
      />
      {error && (
        <p className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
          {error}
        </p>
      )}
      {!data ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-[14px] text-slate-500 shadow-panel">
          {error
            ? "Couldn’t load network design — check the API is running, then use Refresh."
            : "Loading network design…"}
        </div>
      ) : (
        <>
          <AnimatedMetrics>
            <div data-metric>
              <MetricCard
                label="Optimized weekly cost"
                value={`$${data.optimized.objective.toLocaleString()}`}
                hint={`Status: ${data.optimized.status}`}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="All-open baseline"
                value={`$${data.baseline_all_open.objective.toLocaleString()}`}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Savings vs all-open"
                value={`$${data.savings_vs_all_open.toLocaleString()}`}
                tone="success"
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Solve time"
                value={`${data.optimized.solve_time_s.toFixed(2)}s`}
                hint="PuLP CBC"
              />
            </div>
          </AnimatedMetrics>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white shadow-panel p-5">
              <h2 className="text-sm font-semibold">Open warehouses</h2>
              <ul className="mt-4 space-y-2">
                {data.optimized.open_warehouses.map((w) => (
                  <li
                    key={w}
                    className="flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-2 text-[13px] font-medium text-emerald-800"
                  >
                    <span className="h-2 w-2 rounded-full bg-emerald-600" />
                    {w}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-[12px] text-neutral-500">
                Fixed ${data.optimized.fixed_cost.toLocaleString()} · Transport $
                {data.optimized.transport_cost.toLocaleString()}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white shadow-panel p-5">
              <h2 className="text-sm font-semibold">Before / after</h2>
              <div className="mt-6 space-y-4">
                <div>
                  <div className="mb-1 flex justify-between text-[12px] text-neutral-500">
                    <span>All open</span>
                    <span>${data.baseline_all_open.objective.toLocaleString()}</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-neutral-100">
                    <div className="h-full w-full rounded-full bg-neutral-300" />
                  </div>
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-[12px] text-neutral-500">
                    <span>Optimized</span>
                    <span>${data.optimized.objective.toLocaleString()}</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-neutral-100">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{
                        width: `${Math.max(
                          8,
                          (data.optimized.objective /
                            data.baseline_all_open.objective) *
                            100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
              <p className="mt-4 text-[12px] text-neutral-500">
                Weekly demand allocated: {data.weekly_demand_total.toLocaleString()} units
              </p>
            </div>
          </div>

          <div className="mt-6 max-h-80 overflow-auto rounded-2xl border border-slate-200 bg-white shadow-panel">
            <table className="w-full text-left text-[13px]">
              <thead className="sticky top-0 border-b bg-neutral-50 text-[11px] uppercase tracking-wider text-neutral-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Warehouse</th>
                  <th className="px-4 py-3 font-medium">Destination</th>
                  <th className="px-4 py-3 font-medium">Distance km</th>
                  <th className="px-4 py-3 font-medium">Transport $</th>
                </tr>
              </thead>
              <tbody>
                {data.optimized.assignments.slice(0, 50).map((a) => (
                  <tr
                    key={`${a.warehouse_id}-${a.destination_id}`}
                    className="border-b border-neutral-100"
                  >
                    <td className="px-4 py-2">{a.warehouse_id}</td>
                    <td className="px-4 py-2">{a.destination_id}</td>
                    <td className="px-4 py-2 tabular-nums">{a.distance_km}</td>
                    <td className="px-4 py-2 tabular-nums">${a.transport_cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
