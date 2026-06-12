import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, CircleHelp, MessageSquare, RefreshCw } from "lucide-react";
import { api, type ComplianceResultItem, type ComplianceRunResponse } from "../api";
import { trackEvent } from "../analytics";

/* ── CompliancePanel ── */

type CompliancePanelProps = {
  projectId: string;
};

function StatusBadge({ status }: { status: ComplianceResultItem["status"] }) {
  if (status === "likely_pass")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#16a34a", fontWeight: 600 }}>
        <CheckCircle2 size={16} /> Likely pass
      </span>
    );
  if (status === "likely_fail")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#dc2626", fontWeight: 600 }}>
        <CircleAlert size={16} /> Likely fail
      </span>
    );
  if (status === "needs_more_info")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#ca8a04", fontWeight: 600 }}>
        <CircleHelp size={16} /> More info needed
      </span>
    );
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#6b7280", fontWeight: 600 }}>
      — Unsupported
    </span>
  );
}

function ComplianceResultRow({
  item,
  onUploadDrawing,
  onReviewRecorded,
}: {
  item: ComplianceResultItem;
  onUploadDrawing?: () => void;
  onReviewRecorded: (item: ComplianceResultItem) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [reviewDraft, setReviewDraft] = useState(item.review_reason ?? "");
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const drawingEvidence = item.drawing_evidence ?? {};
  const hasDrawingEvidence = Object.keys(drawingEvidence).length > 0;
  const evidenceFactType = typeof drawingEvidence.fact_type === "string" ? drawingEvidence.fact_type : null;
  const evidenceMethod = typeof drawingEvidence.method === "string" ? drawingEvidence.method : null;
  const evidenceDocumentFactId =
    typeof drawingEvidence.document_fact_id === "string" ? drawingEvidence.document_fact_id : null;
  const reviewAction = typeof item.human_override?.action === "string" ? item.human_override.action.replace(/_/g, " ") : null;

  useEffect(() => {
    setReviewDraft(item.review_reason ?? "");
    setReviewError(null);
  }, [item.result_id, item.review_reason]);

  async function recordReview() {
    const reason = reviewDraft.trim();
    if (!reason) {
      setReviewError("Review note is required.");
      return;
    }
    setReviewSaving(true);
    setReviewError(null);
    const response = await api.compliance.recordReview(item.result_id, "operator_note", reason);
    setReviewSaving(false);
    if (response.kind === "ok") {
      onReviewRecorded(response.data);
    } else if (response.kind === "auth") {
      setReviewError("Owner or operator access required.");
    } else if (response.kind === "missing") {
      setReviewError("This result is no longer available.");
    } else if (response.kind === "error") {
      setReviewError(response.message);
    } else {
      setReviewError("Could not record review.");
    }
  }

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        marginBottom: 8,
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontWeight: 500, fontSize: 14 }}>{item.display_name ?? item.check_key}</span>
        <StatusBadge status={item.status} />
      </button>

      {expanded && (
        <div style={{ padding: "0 14px 14px", fontSize: 13, color: "#374151" }}>
          {(item.measured_value !== null || item.threshold_value !== null) && (
            <div
              style={{
                display: "flex",
                gap: 24,
                background: "#f9fafb",
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 10,
              }}
            >
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Measured</div>
                <div style={{ fontWeight: 600 }}>
                  {item.measured_value ?? "—"}{" "}
                  {item.threshold_unit ? <span style={{ fontWeight: 400, color: "#6b7280" }}>{item.threshold_unit}</span> : null}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Threshold</div>
                <div style={{ fontWeight: 600 }}>
                  {item.threshold_value ?? "—"}{" "}
                  {item.threshold_unit ? <span style={{ fontWeight: 400, color: "#6b7280" }}>{item.threshold_unit}</span> : null}
                </div>
              </div>
            </div>
          )}

          {item.rule_quote && (
            <blockquote
              style={{
                margin: "0 0 8px",
                paddingLeft: 10,
                borderLeft: "3px solid #d1d5db",
                color: "#4b5563",
                fontStyle: "italic",
                fontSize: 12,
              }}
            >
              {item.rule_quote}
            </blockquote>
          )}

          {item.citation && (
            <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
              <span style={{ fontWeight: 500 }}>Source:</span> {item.citation}
            </div>
          )}

          {hasDrawingEvidence && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 8,
                fontSize: 12,
                color: "#166534",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 3 }}>Drawing evidence</div>
              <div>
                {[evidenceFactType, evidenceMethod, evidenceDocumentFactId ? `fact ${evidenceDocumentFactId}` : null]
                  .filter(Boolean)
                  .join(" · ") || "Promoted drawing evidence recorded for this check."}
              </div>
            </div>
          )}

          {item.status === "needs_more_info" && (
            <div
              style={{
                background: "#fffbeb",
                border: "1px solid #fde68a",
                borderRadius: 6,
                padding: "8px 12px",
                marginTop: 8,
              }}
            >
              <div style={{ fontWeight: 500, marginBottom: 4, color: "#92400e" }}>Missing information</div>
              {item.missing_info_reason && (
                <div style={{ fontSize: 12, marginBottom: 6 }}>
                  Reason: {item.missing_info_reason.replace(/_/g, " ")}
                </div>
              )}
              {item.missing_data && item.missing_data.length > 0 ? (
                <ul style={{ margin: "0 0 8px", paddingLeft: 16 }}>
                  {item.missing_data.map((d) => (
                    <li key={d} style={{ fontSize: 12 }}>{d}</li>
                  ))}
                </ul>
              ) : null}
              {onUploadDrawing && (
                <button
                  onClick={onUploadDrawing}
                  style={{
                    fontSize: 12,
                    padding: "4px 10px",
                    background: "#f59e0b",
                    color: "#fff",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                  }}
                >
                  Upload drawing to provide this data
                </button>
              )}
            </div>
          )}

          <div
            style={{
              borderTop: "1px solid #e5e7eb",
              marginTop: 12,
              paddingTop: 12,
            }}
          >
            {item.review_reason && (
              <div style={{ fontSize: 12, color: "#4b5563", marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>Review:</span> {item.review_reason}
                {reviewAction ? <span style={{ color: "#6b7280" }}> ({reviewAction})</span> : null}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <textarea
                value={reviewDraft}
                onChange={(event) => setReviewDraft(event.target.value)}
                rows={2}
                aria-label={`Review note for ${item.display_name ?? item.check_key}`}
                style={{
                  flex: 1,
                  minWidth: 0,
                  resize: "vertical",
                  border: "1px solid #d1d5db",
                  borderRadius: 6,
                  padding: "7px 9px",
                  font: "inherit",
                  fontSize: 12,
                  color: "#111827",
                }}
              />
              <button
                onClick={() => void recordReview()}
                disabled={reviewSaving}
                title="Record review"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "7px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: 6,
                  background: reviewSaving ? "#f3f4f6" : "#fff",
                  color: reviewSaving ? "#6b7280" : "#111827",
                  cursor: reviewSaving ? "not-allowed" : "pointer",
                  fontSize: 12,
                  whiteSpace: "nowrap",
                }}
              >
                <MessageSquare size={14} />
                {reviewSaving ? "Saving" : "Record"}
              </button>
            </div>
            {reviewError && <div style={{ fontSize: 12, color: "#b91c1c", marginTop: 6 }}>{reviewError}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

export function CompliancePanel({ projectId }: CompliancePanelProps) {
  const [runResult, setRunResult] = useState<ComplianceRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadPrompted, setUploadPrompted] = useState(false);

  useEffect(() => {
    api.compliance.matrix(projectId).then((r) => {
      if (r.kind === "ok") setRunResult(r.data);
    });
  }, [projectId]);

  async function runCheck() {
    setLoading(true);
    setError(null);
    const r = await api.compliance.run(projectId);
    setLoading(false);
    if (r.kind === "ok") {
      setRunResult(r.data);
      trackEvent("compliance_run", { result_count: r.data.results.length, status: r.data.status });
    } else if (r.kind === "notBuilt") {
      setError("Compliance check endpoint not yet available on this server.");
    } else if (r.kind === "auth") {
      setError("Sign in required.");
    } else if (r.kind === "error") {
      setError(r.message);
    } else {
      setError("Could not reach server.");
    }
  }

  function updateReviewedResult(updated: ComplianceResultItem) {
    setRunResult((current) => {
      if (!current) return current;
      return {
        ...current,
        results: current.results.map((item) => (item.result_id === updated.result_id ? updated : item)),
      };
    });
  }

  const results = runResult?.results ?? [];
  const passCount = results.filter((r) => r.status === "likely_pass").length;
  const failCount = results.filter((r) => r.status === "likely_fail").length;
  const moreInfoCount = results.filter((r) => r.status === "needs_more_info").length;

  return (
    <div style={{ padding: "0 0 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Compliance check</h3>
          {results.length > 0 && (
            <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
              {passCount} likely pass · {failCount} likely fail · {moreInfoCount} needs info · {results.filter(r => r.status === "unsupported").length} unsupported
            </div>
          )}
        </div>
        <button
          onClick={() => void runCheck()}
          disabled={loading}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "8px 16px",
            background: loading ? "#e5e7eb" : "#2563eb",
            color: loading ? "#6b7280" : "#fff",
            border: "none",
            borderRadius: 6,
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          <RefreshCw size={15} style={loading ? { animation: "spin 1s linear infinite" } : {}} />
          {loading ? "Running…" : "Run compliance check"}
        </button>
      </div>

      {error && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#b91c1c",
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {runResult?.advisory_disclaimer && (
        <div
          style={{
            background: "#fffbeb",
            border: "1px solid #fcd34d",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#92400e",
            fontSize: 12,
            marginBottom: 12,
          }}
        >
          {runResult.advisory_disclaimer}
        </div>
      )}

      {results.length === 0 && !loading && !error && (
        <div style={{ color: "#6b7280", fontSize: 14 }}>
          No compliance results yet. Run a check to get started.
        </div>
      )}

      {results.map((item) => (
        <ComplianceResultRow
          key={item.result_id}
          item={item}
          onUploadDrawing={item.status === "needs_more_info" ? () => setUploadPrompted(true) : undefined}
          onReviewRecorded={updateReviewedResult}
        />
      ))}

      {uploadPrompted && (
        <div
          style={{
            marginTop: 12,
            padding: "10px 14px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 8,
            fontSize: 13,
            color: "#1e40af",
          }}
        >
          Scroll down to the Documents section to upload a drawing or plan.
        </div>
      )}
    </div>
  );
}
