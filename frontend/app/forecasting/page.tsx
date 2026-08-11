"use client";

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnimatedMetrics } from "@/components/AnimatedMetrics";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, PageSkeleton } from "@/components/Skeleton";
import { RunButton } from "@/components/RunButton";
import { useModuleData } from "@/lib/useModuleData";

type ForecastResponse = {
  results: Array<{
    sku_id: string;
    forecast: Array<{
      week_start: string;
      forecast: number;
      lower_ci: number;
      upper_ci: number;
    }>;
    metrics: { mape: number; rmse: number };
    weights: Record<string, number>;
    method?: string;
  }>;
  history: Array<{ sku_id: string; week_start: string; quantity: number }>;
  summary: {
    n_skus: number;
    mean_mape: number;
    solve_time_s: number;
    method: string;
    mode?: string;
  };
};

const SKU_COLORS = ["#14b8a6", "#0ea5e9", "#f59e0b", "#8b5cf6", "#f43f5e"];

export default function ForecastingPage() {
  const { data, loading, refreshing, error, fromCache, run } =
    useModuleData<ForecastResponse>({
      resultsPath: "/api/forecasting/results?sku_limit=5&mode=quick",
      runPath: "/api/forecasting/run?sku_limit=5&mode=quick",
    });
  const [sku, setSku] = useState<string>("");

  const active = useMemo(() => {
    if (!data?.results?.length) return undefined;
    return data.results.find((r) => r.sku_id === sku) ?? data.results[0];
  }, [data, sku]);

  const chartData = useMemo(() => {
    if (!data || !active) return [];
    const hist = data.history
      .filter((h) => h.sku_id === active.sku_id)
      .map((h) => ({ week: h.week_start.slice(0, 10), actual: h.quantity }));
    const fc = active.forecast.map((f) => ({
      week: f.week_start.slice(0, 10),
      forecast: f.forecast,
      lower: f.lower_ci,
      upper: f.upper_ci,
    }));
    return [...hist.slice(-26).map((h) => ({ ...h, forecast: undefined })), ...fc];
  }, [data, active]);

  if (loading && !data) return <PageSkeleton />;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader
        badge="Module 01"
        title="Demand Forecasting"
        subtitle="Quick path uses LightGBM for interactive speed. Cached after warmup — refresh for a fresh solve."
        action={
          <div className="flex items-center gap-3">
            {fromCache && data ? (
              <span className="rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
                Cached
              </span>
            ) : null}
            <RunButton onClick={run} loading={refreshing} label="Refresh forecast" />
          </div>
        }
      />

      {error && (
        <p className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] text-rose-700">
          {error}
        </p>
      )}

      {!data ? (
        <EmptyState
          title="Warming up forecasts"
          body="Baseline results load automatically after API warmup. You can also refresh to recompute."
        />
      ) : (
        <>
          <AnimatedMetrics>
            <div data-metric>
              <MetricCard
                label="SKUs forecasted"
                value={String(data.summary.n_skus)}
                hint={data.summary.method}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Mean MAPE"
                value={`${(data.summary.mean_mape * 100).toFixed(1)}%`}
                hint="Holdout"
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Active SKU MAPE"
                value={`${((active?.metrics.mape ?? 0) * 100).toFixed(1)}%`}
                hint={active?.sku_id}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Solve time"
                value={`${data.summary.solve_time_s.toFixed(1)}s`}
                hint={data.summary.mode ?? "quick"}
              />
            </div>
          </AnimatedMetrics>

          <div className="mt-8 flex flex-wrap gap-2">
            {data.results.map((r, i) => (
              <button
                key={r.sku_id}
                type="button"
                onClick={() => setSku(r.sku_id)}
                className={`focus-ring rounded-xl px-3 py-1.5 text-[12px] font-medium transition ${
                  (active?.sku_id ?? "") === r.sku_id
                    ? "bg-slate-900 text-white"
                    : "border border-slate-200 bg-white text-slate-500 hover:text-slate-900"
                }`}
              >
                <span
                  className="mr-1.5 inline-block h-2 w-2 rounded-full"
                  style={{ background: SKU_COLORS[i % SKU_COLORS.length] }}
                />
                {r.sku_id}
              </button>
            ))}
          </div>

          <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
            <h2 className="mb-4 text-sm font-semibold text-slate-900">
              History + 12-week forecast — {active?.sku_id}
            </h2>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="fcFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(15,23,42,0.06)" />
                  <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#5b657a" }} minTickGap={24} />
                  <YAxis tick={{ fontSize: 11, fill: "#5b657a" }} />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 12,
                      border: "1px solid rgba(15,23,42,0.08)",
                      background: "rgba(255,255,255,0.95)",
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="upper"
                    stroke="none"
                    fill="#14b8a6"
                    fillOpacity={0.08}
                    name="Upper CI"
                  />
                  <Area
                    type="monotone"
                    dataKey="lower"
                    stroke="none"
                    fill="#fff"
                    fillOpacity={1}
                    name="Lower CI"
                  />
                  <Area
                    type="monotone"
                    dataKey="actual"
                    stroke="#0b1220"
                    fill="none"
                    strokeWidth={1.6}
                    name="Actual"
                  />
                  <Area
                    type="monotone"
                    dataKey="forecast"
                    stroke="#14b8a6"
                    fill="url(#fcFill)"
                    strokeWidth={2.2}
                    name="Forecast"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
            <table className="w-full text-left text-[13px]">
              <thead className="border-b border-slate-100 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">MAPE</th>
                  <th className="px-4 py-3 font-medium">RMSE</th>
                  <th className="px-4 py-3 font-medium">Avg forecast</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={r.sku_id} className="border-b border-slate-50 last:border-0">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.sku_id}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {(r.metrics.mape * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 tabular-nums">{r.metrics.rmse.toFixed(1)}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {(
                        r.forecast.reduce((s, f) => s + f.forecast, 0) / r.forecast.length
                      ).toFixed(1)}
                    </td>
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
