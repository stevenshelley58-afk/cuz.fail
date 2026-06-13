import { useCallback, useEffect, useState } from "react";
import { api, type ApiResult, type SessionInfo } from "./api";
import { Icon } from "./components/common";
import { PaywallModal, SignInModal } from "./components/modals";
import { GUEST_ADDRESS_LIMIT, GUEST_CHAT_LIMIT } from "./config";
import { useGuestUsage } from "./hooks/useGuestUsage";
import type { GuestFeature, PaywallState } from "./types";
import { Home } from "./views/home";
import { LandingPage, LegalPage } from "./views/launch";
import { Library } from "./views/library";
import { ProjectDetail, Projects } from "./views/projects";
import { RulesView } from "./views/rules";
import { Settings } from "./views/settings";

type View = "home" | "projects" | "library" | "rules" | "settings";
type AppRoute = "landing" | "privacy" | "terms" | "product";

const ROUTE_META: Record<AppRoute, { title: string; description: string; canonical: string }> = {
  landing: {
    title: "LotFile - WA R-Code & Planning Compliance Checker",
    description: "Advisory WA planning checks for addresses, drawings, R-Codes and source-cited project risk review. Not a certification or council decision.",
    canonical: "https://lotfile.app/",
  },
  privacy: {
    title: "Privacy - LotFile",
    description: "How LotFile handles account, project, address and uploaded drawing data for advisory WA planning checks.",
    canonical: "https://lotfile.app/privacy",
  },
  terms: {
    title: "Terms - LotFile",
    description: "LotFile terms for advisory-only planning checks, uploaded drawings, liability limits and user responsibilities.",
    canonical: "https://lotfile.app/terms",
  },
  product: {
    title: "LotFile App - Advisory WA Planning Checks",
    description: "Address-first LotFile workspace for advisory WA planning checks with cited sources and uploaded drawing review.",
    canonical: "https://lotfile.app/app",
  },
};

function routeFromLocation(): AppRoute {
  const path = window.location.pathname;
  if (path === "/privacy") return "privacy";
  if (path === "/terms") return "terms";
  if (path.startsWith("/app") || path.startsWith("/auth/magic-link/verify")) return "product";
  return "landing";
}

function applyRouteMeta(route: AppRoute) {
  const meta = ROUTE_META[route];
  document.title = meta.title;
  document.querySelector('meta[name="description"]')?.setAttribute("content", meta.description);
  document.querySelector('meta[property="og:title"]')?.setAttribute("content", meta.title);
  document.querySelector('meta[property="og:description"]')?.setAttribute("content", meta.description);
  document.querySelector('meta[property="og:url"]')?.setAttribute("content", meta.canonical);
  document.querySelector('meta[name="twitter:title"]')?.setAttribute("content", meta.title);
  document.querySelector('meta[name="twitter:description"]')?.setAttribute("content", meta.description);
  document.querySelector('link[rel="canonical"]')?.setAttribute("href", meta.canonical);
}

export function App() {
  const [route, setRoute] = useState<AppRoute>(() => routeFromLocation());

  const navigate = useCallback((path: string) => {
    window.history.pushState(null, "", path);
    setRoute(routeFromLocation());
    window.scrollTo({ top: 0 });
  }, []);

  useEffect(() => {
    const onPopState = () => setRoute(routeFromLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    applyRouteMeta(route);
  }, [route]);

  if (route === "privacy") return <LegalPage kind="privacy" onNavigate={navigate} />;
  if (route === "terms") return <LegalPage kind="terms" onNavigate={navigate} />;
  if (route === "product") return <ProductApp />;
  return <LandingPage onNavigate={navigate} />;
}

/* ── app shell ── */

function ProductApp() {
  const [view, setView] = useState<View>("home");
  const [session, setSession] = useState<ApiResult<SessionInfo> | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInNotice, setSignInNotice] = useState<string | null>(null);
  const [paywall, setPaywall] = useState<PaywallState | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  const refreshSession = useCallback(() => { void api.session().then(setSession); }, []);
  const bootstrapSession = useCallback(() => {
    void api.session().then((r) => {
      if (r.kind === "auth") {
        void api.guestSession().then((g) => {
          if (g.kind === "ok") refreshSession();
          else setSession(r);
        });
      } else {
        setSession(r);
      }
    });
  }, [refreshSession]);

  useEffect(() => {
    // magic-link verify deep link: /auth/magic-link/verify?token=…
    const url = new URL(window.location.href);
    if (url.pathname.startsWith("/auth/magic-link/verify")) {
      const token = url.searchParams.get("token");
      if (token) {
        void api.magicLinkVerify(token).then((r) => {
          window.history.replaceState(null, "", "/app");
          if (r.kind === "ok") {
            refreshSession();
            return;
          }
          setSignInNotice("That sign-in link has expired or could not be verified. Send yourself a new link.");
          setSignInOpen(true);
          bootstrapSession();
        });
        return;
      }
    }
    // Guest bootstrap: no session → mint a guest session so the real product
    // works immediately. If guest creation fails (API down, guest mode off),
    // fall back to showing whatever the session call returned.
    bootstrapSession();
  }, [bootstrapSession, refreshSession]);

  const role = session?.kind === "ok" ? String(session.data.role ?? session.data.user?.role ?? "") : "";
  const isGuest = role === "guest";
  const authed = session?.kind === "ok" && !isGuest;

  const { guestUsage, recordGuestAddress, recordGuestChat } = useGuestUsage(isGuest);

  const goSignIn = useCallback(() => {
    setSignInNotice(null);
    setSignInOpen(true);
  }, []);
  const showPaywall = useCallback((feature: GuestFeature) => {
    const used = feature === "address" ? guestUsage.addressChecks : guestUsage.chatMessages;
    const limit = feature === "address" ? GUEST_ADDRESS_LIMIT : GUEST_CHAT_LIMIT;
    setPaywall({ feature, used, limit });
  }, [guestUsage]);
  const openSignIn = useCallback(() => {
    setPaywall(null);
    setSignInNotice(null);
    setSignInOpen(true);
  }, []);
  const handleSignedIn = useCallback(() => {
    setSignInOpen(false);
    setSignInNotice(null);
    refreshSession();
  }, [refreshSession]);
  const closeSignIn = useCallback(() => {
    setSignInOpen(false);
    setSignInNotice(null);
  }, []);
  const goView = useCallback((nextView: View) => {
    setActiveProjectId(null);
    setView(nextView);
  }, []);

  const navItem = (v: View, icon: string, label: string) => (
    <button className={view === v ? "on" : ""} onClick={() => goView(v)} aria-current={view === v ? "page" : undefined} aria-label={label}>
      <Icon name={icon} />{label}
    </button>
  );
  const tab = (v: View, icon: string, label: string) => (
    <button className={`tb${view === v ? " on" : ""}`} onClick={() => goView(v)} aria-current={view === v ? "page" : undefined} aria-label={label}>
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
        <button className="newbtn" onClick={() => goView("home")} aria-label="Start a new address check"><Icon name="add_home_work" />New check</button>
        <nav className="nav">
          {navItem("home", "home", "Home")}
          {navItem("projects", "home_work", "Projects")}
          {navItem("library", "menu_book", "Library")}
          {navItem("rules", "gavel", "Rules")}
          {navItem("settings", "tune", "Settings")}
        </nav>
        <div className="grow" />
        <div className="user">
          <div className="avatar">{authed ? "OK" : "✦"}</div>
          <div className="who">
            {authed ? String(session.data.email ?? session.data.user?.email ?? "Signed in") : "Free preview"}
            {authed
              ? <small>{String(session.data.role ?? session.data.user?.role ?? "")}</small>
              : <small><button onClick={goSignIn} style={{ background: "none", border: "none", padding: 0, color: "inherit", textDecoration: "underline", cursor: "pointer", font: "inherit" }}>Sign in</button></small>}
          </div>
        </div>
      </aside>

      <main className="stage">
        {activeProjectId ? (
          <ProjectDetail projectId={activeProjectId} onClose={() => setActiveProjectId(null)} />
        ) : view === "home" ? (
          <Home
            isGuest={isGuest}
            guestUsage={guestUsage}
            onGuestAddressDone={recordGuestAddress}
            onGuestChatDone={recordGuestChat}
            onNeedSignIn={openSignIn}
            onShowPaywall={showPaywall}
            onProjectOpen={(id) => setActiveProjectId(id)}
          />
        ) : view === "projects" ? (
          <Projects isGuest={isGuest} onNeedSignIn={openSignIn} onProjectOpen={(id) => setActiveProjectId(id)} />
        ) : view === "library" ? (
          <Library onNeedSignIn={goSignIn} />
        ) : view === "rules" ? (
          <RulesView />
        ) : view === "settings" ? (
          <Settings session={session} refresh={refreshSession} />
        ) : null}
      </main>

      <div className="tabbar">
        {tab("home", "home", "Home")}
        {tab("projects", "home_work", "Projects")}
        {tab("library", "menu_book", "Library")}
        {tab("rules", "gavel", "Rules")}
        {tab("settings", "tune", "Settings")}
      </div>

      {signInOpen && <SignInModal notice={signInNotice} onClose={closeSignIn} onSignedIn={handleSignedIn} />}
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
