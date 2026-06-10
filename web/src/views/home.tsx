import { useCallback, useEffect, useRef, useState } from "react";
import { marked } from "marked";
import { api, type AddressSuggestion, type AssistantTurn, type ChatReply, type CitationMapEntry, type ProjectSummary } from "../api";
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

// Looser than looksLikeAddress — fires while the user is still typing
// (e.g. "42 Bank") so we can offer predictive suggestions early.
function addressIntent(t: string): boolean {
  return /^\d+[a-z]?([\s/,]|$)/i.test(t.trim()) && t.trim().length >= 3;
}

// Session-lived suggestion cache so backspacing/retyping renders instantly
// without a round-trip. Bounded to keep memory flat.
const sugCache = new Map<string, AddressSuggestion[]>();
const SUG_CACHE_MAX = 200;
function cacheSugs(key: string, value: AddressSuggestion[]) {
  if (sugCache.size >= SUG_CACHE_MAX) {
    const oldest = sugCache.keys().next().value;
    if (oldest !== undefined) sugCache.delete(oldest);
  }
  sugCache.set(key, value);
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
  isGuest,
  guestUsage,
  onGuestAddressDone,
  onGuestChatDone,
  onNeedSignIn,
  onShowPaywall,
  onProjectOpen,
}: {
  isGuest: boolean;
  guestUsage: GuestUsage;
  onGuestAddressDone: (address: string, projectId: string) => void;
  onGuestChatDone: () => void;
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
  const [sugs, setSugs] = useState<AddressSuggestion[]>([]);
  const [sugIdx, setSugIdx] = useState(-1);
  const sugTimer = useRef<number | undefined>(undefined);
  const sugSeq = useRef(0);

  const closeSugs = useCallback(() => {
    window.clearTimeout(sugTimer.current);
    sugSeq.current += 1; // invalidate in-flight lookups
    setSugs([]);
    setSugIdx(-1);
  }, []);

  const queueSuggest = useCallback((text: string) => {
    window.clearTimeout(sugTimer.current);
    const t = text.trim();
    if (!addressIntent(t)) {
      closeSugs();
      return;
    }
    const key = t.toLowerCase();
    const cached = sugCache.get(key);
    if (cached) {
      sugSeq.current += 1; // cancel any in-flight lookup
      setSugs(cached.slice(0, 6));
      setSugIdx(-1);
      return;
    }
    sugTimer.current = window.setTimeout(async () => {
      const seq = ++sugSeq.current;
      const r = await api.suggestAddresses(t);
      if (seq !== sugSeq.current) return; // stale response
      const list = r.kind === "ok" ? r.data.suggestions : [];
      if (r.kind === "ok") cacheSugs(key, list);
      setSugs(list.slice(0, 6));
      setSugIdx(-1);
    }, 120);
  }, [closeSugs]);

  useEffect(() => () => window.clearTimeout(sugTimer.current), []);

  useEffect(() => {
    if (isGuest) {
      setRecents(guestProjectList(guestUsage).slice(0, 2));
      return;
    }
    void api.projects().then((r) => setRecents(projectList(r).slice(0, 2)));
  }, [isGuest, guestUsage]);
  useEffect(() => {
    threadRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs]);

  const push = (m: Msg) => setMsgs((prev) => [...prev, m]);

  const startCheck = useCallback(async (address: string) => {
    const created = await api.createProject(address);
    if (created.kind === "ok") {
      const id = created.data.id;
      if (isGuest) onGuestAddressDone(address, id);
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
      } else if (resolved.kind === "notBuilt" || resolved.kind === "missing") {
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
    } else if (created.kind === "quota") {
      onShowPaywall(created.feature);
    } else if (created.kind === "auth") {
      push({
        role: "a",
        tone: "note",
        text: "Sign in first.",
        action: { label: "Go to sign in", run: onNeedSignIn },
      });
    } else {
      const reason =
        created.kind === "down"
          ? "can't reach the API right now"
          : created.kind === "notBuilt" || created.kind === "missing"
            ? "endpoint not available"
            : created.message || "unexpected error";
      push({ role: "a", tone: "warn", text: `Couldn't start the check (${reason}).` });
    }
  }, [isGuest, onGuestAddressDone, onNeedSignIn, onShowPaywall]);

  const send = useCallback(async () => {
    const el = inputRef.current;
    const t = el?.value.trim() ?? "";
    if (!t || busy) return;
    if (el) { el.value = ""; el.style.height = "auto"; }
    closeSugs();
    setBusy(true);
    // Capture history before pushing the current question
    const history: AssistantTurn[] = msgs
      .filter((m) => m.role === "q" || m.role === "a")
      .map((m) => ({ role: m.role === "q" ? "user" : "assistant" as const, content: m.text }));
    push({ role: "q", text: t });
    if (looksLikeAddress(t)) {
      await startCheck(t);
    } else {
      const r = await api.ask(t, { web: webOn }, history);
      if (r.kind === "ok") {
        if (isGuest) onGuestChatDone();
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
      } else if (r.kind === "quota") {
        push({
          role: "a",
          tone: "note",
          text: "You've used the free allowance — sign in to keep going, it's free.",
          action: { label: "Keep going", run: () => onShowPaywall("chat") },
        });
      } else if (r.kind === "auth") {
        push({ role: "a", tone: "note", text: "Session expired — please sign in again.", action: { label: "Sign in", run: onNeedSignIn } });
      } else {
        const reason =
          r.kind === "down"
            ? "Can't reach the API right now."
            : r.kind === "missing" || r.kind === "notBuilt"
              ? "endpoint not available"
              : r.message || "the assistant hit an unexpected error";
        push({ role: "a", tone: "warn", text: `Ask failed (${reason}).` });
      }
    }
    setBusy(false);
  }, [isGuest, busy, webOn, msgs, startCheck, closeSugs, onGuestChatDone, onNeedSignIn, onShowPaywall]);

  const pickSuggestion = useCallback(async (s: AddressSuggestion) => {
    if (busy) return;
    const el = inputRef.current;
    if (el) { el.value = ""; el.style.height = "auto"; }
    closeSugs();
    setBusy(true);
    push({ role: "q", text: s.address });
    await startCheck(s.address);
    setBusy(false);
  }, [busy, closeSugs, startCheck]);

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
            placeholder="Type a street address (e.g. 42 Banksia St, Fremantle)… or ask anything about WA planning"
            onKeyDown={(e) => {
              if (sugs.length) {
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setSugIdx((i) => (i + 1) % sugs.length);
                  return;
                }
                if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setSugIdx((i) => (i <= 0 ? sugs.length - 1 : i - 1));
                  return;
                }
                if (e.key === "Escape") {
                  closeSugs();
                  return;
                }
                if ((e.key === "Enter" && !e.shiftKey && sugIdx >= 0) || (e.key === "Tab" && !e.shiftKey)) {
                  e.preventDefault();
                  void pickSuggestion(sugs[sugIdx >= 0 ? sugIdx : 0]);
                  return;
                }
              }
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = t.scrollHeight + "px";
              queueSuggest(t.value);
            }}
            onBlur={() => window.setTimeout(closeSugs, 150)}
          />
          {sugs.length > 0 && (
            <div className="suggest" role="listbox" aria-label="Address suggestions">
              <span className="suggest-head"><Icon name="location_on" />Addresses — pick one to start a check</span>
              {sugs.map((s, i) => (
                <button
                  key={s.gnaf_pid ?? s.address}
                  role="option"
                  aria-selected={i === sugIdx}
                  className={`suggest-item${i === sugIdx ? " on" : ""}`}
                  onMouseDown={(e) => { e.preventDefault(); void pickSuggestion(s); }}
                  onMouseEnter={() => setSugIdx(i)}
                >
                  <Icon name="location_on" />{s.address}
                </button>
              ))}
            </div>
          )}
          <div className="belt">
            <span className="chip on"><Icon name="verified" />WA library</span>
            <button className={`chip${webOn ? " on" : ""}`} onClick={() => setWebOn(!webOn)}>
              <Icon name="public" />Web
            </button>
            {isGuest && (
              <span className="chip guest"><Icon name="sparkles" />Free preview · {Math.min(guestUsage.addressChecks, GUEST_ADDRESS_LIMIT)}/{GUEST_ADDRESS_LIMIT} checks · {Math.min(guestUsage.chatMessages, GUEST_CHAT_LIMIT)}/{GUEST_CHAT_LIMIT} questions</span>
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
