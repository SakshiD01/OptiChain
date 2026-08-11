"use client";

import { ShimmerButton } from "@/components/ui/shimmer-button";
import { cn } from "@/lib/utils";

type Props = {
  onClick: () => void;
  loading?: boolean;
  label?: string;
  secondary?: boolean;
};

export function RunButton({
  onClick,
  loading,
  label = "Refresh",
  secondary,
}: Props) {
  if (secondary) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className={cn(
          "focus-ring inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-[13px] font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-wait disabled:opacity-70"
        )}
      >
        {loading ? "Solving…" : label}
      </button>
    );
  }

  return (
    <ShimmerButton onClick={onClick} disabled={loading} className="min-w-[8.5rem]">
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/25 border-t-white" />
          Solving…
        </span>
      ) : (
        label
      )}
    </ShimmerButton>
  );
}
