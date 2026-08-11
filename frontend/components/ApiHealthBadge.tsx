"use client";

import { useApiHealth } from "@/lib/useApiHealth";
import { formatHealthStatus } from "@/lib/health";

export function ApiHealthBadge() {
  const { status } = useApiHealth();

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
      <p className="text-[12px] font-medium text-slate-700">
        {formatHealthStatus(status)}
      </p>
    </div>
  );
}
