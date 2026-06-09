/**
 * SearchAsk — chat-style planning question interface.
 * Sends questions to POST /search/ask and renders answers with
 * inline citation highlights. Falls back to POST /assistant.
 */

import { useRef, useState } from "react";
import { marked } from "marked";
import { api, type ChatCitation, type ChatReply } from "./api";

type Msg = {
  role: "q" | "a";
  text: string;
  citations?: ChatCitation[];
  disclaimer?: string | null;
  grounded?: boolean;
};

function CitationChip({ citation }: { citation: ChatCitation }) {
  const label = [
    citation.source_title,
    citation.clause_id ?? citation.locator ?? citation.heading,
    citation.page_number ? `p.${citation.page_number}` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  const [hover, setHover] = useState(false);

  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          fontSize: ".72rem",
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: 99,
          background: "#EFF6FF",
          color: "#1D4ED8",
          border: "1px solid #BFDBFE",
          cursor: citation.quote ? "pointer" : "default",
          marginRight: 4,
          marginBottom: 4,
        }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        {label || "Source"}
      </span>
      {hover && citation.quote && (
        <span
          style={{
            position: "absolute",
            bottom: "calc(100% + 4px)",
            left: 0,
            zIndex: 10,
            background: "#fff",
            border: "1px solid #BFDBFE",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: ".78rem",
            color: "var(--ink-soft, #6B7280)",
            fontStyle: "italic",
            maxWidth: 320,
            boxShadow: "0 4px 16px rgba(0,0,0,.12)",
            pointerEvents: "none",
          }}
        >
          {citation.quote}
        </span>
      )}
    </span>
  );
}

function AnswerBubble({ msg }: { msg: Msg }) {
  const html =
    msg.role === "a"
      ? String(marked.parse(msg.text, { async: false }))
      : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: msg.role === "q" ? "flex-end" : "flex-start",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          maxWidth: "85%",
          padding: "10px 14px",
          borderRadius: msg.role === "q" ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
          background:
            msg.role === "q"
              ? "var(--accent, #2563EB)"
              : "var(--paper, #F9FAFB)",
          color: msg.role === "q" ? "#fff" : "var(--ink, #111)",
          border:
            msg.role === "a" ? "1px solid var(--line, #E5E7EB)" : "none",
          fontSize: ".88rem",
          lineHeight: 1.5,
        }}
      >
        {msg.role === "q" ? (
          <span>{msg.text}</span>
        ) : (
          <div
            className="prose"
            // biome-ignore lint/security/noDangerouslySetInnerHtml: markdown from trusted API
            dangerouslySetInnerHTML={{ __html: html ?? "" }}
          />
        )}
      </div>

      {msg.role === "a" && msg.citations && msg.citations.length > 0 && (
        <div style={{ maxWidth: "85%", marginTop: 6, display: "flex", flexWrap: "wrap" }}>
          {msg.citations.map((c, i) => (
            <CitationChip key={i} citation={c} />
          ))}
        </div>
      )}

      {msg.role === "a" && msg.disclaimer && (
        <div
          style={{
            maxWidth: "85%",
            marginTop: 4,
            fontSize: ".72rem",
            color: "#B45309",
            fontStyle: "italic",
          }}
        >
          {msg.disclaimer}
        </div>
      )}
    </div>
  );
}

export function SearchAsk({
  placeholder = "Ask a planning question…",
  scope,
}: {
  placeholder?: string;
  scope?: string;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [webSearch, setWebSearch] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  function appendMsg(msg: Msg) {
    setMessages((prev) => [...prev, msg]);
  }

  async function send() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setError(null);
    appendMsg({ role: "q", text: q });
    setLoading(true);

    // Try /search/ask first, fall back to /assistant
    let reply: ChatReply | null = null;
    const r = await api.search.ask(q, { web: webSearch, scope });
    if (r.kind === "ok") {
      reply = r.data;
    } else if (r.kind === "notBuilt" || r.kind === "missing") {
      // fallback
      const r2 = await api.ask(q, { web: webSearch });
      if (r2.kind === "ok") {
        reply = r2.data;
      } else {
        const msg =
          r2.kind === "error"
            ? r2.message
            : r2.kind === "down"
            ? "API unreachable: " + r2.message
            : "Unexpected error";
        setError(msg);
      }
    } else if (r.kind === "error") {
      setError(r.message);
    } else if (r.kind === "down") {
      setError("API unreachable: " + r.message);
    }

    if (reply) {
      appendMsg({
        role: "a",
        text: reply.answer,
        citations: reply.citations,
        disclaimer: reply.disclaimer,
        grounded: reply.grounded,
      });
    }

    setLoading(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* message list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 0",
          minHeight: 120,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: "var(--ink-soft, #6B7280)",
              fontSize: ".88rem",
              paddingTop: 24,
            }}
          >
            Ask a question about planning rules, zoning, or compliance.
          </div>
        )}
        {messages.map((msg, i) => (
          <AnswerBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "4px 18px 18px 18px",
                background: "var(--paper, #F9FAFB)",
                border: "1px solid var(--line, #E5E7EB)",
                fontSize: ".88rem",
                color: "var(--ink-soft, #6B7280)",
              }}
            >
              Thinking…
            </div>
          </div>
        )}
      </div>

      {error && (
        <div
          style={{
            fontSize: ".82rem",
            color: "#B91C1C",
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderRadius: 8,
            padding: "6px 10px",
            marginBottom: 8,
          }}
        >
          {error}
        </div>
      )}

      {/* input row */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "flex-end",
          borderTop: "1px solid var(--line, #E5E7EB)",
          paddingTop: 10,
          marginTop: 4,
        }}
      >
        <div style={{ flex: 1 }}>
          <textarea
            ref={inputRef}
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            style={{
              width: "100%",
              resize: "none",
              padding: "8px 12px",
              borderRadius: 10,
              border: "1px solid var(--line, #E5E7EB)",
              fontSize: ".88rem",
              fontFamily: "inherit",
              color: "var(--ink, #111)",
              background: "#fff",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              fontSize: ".72rem",
              color: "var(--ink-soft, #6B7280)",
              marginTop: 4,
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            <input
              type="checkbox"
              checked={webSearch}
              onChange={(e) => setWebSearch(e.target.checked)}
            />
            Include web search
          </label>
        </div>
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            padding: "10px 18px",
            borderRadius: 10,
            fontWeight: 700,
            fontSize: ".88rem",
            background:
              loading || !input.trim()
                ? "#E5E7EB"
                : "var(--accent, #2563EB)",
            color: loading || !input.trim() ? "#9CA3AF" : "#fff",
            border: "none",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            flexShrink: 0,
            alignSelf: "flex-start",
          }}
        >
          {loading ? "…" : "Ask"}
        </button>
      </div>
    </div>
  );
}
