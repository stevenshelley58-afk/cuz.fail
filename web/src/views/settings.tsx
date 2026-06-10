import { api, type ApiResult, type SessionInfo } from "../api";
import { Icon } from "../components/common";
import { DevLoginForm, MagicLinkForm } from "../components/modals";
import { DEV_LOGIN } from "../config";

/* ── settings / auth ── */

export function Settings({ session, refresh }: { session: ApiResult<SessionInfo> | null; refresh: () => void }) {
  const role = session?.kind === "ok" ? String(session.data.role ?? session.data.user?.role ?? "") : "";
  const authed = session?.kind === "ok" && role !== "guest";
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
          <DevLoginForm variant="panel" onSignedIn={refresh} />
        ) : (
          <MagicLinkForm variant="panel" onSignedIn={refresh} />
        )}
      </div>
      <div className="panel">
        <h3><Icon name="gavel" />Ground rules</h3>
        <p>Verdicts are likely-pass / needs-review / missing-info — never pass/fail. Every regulatory claim is cited to an approved source version or flagged as unsupported. Outputs are advisory and cited to approved source versions; they are not final certifications.</p>
      </div>
    </div>
  );
}
