/** Shared API client for OptiChain backend. */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail ?? body.error ?? `HTTP ${res.status}`;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
  }
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const detail = payload.detail ?? payload.error ?? `HTTP ${res.status}`;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
  }
  return res.json() as Promise<T>;
}

export { API_BASE };
