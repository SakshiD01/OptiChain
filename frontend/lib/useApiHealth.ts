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
  refresh: () => void;
};

export function useApiHealth(): ApiHealthState {
  const [status, setStatus] = useState<HealthStatus>("checking");
  const [service, setService] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => {
    setStatus("checking");
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
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
      } catch (err) {
        if (cancelled || controller.signal.aborted) return;
        setStatus("offline");
        setService(null);
        setError(err instanceof Error ? err.message : "Health check failed");
        setCheckedAt(Date.now());
      }
    })();

    const id = window.setInterval(() => setTick((n) => n + 1), HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(id);
    };
  }, [tick]);

  return { status, service, checkedAt, error, refresh };
}
