"use client";

import Link from "next/link";
import {
  Activity,
  Boxes,
  Factory,
  Network,
  Route,
  TrendingUp,
} from "lucide-react";
import { AnimatedGridPattern } from "@/components/ui/animated-grid-pattern";
import { AnimatedShinyText } from "@/components/ui/animated-shiny-text";
import { BentoCard, BentoGrid } from "@/components/ui/bento-grid";
import { BlurFade } from "@/components/ui/blur-fade";
import { BorderBeam } from "@/components/ui/border-beam";
import { MagicCard } from "@/components/ui/magic-card";
import { NumberTicker } from "@/components/ui/number-ticker";
import { ShimmerButton } from "@/components/ui/shimmer-button";

const MODULES = [
  {
    href: "/forecasting",
    name: "Demand Forecasting",
    description: "Quick LightGBM path for interactive speed, full ensemble on demand.",
    Icon: TrendingUp,
    className: "lg:col-span-1",
  },
  {
    href: "/inventory",
    name: "Inventory",
    description: "EOQ, z-score safety stock, multi-echelon reorder points.",
    Icon: Boxes,
    className: "lg:col-span-1",
  },
  {
    href: "/network",
    name: "Network Design",
    description: "MILP warehouse location with before/after cost comparison.",
    Icon: Network,
    className: "lg:col-span-1",
  },
  {
    href: "/routing",
    name: "Vehicle Routing",
    description: "CVRPTW per open DC — sequences, distance, utilization.",
    Icon: Route,
    className: "lg:col-span-1",
  },
  {
    href: "/scheduling",
    name: "Scheduling",
    description: "CP-SAT job-shop with sequence-dependent setups.",
    Icon: Factory,
    className: "lg:col-span-1",
  },
  {
    href: "/simulation",
    name: "Simulation",
    description: "SimPy Monte Carlo disruptions and resilience score.",
    Icon: Activity,
    className: "lg:col-span-1",
  },
];

export default function HomePage() {
  return (
    <div className="relative mx-auto max-w-6xl overflow-hidden px-8 py-10">
      <AnimatedGridPattern
        numSquares={28}
        maxOpacity={0.18}
        duration={3.2}
        className="inset-x-0 top-0 h-[28rem] skew-y-0 [mask-image:radial-gradient(500px_circle_at_center,white,transparent)]"
      />

      <BlurFade delay={0.05}>
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-[12px] shadow-sm backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-teal-500" />
          <AnimatedShinyText className="text-slate-600">
            Prescriptive supply-chain intelligence
          </AnimatedShinyText>
        </div>
      </BlurFade>

      <BlurFade delay={0.12}>
        <header className="relative mb-10 max-w-2xl">
          <h1 className="font-display text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            OptiChain
          </h1>
          <p className="mt-4 text-[16px] leading-relaxed text-slate-500">
            Forecast demand, optimize inventory, network, routes, and production —
            then stress-test the plan with Monte Carlo disruptions. Modules load
            automatically from warm cache.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <ShimmerButton href="/scenario" className="shadow-lg shadow-slate-900/10">
              Open scenario dashboard
            </ShimmerButton>
            <Link
              href="/forecasting"
              className="focus-ring inline-flex rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-[13px] font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Browse modules
            </Link>
          </div>
        </header>
      </BlurFade>

      <BlurFade delay={0.2}>
        <section className="mb-10 grid gap-4 sm:grid-cols-3">
          {[
            { label: "Analytical modules", value: 6 },
            { label: "SKUs in scenario", value: 25 },
            { label: "Candidate DCs", value: 4 },
          ].map((m, i) => (
            <MagicCard key={m.label} className="rounded-2xl">
              <div className="px-5 py-4">
                <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-400">
                  {m.label}
                </p>
                <p className="mt-2 font-display text-3xl font-semibold text-slate-900">
                  <NumberTicker value={m.value} delay={0.15 * i} />
                </p>
              </div>
            </MagicCard>
          ))}
        </section>
      </BlurFade>

      <BlurFade delay={0.28}>
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-panel">
          <BorderBeam
            size={80}
            duration={10}
            colorFrom="#14b8a6"
            colorTo="#38bdf8"
          />
          <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">
                Flagship
              </p>
              <h2 className="mt-1 font-display text-xl font-semibold text-slate-900">
                Live scenario re-solve
              </h2>
              <p className="mt-1 max-w-lg text-[13px] text-slate-500">
                Change demand, service level, or disruption intensity — every
                module re-solves for real.
              </p>
            </div>
            <ShimmerButton href="/scenario" background="#0f766e">
              Launch scenario
            </ShimmerButton>
          </div>
        </div>
      </BlurFade>

      <BlurFade delay={0.35}>
        <BentoGrid>
          {MODULES.map((m) => (
            <BentoCard
              key={m.href}
              name={m.name}
              description={m.description}
              href={m.href}
              Icon={m.Icon}
              className={m.className}
              background={
                <div className="absolute inset-0 bg-[radial-gradient(400px_circle_at_80%_0%,rgba(20,184,166,0.12),transparent_55%)]" />
              }
            />
          ))}
        </BentoGrid>
      </BlurFade>
    </div>
  );
}
