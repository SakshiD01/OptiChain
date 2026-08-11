"use client";

import { BlurFade } from "@/components/ui/blur-fade";

export function PageHeader({
  title,
  subtitle,
  action,
  badge,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
  badge?: string;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        {badge ? (
          <BlurFade delay={0.02}>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">
              {badge}
            </p>
          </BlurFade>
        ) : null}
        <BlurFade delay={0.06}>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-slate-900">
            {title}
          </h1>
        </BlurFade>
        <BlurFade delay={0.1}>
          <p className="mt-2 text-[14px] leading-relaxed text-slate-500">
            {subtitle}
          </p>
        </BlurFade>
      </div>
      {action ? <BlurFade delay={0.12}>{action}</BlurFade> : null}
    </header>
  );
}
