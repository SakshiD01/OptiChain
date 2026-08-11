"use client";

import { useCallback, useState } from "react";
import type { HealthStatus } from "@/lib/health";

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

  const refresh = useCallback(() => {
    setStatus("checking");
  }, []);

  return { status, service, checkedAt, error, refresh };
}
