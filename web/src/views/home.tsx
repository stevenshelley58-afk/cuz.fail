import { useCallback, useEffect, useRef, useState } from "react";
import { marked } from "marked";
import { api, type AssistantTurn, type ChatReply, type CitationMapEntry, type ProjectSummary } from "../api";
import { Icon, StatusBar, ThinkBlock } from "../components/common";
import { GUEST_ADDRESS_LIMIT, GUEST_CHAT_LIMIT } from "../config";
import { guestProjectList } from "../hooks/useGuestUsage";
import type { GuestFeature, GuestUsage, WizardState } from "../types";
import { projectList } from "./projects";
import { WizardShell } from "./wizard";

type Msg = {
  role: "q" | "a";
  text: string;
  thinking?: string;
  tone?: "note" | "warn";
  chips?: string[];
  citation_map?: CitationMapEntry[];
  disclaimer?: string;
  action?: { label: string; run: () => void };
};

function looksLikeAddress(t: string): boolean {
  return /^\d+\s+\w+.*(st|street|rd|road|ave|avenue|lane|ln|way|cres|crescent|court|ct|pl|place)\b/i.test(t.trim());
}

function guestLimitMessage(feature: GuestFeature): string {
  return feature === "address"
    ? "You have used the free guest address checks. Unlock more searches to keep going."
    : "You have used the free guest chat allowance. Unlock more questions to keep going.";
}

function citationChip(citation: NonNullable<ChatReply["citations"]>[number]): string {
  return [
    citation.source_title,
    citation.clause_id ?? citation.locator ?? citation.heading,
    citation.page_number ? `p.${citation.page_number}` : "",
  ].filter(Boolean).join(" · ");
}

/* ── one-box home ── */

export function Home({
  authed,
  guestUsage,
  onGuestAddressStart,
  onGuestChatStart,
  onNeedSignIn,
  onShowPaywall,
  onProjectOpen,
}: {
  authed: boolean;
  guestUsage: GuestUsage;
  onGuestAddressStart: (address: string) => boolean;
  onGuestChatStart: () => boolean;
  onNeedSignIn: () => void;
  onShowPaywall: (feature: GuestFeature) => void;
  onProjectOpen: (projectId: string) => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);

  function renderMsgHtml(text: string, msgIndex: number, chips?: string[]): string {
    const html = marked.parse(text) as string;
    if (!chips?.length) return html;
    return html.replace(/\[(\d+)\]/g, (match, n: string) => {
      const idx = parseInt(n, 10);
      if (idx < 1 || idx > chips.length) return match;
      return `<sup><a href="#cite-${msgIndex}-${idx}" class="cite-ref">[${idx}]</a></sup>`;
    });
  }
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
    threadRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
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
    if (el) { el.value = ""; el.style.height = "auto"; }
    setBusy(true);
    // Capture history before pushing the current question
    const history: AssistantTurn[] = msgs
      .filter((m) => m.role === "q" || m.role === "a")
      .map((m) => ({ role: m.role === "q" ? "user" : "assistant" as const, content: m.text }));
    push({ role: "q", text: t });
    if (looksLikeAddress(t)) {
      await startCheck(t);
    } else {
      if (!authed && !onGuestChatStart()) {
        push({ role: "a", tone: "note", text: guestLimitMessage("chat"), action: { label: "Unlock more", run: () => onShowPaywall("chat") } });
        setBusy(false);
        return;
      }
      const r = await api.ask(t, { web: webOn }, history);
      if (r.kind === "ok") {
        const d: ChatReply = r.data;
        const chips = (d.citations ?? [])
          .map(citationChip)
          .filter((chip) => chip.length > 0);
        const rawAnswer = d.answer ?? "I couldn't get an answer just now.";
        const thinkParts: string[] = [];
        const cleanAnswer = rawAnswer.replace(/<think>([\s\S]*?)<\/think>/gi, (_, t: string) => {
          thinkParts.push(t.trim());
          return "";
        }).trim();
        push({
          role: "a",
          text: cleanAnswer || "I couldn't get an answer just now.",
          thinking: thinkParts.length ? thinkParts.join("\n\n") : undefined,
          chips: chips.length ? chips : undefined,
          citation_map: d.citation_map,
          disclaimer: d.disclaimer ?? undefined,
        });
      } else if (r.kind === "auth") {
        if (!authed) {
          pushGuestChatPreview(t);
        } else {
          push({ role: "a", tone: "note", text: "Session expired — please sign in again.", action: { label: "Sign in", run: onNeedSignIn } });
        }
      } else if ((r.kind === "missing" || r.kind === "notBuilt") && !authed) {
        pushGuestChatPreview(t);
      } else {
        push({ role: "a", tone: "warn", text: r.kind === "down" ? "Can't reach the API right now." : `Ask failed (${r.kind === "missing" || r.kind === "notBuilt" ? "endpoint not available" : r.message}).` });
      }
    }
    setBusy(false);
  }, [authed, busy, webOn, msgs, startCheck, onGuestChatStart, onNeedSignIn, onShowPaywall, pushGuestChatPreview]);

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
        <WizardShell wizard={wizard} onClose={() => setWizard(null)} onProjectOpen={(id) => { setWizard(null); onProjectOpen(id); }} />
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
                  {m.thinking && <ThinkBlock text={m.thinking} />}
                  <div className="md" dangerouslySetInnerHTML={{ __html: renderMsgHtml(m.text, i, m.chips) }} />
                  {m.chips && m.chips.length > 0 && (
                    <div className="src">
                      {m.chips.slice(0, 3).map((c, j) => (
                        <span key={j} id={`cite-${i}-${j + 1}`} className="srcchip"><Icon name="verified" />{c}</span>
                      ))}
                      {m.chips.length > 3 && (
                        <details className="src-more">
                          <summary className="srcchip"><Icon name="verified" />Sources ({m.chips.length})</summary>
                          {m.chips.slice(3).map((c, j) => (
                            <span key={j} id={`cite-${i}-${j + 4}`} className="srcchip"><Icon name="verified" />{c}</span>
                          ))}
                        </details>
                      )}
                    </div>
                  )}
                  {m.disclaimer && (
                    <p className="disclaimer">{m.disclaimer}</p>
                  )}
                  {m.action && (
                    <div className="act">
                      <button onClick={m.action.run}>{m.action.label}</button>
                    </div>
                  )}
                </div>
              ),
            )}
            {busy && (
              <div className="a typing">
                <span /><span /><span />
              </div>
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
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = t.scrollHeight + "px";
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
              <button key={p.id} className="proj" onClick={() => onProjectOpen(p.id)}>
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
