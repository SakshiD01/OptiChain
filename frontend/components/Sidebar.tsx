"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Boxes,
  Factory,
  LayoutDashboard,
  Network,
  Route,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/forecasting", label: "Forecasting", icon: TrendingUp },
  { href: "/inventory", label: "Inventory", icon: Boxes },
  { href: "/network", label: "Network", icon: Network },
  { href: "/routing", label: "Routing", icon: Route },
  { href: "/scheduling", label: "Scheduling", icon: Factory },
  { href: "/simulation", label: "Simulation", icon: Activity },
  { href: "/scenario", label: "Scenario", icon: Sparkles, flagship: true },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-slate-200/80 bg-white">
      <div className="border-b border-slate-100 px-5 py-6">
        <Link href="/" className="focus-ring block rounded-md">
          <span className="font-display text-[17px] font-semibold tracking-tight text-slate-900">
            OptiChain
          </span>
          <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-400">
            Supply intelligence
          </p>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          const flagship = "flagship" in item && item.flagship;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "focus-ring group flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all",
                active
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                flagship && !active && "text-teal-700"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  active ? "text-teal-300" : "text-slate-400 group-hover:text-slate-600",
                  flagship && !active && "text-teal-600"
                )}
              />
              {item.label}
              {flagship && !active ? (
                <span className="ml-auto rounded-md bg-teal-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-teal-700">
                  Live
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-100 px-5 py-4">
        <p className="text-[11px] leading-relaxed text-slate-400">
          Seeded FMCG scenario
          <br />
          <span className="text-slate-600">25 SKUs · 4 DCs · 40 nodes</span>
        </p>
      </div>
    </aside>
  );
}
