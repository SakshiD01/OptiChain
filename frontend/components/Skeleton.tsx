"use client";

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-slate-200/70 ${className}`}
      aria-hidden
    />
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6 px-8 py-10">
      <div className="space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <Skeleton className="h-80 w-full" />
    </div>
  );
}

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white px-8 py-16 text-center shadow-panel">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(500px 180px at 50% 0%, rgba(20,184,166,0.12), transparent 70%)",
        }}
      />
      <p className="relative font-display text-lg font-semibold text-slate-900">
        {title}
      </p>
      <p className="relative mx-auto mt-2 max-w-md text-[14px] leading-relaxed text-slate-500">
        {body}
      </p>
    </div>
  );
}
