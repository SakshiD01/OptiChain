"use client";

import { useApiHealth } from "@/lib/useApiHealth";
import {
  formatCheckedAgo,
  formatHealthStatus,
  type HealthStatus,
} from "@/lib/health";
import { cn } from "@/lib/utils";

function statusDotClass(status: HealthStatus): string {
  switch (status) {
    case "online":
      return "bg-emerald-500";
    case "offline":
      return "bg-rose-500";
    default:
      return "bg-amber-400";
  }
}

export function ApiHealthBadge() {
  const { status, service, checkedAt, now } = useApiHealth();

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span
          className={cn("h-2 w-2 shrink-0 rounded-full", statusDotClass(status))}
          aria-hidden
        />
        <div className="min-w-0">
          <p className="text-[12px] font-medium text-slate-700">
            {formatHealthStatus(status)}
            {service ? (
              <span className="font-normal text-slate-400"> · {service}</span>
            ) : null}
          </p>
          <p className="text-[10px] text-slate-400">
            {formatCheckedAgo(checkedAt, now)}
          </p>
        </div>
      </div>
    </div>
  );
}
