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

type InventoryResponse = {
  policies: Array<{
    sku_id: string;
    warehouse_id: string;
    eoq: number;
    safety_stock: number;
    reorder_point: number;
    total_annual_inventory_cost: number;
    service_level: number;
  }>;
  summary: {
    n_policies: number;
    service_level: number;
    total_annual_inventory_cost: number;
    solve_time_s: number;
    method: string;
  };
};

export default function InventoryPage() {
  const { data, loading, refreshing, error, fromCache, run } =
    useModuleData<InventoryResponse>({
      resultsPath: "/api/inventory/results",
      runPath: "/api/inventory/run",
    });

  if (loading && !data) return <PageSkeleton />;

  const bySku = data
    ? Object.values(
        data.policies.reduce<Record<string, { sku: string; eoq: number; ss: number; cost: number }>>(
          (acc, p) => {
            if (!acc[p.sku_id]) {
              acc[p.sku_id] = { sku: p.sku_id, eoq: 0, ss: 0, cost: 0 };
            }
            acc[p.sku_id].eoq += p.eoq;
            acc[p.sku_id].ss += p.safety_stock;
            acc[p.sku_id].cost += p.total_annual_inventory_cost;
            return acc;
          },
          {}
        )
      ).slice(0, 12)
    : [];

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader
        title="Inventory Optimization"
        badge="Module 02"
        subtitle="EOQ, z-score safety stock, and multi-echelon reorder points. Auto-loads from warm cache."
        action={<RunButton onClick={run} loading={refreshing} label="Refresh" />}
      />
      {error && (
        <p className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
          {error}
        </p>
      )}
      {!data ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-[14px] text-slate-500 shadow-panel">
          {error
            ? "Couldn’t load inventory — check the API is running, then use Refresh."
            : "Loading inventory policies…"}
        </div>
      ) : (
        <>
          <AnimatedMetrics>
            <div data-metric>
              <MetricCard
                label="Policies"
                value={String(data.summary.n_policies)}
                hint="SKU × warehouse"
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Annual inventory cost"
                value={`$${data.summary.total_annual_inventory_cost.toLocaleString()}`}
                hint={data.summary.method}
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Service level"
                value={`${(data.summary.service_level * 100).toFixed(0)}%`}
                tone="success"
              />
            </div>
            <div data-metric>
              <MetricCard
                label="Solve time"
                value={`${data.summary.solve_time_s.toFixed(2)}s`}
              />
            </div>
          </AnimatedMetrics>

          <div className="mt-8 rounded-2xl border border-slate-200 bg-white shadow-panel p-5">
            <h2 className="mb-4 text-sm font-semibold">EOQ & safety stock by SKU (summed)</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bySku}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="sku" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar dataKey="eoq" fill="#0f766e" name="EOQ" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="ss" fill="#99f6e4" name="Safety stock" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mt-6 max-h-96 overflow-auto rounded-2xl border border-slate-200 bg-white shadow-panel">
            <table className="w-full text-left text-[13px]">
              <thead className="sticky top-0 border-b border-neutral-200 bg-neutral-50 text-[11px] uppercase tracking-wider text-neutral-400">
                <tr>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">Warehouse</th>
                  <th className="px-4 py-3 font-medium">EOQ</th>
                  <th className="px-4 py-3 font-medium">Safety stock</th>
                  <th className="px-4 py-3 font-medium">ROP</th>
                  <th className="px-4 py-3 font-medium">Annual cost</th>
                </tr>
              </thead>
              <tbody>
                {data.policies.slice(0, 40).map((p) => (
                  <tr
                    key={`${p.sku_id}-${p.warehouse_id}`}
                    className="border-b border-neutral-100"
                  >
                    <td className="px-4 py-2.5 font-medium">{p.sku_id}</td>
                    <td className="px-4 py-2.5">{p.warehouse_id}</td>
                    <td className="px-4 py-2.5 tabular-nums">{p.eoq}</td>
                    <td className="px-4 py-2.5 tabular-nums">{p.safety_stock}</td>
                    <td className="px-4 py-2.5 tabular-nums">{p.reorder_point}</td>
                    <td className="px-4 py-2.5 tabular-nums">
                      ${p.total_annual_inventory_cost.toLocaleString()}
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
