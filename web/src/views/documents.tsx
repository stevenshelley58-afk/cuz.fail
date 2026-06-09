import { useRef, useState } from "react";
import { BookOpen, CheckCircle2, RefreshCw, Sparkles } from "lucide-react";
import { api, type DocumentUploadResponse, type ExtractedFact } from "../api";

/* ── DocumentUpload ── */

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
  onConfirmed: (factKey: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(fact.confirmed ?? false);
  const [err, setErr] = useState<string | null>(null);

  async function confirm() {
    setConfirming(true);
    setErr(null);
    const r = await api.documents.confirmFact(docId, fact.fact_key);
    setConfirming(false);
    if (r.kind === "ok" || r.kind === "notBuilt") {
      setConfirmed(true);
      onConfirmed(fact.fact_key);
    } else {
      setErr("Could not confirm fact.");
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
        </div>
        <div style={{ flexShrink: 0 }}>
          {confirmed ? (
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
        </div>
      </div>
      {err && <div style={{ color: "#dc2626", fontSize: 11, marginTop: 4 }}>{err}</div>}
    </div>
  );
}

export function DocumentUpload({ projectId }: { projectId: string }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const [confirmedKeys, setConfirmedKeys] = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    const r = await api.documents.upload(projectId, file);
    setUploading(false);
    if (r.kind === "ok") {
      setUploadResult(r.data);
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

  function handleConfirmed(factKey: string) {
    setConfirmedKeys((prev) => new Set([...prev, factKey]));
  }

  const facts = uploadResult?.extracted_facts ?? [];

  return (
    <div style={{ padding: "0 0 24px" }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 600 }}>Documents</h3>

      <label
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
              {facts.length} fact{facts.length !== 1 ? "s" : ""} extracted
            </span>
            {confirmedKeys.size > 0 && (
              <>
                <span style={{ color: "#6b7280" }}>·</span>
                <span style={{ color: "#16a34a" }}>{confirmedKeys.size} confirmed</span>
              </>
            )}
          </div>

          {facts.length === 0 && (
            <div style={{ color: "#6b7280", fontSize: 13 }}>
              No measurable facts were extracted from this document.
            </div>
          )}

          {facts.map((fact) => (
            <FactCard
              key={fact.fact_key}
              fact={{ ...fact, confirmed: confirmedKeys.has(fact.fact_key) }}
              docId={uploadResult.document_id}
              onConfirmed={handleConfirmed}
            />
          ))}
        </div>
      )}
    </div>
  );
}
