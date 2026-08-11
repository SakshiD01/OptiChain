"use client";

import { useModuleData } from "@/lib/useModuleData";
import { AnimatedMetrics } from "@/components/AnimatedMetrics";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { PageSkeleton } from "@/components/Skeleton";
import { RunButton } from "@/components/RunButton";

type ScheduleResponse = {
  feasible: boolean;
  status: string;
  makespan: number;
  total_tardiness: number;
  tasks: Array<{
    job_id: string;
    sku_id: string;
    machine: string;
    start_min: number;
    end_min: number;
    due_min: number;
  }>;
  machine_utilization: Record<string, number>;
  missed_due_dates: Array<{ job_id: string; tardiness_min: number }>;
  solve_time_s: number;
};

const MACHINE_COLORS: Record<string, string> = {
  M1: "#0f766e",
  M2: "#0369a1",
  M3: "#b45309",
};

export default function SchedulingPage() {
  const { data, loading, refreshing, error, run } =
    useModuleData<ScheduleResponse>({
      resultsPath: "/api/scheduling/results",
      runPath: "/api/scheduling/run",
    });

  if (loading && !data) return <PageSkeleton />;

  const maxEnd = data ? Math.max(...data.tasks.map((t) => t.end_min), 1) : 1;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader
        title="Production Scheduling"
        subtitle="Job-shop CP-SAT schedule across 3 machines with sequence-dependent category setups."
        action={<RunButton onClick={run} loading={refreshing} label="Refresh schedule" />}
      />
      {error && (
        <p className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
          {error}
        </p>
      )}
      {!data ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-[14px] text-slate-500 shadow-panel">
          {error
            ? "Couldn’t load schedule — check the API is running, then use Refresh."
            : "Loading production schedule…"}
        </div>
      ) : (
        <>
          <AnimatedMetrics>
            <div data-metric>
              <MetricCard
                label="Makespan"
                value={`${(data.makespan / 60).toFixed(1)} h`}
                hint={`${data.makespan} minutes`}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Missed due dates"
                value={String(data.missed_due_dates.length)}
                tone={data.missed_due_dates.length ? "warning" : "success"}
              />
            </div>
            <div data-metric>
              <MetricCard label="Status" value={data.status} />
            </div>
            <div data-metric>
              <MetricCard label="Solve time" value={`${data.solve_time_s.toFixed(2)}s`} />
            </div>
          </AnimatedMetrics>

          <div className="mt-8 rounded-2xl border border-slate-200 bg-white shadow-panel p-5">
            <h2 className="mb-4 text-sm font-semibold">Gantt — machine timeline</h2>
            <div className="space-y-4">
              {(["M1", "M2", "M3"] as const).map((m) => {
                const tasks = data.tasks.filter((t) => t.machine === m);
                return (
                  <div key={m}>
                    <div className="mb-1 flex justify-between text-[12px]">
                      <span className="font-medium">{m}</span>
                      <span className="text-neutral-500">
                        util {((data.machine_utilization[m] ?? 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="relative h-9 overflow-hidden rounded-md bg-neutral-100">
                      {tasks.map((t) => (
                        <div
                          key={t.job_id}
                          title={`${t.sku_id}: ${t.start_min}–${t.end_min}`}
                          className="absolute top-1 h-7 rounded-sm text-[10px] leading-7 text-white"
                          style={{
                            left: `${(t.start_min / maxEnd) * 100}%`,
                            width: `${Math.max(
                              0.8,
                              ((t.end_min - t.start_min) / maxEnd) * 100
                            )}%`,
                            background: MACHINE_COLORS[m],
                          }}
                        >
                          <span className="px-1 truncate block">{t.sku_id.replace("SKU-", "")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
