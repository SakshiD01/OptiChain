/** API health probe types and helpers for the sidebar status badge. */

import { API_BASE } from "@/lib/api";

export type HealthStatus = "checking" | "online" | "offline";

export const HEALTH_PATH = "/health";
export const HEALTH_POLL_MS = 15_000;

export type HealthResponse = {
  status: string;
  service?: string;
};

export async function checkApiHealth(
  signal?: AbortSignal
): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}${HEALTH_PATH}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!res.ok) {
    throw new Error(`Health check failed (${res.status})`);
  }
  return res.json() as Promise<HealthResponse>;
}
