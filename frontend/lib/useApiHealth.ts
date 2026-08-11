"use client";

import { useCallback, useEffect, useState } from "react";
import {
  checkApiHealth,
  HEALTH_POLL_MS,
  type HealthStatus,
} from "@/lib/health";

export type ApiHealthState = {
  status: HealthStatus;
  service: string | null;
  checkedAt: number | null;
  error: string | null;
  now: number;
  refresh: () => void;
};

export function useApiHealth(): ApiHealthState {
  const [status, setStatus] = useState<HealthStatus>("checking");
  const [service, setService] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  const refresh = useCallback(() => {
    setStatus("checking");
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        setTick((n) => n + 1);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined" && document.visibilityState === "hidden") {
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    (async () => {
      try {
        const data = await checkApiHealth(controller.signal);
        if (cancelled) return;
        const ok = (data.status || "").toLowerCase() === "ok";
        setStatus(ok ? "online" : "offline");
        setService(data.service ?? null);
        setError(ok ? null : "Unexpected health payload");
        setCheckedAt(Date.now());
        setNow(Date.now());
      } catch (err) {
        if (cancelled || controller.signal.aborted) return;
        setStatus("offline");
        setService(null);
        setError(err instanceof Error ? err.message : "Health check failed");
        setCheckedAt(Date.now());
        setNow(Date.now());
      }
    })();

    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        setTick((n) => n + 1);
      }
    }, HEALTH_POLL_MS);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(id);
    };
  }, [tick]);

  return { status, service, checkedAt, error, now, refresh };
}
