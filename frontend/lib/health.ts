/** API health probe types and helpers for the sidebar status badge. */

export type HealthStatus = "checking" | "online" | "offline";

export const HEALTH_PATH = "/health";
export const HEALTH_POLL_MS = 15_000;
