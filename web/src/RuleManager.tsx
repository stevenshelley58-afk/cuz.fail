/**
 * RuleManager — lists pending rule candidates and allows approve/reject.
 * Intended for admin/operator use (OPERATOR/ADMIN roles).
 */

import { useEffect, useState } from "react";
import { api, type CandidateSummary } from "./api";

type ActionState = "idle" | "promoting" | "rejecting" | "done_promote" | "done_reject" | "error";

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
            borderRadius: 99,
          }}
        />
      </div>
      <span style={{ fontSize: ".72rem", color, fontWeight: 700, minWidth: 28 }}>
        {pct}%
      </span>
    </div>
  );
}

function ValidatorResults({
  results,
}: {
  results: CandidateSummary["validator_results_json"];
}) {
  if (!results || Object.keys(results).length === 0) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ fontSize: ".72rem", fontWeight: 600, color: "var(--ink-soft, #6B7280)", marginBottom: 4 }}>
        Validator results
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {Object.entries(results).map(([key, v]) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: ".78rem" }}>
            <span
              style={{
                fontWeight: 700,
                color: v.pass ? "#15803D" : "#B91C1C",
              }}
            >
              {v.pass ? "✓" : "✗"}
            </span>
            <span style={{ color: "var(--ink-soft, #6B7280)" }}>{key}</span>
            {v.detail && (
              <span style={{ color: "var(--ink-faint, #9CA3AF)", fontStyle: "italic" }}>
                — {v.detail}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function CandidateCard({
  candidate,
  onAction,
}: {
  candidate: CandidateSummary;
  onAction: (id: string, action: "promote" | "reject") => Promise<void>;
}) {
  const [state, setState] = useState<ActionState>("idle");
  const [expanded, setExpanded] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const isDone = state === "done_promote" || state === "done_reject";
  const isBusy = state === "promoting" || state === "rejecting";

  async function handle(action: "promote" | "reject") {
    setState(action === "promote" ? "promoting" : "rejecting");
    setErr(null);
    try {
      await onAction(candidate.id, action);
      setState(action === "promote" ? "done_promote" : "done_reject");
    } catch (e) {
      setState("error");
      setErr(e instanceof Error ? e.message : "Unknown error");
    }
  }

  return (
    <div
      style={{
        border: "1px solid var(--line, #E5E7EB)",
        borderRadius: 10,
        overflow: "hidden",
        marginBottom: 8,
        opacity: isDone ? 0.6 : 1,
      }}
    >
      <div
        style={{
          padding: "10px 14px",
          background: "var(--paper, #FAFAFA)",
          display: "flex",
          alignItems: "flex-start",
          gap: 10,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, fontSize: ".88rem", color: "var(--ink, #111)" }}>
              {candidate.rule_key ?? "(no rule_key)"}
            </span>
            {candidate.operator && (
              <span
                style={{
                  fontSize: ".72rem",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: 99,
                  background: "#EFF6FF",
                  color: "#1D4ED8",
                  border: "1px solid #BFDBFE",
                }}
              >
                {candidate.operator}
              </span>
            )}
            {candidate.value_json !== null && candidate.value_json !== undefined && (
              <span style={{ fontSize: ".82rem", color: "var(--ink-soft, #6B7280)" }}>
                {String(candidate.value_json)}
                {candidate.unit ? ` ${candidate.unit}` : ""}
              </span>
            )}
          </div>

          {candidate.confidence !== null && (
            <div style={{ marginTop: 6, maxWidth: 180 }}>
              <ConfidenceBar value={candidate.confidence} />
            </div>
          )}

          {candidate.clause_id && (
            <div style={{ fontSize: ".78rem", color: "var(--ink-soft, #6B7280)", marginTop: 4 }}>
              Clause: {candidate.clause_id}
            </div>
          )}

          {candidate.quote && (
            <div
              style={{
                fontSize: ".78rem",
                color: "var(--ink-soft, #6B7280)",
                fontStyle: "italic",
                marginTop: 4,
                cursor: "pointer",
              }}
              onClick={() => setExpanded((e) => !e)}
            >
              {expanded
                ? candidate.quote
                : candidate.quote.length > 120
                ? candidate.quote.slice(0, 120) + "… (more)"
                : candidate.quote}
            </div>
          )}

          {expanded && <ValidatorResults results={candidate.validator_results_json} />}
        </div>

        {!isDone && (
          <div style={{ display: "flex", gap: 6, flexShrink: 0, alignItems: "center" }}>
            <button
              disabled={isBusy}
              onClick={() => handle("promote")}
              style={{
                padding: "5px 14px",
                borderRadius: 7,
                fontWeight: 600,
                fontSize: ".78rem",
                background: isBusy ? "#E5E7EB" : "#F0FDF4",
                color: isBusy ? "#9CA3AF" : "#15803D",
                border: "1px solid #BBF7D0",
                cursor: isBusy ? "not-allowed" : "pointer",
              }}
            >
              {state === "promoting" ? "Approving…" : "Approve"}
            </button>
            <button
              disabled={isBusy}
              onClick={() => handle("reject")}
              style={{
                padding: "5px 14px",
                borderRadius: 7,
                fontWeight: 600,
                fontSize: ".78rem",
                background: isBusy ? "#E5E7EB" : "#FEF2F2",
                color: isBusy ? "#9CA3AF" : "#B91C1C",
                border: "1px solid #FECACA",
                cursor: isBusy ? "not-allowed" : "pointer",
              }}
            >
              {state === "rejecting" ? "Rejecting…" : "Reject"}
            </button>
          </div>
        )}

        {isDone && (
          <span
            style={{
              fontSize: ".78rem",
              fontWeight: 700,
              padding: "4px 10px",
              borderRadius: 99,
              background: state === "done_promote" ? "#F0FDF4" : "#FEF2F2",
              color: state === "done_promote" ? "#15803D" : "#B91C1C",
              border: `1px solid ${state === "done_promote" ? "#BBF7D0" : "#FECACA"}`,
              flexShrink: 0,
            }}
          >
            {state === "done_promote" ? "Approved" : "Rejected"}
          </span>
        )}
      </div>

      {err && (
        <div
          style={{
            padding: "6px 14px",
            background: "#FEF2F2",
            fontSize: ".78rem",
            color: "#B91C1C",
            borderTop: "1px solid #FECACA",
          }}
        >
          {err}
        </div>
      )}
    </div>
  );
}

export function RuleManager() {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("pending");

  async function fetchCandidates() {
    setLoading(true);
    setError(null);
    const r = await api.listCandidates({ review_status: filterStatus });
    if (r.kind === "ok") {
      setCandidates(Array.isArray(r.data) ? r.data : []);
    } else if (r.kind === "error") {
      setError(r.message);
    } else if (r.kind === "down") {
      setError("API unreachable: " + r.message);
    } else if (r.kind === "notBuilt") {
      setError("Rule candidates endpoint not yet available.");
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchCandidates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus]);

  async function handleAction(id: string, action: "promote" | "reject") {
    const fn = action === "promote" ? api.candidates.promote : api.candidates.reject;
    const r = await fn(id);
    if (r.kind !== "ok") {
      const msg =
        r.kind === "error"
          ? r.message
          : r.kind === "down"
          ? "API unreachable: " + r.message
          : "Failed";
      throw new Error(msg);
    }
  }

  const pending = candidates.filter((c) => c.review_status === "pending");
  const others = candidates.filter((c) => c.review_status !== "pending");

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
          gap: 8,
        }}
      >
        <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "var(--ink, #111)" }}>
          Rule Candidates
        </h3>
        <div style={{ display: "flex", gap: 6 }}>
          {["pending", "approved", "rejected", "all"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s === "all" ? "" : s)}
              style={{
                padding: "4px 12px",
                borderRadius: 7,
                fontSize: ".78rem",
                fontWeight: 600,
                background:
                  (filterStatus === "" && s === "all") || filterStatus === s
                    ? "var(--accent, #2563EB)"
                    : "var(--paper, #FAFAFA)",
                color:
                  (filterStatus === "" && s === "all") || filterStatus === s
                    ? "#fff"
                    : "var(--ink-soft, #6B7280)",
                border: "1px solid var(--line, #E5E7EB)",
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {s}
            </button>
          ))}
          <button
            onClick={fetchCandidates}
            style={{
              padding: "4px 12px",
              borderRadius: 7,
              fontSize: ".78rem",
              fontWeight: 600,
              background: "var(--paper, #FAFAFA)",
              color: "var(--ink-soft, #6B7280)",
              border: "1px solid var(--line, #E5E7EB)",
              cursor: "pointer",
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            fontSize: ".82rem",
            color: "#B91C1C",
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderRadius: 8,
            padding: "8px 12px",
            marginBottom: 10,
          }}
        >
          {error}
        </div>
      )}

      {loading && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "12px 0" }}>
          Loading candidates…
        </div>
      )}

      {!loading && candidates.length === 0 && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "12px 0" }}>
          No candidates found.
        </div>
      )}

      {!loading && pending.length > 0 && (
        <>
          <div
            style={{
              fontSize: ".78rem",
              fontWeight: 700,
              color: "#B45309",
              background: "#FFFBEB",
              border: "1px solid #FDE68A",
              borderRadius: 8,
              padding: "6px 12px",
              marginBottom: 8,
            }}
          >
            {pending.length} pending candidate{pending.length !== 1 ? "s" : ""} awaiting review
          </div>
          {pending.map((c) => (
            <CandidateCard key={c.id} candidate={c} onAction={handleAction} />
          ))}
        </>
      )}

      {!loading && others.length > 0 && (
        <>
          {pending.length > 0 && (
            <div
              style={{
                fontSize: ".78rem",
                fontWeight: 600,
                color: "var(--ink-soft, #6B7280)",
                marginTop: 12,
                marginBottom: 6,
              }}
            >
              Previously reviewed
            </div>
          )}
          {others.map((c) => (
            <CandidateCard key={c.id} candidate={c} onAction={handleAction} />
          ))}
        </>
      )}
    </div>
  );
}
