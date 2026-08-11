"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type Options = {
  /** GET path — returns cached/warm results when available */
  resultsPath: string;
  /** POST path — used automatically if GET misses / fails */
  runPath: string;
  runBody?: unknown;
  /** Default true: load on mount without any button press */
  autoLoad?: boolean;
};

function errMessage(e: unknown): string {
  if (e instanceof Error) {
    const m = e.message;
    if (typeof m === "string" && m !== "[object Object]") return m;
  }
  return "Failed to load module data";
}

/**
 * Auto-loads module data on mount.
 * 1) GET cached/warm results
 * 2) If that fails, automatically POST a solve — no button required
 * Refresh button is optional for re-solving later.
 */
export function useModuleData<T>(options: Options) {
  const { resultsPath, runPath, runBody, autoLoad = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(autoLoad);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);

  const run = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const res = await apiPost<T>(runPath, runBody ?? {});
      setData(res);
      setFromCache(false);
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, [runPath, runBody]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<T>(resultsPath);
      setData(res);
      setFromCache(true);
      setLoading(false);
    } catch {
      // Cache miss / cold start — solve automatically, no click required
      try {
        const res = await apiPost<T>(runPath, runBody ?? {});
        setData(res);
        setFromCache(false);
        setError(null);
      } catch (e) {
        setError(errMessage(e));
      } finally {
        setLoading(false);
      }
    }
  }, [resultsPath, runPath, runBody]);

  useEffect(() => {
    if (autoLoad) void load();
  }, [autoLoad, load]);

  return { data, loading, refreshing, error, fromCache, load, run, setData };
}
