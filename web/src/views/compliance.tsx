import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, CircleAlert, CircleHelp, MessageSquare, RefreshCw } from "lucide-react";
import { api, type ComplianceResultItem, type ComplianceRunResponse } from "../api";
import { trackEvent } from "../analytics";

/* ── CompliancePanel ── */

type CompliancePanelProps = {
  projectId: string;
  onUploadDrawing?: () => void;
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

export function CompliancePanel({ projectId, onUploadDrawing }: CompliancePanelProps) {
  const [runResult, setRunResult] = useState<ComplianceRunResponse | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(true);
  const [matrixLoadMessage, setMatrixLoadMessage] = useState<string | null>(null);
  const [matrixLoadTone, setMatrixLoadTone] = useState<"info" | "error">("info");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadPrompted, setUploadPrompted] = useState(false);
  const resultVersionRef = useRef(0);

  const loadMatrix = useCallback(async () => {
    const requestVersion = resultVersionRef.current;
    setMatrixLoading(true);
    setMatrixLoadMessage(null);
    const r = await api.compliance.matrix(projectId);
    setMatrixLoading(false);
    if (requestVersion !== resultVersionRef.current) {
      return;
    }
    if (r.kind === "ok") {
      setRunResult(r.data);
      return;
    }
    if (r.kind === "auth") {
      setMatrixLoadTone("error");
      setMatrixLoadMessage("Sign in required to load saved compliance results.");
    } else if (r.kind === "missing") {
      setMatrixLoadTone("info");
      setMatrixLoadMessage("No saved compliance matrix is available for this project yet.");
    } else if (r.kind === "notBuilt") {
      setMatrixLoadTone("info");
      setMatrixLoadMessage("Saved compliance matrix loading is not available on this server yet.");
    } else if (r.kind === "error") {
      setMatrixLoadTone("error");
      setMatrixLoadMessage(r.message);
    } else {
      setMatrixLoadTone("error");
      setMatrixLoadMessage("Could not reach server to load saved compliance results.");
    }
  }, [projectId]);

  useEffect(() => {
    void loadMatrix();
  }, [loadMatrix]);

  async function retryMatrixLoad() {
    setError(null);
    await loadMatrix();
  }

  async function runCheck() {
    resultVersionRef.current += 1;
    setLoading(true);
    setError(null);
    const r = await api.compliance.run(projectId);
    setLoading(false);
    if (r.kind === "ok") {
      setRunResult(r.data);
      setMatrixLoadMessage(null);
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

  function handleUploadDrawing() {
    setUploadPrompted(true);
    onUploadDrawing?.();
  }

  const results = runResult?.results ?? [];
  const passCount = results.filter((r) => r.status === "likely_pass").length;
  const failCount = results.filter((r) => r.status === "likely_fail").length;
  const moreInfoCount = results.filter((r) => r.status === "needs_more_info").length;
  const unsupportedCount = results.filter((r) => r.status === "unsupported").length;
  const actionableCount = passCount + failCount;
  const allNeedMoreInfo = results.length > 0 && actionableCount === 0 && moreInfoCount > 0;

  return (
    <div style={{ padding: "0 0 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Compliance check</h3>
          {results.length > 0 && (
            <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
              {actionableCount > 0
                ? `${passCount} likely pass · ${failCount} likely fail${moreInfoCount > 0 ? ` · ${moreInfoCount} need a measurement` : ""}`
                : moreInfoCount > 0
                  ? `Ready to check ${moreInfoCount + actionableCount} rules — upload a drawing to fill in measurements`
                  : `${unsupportedCount} check${unsupportedCount === 1 ? "" : "s"} have no rule loaded yet`}
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

      {matrixLoading && !runResult && (
        <div style={{ color: "#6b7280", fontSize: 14, marginBottom: 12 }}>
          Loading saved compliance results...
        </div>
      )}

      {matrixLoadMessage && !runResult && (
        <div
          style={{
            background: matrixLoadTone === "error" ? "#fef2f2" : "#eff6ff",
            border: `1px solid ${matrixLoadTone === "error" ? "#fecaca" : "#bfdbfe"}`,
            borderRadius: 6,
            padding: "8px 12px",
            color: matrixLoadTone === "error" ? "#b91c1c" : "#1e40af",
            fontSize: 13,
            marginBottom: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          <span>{matrixLoadMessage}</span>
          <button
            onClick={() => void retryMatrixLoad()}
            disabled={matrixLoading}
            style={{
              flexShrink: 0,
              border: "1px solid currentColor",
              borderRadius: 5,
              background: "transparent",
              color: "inherit",
              padding: "4px 8px",
              fontSize: 12,
              cursor: matrixLoading ? "not-allowed" : "pointer",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {results.length === 0 && !loading && !matrixLoading && !matrixLoadMessage && !error && (
        <div style={{ color: "#6b7280", fontSize: 14 }}>
          No compliance results yet. Run a check to get started.
        </div>
      )}

      {allNeedMoreInfo && (
        <div
          style={{
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 8,
            padding: "12px 14px",
            marginBottom: 12,
          }}
        >
          <div style={{ fontWeight: 600, color: "#1e40af", fontSize: 14, marginBottom: 4 }}>
            Add measurements to see your results
          </div>
          <div style={{ fontSize: 13, color: "#1e40af", marginBottom: 8 }}>
            We have {moreInfoCount} approved rule{moreInfoCount === 1 ? "" : "s"} ready to check against this property. Upload a drawing or enter measurements to see likely pass/fail per check.
          </div>
          {onUploadDrawing && (
            <button
              onClick={handleUploadDrawing}
              style={{
                fontSize: 13,
                padding: "6px 14px",
                background: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: 5,
                cursor: "pointer",
                fontWeight: 500,
              }}
            >
              Upload drawing
            </button>
          )}
        </div>
      )}

      {results
        .filter((item) => !(allNeedMoreInfo && item.status === "needs_more_info"))
        .filter((item) => item.status !== "unsupported")
        .map((item) => (
          <ComplianceResultRow
            key={item.result_id}
            item={item}
            onUploadDrawing={item.status === "needs_more_info" ? handleUploadDrawing : undefined}
            onReviewRecorded={updateReviewedResult}
          />
        ))}

      {runResult?.advisory_disclaimer && (
        <div
          style={{
            marginTop: 16,
            fontSize: 11,
            color: "#9ca3af",
            textAlign: "center",
            fontStyle: "italic",
          }}
        >
          {runResult.advisory_disclaimer}
        </div>
      )}

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
          Use the Documents upload area to add a drawing or plan for this check.
        </div>
      )}
    </div>
  );
}
