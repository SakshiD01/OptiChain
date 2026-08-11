"use client";

import { useLayoutEffect, useRef } from "react";
import gsap from "gsap";

export function AnimatedMetrics({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from("[data-metric]", {
        y: 16,
        opacity: 0,
        duration: 0.4,
        stagger: 0.07,
        ease: "power2.out",
      });
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {children}
    </div>
  );
}
