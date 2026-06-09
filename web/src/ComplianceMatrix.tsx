/**
 * ComplianceMatrix — displays compliance check results for a project.
 * Shows a "Run Compliance Check" button, then renders a result table
 * with status badges, measured vs threshold values, and expandable
 * citation quotes.
 *
 * Advisory disclaimer is shown at the top of every result set.
 */

import { useEffect, useState } from "react";
import { api, type ComplianceResultItem, type ComplianceRunResponse } from "./api";

/* ── status config ── */

type StatusKey = ComplianceResultItem["status"];

const STATUS_CONFIG: Record<
  StatusKey,
  { label: string; bg: string; color: string; border: string }
> = {
  likely_pass: {
    label: "Likely Pass",
    bg: "#F0FDF4",
    color: "#15803D",
    border: "#BBF7D0",
  },
  likely_fail: {
    label: "Likely Fail",
    bg: "#FEF2F2",
    color: "#B91C1C",
    border: "#FECACA",
  },
  needs_more_info: {
    label: "Needs More Info",
    bg: "#FFFBEB",
    color: "#B45309",
    border: "#FDE68A",
  },
  unsupported: {
    label: "Unsupported",
    bg: "#F9FAFB",
    color: "#6B7280",
    border: "#E5E7EB",
  },
};

function StatusBadge({ status }: { status: StatusKey }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unsupported;
  return (
    <span
      style={{
        fontSize: ".72rem",
        fontWeight: 700,
        padding: "3px 10px",
        borderRadius: 99,
        background: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`,
        display: "inline-flex",
        alignItems: "center",
        whiteSpace: "nowrap",
      }}
    >
      {cfg.label}
    </span>
  );
}

/* ── single result row ── */

function ComplianceResultRow({ item }: { item: ComplianceResultItem }) {
  const [expanded, setExpanded] = useState(false);

  const hasMeasured =
    item.measured_value !== null && item.measured_value !== undefined;
  const hasThreshold =
    item.threshold_value !== null && item.threshold_value !== undefined;
  const hasDetail =
    item.rule_quote || item.citation || (item.missing_data && item.missing_data.length > 0);

  return (
    <div
      style={{
        border: "1px solid var(--line, #E5E7EB)",
        borderRadius: 10,
        overflow: "hidden",
        marginBottom: 6,
      }}
    >
      {/* header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          background: "var(--paper, #FAFAFA)",
          cursor: hasDetail ? "pointer" : "default",
        }}
        onClick={() => hasDetail && setExpanded((e) => !e)}
        role={hasDetail ? "button" : undefined}
        aria-expanded={hasDetail ? expanded : undefined}
      >
        <StatusBadge status={item.status} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: ".88rem", color: "var(--ink, #111)" }}>
            {item.check_name || item.check_key}
          </div>
          {item.check_name && (
            <div style={{ fontSize: ".72rem", color: "var(--ink-soft, #6B7280)", marginTop: 1 }}>
              {item.check_key}
            </div>
          )}
        </div>

        {/* measured vs threshold */}
        {(hasMeasured || hasThreshold) && (
          <div
            style={{
              fontSize: ".78rem",
              color: "var(--ink-soft, #6B7280)",
              textAlign: "right",
              whiteSpace: "nowrap",
            }}
          >
            {hasMeasured && (
              <div>
                <span style={{ color: "var(--ink, #111)", fontWeight: 600 }}>
                  {String(item.measured_value)}
                </span>
                {item.threshold_unit ? ` ${item.threshold_unit}` : ""}
                {" measured"}
              </div>
            )}
            {hasThreshold && (
              <div>
                limit: {String(item.threshold_value)}
                {item.threshold_unit ? ` ${item.threshold_unit}` : ""}
              </div>
            )}
          </div>
        )}

        {hasDetail && (
          <span style={{ fontSize: ".72rem", color: "var(--ink-soft, #6B7280)" }}>
            {expanded ? "▲" : "▼"}
          </span>
        )}
      </div>

      {/* expanded detail */}
      {expanded && hasDetail && (
        <div
          style={{
            padding: "10px 14px",
            borderTop: "1px solid var(--line, #E5E7EB)",
            background: "#fff",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {item.rule_quote && (
            <blockquote
              style={{
                margin: 0,
                padding: "8px 12px",
                background: "#F8FAFC",
                borderLeft: "3px solid var(--line, #E5E7EB)",
                borderRadius: "0 6px 6px 0",
                fontSize: ".82rem",
                color: "var(--ink-soft, #6B7280)",
                fontStyle: "italic",
              }}
            >
              {item.rule_quote}
            </blockquote>
          )}
          {item.citation && (
            <div style={{ fontSize: ".78rem", color: "var(--ink-soft, #6B7280)" }}>
              <span style={{ fontWeight: 600 }}>Source: </span>
              {item.citation}
            </div>
          )}
          {item.missing_data && item.missing_data.length > 0 && (
            <div>
              <div
                style={{
                  fontSize: ".78rem",
                  fontWeight: 600,
                  color: "#B45309",
                  marginBottom: 4,
                }}
              >
                Missing data required:
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: ".78rem", color: "#B45309" }}>
                {item.missing_data.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── advisory disclaimer ── */

const ADVISORY_DISCLAIMER = (
  <div
    style={{
      fontSize: ".78rem",
      fontWeight: 600,
      color: "#B45309",
      background: "#FFFBEB",
      border: "1px solid #FDE68A",
      borderRadius: 10,
      padding: "8px 14px",
      marginBottom: 14,
      display: "flex",
      alignItems: "flex-start",
      gap: 6,
    }}
  >
    <span aria-hidden="true">⚠</span>
    <span>
      Results are advisory only (likely_pass / likely_fail / needs_more_info /
      unsupported). They are not final certifications and must not substitute for
      professional advice or approved council assessment.
    </span>
  </div>
);

/* ── summary counts ── */

function SummaryCounts({ results }: { results: ComplianceResultItem[] }) {
  const counts: Record<StatusKey, number> = {
    likely_pass: 0,
    likely_fail: 0,
    needs_more_info: 0,
    unsupported: 0,
  };
  for (const r of results) {
    if (r.status in counts) counts[r.status]++;
  }
  const cfg = STATUS_CONFIG;
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
      {(Object.keys(counts) as StatusKey[]).map((k) =>
        counts[k] > 0 ? (
          <span
            key={k}
            style={{
              fontSize: ".72rem",
              fontWeight: 700,
              padding: "3px 10px",
              borderRadius: 99,
              background: cfg[k].bg,
              color: cfg[k].color,
              border: `1px solid ${cfg[k].border}`,
            }}
          >
            {counts[k]} {cfg[k].label}
          </span>
        ) : null
      )}
    </div>
  );
}

/* ── main export ── */

export function ComplianceMatrix({ projectId }: { projectId: string }) {
  const [matrix, setMatrix] = useState<ComplianceRunResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchMatrix() {
    setLoading(true);
    setError(null);
    const r = await api.compliance.matrix(projectId);
    if (r.kind === "ok") {
      setMatrix(r.data);
    } else if (r.kind === "missing" || r.kind === "notBuilt") {
      setMatrix(null);
    } else if (r.kind === "error") {
      setError(r.message);
    } else if (r.kind === "down") {
      setError("API unreachable: " + r.message);
    }
    setLoading(false);
  }

  async function runCheck() {
    setRunning(true);
    setError(null);
    const r = await api.compliance.run(projectId);
    if (r.kind === "ok") {
      setMatrix(r.data);
    } else if (r.kind === "error") {
      setError(r.message);
    } else if (r.kind === "down") {
      setError("API unreachable: " + r.message);
    } else if (r.kind === "notBuilt") {
      setError("Compliance check not yet available: " + (r.detail ?? ""));
    }
    setRunning(false);
  }

  useEffect(() => {
    fetchMatrix();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const results = matrix?.results ?? [];

  return (
    <div style={{ marginTop: 16 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
          gap: 8,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: "1rem",
            fontWeight: 700,
            color: "var(--ink, #111)",
          }}
        >
          Compliance Check
        </h3>
        <button
          onClick={runCheck}
          disabled={running}
          style={{
            padding: "6px 16px",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: ".82rem",
            background: running ? "#E5E7EB" : "var(--accent, #2563EB)",
            color: running ? "#9CA3AF" : "#fff",
            border: "none",
            cursor: running ? "not-allowed" : "pointer",
          }}
        >
          {running ? "Running…" : "Run Compliance Check"}
        </button>
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

      {loading && !matrix && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "12px 0" }}>
          Loading…
        </div>
      )}

      {!loading && !error && !matrix && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "12px 0" }}>
          No compliance results yet. Click "Run Compliance Check" to start.
        </div>
      )}

      {matrix && results.length > 0 && (
        <>
          {ADVISORY_DISCLAIMER}
          <SummaryCounts results={results} />
          {results.map((item) => (
            <ComplianceResultRow key={item.check_key} item={item} />
          ))}
        </>
      )}

      {matrix && results.length === 0 && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft, #6B7280)", padding: "12px 0" }}>
          No check results returned. Run the check again or ensure the proposal is configured.
        </div>
      )}
    </div>
  );
}
