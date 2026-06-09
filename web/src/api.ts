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

/* ── Stage 3 types ── */

export type RuleSummary = {
  id: string;
  rule_key: string;
  operator: string;
  value_json: number | object | null;
  unit: string | null;
  rule_type: string;
  lifecycle_status: string;
  confidence: number;
  clause_id: string | null;
  source_version_id: string | null;
  created_at: string;
};

export type CandidateSummary = {
  id: string;
  rule_key: string | null;
  operator: string | null;
  value_json: number | object | null;
  unit: string | null;
  quote: string | null;
  review_status: string;
  confidence: number | null;
  validator_results_json: Record<string, { pass: boolean; detail: string }> | null;
  extraction_pass: number | null;
  clause_id: string | null;
  auto_promoted_at: string | null;
};

/* ── Stage 2 types ── */

export type ProvenanceResponse = {
  kind: "spatial_dataset" | "manual_override";
  method: string;
  target_crs: string;
  dataset_id?: string | null;
  licence_status?: string | null;
};

export type PropertyFactResponse = {
  fact_id: string;
  fact_type: string;
  value: unknown;
  confidence: "high" | "medium" | "low" | "none";
  review_status: string;
  provenance: ProvenanceResponse;
};

export type PropertyProfileResponse = {
  org_id: string;
  project_id: string;
  resolution_status: "resolved" | "missing_info" | "needs_human_review" | "unsupported";
  confidence: "high" | "medium" | "low" | "none";
  address?: string | null;
  local_government?: string | null;
  target_crs: string;
  issues: string[];
  provenance: ProvenanceResponse[];
  facts: PropertyFactResponse[];
};

export type ProposalRequest = {
  proposal_type?: string | null;
  dwelling_type?: string | null;
  building_class?: string | null;
  work_type?: string | null;
  new_or_existing?: "new" | "existing" | null;
  lot_type?: string | null;
  primary_street_confirmed?: boolean;
  secondary_street_confirmed?: boolean;
};

export type ProposalResponse = {
  id: string;
  org_id: string;
  project_id: string;
  proposal_type?: string | null;
  dwelling_type?: string | null;
  building_class?: string | null;
  work_type?: string | null;
  lot_type?: string | null;
  created_at: string;
  updated_at: string;
};

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
  // Dev-only password login (disabled in production on the server). See web/src/main.tsx DEV_LOGIN.
  devLogin: (username: string, password: string) =>
    call<Record<string, unknown>>("POST", "/auth/dev-login", { username, password }),
  logout: () => call<Record<string, unknown>>("POST", "/auth/logout"),
  projects: () => call<ProjectSummary[] | { projects?: ProjectSummary[] }>("GET", "/projects"),
  createProject: (address: string) => call<ProjectSummary>("POST", "/projects", {
    name: address,
    project_name: address,
    address,
    project_type: "single_house",
    stage: "concept",
  }),
  resolveAddress: (projectId: string, address: string) =>
    call<PropertyProfileResponse>("POST", `/projects/${projectId}/resolve-address`, { address }),
  getProperty: (projectId: string) =>
    call<PropertyProfileResponse>("GET", `/projects/${projectId}/property`),
  upsertProposal: (projectId: string, data: ProposalRequest) =>
    call<ProposalResponse>("POST", `/projects/${projectId}/proposal`, data),
  createProjectV2: (name: string, council_scope?: string) =>
    call<ProjectSummary>("POST", "/projects", { name, council_scope }),
  rules: () => call<unknown>("GET", "/sources"),
  listRules: (opts?: { lifecycle_status?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams();
    if (opts?.lifecycle_status) params.set("lifecycle_status", opts.lifecycle_status);
    if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts?.offset !== undefined) params.set("offset", String(opts.offset));
    const qs = params.toString();
    return call<RuleSummary[]>("GET", `/rules${qs ? `?${qs}` : ""}`);
  },
  getRule: (id: string) => call<RuleSummary>("GET", `/rules/${id}`),
  listCandidates: (opts?: { review_status?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams();
    if (opts?.review_status) params.set("review_status", opts.review_status);
    if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts?.offset !== undefined) params.set("offset", String(opts.offset));
    const qs = params.toString();
    return call<CandidateSummary[]>("GET", `/rules/candidates${qs ? `?${qs}` : ""}`);
  },
  getCandidate: (id: string) => call<CandidateSummary>("GET", `/rules/candidates/${id}`),
  ask: (question: string, scope: { web: boolean }) =>
    call<ChatReply>("POST", "/assistant", { message: question, web_search_requested: scope.web }),
};
