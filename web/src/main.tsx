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
import { api, type ApiResult, type ChatReply, type HealthInfo, type ProjectSummary, type SessionInfo } from "./api";
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
      tone: "note",
      text: `${label} for ${address}: I can build the dossier shell, run the address-first workflow, and line the property up with parcel, council, zoning, overlays, source-library search, drawing upload, and Tier-1 check readiness when the live API has authoritative data.`,
      chips,
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
      tone: "note",
      text,
      chips: authed
        ? ["library-first", "preview fallback", "citations required"]
        : [
            `chat ${Math.min(guestUsage.chatMessages + 1, GUEST_CHAT_LIMIT)}/${GUEST_CHAT_LIMIT}`,
            "library-first",
            "guest preview",
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
        push({ role: "a", tone: "note", text: "Property resolved. Drawings upload and Tier-1 checks are the next build steps — this project is saved and waiting.", chips: ["resolve-address · live"] });
      } else if (!authed && (resolved.kind === "auth" || resolved.kind === "notBuilt" || resolved.kind === "missing")) {
        pushGuestAddressPreview(address, "guest");
      } else if (resolved.kind === "notBuilt") {
        pushGuestAddressPreview(address, "fallback");
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
