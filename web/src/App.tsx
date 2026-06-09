import { useCallback, useEffect, useState } from "react";
import { api, type ApiResult, type SessionInfo } from "./api";
import { Icon } from "./components/common";
import { PaywallModal, SignInModal } from "./components/modals";
import { GUEST_ADDRESS_LIMIT, GUEST_CHAT_LIMIT } from "./config";
import { useGuestUsage } from "./hooks/useGuestUsage";
import type { GuestFeature, PaywallState } from "./types";
import { Home } from "./views/home";
import { Library } from "./views/library";
import { ProjectDetail, Projects } from "./views/projects";
import { RulesView } from "./views/rules";
import { Settings } from "./views/settings";

type View = "home" | "projects" | "library" | "rules" | "settings";

/* ── app shell ── */

export function App() {
  const [view, setView] = useState<View>("home");
  const [session, setSession] = useState<ApiResult<SessionInfo> | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [paywall, setPaywall] = useState<PaywallState | null>(null);
  const [autoPrompted, setAutoPrompted] = useState(false);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

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

  const { guestUsage, startGuestAddress, startGuestChat } = useGuestUsage(authed, setPaywall);

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
        {activeProjectId ? (
          <ProjectDetail projectId={activeProjectId} onClose={() => setActiveProjectId(null)} />
        ) : view === "home" ? (
          <Home
            authed={authed}
            guestUsage={guestUsage}
            onGuestAddressStart={startGuestAddress}
            onGuestChatStart={startGuestChat}
            onNeedSignIn={openSignIn}
            onShowPaywall={showPaywall}
            onProjectOpen={(id) => setActiveProjectId(id)}
          />
        ) : view === "projects" ? (
          <Projects authed={authed} guestUsage={guestUsage} onNeedSignIn={openSignIn} onProjectOpen={(id) => setActiveProjectId(id)} />
        ) : view === "library" ? (
          <Library onNeedSignIn={goSignIn} />
        ) : view === "rules" ? (
          authed ? <RulesView /> : <div className="view"><div className="panel"><div className="state"><Icon name="lock" /><span>Sign in to view rules. <button className="btn alt" style={{ marginLeft: 8 }} onClick={openSignIn}>Sign in</button></span></div></div></div>
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
