import { useEffect, useRef, useState } from "react";
import { AlertCircle, BookOpen, CheckCircle2, Clock3, RefreshCw, Search, Sparkles } from "lucide-react";
import { api, type DocumentEvidenceHit, type DocumentUploadResponse, type ExtractedFact, type ProjectDocumentSummary } from "../api";

/* ── DocumentUpload ── */

const ACTIVE_PARSE_STATUSES = new Set(["parse_pending", "parsing"]);

function isActiveParseStatus(status: string | null | undefined): boolean {
  return Boolean(status && ACTIVE_PARSE_STATUSES.has(status));
}

function parseStatusLabel(status: string | null | undefined, factCount: number): string {
  if (status === "parse_pending") return "Queued";
  if (status === "parsing") return "Parsing";
  if (status === "parse_failed") return "Parse failed";
  return `${factCount} facts`;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "#16a34a" : pct >= 50 ? "#ca8a04" : "#dc2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: "#e5e7eb",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.3s",
          }}
        />
      </div>
      <span style={{ fontSize: 11, color: "#6b7280", minWidth: 32 }}>{pct}%</span>
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
  onConfirmed: (factId: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(fact.confirmed ?? fact.review_status === "confirmed");
  const [promoting, setPromoting] = useState(false);
  const [promoted, setPromoted] = useState(fact.promoted_to_measurement ?? false);
  const [calibrating, setCalibrating] = useState(false);
  const [calibrationRef, setCalibrationRef] = useState(
    typeof fact.metadata?.calibration_ref === "string" ? fact.metadata.calibration_ref : "",
  );
  const [calibrationDraft, setCalibrationDraft] = useState(calibrationRef);
  const [err, setErr] = useState<string | null>(null);
  const factId = fact.fact_id ?? fact.fact_key;
  const needsCalibration = fact.fact_kind === "drawing_dimension" && !calibrationRef;
  const canPromote = fact.numeric_value !== null && Boolean(fact.unit) && !needsCalibration;

  async function confirm() {
    setConfirming(true);
    setErr(null);
    const r = await api.documents.confirmFact(docId, factId);
    setConfirming(false);
    if (r.kind === "ok") {
      setConfirmed(true);
      onConfirmed(factId);
    } else if (r.kind === "notBuilt") {
      setErr("Fact confirmation is not available on this server.");
    } else {
      setErr("Could not confirm fact.");
    }
  }

  async function promote() {
    setPromoting(true);
    setErr(null);
    const r = await api.documents.promoteFact(docId, factId);
    setPromoting(false);
    if (r.kind === "ok") {
      setConfirmed(true);
      setPromoted(true);
      onConfirmed(factId);
    } else if (r.kind === "error") {
      setErr(r.message);
    } else {
      setErr("Could not make this fact available for checks.");
    }
  }

  async function saveCalibration() {
    const nextRef = calibrationDraft.trim();
    if (nextRef.length < 3) {
      setErr("Enter a calibration reference before using this dimension.");
      return;
    }
    setCalibrating(true);
    setErr(null);
    const r = await api.documents.calibrateFact(docId, factId, nextRef);
    setCalibrating(false);
    if (r.kind === "ok") {
      setCalibrationRef(nextRef);
      onConfirmed(factId);
    } else if (r.kind === "error") {
      setErr(r.message);
    } else {
      setErr("Could not save calibration evidence.");
    }
  }

  return (
    <div
      style={{
        border: `1px solid ${confirmed ? "#bbf7d0" : "#e5e7eb"}`,
        borderRadius: 8,
        padding: "10px 14px",
        marginBottom: 8,
        background: confirmed ? "#f0fdf4" : "#fff",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>
            {fact.fact_key.replace(/_/g, " ")}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#111827", marginBottom: 4 }}>
            {fact.numeric_value !== null ? (
              <>
                {fact.numeric_value}
                {fact.unit ? <span style={{ fontWeight: 400, fontSize: 12, color: "#6b7280", marginLeft: 4 }}>{fact.unit}</span> : null}
              </>
            ) : (
              <span style={{ color: "#9ca3af" }}>No numeric value</span>
            )}
          </div>
          <ConfidenceBar value={fact.confidence} />
          {fact.source_text && (
            <div
              style={{
                marginTop: 6,
                fontSize: 11,
                color: "#6b7280",
                fontStyle: "italic",
                background: "#f9fafb",
                borderRadius: 4,
                padding: "4px 8px",
                borderLeft: "2px solid #d1d5db",
              }}
            >
              {fact.source_text.length > 120
                ? fact.source_text.slice(0, 120) + "…"
                : fact.source_text}
            </div>
          )}
          {fact.fact_kind === "drawing_dimension" && !promoted && (
            <div style={{ marginTop: 8, display: "flex", gap: 6, alignItems: "center" }}>
              <input
                value={calibrationDraft}
                onChange={(e) => setCalibrationDraft(e.target.value)}
                placeholder="Calibration ref"
                aria-label={`Calibration reference for ${fact.fact_key.replace(/_/g, " ")}`}
                style={{
                  minWidth: 0,
                  flex: 1,
                  border: "1px solid #d1d5db",
                  borderRadius: 5,
                  padding: "5px 7px",
                  fontSize: 12,
                }}
              />
              <button
                onClick={() => void saveCalibration()}
                disabled={calibrating || calibrationDraft.trim().length < 3}
                style={{
                  fontSize: 12,
                  padding: "5px 8px",
                  background: calibrating || calibrationDraft.trim().length < 3 ? "#e5e7eb" : "#111827",
                  color: calibrating || calibrationDraft.trim().length < 3 ? "#6b7280" : "#fff",
                  border: "none",
                  borderRadius: 5,
                  cursor: calibrating || calibrationDraft.trim().length < 3 ? "not-allowed" : "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                {calibrating ? "Saving..." : calibrationRef ? "Update" : "Save"}
              </button>
            </div>
          )}
        </div>
        <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          {promoted ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#16a34a", fontSize: 12 }}>
              <CheckCircle2 size={14} /> In checks
            </span>
          ) : confirmed ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#16a34a", fontSize: 12 }}>
              <CheckCircle2 size={14} /> Confirmed
            </span>
          ) : (
            <button
              onClick={() => void confirm()}
              disabled={confirming}
              style={{
                fontSize: 12,
                padding: "4px 10px",
                background: confirming ? "#e5e7eb" : "#2563eb",
                color: confirming ? "#6b7280" : "#fff",
                border: "none",
                borderRadius: 4,
                cursor: confirming ? "not-allowed" : "pointer",
              }}
            >
              {confirming ? "Confirming…" : "Confirm"}
            </button>
          )}
          {!promoted && canPromote && (
            <button
              onClick={() => void promote()}
              disabled={promoting}
              aria-label={`Use ${fact.fact_key.replace(/_/g, " ")} in compliance checks`}
              style={{
                fontSize: 12,
                padding: "4px 10px",
                background: promoting ? "#e5e7eb" : "#16a34a",
                color: promoting ? "#6b7280" : "#fff",
                border: "none",
                borderRadius: 4,
                cursor: promoting ? "not-allowed" : "pointer",
              }}
            >
              {promoting ? "Adding..." : "Use in checks"}
            </button>
          )}
        </div>
      </div>
      {err && <div style={{ color: "#dc2626", fontSize: 11, marginTop: 4 }}>{err}</div>}
    </div>
  );
}

export function DocumentUpload({ projectId, focusRequest = 0 }: { projectId: string; focusRequest?: number }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const [documents, setDocuments] = useState<ProjectDocumentSummary[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [factsLoading, setFactsLoading] = useState(false);
  const [confirmedKeys, setConfirmedKeys] = useState<Set<string>>(new Set());
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const [evidenceResults, setEvidenceResults] = useState<DocumentEvidenceHit[]>([]);
  const [evidenceNotice, setEvidenceNotice] = useState<string | null>(null);
  const [evidenceSearching, setEvidenceSearching] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const uploadTargetRef = useRef<HTMLLabelElement>(null);

  useEffect(() => {
    if (focusRequest <= 0) return;
    const target = uploadTargetRef.current;
    if (!target) return;
    target.scrollIntoView({ block: "center", behavior: "smooth" });
    target.focus();
  }, [focusRequest]);

  async function refreshDocuments() {
    const r = await api.documents.listForProject(projectId);
    if (r.kind === "ok") {
      setDocuments(r.data.items);
      setListError(null);
    } else if (r.kind !== "auth" && r.kind !== "missing") {
      setListError("Could not refresh document status.");
    }
  }

  async function refreshFacts(documentId: string) {
    setFactsLoading(true);
    const r = await api.documents.facts(documentId);
    setFactsLoading(false);
    if (r.kind === "ok") {
      setUploadResult((current) => current && current.document_id === documentId
        ? {
            ...current,
            parse_status: r.data.parse_status ?? current.parse_status,
            fact_count: r.data.count,
            extracted_facts: r.data.items,
          }
        : current);
      setListError(null);
    } else if (r.kind !== "auth" && r.kind !== "missing") {
      setListError("Could not load extracted facts.");
    }
  }

  useEffect(() => {
    void refreshDocuments();
  }, [projectId]);

  useEffect(() => {
    const hasActiveParse =
      isActiveParseStatus(uploadResult?.parse_status) ||
      documents.some((doc) => isActiveParseStatus(doc.parse_status ?? doc.status));
    if (!hasActiveParse) return;
    const timer = window.setInterval(() => {
      void refreshDocuments();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [documents, projectId, uploadResult?.parse_status]);

  useEffect(() => {
    if (!uploadResult || !isActiveParseStatus(uploadResult.parse_status)) return;
    const parsedDocument = documents.find((doc) => doc.id === uploadResult.document_id);
    const status = parsedDocument ? (parsedDocument.parse_status ?? parsedDocument.status) : uploadResult.parse_status;
    if (isActiveParseStatus(status)) return;
    void refreshFacts(uploadResult.document_id);
  }, [documents, uploadResult]);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    setConfirmedKeys(new Set());
    const r = await api.documents.upload(projectId, file);
    setUploading(false);
    if (r.kind === "ok") {
      setUploadResult(r.data);
      void refreshDocuments();
    } else if (r.kind === "notBuilt") {
      setUploadError("Document upload endpoint not yet available on this server.");
    } else if (r.kind === "auth") {
      setUploadError("Sign in required.");
    } else if (r.kind === "error") {
      setUploadError(r.message);
    } else {
      setUploadError("Could not reach server.");
    }
    if (fileRef.current) fileRef.current.value = "";
  }

  async function reviewDocument(doc: ProjectDocumentSummary) {
    setConfirmedKeys(new Set());
    setUploadResult({
      document_id: doc.id,
      filename: doc.title,
      project_id: projectId,
      parse_status: doc.parse_status ?? doc.status,
      fact_count: doc.fact_count,
      extracted_facts: [],
    });
    await refreshFacts(doc.id);
  }

  function handleConfirmed(factId: string) {
    setConfirmedKeys((prev) => new Set([...prev, factId]));
  }

  async function handleEvidenceSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const query = evidenceQuery.trim();
    if (query.length < 2) {
      setEvidenceResults([]);
      setEvidenceNotice(null);
      setEvidenceError("Enter at least 2 characters.");
      return;
    }
    setEvidenceSearching(true);
    setEvidenceError(null);
    const r = await api.documents.searchEvidence(projectId, query);
    setEvidenceSearching(false);
    if (r.kind === "ok") {
      setEvidenceResults(r.data.items);
      setEvidenceNotice(r.data.advisory_notice);
    } else if (r.kind === "auth") {
      setEvidenceError("Sign in required.");
    } else if (r.kind === "missing") {
      setEvidenceError("Evidence search is not available on this server.");
    } else if (r.kind === "error") {
      setEvidenceError(r.message);
    } else {
      setEvidenceError("Could not search uploaded evidence.");
    }
  }

  const facts = uploadResult?.extracted_facts ?? [];
  const parseStatus = uploadResult?.parse_status ?? null;
  const parseActive = isActiveParseStatus(parseStatus);
  const parseFailed = parseStatus === "parse_failed";

  return (
    <div style={{ padding: "0 0 24px" }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 600 }}>Documents</h3>

      <label
        ref={uploadTargetRef}
        tabIndex={-1}
        aria-label="Upload drawing or document"
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          border: "2px dashed #d1d5db",
          borderRadius: 10,
          padding: "24px 16px",
          cursor: "pointer",
          background: uploading ? "#f9fafb" : "#fff",
          transition: "border-color 0.15s",
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files?.[0];
          if (file && fileRef.current) {
            const dt = new DataTransfer();
            dt.items.add(file);
            fileRef.current.files = dt.files;
            fileRef.current.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }}
      >
        {uploading ? (
          <>
            <RefreshCw size={24} style={{ color: "#2563eb", animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: 13, color: "#6b7280" }}>Uploading…</span>
          </>
        ) : (
          <>
            <Sparkles size={24} style={{ color: "#9ca3af" }} />
            <span style={{ fontSize: 14, fontWeight: 500 }}>
              Upload a drawing or document
            </span>
            <span style={{ fontSize: 12, color: "#9ca3af" }}>
              PDF, DOCX, TXT, DXF — click or drag and drop
            </span>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.dxf"
          style={{ display: "none" }}
          onChange={(e) => void handleFile(e)}
        />
      </label>

      {uploadError && (
        <div
          style={{
            marginTop: 10,
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#b91c1c",
            fontSize: 13,
          }}
        >
          {uploadError}
        </div>
      )}

      {listError && (
        <div
          style={{
            marginTop: 10,
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#92400e",
            fontSize: 13,
          }}
        >
          {listError}
        </div>
      )}

      {documents.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#6b7280", marginBottom: 8 }}>
            Uploaded documents
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {documents.slice(0, 4).map((doc) => {
              const status = doc.parse_status ?? doc.status;
              const active = isActiveParseStatus(status);
              const failed = status === "parse_failed";
              return (
                <div
                  key={doc.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    border: "1px solid #e5e7eb",
                    borderRadius: 8,
                    padding: "8px 10px",
                    background: "#fff",
                    fontSize: 13,
                  }}
                >
                  <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {doc.title}
                  </span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: active ? "#92400e" : failed ? "#b91c1c" : "#16a34a", flexShrink: 0 }}>
                    {active ? <Clock3 size={14} /> : failed ? <AlertCircle size={14} /> : <CheckCircle2 size={14} />}
                    {parseStatusLabel(status, doc.fact_count)}
                  </span>
                  {!active && !failed && (
                    <button
                      type="button"
                      onClick={() => void reviewDocument(doc)}
                      aria-label={`Review facts for ${doc.title}`}
                      style={{
                        fontSize: 12,
                        padding: "4px 8px",
                        border: "1px solid #d1d5db",
                        borderRadius: 5,
                        background: "#fff",
                        color: "#111827",
                        cursor: "pointer",
                        flexShrink: 0,
                      }}
                    >
                      Review facts
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <form
            onSubmit={(e) => void handleEvidenceSearch(e)}
            style={{ marginTop: 12, display: "flex", gap: 8 }}
          >
            <div style={{ position: "relative", flex: 1, minWidth: 0 }}>
              <Search
                size={15}
                style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#9ca3af" }}
              />
              <input
                value={evidenceQuery}
                onChange={(e) => setEvidenceQuery(e.target.value)}
                placeholder="Search uploaded evidence"
                aria-label="Search uploaded evidence"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "8px 10px 8px 32px",
                  border: "1px solid #d1d5db",
                  borderRadius: 6,
                  fontSize: 13,
                  color: "#111827",
                }}
              />
            </div>
            <button
              type="submit"
              disabled={evidenceSearching}
              aria-label="Run uploaded evidence search"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 36,
                height: 36,
                border: "none",
                borderRadius: 6,
                background: evidenceSearching ? "#e5e7eb" : "#111827",
                color: evidenceSearching ? "#6b7280" : "#fff",
                cursor: evidenceSearching ? "not-allowed" : "pointer",
                flexShrink: 0,
              }}
            >
              {evidenceSearching ? <RefreshCw size={15} style={{ animation: "spin 1s linear infinite" }} /> : <Search size={15} />}
            </button>
          </form>

          {evidenceError && (
            <div style={{ marginTop: 8, color: "#b91c1c", fontSize: 12 }}>
              {evidenceError}
            </div>
          )}

          {evidenceResults.length > 0 && (
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
              {evidenceResults.map((hit) => (
                <div
                  key={`${hit.document_id}:${hit.chunk_index}`}
                  style={{
                    border: "1px solid #e5e7eb",
                    borderRadius: 8,
                    padding: "9px 10px",
                    background: "#fff",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                    <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, fontWeight: 600 }}>
                      {hit.document_title ?? "Uploaded document"}
                    </span>
                    <span style={{ color: "#6b7280", fontSize: 11, flexShrink: 0 }}>
                      {hit.page_number ? `Page ${hit.page_number}` : `Chunk ${hit.chunk_index}`}
                    </span>
                  </div>
                  <div style={{ maxHeight: 52, overflow: "hidden", color: "#374151", fontSize: 12, lineHeight: 1.45 }}>
                    {hit.text}
                  </div>
                </div>
              ))}
              {evidenceNotice && (
                <div style={{ color: "#6b7280", fontSize: 11, lineHeight: 1.45 }}>
                  {evidenceNotice}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {uploadResult && (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 12,
              fontSize: 14,
              color: "#374151",
            }}
          >
            <BookOpen size={16} />
            <span style={{ fontWeight: 500 }}>{uploadResult.filename}</span>
            <span style={{ color: "#6b7280" }}>·</span>
            <span style={{ color: "#6b7280" }}>
              {parseActive ? parseStatusLabel(parseStatus, facts.length) : `${facts.length} fact${facts.length !== 1 ? "s" : ""} extracted`}
            </span>
            {confirmedKeys.size > 0 && (
              <>
                <span style={{ color: "#6b7280" }}>·</span>
                <span style={{ color: "#16a34a" }}>{confirmedKeys.size} confirmed</span>
              </>
            )}
          </div>

          {parseActive && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#92400e", fontSize: 13 }}>
              <RefreshCw size={14} style={{ animation: "spin 1s linear infinite" }} />
              The parser job is queued or running. This list refreshes while processing continues.
            </div>
          )}

          {factsLoading && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#2563eb", fontSize: 13 }}>
              <RefreshCw size={14} style={{ animation: "spin 1s linear infinite" }} />
              Loading extracted facts...
            </div>
          )}

          {parseFailed && (
            <div style={{ color: "#b91c1c", fontSize: 13 }}>
              The parser could not extract this document. Try another file format or review the document manually.
            </div>
          )}

          {!parseActive && !parseFailed && !factsLoading && facts.length === 0 && (
            <div style={{ color: "#6b7280", fontSize: 13 }}>
              No measurable facts were extracted from this document.
            </div>
          )}

          {facts.map((fact) => (
            <FactCard
              key={fact.fact_id ?? fact.fact_key}
              fact={{ ...fact, confirmed: confirmedKeys.has(fact.fact_id ?? fact.fact_key) }}
              docId={uploadResult.document_id}
              onConfirmed={handleConfirmed}
            />
          ))}
        </div>
      )}
    </div>
  );
}
