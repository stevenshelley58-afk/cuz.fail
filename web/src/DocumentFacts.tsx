/**
 * DocumentFacts — lists extracted facts from a document and allows
 * promoting (confirming) individual facts.
 *
 * Props:
 *   docId — the document ID to fetch facts for
 *   initialFacts — optionally pass facts already fetched (e.g. from upload response)
 */

import { useEffect, useState } from "react";
import { api, type ExtractedFact } from "./api";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round((value ?? 0) * 100);
  const color =
    pct >= 80 ? "#15803D" : pct >= 50 ? "#B45309" : "#B91C1C";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          flex: 1,
          height: 4,
          background: "#E5E7EB",
          borderRadius: 99,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            transition: "width .3s",
            borderRadius: 99,
          }}
        />
      </div>
      <span
        style={{
          fontSize: ".72rem",
          color,
          fontWeight: 700,
          minWidth: 28,
          textAlign: "right",
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

function FactCard({
  fact,
  docId,
  onConfirmed,
}: {
  fact: ExtractedFact;
  docId: string;
  onConfirmed: (factKey: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(fact.confirmed ?? false);
  const [err, setErr] = useState<string | null>(null);

  async function confirm() {
    setConfirming(true);
    setErr(null);
    const r = await api.documents.confirmFact(docId, fact.fact_key);
    if (r.kind === "ok") {
      setConfirmed(true);
      onConfirmed(fact.fact_key);
    } else {
      const msg =
        r.kind === "error"
          ? r.message
          : r.kind === "down"
          ? "API unreachable: " + r.message
          : "Failed to confirm";
      setErr(msg);
    }
    setConfirming(false);
  }

  return (
    <div
      style={{
        border: "1px solid var(--line, #E5E7EB)",
        borderRadius: 10,
        padding: "10px 14px",
        marginBottom: 8,
        background: confirmed ? "#F0FDF4" : "#fff",
        borderColor: confirmed ? "#BBF7D0" : "var(--line, #E5E7EB)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 10,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontWeight: 700,
              fontSize: ".85rem",
              color: "var(--ink, #111)",
              marginBottom: 4,
              textTransform: "capitalize",
            }}
          >
            {fact.fact_key.replace(/_/g, " ")}
          </div>

          {fact.numeric_value !== null && fact.numeric_value !== undefined && (
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--ink, #111)", marginBottom: 6 }}>
              {fact.numeric_value}
              {fact.unit ? (
                <span style={{ fontSize: ".78rem", fontWeight: 400, color: "var(--ink-soft, #6B7280)", marginLeft: 4 }}>
                  {fact.unit}
                </span>
              ) : null}
            </div>
          )}

          <ConfidenceBar value={fact.confidence} />

          {fact.source_text && (
            <div
              style={{
                marginTop: 8,
                fontSize: ".78rem",
                color: "var(--ink-soft, #6B7280)",
                fontStyle: "italic",
                borderLeft: "2px solid var(--line, #E5E7EB)",
                paddingLeft: 8,
              }}
            >
              {fact.source_text.length > 200
                ? fact.source_text.slice(0, 200) + "…"
                : fact.source_text}
            </div>
          )}
        </div>

        <div style={{ flexShrink: 0 }}>
          {confirmed ? (
            <span
              style={{
                fontSize: ".72rem",
                fontWeight: 700,
                padding: "3px 10px",
                borderRadius: 99,
                background: "#F0FDF4",
                color: "#15803D",
                border: "1px solid #BBF7D0",
              }}
            >
              Confirmed
            </span>
          ) : (
            <button
              disabled={confirming}
              onClick={confirm}
              style={{
                padding: "5px 14px",
                borderRadius: 7,
                fontWeight: 600,
                fontSize: ".78rem",
                background: confirming ? "#E5E7EB" : "#EFF6FF",
                color: confirming ? "#9CA3AF" : "#1D4ED8",
                border: "1px solid #BFDBFE",
                cursor: confirming ? "not-allowed" : "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {confirming ? "Confirming…" : "Confirm"}
            </button>
          )}
        </div>
      </div>

      {err && (
        <div
          style={{
            marginTop: 6,
            fontSize: ".78rem",
            color: "#B91C1C",
          }}
        >
          {err}
        </div>
      )}
    </div>
  );
}

export function DocumentFacts({
  docId,
  initialFacts,
}: {
  docId: string;
  initialFacts?: ExtractedFact[];
}) {
  const [facts, setFacts] = useState<ExtractedFact[]>(initialFacts ?? []);
  const [loading, setLoading] = useState(!initialFacts);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialFacts) return; // use provided facts
    let cancelled = false;
    setLoading(true);
    api.documents.facts(docId).then((r) => {
      if (cancelled) return;
      if (r.kind === "ok") {
        setFacts(r.data.items ?? []);
      } else if (r.kind === "error") {
        setError(r.message);
      } else if (r.kind === "down") {
        setError("API unreachable: " + r.message);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [docId, initialFacts]);

  function handleConfirmed(factKey: string) {
    setFacts((prev) =>
      prev.map((f) => (f.fact_key === factKey ? { ...f, confirmed: true } : f))
    );
  }

  const confirmedCount = facts.filter((f) => f.confirmed).length;

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 10,
        }}
      >
        <div style={{ fontWeight: 700, fontSize: ".88rem", color: "var(--ink, #111)" }}>
          Extracted Facts
          {facts.length > 0 && (
            <span
              style={{
                marginLeft: 8,
                fontSize: ".72rem",
                fontWeight: 600,
                color: "var(--ink-soft, #6B7280)",
              }}
            >
              {confirmedCount}/{facts.length} confirmed
            </span>
          )}
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "8px 0" }}>
          Loading facts…
        </div>
      )}

      {error && (
        <div
          style={{
            fontSize: ".82rem",
            color: "#B91C1C",
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderRadius: 8,
            padding: "8px 12px",
            marginBottom: 8,
          }}
        >
          {error}
        </div>
      )}

      {!loading && !error && facts.length === 0 && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "8px 0" }}>
          No facts extracted from this document.
        </div>
      )}

      {facts.map((fact) => (
        <FactCard
          key={fact.fact_key}
          fact={fact}
          docId={docId}
          onConfirmed={handleConfirmed}
        />
      ))}
    </div>
  );
}
