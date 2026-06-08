/* LotFile API client — V3 /api/v1 (VPS). Honest result kinds, no fakes. */

const DEFAULT_BASE = "/api/v1";

export type ApiResult<T> =
  | { kind: "ok"; status: number; data: T }
  | { kind: "auth" }                       // 401/403 — sign in required
  | { kind: "notBuilt"; detail?: string }  // 501 — endpoint not shipped yet
  | { kind: "missing" }                    // 404 — route absent
  | { kind: "error"; status: number; message: string }
  | { kind: "down"; message: string };     // network / API unreachable

export type SessionInfo = {
  authenticated?: boolean;
  email?: string;
  user?: { email?: string; role?: string } | null;
  role?: string;
} & Record<string, unknown>;

export type ProjectSummary = {
  id: string;
  name?: string;
  address?: string;
  created_at?: string;
} & Record<string, unknown>;

export type HealthInfo = { status?: string; service?: string; version?: string } & Record<string, unknown>;

export type ChatCitation = {
  source_title?: string;
  locator?: string;
  clause_id?: string | null;
  heading?: string | null;
  page_number?: number | null;
  canonical_url?: string | null;
  quote?: string;
} & Record<string, unknown>;

export type ChatReply = {
  answer: string;
  citations?: ChatCitation[];
  grounded?: boolean;
  model?: string;
  provider?: string;
  used_fallback?: boolean;
  disclaimer?: string | null;
} & Record<string, unknown>;

function base(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  return (raw && raw.length > 0 ? raw : DEFAULT_BASE).replace(/\/+$/, "");
}

async function call<T>(method: string, path: string, body?: unknown): Promise<ApiResult<T>> {
  let res: Response;
  try {
    res = await fetch(`${base()}${path}`, {
      method,
      credentials: "include",
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    return { kind: "down", message: err instanceof Error ? err.message : "network error" };
  }
  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (res.ok) return { kind: "ok", status: res.status, data: data as T };
  if (res.status === 401 || res.status === 403) return { kind: "auth" };
  if (res.status === 501) {
    const d = data as { detail?: string; title?: string } | null;
    return { kind: "notBuilt", detail: d?.detail ?? d?.title };
  }
  if (res.status === 404) return { kind: "missing" };
  const d = data as { detail?: string; title?: string } | null;
  return { kind: "error", status: res.status, message: d?.detail ?? d?.title ?? res.statusText };
}

export const api = {
  health: () => call<HealthInfo>("GET", "/health"),
  ready: () => call<Record<string, unknown>>("GET", "/ready"),
  session: () => call<SessionInfo>("GET", "/auth/session"),
  magicLinkRequest: (email: string) => call<Record<string, unknown>>("POST", "/auth/magic-link/request", { email }),
  magicLinkVerify: (token: string) => call<Record<string, unknown>>("POST", "/auth/magic-link/verify", { token }),
  logout: () => call<Record<string, unknown>>("POST", "/auth/logout"),
  projects: () => call<ProjectSummary[] | { projects?: ProjectSummary[] }>("GET", "/projects"),
  createProject: (address: string) => call<ProjectSummary>("POST", "/projects", { name: address, address }),
  resolveAddress: (projectId: string, address: string) =>
    call<Record<string, unknown>>("POST", `/projects/${projectId}/resolve-address`, { address }),
  rules: () => call<unknown>("GET", "/sources"),
  ask: (question: string, scope: { web: boolean }) =>
    call<ChatReply>("POST", "/assistant", { message: question, web_search_requested: scope.web }),
};
