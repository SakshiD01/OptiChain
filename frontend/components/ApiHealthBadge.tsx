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
      return "bg-amber-400 oc-health-pulse";
  }
}

export function ApiHealthBadge() {
  const { status, service, checkedAt, error, now, refresh } = useApiHealth();
  const label = formatHealthStatus(status);

  return (
    <button
      type="button"
      onClick={refresh}
      className="focus-ring w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-left transition hover:border-slate-300 hover:bg-white"
      title={error ? error : "Click to refresh API status"}
      aria-label={`${label}. ${formatCheckedAgo(checkedAt, now)}. Click to refresh.`}
    >
      <div className="flex items-center gap-2" aria-live="polite" aria-atomic="true">
        <span
          className={cn("h-2 w-2 shrink-0 rounded-full", statusDotClass(status))}
          aria-hidden
        />
        <div className="min-w-0">
          <p className="text-[12px] font-medium text-slate-700">
            {label}
            {service ? (
              <span className="font-normal text-slate-400"> · {service}</span>
            ) : null}
          </p>
          <p className="text-[10px] text-slate-400">
            {formatCheckedAgo(checkedAt, now)} · tap to refresh
          </p>
        </div>
      </div>
    </button>
  );
}
