"use client";

import { useApiHealth } from "@/lib/useApiHealth";
import { formatHealthStatus, type HealthStatus } from "@/lib/health";
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
  const { status } = useApiHealth();

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span
          className={cn("h-2 w-2 rounded-full", statusDotClass(status))}
          aria-hidden
        />
        <p className="text-[12px] font-medium text-slate-700">
          {formatHealthStatus(status)}
        </p>
      </div>
    </div>
  );
}
