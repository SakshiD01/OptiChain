"use client";

import { MagicCard } from "@/components/ui/magic-card";
import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    default: "text-slate-900",
    success: "text-emerald-700",
    warning: "text-amber-700",
    danger: "text-rose-700",
  }[tone];

  return (
    <MagicCard className="h-full rounded-2xl">
      <div className="px-5 py-4">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-400">
          {label}
        </p>
        <p
          className={cn(
            "mt-2 font-display text-[1.65rem] font-semibold tabular-nums tracking-tight",
            toneClass
          )}
        >
          {value}
        </p>
        {hint ? (
          <p className="mt-1.5 text-[12px] text-slate-500">{hint}</p>
        ) : null}
      </div>
    </MagicCard>
  );
}
