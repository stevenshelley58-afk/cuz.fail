import { api, type ApiResult, type SessionInfo } from "../api";
import { Icon } from "../components/common";
import { DevLoginForm, MagicLinkForm } from "../components/modals";
import { DEV_LOGIN } from "../config";

/* ── settings / auth ── */

export function Settings({ session, refresh }: { session: ApiResult<SessionInfo> | null; refresh: () => void }) {
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
          <DevLoginForm variant="panel" onSignedIn={refresh} />
        ) : (
          <MagicLinkForm variant="panel" onSignedIn={refresh} />
        )}
      </div>
      <div className="panel">
        <h3><Icon name="gavel" />Ground rules</h3>
        <p>Verdicts are likely-pass / needs-review / missing-info — never pass/fail. Every regulatory claim is cited to an approved source version or flagged as unsupported. A human reviewer signs off; the model never does.</p>
      </div>
    </div>
  );
}
