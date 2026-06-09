import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUp,
  Badge,
  BookOpen,
  Building2,
  CheckCircle2,
  CircleAlert,
  CircleHelp,
  CreditCard,
  Construction,
  Gavel,
  Gauge,
  Globe2,
  Home as HomeIcon,
  HousePlus,
  Lock,
  MailCheck,
  MapPin,
  MessageCircle,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, type ApiResult, type ChatReply, type HealthInfo, type ProjectSummary, type SessionInfo, type PropertyProfileResponse, type PropertyFactResponse, type ProposalRequest, type ProposalResponse, type RuleSummary, type CandidateSummary, type ComplianceRunResponse, type ComplianceResultItem, type ExtractedFact, type DocumentUploadResponse } from "./api";
import "./styles.css";

// Magic link is disabled — always use the username/password login form.
const DEV_LOGIN = true;

const GUEST_USAGE_KEY = "lotfile_guest_usage_v1";
const GUEST_ADDRESS_LIMIT = envNumber("VITE_GUEST_ADDRESS_LIMIT", 2);
const GUEST_CHAT_LIMIT = envNumber("VITE_GUEST_CHAT_LIMIT", 8);
const CHECKOUT_URL = String((import.meta.env as Record<string, unknown>).VITE_CHECKOUT_URL ?? "").trim();

/* ── helpers ── */

type View = "home" | "projects" | "library" | "rules" | "settings";
type GuestFeature = "address" | "chat";

type GuestCheck = {
  id: string;
  address: string;
  createdAt: string;
  mode: "guest" | "fallback";
};

type GuestUsage = {
  addressChecks: number;
  chatMessages: number;
  checks: GuestCheck[];
  updatedAt: string;
};

type PaywallState = {
  feature: GuestFeature;
  used: number;
  limit: number;
};

type Msg = {
  role: "q" | "a";
  text: string;
  tone?: "note" | "warn";
  chips?: string[];
  action?: { label: string; run: () => void };
};

const ICONS: Record<string, LucideIcon> = {
  add_home_work: HousePlus,
  arrow_upward: ArrowUp,
  badge: Badge,
  check_circle: CheckCircle2,
  credit_card: CreditCard,
  construction: Construction,
  error: CircleAlert,
  forum: MessageCircle,
  gavel: Gavel,
  gauge: Gauge,
  home: HomeIcon,
  home_work: Building2,
  location_on: MapPin,
  lock: Lock,
  mark_email_read: MailCheck,
  menu_book: BookOpen,
  public: Globe2,
  sparkles: Sparkles,
  sync: RefreshCw,
  tune: Settings2,
  verified: ShieldCheck,
};

function Icon({ name, size }: { name: string; size?: number }) {
  const Component = ICONS[name] ?? CircleHelp;
  return (
    <Component
      aria-hidden="true"
      className="icon"
      focusable="false"
      size={size}
      strokeWidth={2.25}
    />
  );
}

function looksLikeAddress(t: string): boolean {
  return /^\d+\s+\w+.*(st|street|rd|road|ave|avenue|lane|ln|way|cres|crescent|court|ct|pl|place)\b/i.test(t.trim());
}

function envNumber(name: string, fallback: number): number {
  const raw = (import.meta.env as Record<string, unknown>)[name];
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

function emptyGuestUsage(): GuestUsage {
  return {
    addressChecks: 0,
    chatMessages: 0,
    checks: [],
    updatedAt: new Date().toISOString(),
  };
}

function normalizeGuestUsage(value: Partial<GuestUsage> | null | undefined): GuestUsage {
  const empty = emptyGuestUsage();
  return {
    addressChecks: Math.max(0, Number(value?.addressChecks ?? 0) || 0),
    chatMessages: Math.max(0, Number(value?.chatMessages ?? 0) || 0),
    checks: Array.isArray(value?.checks) ? value.checks.slice(0, 4) : [],
    updatedAt: typeof value?.updatedAt === "string" ? value.updatedAt : empty.updatedAt,
  };
}

function loadGuestUsage(): GuestUsage {
  try {
    return normalizeGuestUsage(JSON.parse(window.localStorage.getItem(GUEST_USAGE_KEY) ?? "null") as Partial<GuestUsage> | null);
  } catch {
    return emptyGuestUsage();
  }
}

function saveGuestUsage(usage: GuestUsage) {
  window.localStorage.setItem(GUEST_USAGE_KEY, JSON.stringify(usage));
}

function guestProjectList(usage: GuestUsage): ProjectSummary[] {
  return usage.checks.map((check) => ({
    id: check.id,
    name: check.address,
    address: check.address,
    created_at: new Date(check.createdAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
    status: check.mode,
  }));
}

function paywallCopy(feature: GuestFeature): { title: string; body: string } {
  if (feature === "address") {
    return {
      title: "Guest address checks used",
      body: "You have seen the address-first workflow. Upgrade or sign in to keep running property searches, save dossiers, and unlock deeper checks.",
    };
  }
  return {
    title: "Guest chat limit reached",
    body: "You have used the free guest chat allowance. Upgrade or sign in to keep asking source-backed planning questions.",
  };
}

function guestLimitMessage(feature: GuestFeature): string {
  return feature === "address"
    ? "You have used the free guest address checks. Unlock more searches to keep going."
    : "You have used the free guest chat allowance. Unlock more questions to keep going.";
}

function projectList(r: ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }>): ProjectSummary[] {
  if (r.kind !== "ok") return [];
  const d = r.data;
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d.projects)) return d.projects;
  return [];
}

function citationChip(citation: NonNullable<ChatReply["citations"]>[number]): string {
  return [
    citation.source_title,
    citation.clause_id ?? citation.locator ?? citation.heading,
    citation.page_number ? `p.${citation.page_number}` : "",
  ].filter(Boolean).join(" · ");
}

/* ── wizard types ── */

type WizardStep = 1 | 2 | 3;

type WizardState = {
  step: WizardStep;
  projectId: string;
  address: string;
  property: PropertyProfileResponse | null;
  proposal: ProposalRequest;
  savedProposal: ProposalResponse | null;
};

/* ── helpers for wizard display ── */

function resolutionBadge(status: PropertyProfileResponse["resolution_status"]) {
  const map: Record<string, { label: string; bg: string; color: string }> = {
    resolved: { label: "Resolved", bg: "var(--mint)", color: "var(--green-800)" },
    missing_info: { label: "Missing info", bg: "var(--flag-bg)", color: "var(--flag)" },
    needs_human_review: { label: "Needs human review", bg: "#EFF6FF", color: "#1D4ED8" },
    unsupported: { label: "Unsupported", bg: "#FEF2F2", color: "#B91C1C" },
  };
  const s = map[status] ?? { label: status, bg: "#EFF1F1", color: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 99, background: s.bg, color: s.color, display: "inline-flex", alignItems: "center", gap: 5 }}>
      {s.label}
    </span>
  );
}

function confidenceBadge(confidence: string) {
  const colors: Record<string, string> = { high: "var(--green-800)", medium: "var(--flag)", low: "#B91C1C", none: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 99, background: "var(--paper)", border: "1px solid var(--line)", color: colors[confidence] ?? "var(--ink-soft)", display: "inline-flex", alignItems: "center", gap: 4 }}>
      Confidence: {confidence}
    </span>
  );
}

function groupFactsByType(facts: PropertyFactResponse[]): Map<string, PropertyFactResponse[]> {
  const m = new Map<string, PropertyFactResponse[]>();
  for (const f of facts) {
    const arr = m.get(f.fact_type) ?? [];
    arr.push(f);
    m.set(f.fact_type, arr);
  }
  return m;
}

function formatFactValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

const NOT_LEGAL_PROOF_NOTE = (
  <div style={{ fontSize: ".72rem", fontWeight: 600, color: "var(--flag)", background: "var(--flag-bg)", border: "1px solid #F5DEB9", borderRadius: 10, padding: "6px 12px", margin: "8px 0", display: "flex", alignItems: "flex-start", gap: 6 }}>
    <Icon name="error" />
    <span>Not legal proof of property boundaries. Resolution status is advisory only and must not be used as a substitute for a registered survey or certificate of title.</span>
  </div>
);

/* ── ProvenanceAccordion ── */

function ProvenanceAccordion({ provenance }: { provenance: PropertyProfileResponse["provenance"] }) {
  const [open, setOpen] = useState(false);
  if (!provenance || provenance.length === 0) return null;
  return (
    <div style={{ marginTop: 8 }}>
      <button
        style={{ fontSize: ".72rem", fontWeight: 700, color: "var(--ink-soft)", display: "flex", alignItems: "center", gap: 5, background: "none", border: "none", cursor: "pointer" }}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <Icon name="verified" />
        {open ? "Hide" : "Show"} data provenance ({provenance.length})
      </button>
      {open && (
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
          {provenance.map((p, i) => (
            <div key={i} style={{ fontSize: ".72rem", background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 10, padding: "8px 12px" }}>
              <div><b>Kind:</b> {p.kind}</div>
              <div><b>Method:</b> {p.method}</div>
              <div><b>CRS:</b> {p.target_crs}</div>
              {p.dataset_id && <div><b>Dataset:</b> {p.dataset_id}</div>}
              {p.licence_status && <div><b>Licence:</b> {p.licence_status}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── AddressResolverPanel ── */

function AddressResolverPanel({ property, onContinue, onBack }: { property: PropertyProfileResponse; onContinue: () => void; onBack?: () => void }) {
  const factsByType = groupFactsByType(property.facts ?? []);

  const zoneEntry = factsByType.get("zone");
  const rCodeEntry = factsByType.get("r_code");
  const overlayEntries = factsByType.get("overlay");

  return (
    <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h3 style={{ marginBottom: 12 }}><Icon name="location_on" />Property Resolution</h3>

      {NOT_LEGAL_PROOF_NOTE}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
        {resolutionBadge(property.resolution_status)}
        {confidenceBadge(property.confidence)}
      </div>

      {property.address && (
        <div style={{ fontSize: ".85rem", marginBottom: 6 }}><b>Address:</b> {property.address}</div>
      )}
      {property.local_government && (
        <div style={{ fontSize: ".85rem", marginBottom: 6 }}><b>Local government:</b> {property.local_government}</div>
      )}

      {property.resolution_status !== "resolved" && property.issues.length > 0 && (
        <div className="state" style={{ marginTop: 8 }}>
          <Icon name="error" />
          <div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Issues preventing full resolution:</div>
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {property.issues.map((issue, i) => <li key={i}>{issue}</li>)}
            </ul>
          </div>
        </div>
      )}

      {(zoneEntry || rCodeEntry || overlayEntries) && (
        <div style={{ marginTop: 10, fontSize: ".85rem" }}>
          <div style={{ fontWeight: 700, marginBottom: 6, color: "var(--ink)" }}>Planning facts</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {zoneEntry?.map((f) => (
              <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ color: "var(--ink-soft)" }}>Zone</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
              </div>
            ))}
            {rCodeEntry?.map((f) => (
              <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ color: "var(--ink-soft)" }}>R-Code</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
              </div>
            ))}
            {overlayEntries?.map((f) => (
              <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ color: "var(--ink-soft)" }}>Overlay</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {factsByType.size > 0 && (
        <div style={{ marginTop: 10, fontSize: ".85rem" }}>
          <div style={{ fontWeight: 700, marginBottom: 6, color: "var(--ink)" }}>All facts ({property.facts.length})</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {Array.from(factsByType.entries()).map(([factType, entries]) =>
              entries.map((f) => (
                <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                  <span style={{ color: "var(--ink-soft)" }}>{factType}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
                    <span style={{ fontSize: ".66rem", color: "var(--ink-faint)" }}>{f.confidence}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <ProvenanceAccordion provenance={property.provenance} />

      <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
        {onBack && (
          <button className="btn alt" onClick={onBack}>← Back</button>
        )}
        <button className="btn" onClick={onContinue}>Next: Proposal details →</button>
      </div>
    </div>
  );
}

/* ── ProposalForm (Step 2) ── */

function ProposalForm({
  projectId,
  initial,
  onSaved,
  onBack,
}: {
  projectId: string;
  initial: ProposalRequest;
  onSaved: (proposal: ProposalResponse, data: ProposalRequest) => void;
  onBack: () => void;
}) {
  const [data, setData] = useState<ProposalRequest>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Partial<ProposalRequest>) => setData((d) => ({ ...d, ...patch }));

  const save = async () => {
    setBusy(true);
    setError(null);
    const r = await api.upsertProposal(projectId, data);
    setBusy(false);
    if (r.kind === "ok") {
      onSaved(r.data, data);
    } else if (r.kind === "notBuilt") {
      setError("Proposal saving not yet available (endpoint not built).");
      onSaved({ id: "", org_id: "", project_id: projectId, created_at: "", updated_at: "" }, data);
    } else if (r.kind === "auth") {
      setError("Sign in required to save proposal.");
    } else {
      setError(r.kind === "error" ? r.message : `Failed (${r.kind}).`);
    }
  };

  const selectStyle = {
    width: "100%",
    border: "1.5px solid var(--line)",
    borderRadius: 12,
    padding: "10px 14px",
    outline: "none",
    background: "var(--paper)",
    fontSize: ".85rem",
    color: "var(--ink)",
    fontFamily: "inherit",
  } as React.CSSProperties;

  const labelStyle = { fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", display: "block", marginBottom: 4 } as React.CSSProperties;

  const fieldWrap = { marginBottom: 14 } as React.CSSProperties;

  return (
    <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h3 style={{ marginBottom: 16 }}><Icon name="home_work" />Proposal details</h3>

      <div style={fieldWrap}>
        <label style={labelStyle} htmlFor="proposal_type">Proposal type</label>
        <select id="proposal_type" style={selectStyle} value={data.proposal_type ?? ""} onChange={(e) => update({ proposal_type: e.target.value || null })}>
          <option value="">— select —</option>
          <option value="residential">Residential</option>
          <option value="commercial">Commercial</option>
          <option value="mixed_use">Mixed use</option>
        </select>
      </div>

      {data.proposal_type === "residential" && (
        <div style={fieldWrap}>
          <label style={labelStyle} htmlFor="dwelling_type">Dwelling type</label>
          <select id="dwelling_type" style={selectStyle} value={data.dwelling_type ?? ""} onChange={(e) => update({ dwelling_type: e.target.value || null })}>
            <option value="">— select —</option>
            <option value="single_house">Single house</option>
            <option value="grouped_dwelling">Grouped dwelling</option>
            <option value="multiple_dwelling">Multiple dwelling</option>
            <option value="ancillary_dwelling">Ancillary dwelling</option>
            <option value="short_stay">Short stay</option>
          </select>
        </div>
      )}

      <div style={fieldWrap}>
        <label style={labelStyle} htmlFor="work_type">Work type</label>
        <select id="work_type" style={selectStyle} value={data.work_type ?? ""} onChange={(e) => update({ work_type: e.target.value || null })}>
          <option value="">— select —</option>
          <option value="new_construction">New construction</option>
          <option value="extension">Extension</option>
          <option value="renovation">Renovation</option>
          <option value="demolition">Demolition</option>
          <option value="change_of_use">Change of use</option>
        </select>
      </div>

      <div style={fieldWrap}>
        <span style={labelStyle}>New or existing building</span>
        <div style={{ display: "flex", gap: 16 }}>
          {(["new", "existing"] as const).map((v) => (
            <label key={v} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: ".85rem", cursor: "pointer" }}>
              <input
                type="radio"
                name="new_or_existing"
                value={v}
                checked={data.new_or_existing === v}
                onChange={() => update({ new_or_existing: v })}
              />
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </label>
          ))}
        </div>
      </div>

      <div style={fieldWrap}>
        <label style={labelStyle} htmlFor="lot_type">Lot type</label>
        <select id="lot_type" style={selectStyle} value={data.lot_type ?? ""} onChange={(e) => update({ lot_type: e.target.value || null })}>
          <option value="">— select —</option>
          <option value="green_title">Green title</option>
          <option value="strata_title">Strata title</option>
          <option value="survey_strata">Survey strata</option>
        </select>
      </div>

      {error && (
        <div className="state" style={{ marginBottom: 10 }}>
          <Icon name="error" /><span>{error}</span>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn alt" onClick={onBack} disabled={busy}>← Back</button>
        <button className="btn" onClick={() => void save()} disabled={busy}>
          {busy ? "Saving…" : "Save & Continue →"}
        </button>
      </div>
    </div>
  );
}

/* ── ConfirmationStep (Step 3) ── */

function ConfirmationStep({
  projectId,
  address,
  property,
  proposal,
  onBack,
  onStart,
}: {
  projectId: string;
  address: string;
  property: PropertyProfileResponse | null;
  proposal: ProposalRequest;
  onBack: () => void;
  onStart: () => void;
}) {
  const factsByType = property ? groupFactsByType(property.facts ?? []) : new Map<string, PropertyFactResponse[]>();
  const zone = factsByType.get("zone")?.[0];
  const rCode = factsByType.get("r_code")?.[0];

  return (
    <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h3 style={{ marginBottom: 16 }}><Icon name="check_circle" />Confirm and start</h3>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: ".72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--ink-faint)", marginBottom: 4 }}>Project</div>
        <div style={{ fontWeight: 700, fontSize: ".95rem" }}>{address}</div>
      </div>

      {NOT_LEGAL_PROOF_NOTE}

      {property && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: ".72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--ink-faint)", marginBottom: 8 }}>Property summary</div>
          <div style={{ fontSize: ".85rem", display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Status</span>
              {resolutionBadge(property.resolution_status)}
            </div>
            {property.local_government && (
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>LGA</span>
                <span style={{ fontWeight: 600 }}>{property.local_government}</span>
              </div>
            )}
            {zone && (
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Zone</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(zone.value)}</span>
              </div>
            )}
            {rCode && (
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>R-Code</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(rCode.value)}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Confidence</span>
              {confidenceBadge(property.confidence)}
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: ".72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--ink-faint)", marginBottom: 8 }}>Proposal summary</div>
        <div style={{ fontSize: ".85rem", display: "flex", flexDirection: "column", gap: 4 }}>
          {proposal.proposal_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Type</span>
              <span style={{ fontWeight: 600 }}>{proposal.proposal_type}</span>
            </div>
          )}
          {proposal.dwelling_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Dwelling</span>
              <span style={{ fontWeight: 600 }}>{proposal.dwelling_type}</span>
            </div>
          )}
          {proposal.work_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Work type</span>
              <span style={{ fontWeight: 600 }}>{proposal.work_type}</span>
            </div>
          )}
          {proposal.new_or_existing && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>New / existing</span>
              <span style={{ fontWeight: 600 }}>{proposal.new_or_existing}</span>
            </div>
          )}
          {proposal.lot_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Lot type</span>
              <span style={{ fontWeight: 600 }}>{proposal.lot_type}</span>
            </div>
          )}
        </div>
      </div>

      <DocumentUpload projectId={projectId} />

      <CompliancePanel projectId={projectId} />

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn alt" onClick={onBack}>← Back to edit</button>
        <button className="btn" onClick={onStart}>
          <Icon name="check_circle" />Start checking
        </button>
      </div>
    </div>
  );
}

/* ── CompliancePanel ── */

type CompliancePanelProps = {
  projectId: string;
};

function StatusBadge({ status }: { status: ComplianceResultItem["status"] }) {
  if (status === "likely_pass")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#16a34a", fontWeight: 600 }}>
        <CheckCircle2 size={16} /> Pass
      </span>
    );
  if (status === "likely_fail")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#dc2626", fontWeight: 600 }}>
        <CircleAlert size={16} /> Fail
      </span>
    );
  if (status === "needs_more_info")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#ca8a04", fontWeight: 600 }}>
        <CircleHelp size={16} /> More info needed
      </span>
    );
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#6b7280", fontWeight: 600 }}>
      — Unsupported
    </span>
  );
}

function ComplianceResultRow({
  item,
  onUploadDrawing,
}: {
  item: ComplianceResultItem;
  onUploadDrawing?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        marginBottom: 8,
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontWeight: 500, fontSize: 14 }}>{item.check_name}</span>
        <StatusBadge status={item.status} />
      </button>

      {expanded && (
        <div style={{ padding: "0 14px 14px", fontSize: 13, color: "#374151" }}>
          {(item.measured_value !== null || item.threshold_value !== null) && (
            <div
              style={{
                display: "flex",
                gap: 24,
                background: "#f9fafb",
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 10,
              }}
            >
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Measured</div>
                <div style={{ fontWeight: 600 }}>
                  {item.measured_value ?? "—"}{" "}
                  {item.threshold_unit ? <span style={{ fontWeight: 400, color: "#6b7280" }}>{item.threshold_unit}</span> : null}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Threshold</div>
                <div style={{ fontWeight: 600 }}>
                  {item.threshold_value ?? "—"}{" "}
                  {item.threshold_unit ? <span style={{ fontWeight: 400, color: "#6b7280" }}>{item.threshold_unit}</span> : null}
                </div>
              </div>
            </div>
          )}

          {item.rule_quote && (
            <blockquote
              style={{
                margin: "0 0 8px",
                paddingLeft: 10,
                borderLeft: "3px solid #d1d5db",
                color: "#4b5563",
                fontStyle: "italic",
                fontSize: 12,
              }}
            >
              {item.rule_quote}
            </blockquote>
          )}

          {item.citation && (
            <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
              <span style={{ fontWeight: 500 }}>Source:</span> {item.citation}
            </div>
          )}

          {item.status === "needs_more_info" && (
            <div
              style={{
                background: "#fffbeb",
                border: "1px solid #fde68a",
                borderRadius: 6,
                padding: "8px 12px",
                marginTop: 8,
              }}
            >
              <div style={{ fontWeight: 500, marginBottom: 4, color: "#92400e" }}>Missing information</div>
              {item.missing_data && item.missing_data.length > 0 ? (
                <ul style={{ margin: "0 0 8px", paddingLeft: 16 }}>
                  {item.missing_data.map((d) => (
                    <li key={d} style={{ fontSize: 12 }}>{d}</li>
                  ))}
                </ul>
              ) : null}
              {onUploadDrawing && (
                <button
                  onClick={onUploadDrawing}
                  style={{
                    fontSize: 12,
                    padding: "4px 10px",
                    background: "#f59e0b",
                    color: "#fff",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                  }}
                >
                  Upload drawing to provide this data
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CompliancePanel({ projectId }: CompliancePanelProps) {
  const [runResult, setRunResult] = useState<ComplianceRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadPrompted, setUploadPrompted] = useState(false);

  useEffect(() => {
    api.compliance.matrix(projectId).then((r) => {
      if (r.kind === "ok") setRunResult(r.data);
    });
  }, [projectId]);

  async function runCheck() {
    setLoading(true);
    setError(null);
    const r = await api.compliance.run(projectId);
    setLoading(false);
    if (r.kind === "ok") {
      setRunResult(r.data);
    } else if (r.kind === "notBuilt") {
      setError("Compliance check endpoint not yet available on this server.");
    } else if (r.kind === "auth") {
      setError("Sign in required.");
    } else if (r.kind === "error") {
      setError(r.message);
    } else {
      setError("Could not reach server.");
    }
  }

  const results = runResult?.results ?? [];
  const passCount = results.filter((r) => r.status === "likely_pass").length;
  const failCount = results.filter((r) => r.status === "likely_fail").length;
  const moreInfoCount = results.filter((r) => r.status === "needs_more_info").length;

  return (
    <div style={{ padding: "0 0 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Compliance check</h3>
          {results.length > 0 && (
            <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
              {passCount} pass · {failCount} fail · {moreInfoCount} needs info · {results.filter(r => r.status === "unsupported").length} unsupported
            </div>
          )}
        </div>
        <button
          onClick={() => void runCheck()}
          disabled={loading}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "8px 16px",
            background: loading ? "#e5e7eb" : "#2563eb",
            color: loading ? "#6b7280" : "#fff",
            border: "none",
            borderRadius: 6,
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          <RefreshCw size={15} style={loading ? { animation: "spin 1s linear infinite" } : {}} />
          {loading ? "Running…" : "Run compliance check"}
        </button>
      </div>

      {error && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#b91c1c",
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {results.length === 0 && !loading && !error && (
        <div style={{ color: "#6b7280", fontSize: 14 }}>
          No compliance results yet. Run a check to get started.
        </div>
      )}

      {results.map((item) => (
        <ComplianceResultRow
          key={item.check_key}
          item={item}
          onUploadDrawing={item.status === "needs_more_info" ? () => setUploadPrompted(true) : undefined}
        />
      ))}

      {uploadPrompted && (
        <div
          style={{
            marginTop: 12,
            padding: "10px 14px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 8,
            fontSize: 13,
            color: "#1e40af",
          }}
        >
          Scroll down to the Documents section to upload a drawing or plan.
        </div>
      )}
    </div>
  );
}

/* ── DocumentUpload ── */

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#16a34a" : pct >= 50 ? "#ca8a04" : "#dc2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: "#e5e7eb",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.3s",
          }}
        />
      </div>
      <span style={{ fontSize: 11, color: "#6b7280", minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

function FactCard({
  fact,
  docId,
  onConfirmed,
}: {
  fact: ExtractedFact;
  docId: string;
  onConfirmed: (factKey: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(fact.confirmed ?? false);
  const [err, setErr] = useState<string | null>(null);

  async function confirm() {
    setConfirming(true);
    setErr(null);
    const r = await api.documents.confirmFact(docId, fact.fact_key);
    setConfirming(false);
    if (r.kind === "ok" || r.kind === "notBuilt") {
      setConfirmed(true);
      onConfirmed(fact.fact_key);
    } else {
      setErr("Could not confirm fact.");
    }
  }

  return (
    <div
      style={{
        border: `1px solid ${confirmed ? "#bbf7d0" : "#e5e7eb"}`,
        borderRadius: 8,
        padding: "10px 14px",
        marginBottom: 8,
        background: confirmed ? "#f0fdf4" : "#fff",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>
            {fact.fact_key.replace(/_/g, " ")}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#111827", marginBottom: 4 }}>
            {fact.numeric_value !== null ? (
              <>
                {fact.numeric_value}
                {fact.unit ? <span style={{ fontWeight: 400, fontSize: 12, color: "#6b7280", marginLeft: 4 }}>{fact.unit}</span> : null}
              </>
            ) : (
              <span style={{ color: "#9ca3af" }}>No numeric value</span>
            )}
          </div>
          <ConfidenceBar value={fact.confidence} />
          {fact.source_text && (
            <div
              style={{
                marginTop: 6,
                fontSize: 11,
                color: "#6b7280",
                fontStyle: "italic",
                background: "#f9fafb",
                borderRadius: 4,
                padding: "4px 8px",
                borderLeft: "2px solid #d1d5db",
              }}
            >
              {fact.source_text.length > 120
                ? fact.source_text.slice(0, 120) + "…"
                : fact.source_text}
            </div>
          )}
        </div>
        <div style={{ flexShrink: 0 }}>
          {confirmed ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#16a34a", fontSize: 12 }}>
              <CheckCircle2 size={14} /> Confirmed
            </span>
          ) : (
            <button
              onClick={() => void confirm()}
              disabled={confirming}
              style={{
                fontSize: 12,
                padding: "4px 10px",
                background: confirming ? "#e5e7eb" : "#2563eb",
                color: confirming ? "#6b7280" : "#fff",
                border: "none",
                borderRadius: 4,
                cursor: confirming ? "not-allowed" : "pointer",
              }}
            >
              {confirming ? "Confirming…" : "Confirm"}
            </button>
          )}
        </div>
      </div>
      {err && <div style={{ color: "#dc2626", fontSize: 11, marginTop: 4 }}>{err}</div>}
    </div>
  );
}

function DocumentUpload({ projectId }: { projectId: string }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const [confirmedKeys, setConfirmedKeys] = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    const r = await api.documents.upload(projectId, file);
    setUploading(false);
    if (r.kind === "ok") {
      setUploadResult(r.data);
    } else if (r.kind === "notBuilt") {
      setUploadError("Document upload endpoint not yet available on this server.");
    } else if (r.kind === "auth") {
      setUploadError("Sign in required.");
    } else if (r.kind === "error") {
      setUploadError(r.message);
    } else {
      setUploadError("Could not reach server.");
    }
    if (fileRef.current) fileRef.current.value = "";
  }

  function handleConfirmed(factKey: string) {
    setConfirmedKeys((prev) => new Set([...prev, factKey]));
  }

  const facts = uploadResult?.extracted_facts ?? [];

  return (
    <div style={{ padding: "0 0 24px" }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 600 }}>Documents</h3>

      <label
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          border: "2px dashed #d1d5db",
          borderRadius: 10,
          padding: "24px 16px",
          cursor: "pointer",
          background: uploading ? "#f9fafb" : "#fff",
          transition: "border-color 0.15s",
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files?.[0];
          if (file && fileRef.current) {
            const dt = new DataTransfer();
            dt.items.add(file);
            fileRef.current.files = dt.files;
            fileRef.current.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }}
      >
        {uploading ? (
          <>
            <RefreshCw size={24} style={{ color: "#2563eb", animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: 13, color: "#6b7280" }}>Uploading…</span>
          </>
        ) : (
          <>
            <Sparkles size={24} style={{ color: "#9ca3af" }} />
            <span style={{ fontSize: 14, fontWeight: 500 }}>
              Upload a drawing or document
            </span>
            <span style={{ fontSize: 12, color: "#9ca3af" }}>
              PDF, DOCX, TXT, DXF — click or drag and drop
            </span>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.dxf"
          style={{ display: "none" }}
          onChange={(e) => void handleFile(e)}
        />
      </label>

      {uploadError && (
        <div
          style={{
            marginTop: 10,
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#b91c1c",
            fontSize: 13,
          }}
        >
          {uploadError}
        </div>
      )}

      {uploadResult && (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 12,
              fontSize: 14,
              color: "#374151",
            }}
          >
            <BookOpen size={16} />
            <span style={{ fontWeight: 500 }}>{uploadResult.filename}</span>
            <span style={{ color: "#6b7280" }}>·</span>
            <span style={{ color: "#6b7280" }}>
              {facts.length} fact{facts.length !== 1 ? "s" : ""} extracted
            </span>
            {confirmedKeys.size > 0 && (
              <>
                <span style={{ color: "#6b7280" }}>·</span>
                <span style={{ color: "#16a34a" }}>{confirmedKeys.size} confirmed</span>
              </>
            )}
          </div>

          {facts.length === 0 && (
            <div style={{ color: "#6b7280", fontSize: 13 }}>
              No measurable facts were extracted from this document.
            </div>
          )}

          {facts.map((fact) => (
            <FactCard
              key={fact.fact_key}
              fact={{ ...fact, confirmed: confirmedKeys.has(fact.fact_key) }}
              docId={uploadResult.document_id}
              onConfirmed={handleConfirmed}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── WizardShell ── */

function WizardShell({
  wizard,
  onClose,
}: {
  wizard: WizardState;
  onClose: () => void;
}) {
  const [state, setState] = useState<WizardState>(wizard);

  const setStep = (step: WizardStep) => setState((s) => ({ ...s, step }));

  const steps = ["Address & property", "Proposal details", "Confirm"] as const;

  return (
    <div className="view" style={{ paddingTop: 16 }}>
      {/* stepper */}
      <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 20, maxWidth: 640, margin: "0 auto 20px" }}>
        {steps.map((label, idx) => {
          const stepNum = (idx + 1) as WizardStep;
          const isCurrent = state.step === stepNum;
          const isDone = state.step > stepNum;
          return (
            <div key={idx} style={{ display: "flex", alignItems: "center", flex: idx < 2 ? 1 : undefined }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 99, display: "flex", alignItems: "center", justifyContent: "center",
                  background: isCurrent ? "var(--green-900)" : isDone ? "var(--green)" : "var(--paper)",
                  border: isCurrent || isDone ? "none" : "1.5px solid var(--line)",
                  color: isCurrent || isDone ? "#fff" : "var(--ink-faint)",
                  fontSize: ".75rem", fontWeight: 800,
                }}>
                  {isDone ? <Icon name="check_circle" /> : stepNum}
                </div>
                <div style={{ fontSize: ".65rem", fontWeight: 700, color: isCurrent ? "var(--green-800)" : "var(--ink-faint)", whiteSpace: "nowrap" }}>
                  {label}
                </div>
              </div>
              {idx < 2 && (
                <div style={{ flex: 1, height: 2, background: isDone ? "var(--green)" : "var(--line)", margin: "0 6px 16px" }} />
              )}
            </div>
          );
        })}
      </div>

      {state.step === 1 && state.property && (
        <AddressResolverPanel
          property={state.property}
          onContinue={() => setStep(2)}
          onBack={onClose}
        />
      )}

      {state.step === 1 && !state.property && (
        <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
          <div className="state"><Icon name="error" /><span>Property data unavailable. Address was submitted but no profile returned.</span></div>
          <div style={{ marginTop: 12 }}>
            <button className="btn alt" onClick={onClose}>← Back</button>
          </div>
        </div>
      )}

      {state.step === 2 && (
        <ProposalForm
          projectId={state.projectId}
          initial={state.proposal}
          onSaved={(saved, data) => setState((s) => ({ ...s, savedProposal: saved, proposal: data, step: 3 }))}
          onBack={() => setStep(1)}
        />
      )}

      {state.step === 3 && (
        <ConfirmationStep
          projectId={state.projectId}
          address={state.address}
          property={state.property}
          proposal={state.proposal}
          onBack={() => setStep(2)}
          onStart={() => {
            // future: navigate to compliance step
          }}
        />
      )}
    </div>
  );
}

/* ── status bar (live health/ready) ── */

function StatusBar() {
  const [health, setHealth] = useState<ApiResult<HealthInfo> | null>(null);
  const [ready, setReady] = useState<ApiResult<Record<string, unknown>> | null>(null);
  useEffect(() => {
    void api.health().then(setHealth);
    void api.ready().then(setReady);
  }, []);
  const pill = (label: string, r: ApiResult<unknown> | null) => {
    const ok = r?.kind === "ok";
    const cls = r === null ? "pill dim" : ok ? "pill ok" : "pill bad";
    const icon = r === null ? "sync" : ok ? "check_circle" : "error";
    return (
      <span className={cls}>
        <Icon name={icon} />
        {label}
      </span>
    );
  };
  const version = health?.kind === "ok" ? health.data.version : undefined;
  return (
    <div className="statusbar">
      {pill("api", health)}
      {pill("ready", ready)}
      <span className="grow" />
      <span>LotFile · /api/v1{version ? ` · v${version}` : ""} · advisory only — a reviewer signs off, never the model</span>
    </div>
  );
}

/* ── one-box home ── */

function Home({
  authed,
  guestUsage,
  onGuestAddressStart,
  onGuestChatStart,
  onNeedSignIn,
  onShowPaywall,
}: {
  authed: boolean;
  guestUsage: GuestUsage;
  onGuestAddressStart: (address: string) => boolean;
  onGuestChatStart: () => boolean;
  onNeedSignIn: () => void;
  onShowPaywall: (feature: GuestFeature) => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [webOn, setWebOn] = useState(false);
  const [recents, setRecents] = useState<ProjectSummary[]>([]);
  const [wizard, setWizard] = useState<WizardState | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authed) {
      setRecents(guestProjectList(guestUsage).slice(0, 2));
      return;
    }
    void api.projects().then((r) => setRecents(projectList(r).slice(0, 2)));
  }, [authed, guestUsage]);
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [msgs]);

  const push = (m: Msg) => setMsgs((prev) => [...prev, m]);

  const pushGuestAddressPreview = useCallback((address: string, mode: "guest" | "fallback") => {
    const label = mode === "guest" ? "Guest address scan" : "Preview address scan";
    const chips = authed
      ? ["preview fallback", "address-first dossier", "approved sources only"]
      : [
          `address ${Math.min(guestUsage.addressChecks + 1, GUEST_ADDRESS_LIMIT)}/${GUEST_ADDRESS_LIMIT}`,
          "address-first dossier",
          "approved sources only",
        ];
    push({
      role: "a",
      tone: "warn",
      text: `Preview only — not a source-backed answer. ${label} for ${address}: in the full app I can build the dossier shell, run the address-first workflow, and line the property up with parcel, council, zoning, overlays, source-library search, drawing upload, and Tier-1 check readiness once the live API has authoritative data. Sign in to run the real check.`,
      chips: ["guest preview", ...chips],
    });
    push({
      role: "a",
      text: "No final compliance claim is made in guest mode. The app will cite approved source versions, refuse unsupported regulatory answers, and require confirmed measurements plus human signoff before anything is treated as submission-ready.",
      chips: ["cite-or-refuse", "measurements must be confirmed", "human signoff"],
    });
  }, [authed, guestUsage.addressChecks]);

  const pushGuestChatPreview = useCallback((question: string) => {
    const lower = question.toLowerCase();
    let text = "In the full app I search the approved WA source library first, answer only when the source library supports it, attach citations, and keep unsupported regulatory claims out of the response.";
    if (lower.includes("drawing") || lower.includes("da") || lower.includes("application")) {
      text = "For a DA workflow I can help organise the drawing pack, pull out missing-evidence questions, and draft council-ready responses. The exact required documents still need to come from the approved council/state source library before I present them as requirements.";
    } else if (lower.includes("zoning") || lower.includes("r20") || lower.includes("r-code") || lower.includes("rcode")) {
      text = "For zoning and R-Code questions I first resolve the address, then retrieve approved source clauses for the council and WA planning context. I will not invent numeric thresholds or compliance outcomes when the approved source library cannot support them.";
    } else if (lower.includes("setback") || lower.includes("site cover") || lower.includes("open space")) {
      text = "For Tier-1 checks I compare confirmed proposal measurements against approved, cited rules. If a measurement or rule is missing, the result stays missing-info or needs-human-review instead of becoming a guess.";
    }
    if (webOn) {
      text += " Web search can help discover public context, but approved sources still control regulatory answers.";
    }
    push({
      role: "a",
      tone: "warn",
      text: `Preview only — not a source-backed answer. ${text} Sign in to ask against the live source library.`,
      chips: authed
        ? ["guest preview", "library-first", "citations required"]
        : [
            `chat ${Math.min(guestUsage.chatMessages + 1, GUEST_CHAT_LIMIT)}/${GUEST_CHAT_LIMIT}`,
            "guest preview",
            "not a real answer",
          ],
    });
  }, [authed, guestUsage.chatMessages, webOn]);

  const startCheck = useCallback(async (address: string) => {
    if (!authed && !onGuestAddressStart(address)) {
      push({ role: "a", tone: "note", text: guestLimitMessage("address"), action: { label: "Unlock more", run: () => onShowPaywall("address") } });
      return;
    }
    const created = await api.createProject(address);
    if (created.kind === "ok") {
      const id = created.data.id;
      push({ role: "a", tone: "note", text: `Project created for ${address}. Resolving the property…`, chips: ["POST /projects · live"] });
      const resolved = await api.resolveAddress(id, address);
      if (resolved.kind === "ok") {
        // Launch the Stage 2 wizard
        setWizard({
          step: 1,
          projectId: id,
          address,
          property: resolved.data,
          proposal: {},
          savedProposal: null,
        });
      } else if (!authed && (resolved.kind === "auth" || resolved.kind === "notBuilt" || resolved.kind === "missing")) {
        pushGuestAddressPreview(address, "guest");
      } else if (resolved.kind === "notBuilt") {
        // resolveAddress not built yet — show wizard with null property so user can still enter proposal
        push({ role: "a", tone: "note", text: "Property resolution not yet available. You can still enter proposal details.", chips: ["resolve-address · not built"] });
        setWizard({
          step: 1,
          projectId: id,
          address,
          property: null,
          proposal: {},
          savedProposal: null,
        });
      } else if (resolved.kind === "auth") {
        onNeedSignIn();
      } else {
        push({ role: "a", tone: "warn", text: `Project saved, but resolving failed: ${resolved.kind === "error" ? resolved.message : resolved.kind}.` });
      }
    } else if (created.kind === "notBuilt") {
      pushGuestAddressPreview(address, authed ? "fallback" : "guest");
    } else if (created.kind === "auth") {
      if (!authed) {
        pushGuestAddressPreview(address, "guest");
      } else {
        push({
          role: "a",
          tone: "note",
          text: "Sign in first.",
          action: { label: "Go to sign in", run: onNeedSignIn },
        });
      }
    } else if (created.kind === "down") {
      pushGuestAddressPreview(address, authed ? "fallback" : "guest");
    } else {
      pushGuestAddressPreview(address, authed ? "fallback" : "guest");
    }
  }, [authed, onGuestAddressStart, onNeedSignIn, onShowPaywall, pushGuestAddressPreview]);

  const send = useCallback(async () => {
    const el = inputRef.current;
    const t = el?.value.trim() ?? "";
    if (!t || busy) return;
    if (el) el.value = "";
    setBusy(true);
    push({ role: "q", text: t });
    if (looksLikeAddress(t)) {
      await startCheck(t);
    } else {
      if (!authed && !onGuestChatStart()) {
        push({ role: "a", tone: "note", text: guestLimitMessage("chat"), action: { label: "Unlock more", run: () => onShowPaywall("chat") } });
        setBusy(false);
        return;
      }
      const r = await api.ask(t, { web: webOn });
      if (r.kind === "ok") {
        const d: ChatReply = r.data;
        const chips = (d.citations ?? [])
          .map(citationChip)
          .filter((chip) => chip.length > 0);
        push({
          role: "a",
          text: d.answer ?? "I couldn't get an answer just now.",
          chips: chips.length ? chips : undefined,
        });
      } else if (!authed && (r.kind === "auth" || r.kind === "missing" || r.kind === "notBuilt" || r.kind === "down")) {
        pushGuestChatPreview(t);
      } else if (r.kind === "missing" || r.kind === "notBuilt") {
        pushGuestChatPreview(t);
      } else if (r.kind === "auth") {
        push({ role: "a", tone: "note", text: "Sign in to ask questions.", action: { label: "Go to sign in", run: onNeedSignIn } });
      } else {
        push({ role: "a", tone: "warn", text: r.kind === "down" ? "Can't reach the API right now." : `Ask failed (${r.message}).` });
      }
    }
    setBusy(false);
  }, [authed, busy, webOn, startCheck, onGuestChatStart, onNeedSignIn, onShowPaywall, pushGuestChatPreview]);

  const fill = (t: string) => {
    if (inputRef.current) {
      inputRef.current.value = t;
      void send();
    }
  };

  if (wizard) {
    return (
      <>
        <div style={{ flex: "none", width: "100%", maxWidth: "min(760px,100%)", padding: "12px 0 0", display: "flex", alignItems: "center", gap: 10 }}>
          <button
            className="btn alt"
            style={{ fontSize: ".75rem", padding: "6px 12px" }}
            onClick={() => setWizard(null)}
          >
            ← Back to home
          </button>
          <span style={{ fontSize: ".78rem", color: "var(--ink-faint)", fontWeight: 600 }}>
            {wizard.address}
          </span>
        </div>
        <WizardShell wizard={wizard} onClose={() => setWizard(null)} />
      </>
    );
  }

  return (
    <>
      <div className={`conv${msgs.length ? " active" : ""}`}>
        {msgs.length === 0 && (
          <div className="greet">
            <h1>Where do we start?</h1>
            <p>Paste a property address to start a check — or just ask a question.</p>
          </div>
        )}
        {msgs.length > 0 && (
          <div className="thread" ref={threadRef}>
            {msgs.map((m, i) =>
              m.role === "q" ? (
                <div key={i} className="q">{m.text}</div>
              ) : (
                <div key={i} className={`a${m.tone ? ` ${m.tone}` : ""}`}>
                  {m.text}
                  {m.chips && (
                    <div className="src">
                      {m.chips.map((c, j) => (
                        <span key={j} className="srcchip"><Icon name="verified" />{c}</span>
                      ))}
                    </div>
                  )}
                  {m.action && (
                    <div className="act">
                      <button onClick={m.action.run}>{m.action.label}</button>
                    </div>
                  )}
                </div>
              ),
            )}
          </div>
        )}
        <div className="onebox">
          <textarea
            ref={inputRef}
            placeholder="Type an address… or ask anything about WA planning"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
          />
          <div className="belt">
            <span className="chip on"><Icon name="verified" />WA library</span>
            <button className={`chip${webOn ? " on" : ""}`} onClick={() => setWebOn(!webOn)}>
              <Icon name="public" />Web
            </button>
            {!authed && (
              <span className="chip guest"><Icon name="sparkles" />Guest {guestUsage.addressChecks}/{GUEST_ADDRESS_LIMIT} searches · {guestUsage.chatMessages}/{GUEST_CHAT_LIMIT} chats</span>
            )}
            <span className="grow" />
            <button className="go" onClick={() => void send()} disabled={busy}><Icon name="arrow_upward" /></button>
          </div>
        </div>
        {msgs.length === 0 && (
          <div className="hints">
            <button className="addr" onClick={() => fill("42 Banksia St, Fremantle")}><Icon name="location_on" />Try an address</button>
            <button onClick={() => fill("What does R20 zoning allow?")}><Icon name="forum" />What does R20 zoning allow?</button>
            <button onClick={() => fill("What drawings do I need for a DA?")}><Icon name="forum" />What drawings do I need for a DA?</button>
          </div>
        )}
      </div>
      {recents.length > 0 && (
        <div className="recent">
          <h2>Recent</h2>
          <div className="strip">
            {recents.map((p) => (
              <button key={p.id} className="proj">
                <Icon name="home_work" />
                <span className="t">{p.name ?? p.address ?? p.id}<small>{p.created_at ?? ""}</small></span>
              </button>
            ))}
          </div>
        </div>
      )}
      <StatusBar />
    </>
  );
}

/* ── projects view ── */

function Projects({
  authed,
  guestUsage,
  onNeedSignIn,
}: {
  authed: boolean;
  guestUsage: GuestUsage;
  onNeedSignIn: () => void;
}) {
  const [result, setResult] = useState<ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }> | null>(null);
  useEffect(() => {
    if (!authed) {
      setResult(null);
      return;
    }
    void api.projects().then(setResult);
  }, [authed]);
  const items = result ? projectList(result) : [];
  const guestItems = guestProjectList(guestUsage);
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="home_work" />Projects</h3>
        {!authed && (
          <>
            <p>Guest checks are saved only on this device. Sign in when you want saved projects, uploads, exports, and reviewer signoff.</p>
            {guestItems.length === 0 && <div className="state"><Icon name="sparkles" /><span>No guest checks yet — start one from Home by pasting an address.</span></div>}
            {guestItems.length > 0 && (
              <div className="strip" style={{ marginTop: 10 }}>
                {guestItems.map((p) => (
                  <button key={p.id} className="proj">
                    <Icon name="home_work" />
                    <span className="t">{p.address ?? p.id}<small>Guest preview · {p.created_at ?? ""}</small></span>
                  </button>
                ))}
              </div>
            )}
            <div className="field">
              <button className="btn" onClick={onNeedSignIn}>Sign in to save projects</button>
            </div>
          </>
        )}
        {authed && result === null && <p>Loading…</p>}
        {result?.kind === "ok" && items.length === 0 && <p>No projects yet — start one from Home by pasting an address.</p>}
        {result?.kind === "ok" && items.length > 0 && (
          <div className="strip" style={{ marginTop: 10 }}>
            {items.map((p) => (
              <button key={p.id} className="proj">
                <Icon name="home_work" />
                <span className="t">{p.name ?? p.address ?? p.id}<small>{p.created_at ?? ""}</small></span>
              </button>
            ))}
          </div>
        )}
        {result?.kind === "notBuilt" && (
          <div className="state"><Icon name="construction" /><span>Project creation is coming soon — this screen wires itself up automatically when it lands.</span></div>
        )}
        {result?.kind === "auth" && (
          <div className="state"><Icon name="lock" /><span>Sign in to see your projects. <button className="btn alt" style={{ marginLeft: 8 }} onClick={onNeedSignIn}>Go to sign in</button></span></div>
        )}
        {(result?.kind === "down" || result?.kind === "error" || result?.kind === "missing") && (
          <div className="state"><Icon name="error" /><span>Couldn't load projects ({result.kind}).</span></div>
        )}
      </div>
    </div>
  );
}

/* ── library view ── */

function Library({ onNeedSignIn }: { onNeedSignIn: () => void }) {
  const [result, setResult] = useState<ApiResult<unknown> | null>(null);
  useEffect(() => { void api.rules().then(setResult); }, []);
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="menu_book" />Approved library</h3>
        <p>R-Codes, local planning policies and council checklists — versioned, citable, and the only sources LotFile answers from.</p>
        {result?.kind === "ok" && (
          <div className="state okay"><Icon name="check_circle" /><span>The approved source library is being loaded and reviewed.</span></div>
        )}
        {result?.kind === "auth" && (
          <div className="state"><Icon name="lock" /><span>Sign in to browse the library. <button className="btn alt" style={{ marginLeft: 8 }} onClick={onNeedSignIn}>Go to sign in</button></span></div>
        )}
        {result?.kind === "notBuilt" && (
          <div className="state"><Icon name="construction" /><span>Library browsing is coming soon.</span></div>
        )}
        {(result?.kind === "down" || result?.kind === "error" || result?.kind === "missing") && result !== null && (
          <div className="state"><Icon name="error" /><span>Couldn't reach the library ({result.kind}).</span></div>
        )}
      </div>
    </div>
  );
}

/* ── settings / auth ── */

function Settings({ session, refresh }: { session: ApiResult<SessionInfo> | null; refresh: () => void }) {
  const authed = session?.kind === "ok";
  const who = authed ? (session.data.email ?? session.data.user?.email ?? "signed in") : null;
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="badge" />Account</h3>
        {authed ? (
          <>
            <p>Signed in as <b>{String(who)}</b>.</p>
            <div className="field">
              <button className="btn alt" onClick={() => { void api.logout().then(refresh); }}>Sign out</button>
            </div>
          </>
        ) : (
          <DevLoginForm variant="panel" onSignedIn={refresh} />
        )}
      </div>
      <div className="panel">
        <h3><Icon name="gavel" />Ground rules</h3>
        <p>Verdicts are likely-pass / needs-review / missing-info — never pass/fail. Every regulatory claim is cited to an approved source version or flagged as unsupported. A human reviewer signs off; the model never does.</p>
      </div>
    </div>
  );
}

/* ── dev username/password form (used in place of magic link while DEV_LOGIN) ── */

function DevLoginForm({ variant, onSignedIn }: { variant: "modal" | "panel"; onSignedIn: () => void }) {
  const [username, setUsername] = useState("jemma");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);

  const submit = useCallback(async () => {
    if (busy || !username.trim() || !password) return;
    setBusy(true);
    setErr(false);
    const r = await api.devLogin(username.trim(), password);
    setBusy(false);
    if (r.kind === "ok") onSignedIn();
    else setErr(true);
  }, [busy, username, password, onSignedIn]);

  const inputClass = variant === "modal" ? "modal-input" : undefined;
  const fields = (
    <>
      <input
        className={inputClass}
        placeholder="username"
        autoComplete="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") void submit(); }}
      />
      <input
        className={inputClass}
        type="password"
        placeholder="password"
        autoComplete="current-password"
        autoFocus={variant === "modal"}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") void submit(); }}
      />
      <button className={variant === "modal" ? "btn block" : "btn"} onClick={() => void submit()} disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </>
  );

  return (
    <>
      {variant === "modal"
        ? fields
        : <div className="field" style={{ flexDirection: "column", alignItems: "stretch", gap: 8 }}>{fields}</div>}
      {err && (
        <p className={variant === "modal" ? "modal-err" : undefined} style={variant === "panel" ? { color: "#b00", marginTop: 8 } : undefined}>
          Wrong username or password.
        </p>
      )}
    </>
  );
}

/* ── sign in / create account popup ── */

function SignInModal({ onClose, onSignedIn }: { onClose?: () => void; onSignedIn: () => void }) {
  return (
    <div className="modal-backdrop" onClick={() => onClose?.()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Sign in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-logo">Lot<span>File</span></div>
        <h2>Sign in</h2>
        <DevLoginForm variant="modal" onSignedIn={onSignedIn} />
      </div>
    </div>
  );
}

function PaywallModal({
  state,
  onClose,
  onSignIn,
}: {
  state: PaywallState;
  onClose: () => void;
  onSignIn: () => void;
}) {
  const copy = paywallCopy(state.feature);
  const cta = CHECKOUT_URL ? "Unlock more checks" : "Sign in to continue";
  const upgrade = () => {
    if (CHECKOUT_URL) {
      window.location.assign(CHECKOUT_URL);
      return;
    }
    onSignIn();
  };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal paywall" role="dialog" aria-modal="true" aria-label={copy.title} onClick={(e) => e.stopPropagation()}>
        <div className="modal-logo">Lot<span>File</span></div>
        <div className="paywall-icon"><Icon name={state.feature === "address" ? "location_on" : "forum"} /></div>
        <h2>{copy.title}</h2>
        <p>{copy.body}</p>
        <div className="usage-meter" aria-label={`Guest usage ${state.used} of ${state.limit}`}>
          <span style={{ width: `${Math.min(100, (state.used / state.limit) * 100)}%` }} />
        </div>
        <div className="plans">
          <div>
            <b>Guest</b>
            <span>{GUEST_ADDRESS_LIMIT} address checks · {GUEST_CHAT_LIMIT} chat questions</span>
          </div>
          <div>
            <b>Unlocked</b>
            <span>Saved dossiers, more searches, uploads, exports, reviewer workflow</span>
          </div>
        </div>
        <button className="btn block" onClick={upgrade}>
          <Icon name={CHECKOUT_URL ? "credit_card" : "badge"} />{cta}
        </button>
        {CHECKOUT_URL && <button className="btn alt block" onClick={onSignIn}>Sign in instead</button>}
        <button className="modal-skip" onClick={onClose}>Not now</button>
      </div>
    </div>
  );
}

/* ── rules view ── */

function lifecycleBadge(status: string) {
  const map: Record<string, { bg: string; color: string }> = {
    auto_accepted: { bg: "var(--mint)", color: "var(--green-800)" },
    approved: { bg: "#EFF6FF", color: "#1D4ED8" },
    rejected: { bg: "#FEF2F2", color: "#B91C1C" },
    stale: { bg: "#EFF1F1", color: "var(--ink-soft)" },
  };
  const s = map[status] ?? { bg: "#EFF1F1", color: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "3px 9px", borderRadius: 99, background: s.bg, color: s.color, display: "inline-block" }}>
      {status}
    </span>
  );
}

function reviewBadge(status: string) {
  const map: Record<string, { bg: string; color: string }> = {
    pending: { bg: "#FEF9C3", color: "#92400E" },
    accepted: { bg: "var(--mint)", color: "var(--green-800)" },
    rejected: { bg: "#FEF2F2", color: "#B91C1C" },
    promoted: { bg: "#EFF6FF", color: "#1D4ED8" },
  };
  const s = map[status] ?? { bg: "#EFF1F1", color: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "3px 9px", borderRadius: 99, background: s.bg, color: s.color, display: "inline-block" }}>
      {status}
    </span>
  );
}

function formatValueJson(v: number | object | null): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return String(v);
  return JSON.stringify(v);
}

function RuleDetail({ rule, onBack }: { rule: RuleSummary; onBack: () => void }) {
  return (
    <div className="panel" style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "5px 10px" }} onClick={onBack}>← Back</button>
        <span style={{ fontWeight: 700, fontSize: ".9rem" }}>{rule.rule_key}</span>
        {lifecycleBadge(rule.lifecycle_status)}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: ".83rem" }}>
        {[
          ["ID", rule.id],
          ["Rule key", rule.rule_key],
          ["Rule type", rule.rule_type],
          ["Operator", rule.operator],
          ["Value", formatValueJson(rule.value_json)],
          ["Unit", rule.unit ?? "—"],
          ["Confidence", `${Math.round(rule.confidence * 100)}%`],
          ["Lifecycle status", rule.lifecycle_status],
          ["Clause ID", rule.clause_id ?? "—"],
          ["Source version ID", rule.source_version_id ?? "—"],
          ["Created at", rule.created_at],
        ].map(([label, val]) => (
          <div key={label} style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--line)", padding: "4px 0" }}>
            <span style={{ color: "var(--ink-soft)", minWidth: 140, flexShrink: 0 }}>{label}</span>
            <span style={{ fontWeight: 500, wordBreak: "break-all" }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CandidateDetail({ candidate, onBack }: { candidate: CandidateSummary; onBack: () => void }) {
  const validators = candidate.validator_results_json
    ? Object.entries(candidate.validator_results_json)
    : [];
  return (
    <div className="panel" style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "5px 10px" }} onClick={onBack}>← Back</button>
        <span style={{ fontWeight: 700, fontSize: ".9rem" }}>{candidate.rule_key ?? "pending"}</span>
        {reviewBadge(candidate.review_status)}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: ".83rem" }}>
        {[
          ["ID", candidate.id],
          ["Rule key", candidate.rule_key ?? "—"],
          ["Operator", candidate.operator ?? "—"],
          ["Value", formatValueJson(candidate.value_json)],
          ["Unit", candidate.unit ?? "—"],
          ["Confidence", candidate.confidence !== null ? `${Math.round(candidate.confidence * 100)}%` : "—"],
          ["Review status", candidate.review_status],
          ["Extraction pass", candidate.extraction_pass !== null ? String(candidate.extraction_pass) : "—"],
          ["Clause ID", candidate.clause_id ?? "—"],
          ["Auto promoted at", candidate.auto_promoted_at ?? "—"],
        ].map(([label, val]) => (
          <div key={label} style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--line)", padding: "4px 0" }}>
            <span style={{ color: "var(--ink-soft)", minWidth: 140, flexShrink: 0 }}>{label}</span>
            <span style={{ fontWeight: 500, wordBreak: "break-all" }}>{val}</span>
          </div>
        ))}
      </div>
      {candidate.quote && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", marginBottom: 4 }}>Source quote</div>
          <pre style={{ background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 10, padding: "10px 14px", fontSize: ".78rem", whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0 }}>
            {candidate.quote}
          </pre>
        </div>
      )}
      {validators.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", marginBottom: 6 }}>Validator results</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {validators.map(([name, result]) => (
              <div key={name} style={{ display: "flex", gap: 8, fontSize: ".82rem", padding: "5px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ fontSize: ".85rem" }}>{result.pass ? "✓" : "✗"}</span>
                <span style={{ color: result.pass ? "var(--green-800)" : "#B91C1C", fontWeight: 700, minWidth: 140, flexShrink: 0 }}>{name}</span>
                <span style={{ color: "var(--ink-soft)" }}>{result.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RulesView() {
  const [tab, setTab] = useState<"rules" | "candidates">("rules");
  const [rules, setRules] = useState<ApiResult<RuleSummary[]> | null>(null);
  const [candidates, setCandidates] = useState<ApiResult<CandidateSummary[]> | null>(null);
  const [selectedRule, setSelectedRule] = useState<RuleSummary | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateSummary | null>(null);

  useEffect(() => {
    void api.listRules({ limit: 100 }).then(setRules);
  }, []);

  useEffect(() => {
    void api.listCandidates({ limit: 100 }).then(setCandidates);
  }, []);

  const th: React.CSSProperties = {
    padding: "7px 10px",
    textAlign: "left",
    fontSize: ".72rem",
    fontWeight: 700,
    color: "var(--ink-soft)",
    borderBottom: "2px solid var(--line)",
    whiteSpace: "nowrap",
  };
  const td: React.CSSProperties = {
    padding: "7px 10px",
    fontSize: ".8rem",
    borderBottom: "1px solid var(--line)",
    verticalAlign: "middle",
  };

  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="gavel" />Rules</h3>
        <div style={{ display: "flex", gap: 0, marginBottom: 16, borderBottom: "2px solid var(--line)" }}>
          {(["rules", "candidates"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: "none",
                border: "none",
                borderBottom: tab === t ? "2px solid var(--green-900)" : "2px solid transparent",
                marginBottom: -2,
                padding: "8px 18px",
                fontSize: ".83rem",
                fontWeight: tab === t ? 700 : 500,
                color: tab === t ? "var(--green-900)" : "var(--ink-soft)",
                cursor: "pointer",
              }}
            >
              {t === "rules" ? "Accepted Rules" : "Candidates"}
            </button>
          ))}
        </div>

        {tab === "rules" && (
          <>
            {selectedRule ? (
              <RuleDetail rule={selectedRule} onBack={() => setSelectedRule(null)} />
            ) : (
              <>
                {rules === null && <p>Loading…</p>}
                {rules?.kind === "auth" && <div className="state"><Icon name="lock" /><span>Sign in to view rules.</span></div>}
                {rules?.kind === "notBuilt" && <div className="state"><Icon name="construction" /><span>Rules endpoint not yet available.</span></div>}
                {rules?.kind === "missing" && <div className="state"><Icon name="construction" /><span>Rules endpoint not found.</span></div>}
                {(rules?.kind === "error" || rules?.kind === "down") && (
                  <div className="state"><Icon name="error" /><span>Could not load rules ({rules.kind}).</span></div>
                )}
                {rules?.kind === "ok" && rules.data.length === 0 && (
                  <div className="state"><Icon name="sparkles" /><span>No accepted rules yet.</span></div>
                )}
                {rules?.kind === "ok" && rules.data.length > 0 && (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={th}>Rule key</th>
                          <th style={th}>Operator</th>
                          <th style={th}>Value</th>
                          <th style={th}>Unit</th>
                          <th style={th}>Status</th>
                          <th style={th}>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rules.data.map((r) => (
                          <tr
                            key={r.id}
                            style={{ cursor: "pointer" }}
                            onClick={() => setSelectedRule(r)}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--paper)")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                          >
                            <td style={{ ...td, fontWeight: 600 }}>{r.rule_key}</td>
                            <td style={td}>{r.operator}</td>
                            <td style={td}>{formatValueJson(r.value_json)}</td>
                            <td style={td}>{r.unit ?? "—"}</td>
                            <td style={td}>{lifecycleBadge(r.lifecycle_status)}</td>
                            <td style={td}>{Math.round(r.confidence * 100)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {tab === "candidates" && (
          <>
            {selectedCandidate ? (
              <CandidateDetail candidate={selectedCandidate} onBack={() => setSelectedCandidate(null)} />
            ) : (
              <>
                {candidates === null && <p>Loading…</p>}
                {candidates?.kind === "auth" && <div className="state"><Icon name="lock" /><span>Sign in to view candidates.</span></div>}
                {candidates?.kind === "notBuilt" && <div className="state"><Icon name="construction" /><span>Candidates endpoint not yet available.</span></div>}
                {candidates?.kind === "missing" && <div className="state"><Icon name="construction" /><span>Candidates endpoint not found.</span></div>}
                {(candidates?.kind === "error" || candidates?.kind === "down") && (
                  <div className="state"><Icon name="error" /><span>Could not load candidates ({candidates.kind}).</span></div>
                )}
                {candidates?.kind === "ok" && candidates.data.length === 0 && (
                  <div className="state"><Icon name="sparkles" /><span>No candidates yet.</span></div>
                )}
                {candidates?.kind === "ok" && candidates.data.length > 0 && (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={th}>Rule key</th>
                          <th style={th}>Quote (excerpt)</th>
                          <th style={th}>Status</th>
                          <th style={th}>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidates.data.map((c) => (
                          <tr
                            key={c.id}
                            style={{ cursor: "pointer" }}
                            onClick={() => setSelectedCandidate(c)}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--paper)")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                          >
                            <td style={{ ...td, fontWeight: 600 }}>{c.rule_key ?? <span style={{ color: "var(--ink-faint)" }}>pending</span>}</td>
                            <td style={{ ...td, maxWidth: 260 }}>
                              <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--ink-soft)" }}>
                                {c.quote ? c.quote.slice(0, 80) + (c.quote.length > 80 ? "…" : "") : "—"}
                              </span>
                            </td>
                            <td style={td}>{reviewBadge(c.review_status)}</td>
                            <td style={td}>{c.confidence !== null ? `${Math.round(c.confidence * 100)}%` : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ── app shell ── */

function App() {
  const [view, setView] = useState<View>("home");
  const [session, setSession] = useState<ApiResult<SessionInfo> | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [paywall, setPaywall] = useState<PaywallState | null>(null);
  const [guestUsage, setGuestUsage] = useState<GuestUsage>(() => loadGuestUsage());
  const [autoPrompted, setAutoPrompted] = useState(false);

  const refreshSession = useCallback(() => { void api.session().then(setSession); }, []);

  useEffect(() => {
    // magic-link verify deep link: /auth/magic-link/verify?token=…
    const url = new URL(window.location.href);
    if (url.pathname.startsWith("/auth/magic-link/verify")) {
      const token = url.searchParams.get("token");
      if (token) {
        void api.magicLinkVerify(token).then(() => {
          window.history.replaceState(null, "", "/");
          refreshSession();
        });
        return;
      }
    }
    refreshSession();
  }, [refreshSession]);

  const authed = session?.kind === "ok";

  useEffect(() => {
    // Greet unauthenticated visitors with the sign-in / create-account popup once
    // the session has resolved. Dismissable via the modal's "Continue as guest".
    if (session === null) return; // still loading
    if (authed || autoPrompted || signInOpen) return;
    setSignInOpen(true);
    setAutoPrompted(true);
  }, [session, authed, autoPrompted, signInOpen]);

  const goSignIn = useCallback(() => setSignInOpen(true), []);
  const showPaywall = useCallback((feature: GuestFeature) => {
    const used = feature === "address" ? guestUsage.addressChecks : guestUsage.chatMessages;
    const limit = feature === "address" ? GUEST_ADDRESS_LIMIT : GUEST_CHAT_LIMIT;
    setPaywall({ feature, used, limit });
  }, [guestUsage]);
  const openSignIn = useCallback(() => {
    setPaywall(null);
    setSignInOpen(true);
  }, []);
  const handleSignedIn = useCallback(() => {
    setSignInOpen(false);
    refreshSession();
  }, [refreshSession]);
  const startGuestAddress = useCallback((address: string): boolean => {
    if (authed) return true;
    if (guestUsage.addressChecks >= GUEST_ADDRESS_LIMIT) {
      setPaywall({ feature: "address", used: guestUsage.addressChecks, limit: GUEST_ADDRESS_LIMIT });
      return false;
    }
    const now = new Date().toISOString();
    const next = normalizeGuestUsage({
      ...guestUsage,
      addressChecks: guestUsage.addressChecks + 1,
      checks: [
        {
          id: `guest-${Date.now().toString(36)}`,
          address,
          createdAt: now,
          mode: "guest" as const,
        },
        ...guestUsage.checks,
      ].slice(0, 4),
      updatedAt: now,
    });
    saveGuestUsage(next);
    setGuestUsage(next);
    return true;
  }, [authed, guestUsage]);
  const startGuestChat = useCallback((): boolean => {
    if (authed) return true;
    if (guestUsage.chatMessages >= GUEST_CHAT_LIMIT) {
      setPaywall({ feature: "chat", used: guestUsage.chatMessages, limit: GUEST_CHAT_LIMIT });
      return false;
    }
    const next = normalizeGuestUsage({
      ...guestUsage,
      chatMessages: guestUsage.chatMessages + 1,
      updatedAt: new Date().toISOString(),
    });
    saveGuestUsage(next);
    setGuestUsage(next);
    return true;
  }, [authed, guestUsage]);

  const navItem = (v: View, icon: string, label: string) => (
    <button className={view === v ? "on" : ""} onClick={() => setView(v)}>
      <Icon name={icon} />{label}
    </button>
  );
  const tab = (v: View, icon: string, label: string) => (
    <button className={`tb${view === v ? " on" : ""}`} onClick={() => setView(v)}>
      <span className="ico"><Icon name={icon} /></span>{label}
    </button>
  );

  if (session === null) {
    return (
      <div className="boot">
        <div className="boot-logo">Lot<span>File</span></div>
        <div className="boot-spinner" aria-label="Loading" />
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="side">
        <div className="logo">Lot<span>File</span></div>
        <button className="newbtn" onClick={() => setView("home")}><Icon name="add_home_work" />New check</button>
        <nav className="nav">
          {navItem("home", "home", "Home")}
          {navItem("projects", "home_work", "Projects")}
          {navItem("library", "menu_book", "Library")}
          {navItem("rules", "gavel", "Rules")}
          {navItem("settings", "tune", "Settings")}
        </nav>
        <div className="grow" />
        <div className="user">
          <div className="avatar">{authed ? "OK" : "?"}</div>
          <div className="who">
            {authed ? String(session.data.email ?? session.data.user?.email ?? "Signed in") : "Guest mode"}
            <small>{authed ? String(session.data.role ?? session.data.user?.role ?? "") : `${GUEST_ADDRESS_LIMIT} searches · ${GUEST_CHAT_LIMIT} chats`}</small>
          </div>
        </div>
      </aside>

      <main className="stage">
        {view === "home" && (
          <Home
            authed={authed}
            guestUsage={guestUsage}
            onGuestAddressStart={startGuestAddress}
            onGuestChatStart={startGuestChat}
            onNeedSignIn={openSignIn}
            onShowPaywall={showPaywall}
          />
        )}
        {view === "projects" && <Projects authed={authed} guestUsage={guestUsage} onNeedSignIn={openSignIn} />}
        {view === "library" && <Library onNeedSignIn={goSignIn} />}
        {view === "rules" && <RulesView />}
        {view === "settings" && <Settings session={session} refresh={refreshSession} />}
      </main>

      <div className="tabbar">
        {tab("home", "home", "Home")}
        {tab("projects", "home_work", "Projects")}
        {tab("library", "menu_book", "Library")}
        {tab("rules", "gavel", "Rules")}
        {tab("settings", "tune", "Settings")}
      </div>

      {signInOpen && <SignInModal onClose={() => setSignInOpen(false)} onSignedIn={handleSignedIn} />}
      {paywall && (
        <PaywallModal
          state={paywall}
          onClose={() => setPaywall(null)}
          onSignIn={openSignIn}
        />
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
