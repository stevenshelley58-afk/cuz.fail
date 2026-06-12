import { type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { trackEvent } from "../analytics";
import { CHECKOUT_URL, DEV_LOGIN, PRICE_LABEL, PRICE_SUBLABEL } from "../config";
import type { PaywallState } from "../types";
import { Icon } from "./common";

const PAYWALL_COPY = {
  title: "You've used the free preview",
  body: "You've seen real, cited answers from the approved WA source library. Create a free account to keep going — your checks and chats carry on from here.",
};

function useModalFocus(onClose?: () => void) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const modal = ref.current;
    if (!modal) return;
    const focusable = modal.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    (focusable ?? modal).focus();
  }, []);

  const onKeyDown = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && onClose) {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const modal = ref.current;
    if (!modal) return;
    const focusable = Array.from(
      modal.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ),
    );
    if (!focusable.length) {
      event.preventDefault();
      modal.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }, [onClose]);

  return { ref, onKeyDown };
}

/* ── dev username/password form (used in place of magic link while DEV_LOGIN) ── */

export function DevLoginForm({ variant, onSignedIn }: { variant: "modal" | "panel"; onSignedIn: () => void }) {
  const [username, setUsername] = useState("");
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
        aria-label="Username"
        placeholder="username"
        autoComplete="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") void submit(); }}
      />
      <input
        className={inputClass}
        type="password"
        aria-label="Password"
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

export function MagicLinkForm({ variant, onSignedIn }: { variant: "modal" | "panel"; onSignedIn: () => void }) {
  type Stage = "idle" | "sending" | "check_email";
  const [email, setEmail] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const trimmed = email.trim();
    if (!trimmed) return;
    setStage("sending");
    setError(null);
    trackEvent("signup_requested");
    const r = await api.magicLinkRequest(trimmed);
    if (r.kind === "ok") {
      setStage("check_email");
    } else {
      setError(r.kind === "error" ? (r.message ?? "Could not send link") : "Could not reach server");
      setStage("idle");
    }
  }

  if (stage === "check_email") {
    return (
      <div>
        <p style={{ fontSize: 14, color: "#374151", marginBottom: 16 }}>
          Check your email — we sent a sign-in link to <b>{email}</b>.
        </p>
        <p style={{ fontSize: 13, color: "#6b7280" }}>No email? <button className="btn alt" style={{ padding: "4px 10px", fontSize: 12 }} onClick={() => setStage("idle")}>Resend</button></p>
      </div>
    );
  }

  return (
    <div>
      <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>Enter your email — we'll send a sign-in link. New? Your account is created automatically.</p>
      <div className="field">
        <input
          className="inp"
          type="email"
          aria-label="Email address"
          placeholder="your@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") void submit(); }}
          autoFocus={variant === "modal"}
        />
      </div>
      {error && <p style={{ color: "#b91c1c", fontSize: 13 }}>{error}</p>}
      <div className="field">
        <button className="btn block" onClick={() => void submit()} disabled={stage === "sending" || !email.trim()}>
          {stage === "sending" ? "Sending…" : "Send sign-in link"}
        </button>
      </div>
    </div>
  );
}

export function SignInModal({ onClose, onSignedIn }: { onClose?: () => void; onSignedIn: () => void }) {
  const modalFocus = useModalFocus(onClose);
  return (
    <div className="modal-backdrop" onClick={() => onClose?.()}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Sign in"
        tabIndex={-1}
        ref={modalFocus.ref}
        onKeyDown={modalFocus.onKeyDown}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-logo">Lot<span>File</span></div>
        <h2>Sign in</h2>
        {DEV_LOGIN
          ? <DevLoginForm variant="modal" onSignedIn={onSignedIn} />
          : <MagicLinkForm variant="modal" onSignedIn={onSignedIn} />}
        <div className="modal-legal">
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
        </div>
        {onClose && <button className="modal-skip" onClick={onClose}>Continue as guest</button>}
      </div>
    </div>
  );
}

export function PaywallModal({
  state,
  onClose,
  onSignIn,
}: {
  state: PaywallState;
  onClose: () => void;
  onSignIn: () => void;
}) {
  const copy = PAYWALL_COPY;
  const modalFocus = useModalFocus(onClose);
  const cta = CHECKOUT_URL ? "Unlock more checks" : "Sign in to continue";
  const upgrade = () => {
    if (CHECKOUT_URL) {
      trackEvent("checkout_clicked", { feature: state.feature, price: PRICE_LABEL });
      window.location.assign(CHECKOUT_URL);
      return;
    }
    onSignIn();
  };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal paywall"
        role="dialog"
        aria-modal="true"
        aria-label={copy.title}
        tabIndex={-1}
        ref={modalFocus.ref}
        onKeyDown={modalFocus.onKeyDown}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-logo">Lot<span>File</span></div>
        <div className="paywall-icon"><Icon name={state.feature === "address" ? "location_on" : "forum"} /></div>
        <h2>{copy.title}</h2>
        <p>{copy.body}</p>
        <div className="price">
          <span>{PRICE_LABEL}</span>
          <small>{PRICE_SUBLABEL}</small>
        </div>
        <div className="plans">
          <div>
            <b>Saved dossiers</b>
            <span>Your checks and chat history, kept across visits</span>
          </div>
          <div>
            <b>Drawing uploads &amp; Tier-1 checks</b>
            <span>Upload plans and run cited advisory checks</span>
          </div>
          <div>
            <b>Full source library search</b>
            <span>Search the approved WA source library directly</span>
          </div>
        </div>
        <button className="btn block" onClick={upgrade}>
          <Icon name={CHECKOUT_URL ? "credit_card" : "badge"} />{cta}
        </button>
        {CHECKOUT_URL && <button className="btn alt block" onClick={onSignIn}>Sign in instead</button>}
        <div className="modal-legal">
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
        </div>
        <button className="modal-skip" onClick={onClose}>Not now</button>
      </div>
    </div>
  );
}
