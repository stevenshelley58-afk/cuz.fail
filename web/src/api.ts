/* LotFile API client — V3 /api/v1 (VPS). Honest result kinds, no fakes. */

const DEFAULT_BASE = "/api/v1";

export type ApiResult<T> =
  | { kind: "ok"; status: number; data: T }
  | { kind: "auth" }                       // 401/403 — sign in required
  | { kind: "quota"; feature: "address" | "chat" } // 429 — guest allowance used
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
  id: string;
  source_id?: string;
  source_version_id: string;
  chunk_id?: string;
  source_title: string;
  locator?: string | null;
  quote?: string | null;
  uri?: string | null;
  clause_id?: string | null;
  heading?: string | null;
  page_number?: number | null;
  canonical_url?: string | null;
} & Record<string, unknown>;

export type CitationMapEntry = {
  marker: number;
  citation: ChatCitation;
};

export type AssistantTurn = {
  role: "user" | "assistant";
  content: string;
};

export type ChatReply = {
  answer: string;
  citations?: ChatCitation[];
  citation_map?: CitationMapEntry[];
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

// Dropdown row shape — populated from /address/search items.
export type AddressSuggestion = {
  address: string;
  gnaf_pid?: string | null;
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

export type AddressSearchHit = {
  address: string;
  address_point_id: string;
  gnaf_pid?: string | null;
  lat: number;
  lon: number;
  score: number;
};

export type AddressSearchResponse = {
  items: AddressSearchHit[];
  count: number;
  disclaimer?: string;
};

export type PropertyProfileResponse = {
  org_id: string;
  project_id: string;
  resolution_status: "resolved" | "missing_info" | "needs_more_info" | "needs_human_review" | "unsupported";
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

// Same-origin /api/v1 only — never reintroduce VITE_API_BASE_URL (see CLAUDE.md).
function base(): string {
  return DEFAULT_BASE;
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
  if (res.status === 429) {
    const d = data as { detail?: string } | null;
    if (d?.detail === "guest_allowance_used") {
      const feature = res.headers.get("x-lotfile-feature");
      return { kind: "quota", feature: feature === "address" ? "address" : "chat" };
    }
  }
  if (res.status === 501) {
    const d = data as { detail?: string; title?: string } | null;
    return { kind: "notBuilt", detail: d?.detail ?? d?.title };
  }
  if (res.status === 404) return { kind: "missing" };
  const d = data as { detail?: string; title?: string } | null;
  return { kind: "error", status: res.status, message: d?.detail ?? d?.title ?? res.statusText };
}

// ── Compliance types ──

export type ComplianceResultItem = {
  check_key: string;
  display_name: string;
  status: "likely_pass" | "likely_fail" | "needs_more_info" | "unsupported";
  threshold_value: number | string | null;
  threshold_unit: string | null;
  measured_value: number | string | null;
  rule_id: string | null;
  rule_quote: string | null;
  citation: string | null;
  note: string | null;
  missing_data?: string[] | null;
};

export type ComplianceRunResponse = {
  run_id: string;
  project_id: string;
  status: "pending" | "running" | "complete" | "error";
  as_of_date: string;
  advisory_disclaimer: string;
  results: ComplianceResultItem[];
};

// ── Document upload types ──

export type ExtractedFact = {
  fact_id?: string;
  fact_key: string;
  numeric_value: number | null;
  unit: string | null;
  confidence: number; // 0–1
  source_text: string | null;
  confirmed?: boolean;
};

export type DocumentUploadResponse = {
  document_id: string;
  filename: string;
  project_id?: string;
  parse_status?: string;
  parse_job?: { enqueued?: boolean; reason?: string };
  fact_count?: number;
  extracted_facts: ExtractedFact[];
};

export type ProjectDocumentSummary = {
  id: string;
  title: string;
  document_type: string;
  status: string;
  parse_status?: string;
  created_at: string | null;
  fact_count: number;
};

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
  guestSession: () => call<Record<string, unknown>>("POST", "/auth/guest"),
  projects: () => call<ProjectSummary[] | { projects?: ProjectSummary[] }>("GET", "/projects"),
  createProject: (address: string) => call<ProjectSummary>("POST", "/projects", {
    name: address,
    project_name: address,
    address,
    project_type: "single_house",
    stage: "concept",
  }),
  searchAddress: (q: string, limit = 8) =>
    call<AddressSearchResponse>("GET", `/address/search?q=${encodeURIComponent(q)}&limit=${limit}`),
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
  ask: (question: string, scope: { web: boolean }, history?: AssistantTurn[]) =>
    call<ChatReply>("POST", "/assistant", { message: question, web_search_requested: scope.web, history: history ?? [] }),
  compliance: {
    run: (projectId: string) =>
      call<ComplianceRunResponse>("POST", `/compliance/projects/${projectId}/run`, {}),
    matrix: (projectId: string) =>
      call<ComplianceRunResponse>("GET", `/compliance/projects/${projectId}/matrix`),
  },
  documents: {
    upload: async (projectId: string, file: File): Promise<ApiResult<DocumentUploadResponse>> => {
      const form = new FormData();
      form.append("file", file);
      form.append("project_id", projectId);
      let res: Response;
      try {
        res = await fetch(`${base()}/documents/upload`, {
          method: "POST",
          credentials: "include",
          body: form,
        });
      } catch (err) {
        return { kind: "down", message: err instanceof Error ? err.message : "network error" };
      }
      let data: unknown = null;
      const text = await res.text();
      if (text) { try { data = JSON.parse(text); } catch { data = text; } }
      if (res.ok) return { kind: "ok", status: res.status, data: data as DocumentUploadResponse };
      if (res.status === 401 || res.status === 403) return { kind: "auth" };
      if (res.status === 501) { const d = data as { detail?: string } | null; return { kind: "notBuilt", detail: d?.detail }; }
      if (res.status === 404) return { kind: "missing" };
      const d = data as { detail?: string } | null;
      return { kind: "error", status: res.status, message: d?.detail ?? res.statusText };
    },
    facts: (docId: string) => call<{ items: ExtractedFact[] }>("GET", `/documents/${docId}/facts`),
    listForProject: (projectId: string) => call<{ items: ProjectDocumentSummary[]; count: number }>("GET", `/documents/projects/${projectId}`),
    confirmFact: (docId: string, factKey: string) =>
      call<{ ok: boolean }>("POST", `/documents/${docId}/facts/${factKey}/review`, { review_status: "confirmed" }),
  },
  approveRule: (ruleId: string) =>
    call<{ id: string; lifecycle_status: string }>("POST", `/rules/${ruleId}/approve`, {}),
};
