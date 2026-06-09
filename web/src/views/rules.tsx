import { useEffect, useState } from "react";
import { api, type ApiResult, type CandidateSummary, type RuleSummary } from "../api";
import { Icon } from "../components/common";

/* ── rules view ── */

function lifecycleBadge(status: string) {
  const map: Record<string, { bg: string; color: string }> = {
    auto_accepted: { bg: "var(--mint)", color: "var(--green-800)" },
    approved: { bg: "#EFF6FF", color: "#1D4ED8" },
    rejected: { bg: "#FEF2F2", color: "#B91C1C" },
    stale: { bg: "#EFF1F1", color: "var(--ink-soft)" },
  };
  const s = map[status] ?? { bg: "#EFF1F1", color: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "3px 9px", borderRadius: 99, background: s.bg, color: s.color, display: "inline-block" }}>
      {status}
    </span>
  );
}

function reviewBadge(status: string) {
  const map: Record<string, { bg: string; color: string }> = {
    pending: { bg: "#FEF9C3", color: "#92400E" },
    accepted: { bg: "var(--mint)", color: "var(--green-800)" },
    rejected: { bg: "#FEF2F2", color: "#B91C1C" },
    promoted: { bg: "#EFF6FF", color: "#1D4ED8" },
  };
  const s = map[status] ?? { bg: "#EFF1F1", color: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".68rem", fontWeight: 700, padding: "3px 9px", borderRadius: 99, background: s.bg, color: s.color, display: "inline-block" }}>
      {status}
    </span>
  );
}

function formatValueJson(v: number | object | null): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return String(v);
  return JSON.stringify(v);
}

function RuleDetail({ rule, onBack, onApproved }: { rule: RuleSummary; onBack: () => void; onApproved?: (ruleId: string) => void }) {
  const [approving, setApproving] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);

  async function handleApprove() {
    setApproving(true);
    setApproveError(null);
    const r = await api.approveRule(rule.id);
    setApproving(false);
    if (r.kind === "ok") {
      onApproved?.(rule.id);
      onBack();
    } else {
      setApproveError(r.kind === "error" ? (r.message ?? "Failed to approve") : "Could not reach server");
    }
  }

  return (
    <div className="panel" style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "5px 10px" }} onClick={onBack}>← Back</button>
        <span style={{ fontWeight: 700, fontSize: ".9rem" }}>{rule.rule_key}</span>
        {lifecycleBadge(rule.lifecycle_status)}
        {(rule.lifecycle_status === "auto_accepted" || rule.lifecycle_status === "pending_review") && (
          <button
            className="btn"
            style={{ fontSize: ".75rem", padding: "5px 12px", marginLeft: "auto" }}
            onClick={() => void handleApprove()}
            disabled={approving}
          >
            {approving ? "Approving…" : "Approve rule"}
          </button>
        )}
      </div>
      {approveError && <p style={{ color: "#b91c1c", fontSize: 13 }}>{approveError}</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: ".83rem" }}>
        {[
          ["ID", rule.id],
          ["Rule key", rule.rule_key],
          ["Rule type", rule.rule_type],
          ["Operator", rule.operator],
          ["Value", formatValueJson(rule.value_json)],
          ["Unit", rule.unit ?? "—"],
          ["Confidence", `${Math.round(rule.confidence * 100)}%`],
          ["Lifecycle status", rule.lifecycle_status],
          ["Clause ID", rule.clause_id ?? "—"],
          ["Source version ID", rule.source_version_id ?? "—"],
          ["Created at", rule.created_at],
        ].map(([label, val]) => (
          <div key={label} style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--line)", padding: "4px 0" }}>
            <span style={{ color: "var(--ink-soft)", minWidth: 140, flexShrink: 0 }}>{label}</span>
            <span style={{ fontWeight: 500, wordBreak: "break-all" }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CandidateDetail({ candidate, onBack }: { candidate: CandidateSummary; onBack: () => void }) {
  const validators = candidate.validator_results_json
    ? Object.entries(candidate.validator_results_json)
    : [];
  return (
    <div className="panel" style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "5px 10px" }} onClick={onBack}>← Back</button>
        <span style={{ fontWeight: 700, fontSize: ".9rem" }}>{candidate.rule_key ?? "pending"}</span>
        {reviewBadge(candidate.review_status)}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: ".83rem" }}>
        {[
          ["ID", candidate.id],
          ["Rule key", candidate.rule_key ?? "—"],
          ["Operator", candidate.operator ?? "—"],
          ["Value", formatValueJson(candidate.value_json)],
          ["Unit", candidate.unit ?? "—"],
          ["Confidence", candidate.confidence !== null ? `${Math.round(candidate.confidence * 100)}%` : "—"],
          ["Review status", candidate.review_status],
          ["Extraction pass", candidate.extraction_pass !== null ? String(candidate.extraction_pass) : "—"],
          ["Clause ID", candidate.clause_id ?? "—"],
          ["Auto promoted at", candidate.auto_promoted_at ?? "—"],
        ].map(([label, val]) => (
          <div key={label} style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--line)", padding: "4px 0" }}>
            <span style={{ color: "var(--ink-soft)", minWidth: 140, flexShrink: 0 }}>{label}</span>
            <span style={{ fontWeight: 500, wordBreak: "break-all" }}>{val}</span>
          </div>
        ))}
      </div>
      {candidate.quote && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", marginBottom: 4 }}>Source quote</div>
          <pre style={{ background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 10, padding: "10px 14px", fontSize: ".78rem", whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0 }}>
            {candidate.quote}
          </pre>
        </div>
      )}
      {validators.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", marginBottom: 6 }}>Validator results</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {validators.map(([name, result]) => (
              <div key={name} style={{ display: "flex", gap: 8, fontSize: ".82rem", padding: "5px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ fontSize: ".85rem" }}>{result.pass ? "✓" : "✗"}</span>
                <span style={{ color: result.pass ? "var(--green-800)" : "#B91C1C", fontWeight: 700, minWidth: 140, flexShrink: 0 }}>{name}</span>
                <span style={{ color: "var(--ink-soft)" }}>{result.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function RulesView() {
  const [tab, setTab] = useState<"rules" | "candidates">("rules");
  const [rules, setRules] = useState<ApiResult<RuleSummary[]> | null>(null);
  const [candidates, setCandidates] = useState<ApiResult<CandidateSummary[]> | null>(null);
  const [selectedRule, setSelectedRule] = useState<RuleSummary | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateSummary | null>(null);

  useEffect(() => {
    void api.listRules({ limit: 100 }).then(setRules);
  }, []);

  useEffect(() => {
    void api.listCandidates({ limit: 100 }).then(setCandidates);
  }, []);

  const th: React.CSSProperties = {
    padding: "7px 10px",
    textAlign: "left",
    fontSize: ".72rem",
    fontWeight: 700,
    color: "var(--ink-soft)",
    borderBottom: "2px solid var(--line)",
    whiteSpace: "nowrap",
  };
  const td: React.CSSProperties = {
    padding: "7px 10px",
    fontSize: ".8rem",
    borderBottom: "1px solid var(--line)",
    verticalAlign: "middle",
  };

  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="gavel" />Rules</h3>
        <div style={{ display: "flex", gap: 0, marginBottom: 16, borderBottom: "2px solid var(--line)" }}>
          {(["rules", "candidates"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: "none",
                border: "none",
                borderBottom: tab === t ? "2px solid var(--green-900)" : "2px solid transparent",
                marginBottom: -2,
                padding: "8px 18px",
                fontSize: ".83rem",
                fontWeight: tab === t ? 700 : 500,
                color: tab === t ? "var(--green-900)" : "var(--ink-soft)",
                cursor: "pointer",
              }}
            >
              {t === "rules" ? "Accepted Rules" : "Candidates"}
            </button>
          ))}
        </div>

        {tab === "rules" && (
          <>
            {selectedRule ? (
              <RuleDetail rule={selectedRule} onBack={() => setSelectedRule(null)} onApproved={() => { void api.listRules({ limit: 100 }).then(setRules); }} />
            ) : (
              <>
                {rules === null && <p>Loading…</p>}
                {rules?.kind === "auth" && <div className="state"><Icon name="lock" /><span>Sign in to view rules.</span></div>}
                {rules?.kind === "notBuilt" && <div className="state"><Icon name="construction" /><span>Rules endpoint not yet available.</span></div>}
                {rules?.kind === "missing" && <div className="state"><Icon name="construction" /><span>Rules endpoint not found.</span></div>}
                {(rules?.kind === "error" || rules?.kind === "down") && (
                  <div className="state"><Icon name="error" /><span>Could not load rules ({rules.kind}).</span></div>
                )}
                {rules?.kind === "ok" && rules.data.length === 0 && (
                  <div className="state"><Icon name="sparkles" /><span>No accepted rules yet.</span></div>
                )}
                {rules?.kind === "ok" && rules.data.length > 0 && (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={th}>Rule key</th>
                          <th style={th}>Operator</th>
                          <th style={th}>Value</th>
                          <th style={th}>Unit</th>
                          <th style={th}>Status</th>
                          <th style={th}>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rules.data.map((r) => (
                          <tr
                            key={r.id}
                            style={{ cursor: "pointer" }}
                            onClick={() => setSelectedRule(r)}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--paper)")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                          >
                            <td style={{ ...td, fontWeight: 600 }}>{r.rule_key}</td>
                            <td style={td}>{r.operator}</td>
                            <td style={td}>{formatValueJson(r.value_json)}</td>
                            <td style={td}>{r.unit ?? "—"}</td>
                            <td style={td}>{lifecycleBadge(r.lifecycle_status)}</td>
                            <td style={td}>{Math.round(r.confidence * 100)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {tab === "candidates" && (
          <>
            {selectedCandidate ? (
              <CandidateDetail candidate={selectedCandidate} onBack={() => setSelectedCandidate(null)} />
            ) : (
              <>
                {candidates === null && <p>Loading…</p>}
                {candidates?.kind === "auth" && <div className="state"><Icon name="lock" /><span>Sign in to view candidates.</span></div>}
                {candidates?.kind === "notBuilt" && <div className="state"><Icon name="construction" /><span>Candidates endpoint not yet available.</span></div>}
                {candidates?.kind === "missing" && <div className="state"><Icon name="construction" /><span>Candidates endpoint not found.</span></div>}
                {(candidates?.kind === "error" || candidates?.kind === "down") && (
                  <div className="state"><Icon name="error" /><span>Could not load candidates ({candidates.kind}).</span></div>
                )}
                {candidates?.kind === "ok" && candidates.data.length === 0 && (
                  <div className="state"><Icon name="sparkles" /><span>No candidates yet.</span></div>
                )}
                {candidates?.kind === "ok" && candidates.data.length > 0 && (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={th}>Rule key</th>
                          <th style={th}>Quote (excerpt)</th>
                          <th style={th}>Status</th>
                          <th style={th}>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidates.data.map((c) => (
                          <tr
                            key={c.id}
                            style={{ cursor: "pointer" }}
                            onClick={() => setSelectedCandidate(c)}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--paper)")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                          >
                            <td style={{ ...td, fontWeight: 600 }}>{c.rule_key ?? <span style={{ color: "var(--ink-faint)" }}>pending</span>}</td>
                            <td style={{ ...td, maxWidth: 260 }}>
                              <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--ink-soft)" }}>
                                {c.quote ? c.quote.slice(0, 80) + (c.quote.length > 80 ? "…" : "") : "—"}
                              </span>
                            </td>
                            <td style={td}>{reviewBadge(c.review_status)}</td>
                            <td style={td}>{c.confidence !== null ? `${Math.round(c.confidence * 100)}%` : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
