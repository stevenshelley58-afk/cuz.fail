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
  Construction,
  Gavel,
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
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, type ApiResult, type HealthInfo, type ProjectSummary, type SessionInfo } from "./api";
import "./styles.css";

/* ── helpers ── */

type View = "home" | "projects" | "library" | "settings";

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
  construction: Construction,
  error: CircleAlert,
  forum: MessageCircle,
  gavel: Gavel,
  home: HomeIcon,
  home_work: Building2,
  location_on: MapPin,
  lock: Lock,
  mark_email_read: MailCheck,
  menu_book: BookOpen,
  public: Globe2,
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

function projectList(r: ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }>): ProjectSummary[] {
  if (r.kind !== "ok") return [];
  const d = r.data;
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d.projects)) return d.projects;
  return [];
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

function Home({ authed, onNeedSignIn }: { authed: boolean; onNeedSignIn: () => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [webOn, setWebOn] = useState(false);
  const [recents, setRecents] = useState<ProjectSummary[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void api.projects().then((r) => setRecents(projectList(r).slice(0, 2)));
  }, []);
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [msgs]);

  const push = (m: Msg) => setMsgs((prev) => [...prev, m]);

  const startCheck = useCallback(async (address: string) => {
    const created = await api.createProject(address);
    if (created.kind === "ok") {
      const id = created.data.id;
      push({ role: "a", tone: "note", text: `Project created for ${address}. Resolving the property…`, chips: ["POST /projects · live"] });
      const resolved = await api.resolveAddress(id, address);
      if (resolved.kind === "ok") {
        push({ role: "a", tone: "note", text: "Property resolved. Drawings upload and Tier-1 checks are the next build steps — this project is saved and waiting.", chips: ["resolve-address · live"] });
      } else if (resolved.kind === "notBuilt") {
        push({ role: "a", tone: "note", text: "Project saved. Address resolving is coming soon — it'll light up here automatically when it's ready." });
      } else if (resolved.kind === "auth") {
        onNeedSignIn();
      } else {
        push({ role: "a", tone: "warn", text: `Project saved, but resolving failed: ${resolved.kind === "error" ? resolved.message : resolved.kind}.` });
      }
    } else if (created.kind === "notBuilt") {
      push({ role: "a", tone: "note", text: "Project creation is coming soon. Your address is saved and will run the moment it's available.", chips: ["creating projects · coming soon"] });
    } else if (created.kind === "auth") {
      push({ role: "a", tone: "note", text: "Sign in first — LotFile uses email magic links, no passwords.", action: { label: "Go to sign in", run: onNeedSignIn } });
    } else if (created.kind === "down") {
      push({ role: "a", tone: "warn", text: "Can't reach the API right now. The VPS may be restarting — try again shortly." });
    } else {
      push({ role: "a", tone: "warn", text: `Couldn't create the project (${created.kind === "error" ? created.message : created.kind}).` });
    }
  }, [onNeedSignIn]);

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
      const r = await api.ask(t, { web: webOn });
      if (r.kind === "ok") {
        const d = r.data as { answer?: string; citations?: string[] };
        push({ role: "a", text: d.answer ?? JSON.stringify(d), chips: d.citations });
      } else if (r.kind === "missing" || r.kind === "notBuilt") {
        push({
          role: "a", tone: "note",
          text: "Grounded Q&A is coming soon. Answers come from the approved WA library first (cited), and the web only if you toggle it on — and I'll say so plainly when the library can't support an answer.",
          chips: ["library-first · citations required"],
        });
      } else if (r.kind === "auth") {
        push({ role: "a", tone: "note", text: "Sign in to ask questions.", action: { label: "Go to sign in", run: onNeedSignIn } });
      } else {
        push({ role: "a", tone: "warn", text: r.kind === "down" ? "Can't reach the API right now." : `Ask failed (${r.message}).` });
      }
    }
    setBusy(false);
  }, [busy, webOn, startCheck, onNeedSignIn]);

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
            {!authed && <span className="chip"><Icon name="lock" />signed out</span>}
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

function Projects({ onNeedSignIn }: { onNeedSignIn: () => void }) {
  const [result, setResult] = useState<ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }> | null>(null);
  useEffect(() => { void api.projects().then(setResult); }, []);
  const items = result ? projectList(result) : [];
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="home_work" />Projects</h3>
        {result === null && <p>Loading…</p>}
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

/* ── sign in / create account popup ── */

function SignInModal({ onClose }: { onClose?: () => void }) {
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
        {status === "sent" ? (
          <>
            <h2>Check your email</h2>
            <p>We sent a sign-in link to <b>{email.trim()}</b>. Open it on this device to continue.</p>
            <button className="btn block" onClick={() => setStatus("idle")}>Use a different email</button>
          </>
        ) : (
          <>
            <h2>Sign in or create your account</h2>
            <p>Enter your email and we’ll send you a magic link. New here? The same link sets up your account — no password to remember.</p>
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
        {onClose && <button className="modal-skip" onClick={onClose}>Continue browsing</button>}
      </div>
    </div>
  );
}

/* ── app shell ── */

function App() {
  const [view, setView] = useState<View>("home");
  const [session, setSession] = useState<ApiResult<SessionInfo> | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);

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

  // Returning (signed-in) users go straight to home; everyone else gets the popup.
  useEffect(() => {
    if (session === null) return;
    setSignInOpen(session.kind !== "ok");
  }, [session]);

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
            {authed ? String(session.data.email ?? session.data.user?.email ?? "Signed in") : "Signed out"}
            <small>{authed ? String(session.data.role ?? session.data.user?.role ?? "") : "magic-link sign in"}</small>
          </div>
        </div>
      </aside>

      <main className="stage">
        {view === "home" && <Home authed={authed} onNeedSignIn={goSignIn} />}
        {view === "projects" && <Projects onNeedSignIn={goSignIn} />}
        {view === "library" && <Library onNeedSignIn={goSignIn} />}
        {view === "settings" && <Settings session={session} refresh={refreshSession} />}
      </main>

      <div className="tabbar">
        {tab("home", "home", "Home")}
        {tab("projects", "home_work", "Projects")}
        {tab("library", "menu_book", "Library")}
        {tab("settings", "tune", "Settings")}
      </div>

      {signInOpen && <SignInModal onClose={() => setSignInOpen(false)} />}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
