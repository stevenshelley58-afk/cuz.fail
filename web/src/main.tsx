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
import { api, type ApiResult, type ChatReply, type HealthInfo, type ProjectSummary, type SessionInfo, type PropertyProfileResponse, type PropertyFactResponse, type ProposalRequest, type ProposalResponse } from "./api";
import "./styles.css";

/* ── dev login ──
   While building we swap the magic-link round-trip for a simple username/password.
   On by default under the Vite dev server (import.meta.env.DEV); force it on a built
   bundle with VITE_DEV_LOGIN=1. The server hard-disables /auth/dev-login in production. */
const DEV_LOGIN =
  Boolean((import.meta.env as Record<string, unknown>).DEV) ||
  (import.meta.env as Record<string, unknown>).VITE_DEV_LOGIN === "1";

const GUEST_USAGE_KEY = "lotfile_guest_usage_v1";
const GUEST_ADDRESS_LIMIT = envNumber("VITE_GUEST_ADDRESS_LIMIT", 2);
const GUEST_CHAT_LIMIT = envNumber("VITE_GUEST_CHAT_LIMIT", 8);
const CHECKOUT_URL = String((import.meta.env as Record<string, unknown>).VITE_CHECKOUT_URL ?? "").trim();

/* ── helpers ── */

type View = "home" | "projects" | "library" | "settings";
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
  address,
  property,
  proposal,
  onBack,
  onStart,
}: {
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

      <div style={{ background: "var(--paper)", border: "1px dashed var(--line)", borderRadius: 14, padding: "12px 14px", marginBottom: 16 }}>
        <div style={{ fontSize: ".78rem", fontWeight: 700, color: "var(--ink-soft)", marginBottom: 4 }}>Coming soon</div>
        <div style={{ fontSize: ".82rem", color: "var(--ink-soft)" }}>
          Tier-1 compliance checks (setbacks, site coverage, open space) will be available here once the compliance engine is built.
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn alt" onClick={onBack}>← Back to edit</button>
        <button className="btn" onClick={onStart} disabled>
          <Icon name="check_circle" />Start checking (coming soon)
        </button>
      </div>
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
          text: DEV_LOGIN
            ? "Sign in first with the local dev account."
            : "Sign in first — LotFile uses email magic links, no passwords.",
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
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState<string | null>(null);
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
        ) : DEV_LOGIN ? (
          <>
            <p>Local development login — magic links are off while we build.</p>
            <DevLoginForm variant="panel" onSignedIn={refresh} />
          </>
        ) : (
          <>
            <p>LotFile signs you in with an email magic link — no passwords.</p>
            <div className="field">
              <input
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { void api.magicLinkRequest(email).then((r) => setSent(r.kind)); } }}
              />
              <button className="btn" onClick={() => { void api.magicLinkRequest(email).then((r) => setSent(r.kind)); }}>Send link</button>
            </div>
            {sent === "ok" && <div className="state okay" style={{ marginTop: 10 }}><Icon name="mark_email_read" /><span>Link sent — check your email for your sign-in link.</span></div>}
            {sent && sent !== "ok" && <div className="state"><Icon name="error" /><span>Couldn't send the link just now — please try again in a moment.</span></div>}
          </>
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
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const submit = useCallback(async () => {
    const value = email.trim();
    if (!value || status === "sending") return;
    setStatus("sending");
    const r = await api.magicLinkRequest(value);
    setStatus(r.kind === "ok" ? "sent" : "error");
  }, [email, status]);

  return (
    <div className="modal-backdrop" onClick={() => onClose?.()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Sign in or create your account" onClick={(e) => e.stopPropagation()}>
        <div className="modal-logo">Lot<span>File</span></div>
        {DEV_LOGIN ? (
          <>
            <h2>Dev sign in</h2>
            <p>Local development login — magic links are off while we build.</p>
            <DevLoginForm variant="modal" onSignedIn={onSignedIn} />
          </>
        ) : status === "sent" ? (
          <>
            <h2>Check your email</h2>
            <p>We sent a sign-in link to <b>{email.trim()}</b>. Open it on this device to continue.</p>
            <button className="btn block" onClick={() => setStatus("idle")}>Use a different email</button>
          </>
        ) : (
          <>
            <h2>Sign in or create your account</h2>
            <p>Enter your email and we’ll send you a magic link. You can also keep exploring as a guest, with limited address checks and chat.</p>
            <input
              className="modal-input"
              type="email"
              autoFocus
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void submit(); }}
            />
            <button className="btn block" onClick={() => void submit()} disabled={status === "sending"}>
              {status === "sending" ? "Sending…" : "Email me a magic link"}
            </button>
            {status === "error" && <p className="modal-err">Couldn’t send the link just now — please try again in a moment.</p>}
          </>
        )}
        {onClose && <button className="modal-skip" onClick={onClose}>Continue as guest</button>}
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
        {view === "settings" && <Settings session={session} refresh={refreshSession} />}
      </main>

      <div className="tabbar">
        {tab("home", "home", "Home")}
        {tab("projects", "home_work", "Projects")}
        {tab("library", "menu_book", "Library")}
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
