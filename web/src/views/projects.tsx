import { useEffect, useState } from "react";
import { api, type ApiResult, type ProjectSummary } from "../api";
import { Icon } from "../components/common";
import { guestProjectList } from "../hooks/useGuestUsage";
import type { GuestUsage } from "../types";
import { CompliancePanel } from "./compliance";

export function projectList(r: ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }>): ProjectSummary[] {
  if (r.kind !== "ok") return [];
  const d = r.data;
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d.projects)) return d.projects;
  return [];
}

/* ── ProjectDetail — opens when a project card is clicked ── */

type ProjectDoc = { id: string; title: string; document_type: string; status: string; created_at: string | null; fact_count: number };

export function ProjectDetail({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const [docs, setDocs] = useState<ProjectDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);

  useEffect(() => {
    setDocsLoading(true);
    void api.documents.listForProject(projectId).then((r) => {
      if (r.kind === "ok") setDocs(r.data.items ?? []);
      setDocsLoading(false);
    });
  }, [projectId]);

  return (
    <div className="view">
      <div style={{ marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "6px 12px" }} onClick={onClose}>← Back</button>
      </div>
      <div className="panel">
        <CompliancePanel projectId={projectId} />
      </div>
      <div className="panel">
        <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 600 }}>Uploaded documents</h3>
        {docsLoading && <p style={{ color: "#6b7280", fontSize: 14 }}>Loading…</p>}
        {!docsLoading && docs.length === 0 && (
          <p style={{ color: "#6b7280", fontSize: 14 }}>No documents uploaded yet.</p>
        )}
        {docs.map((doc) => (
          <div key={doc.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13, padding: "8px 0", borderBottom: "1px solid #f3f4f6" }}>
            <div>
              <span style={{ color: "#374151", fontWeight: 500 }}>{doc.title}</span>
              <small style={{ color: "#9ca3af", marginLeft: 8 }}>{doc.document_type} · {doc.fact_count} facts</small>
            </div>
            <span style={{ color: "#6b7280", fontSize: 12 }}>{doc.created_at ?? ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── projects view ── */

export function Projects({
  authed,
  guestUsage,
  onNeedSignIn,
  onProjectOpen,
}: {
  authed: boolean;
  guestUsage: GuestUsage;
  onNeedSignIn: () => void;
  onProjectOpen: (projectId: string) => void;
}) {
  const [result, setResult] = useState<ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }> | null>(null);
  useEffect(() => {
    if (!authed) {
      setResult(null);
      return;
    }
    void api.projects().then(setResult);
  }, [authed]);
  const items = result ? projectList(result) : [];
  const guestItems = guestProjectList(guestUsage);
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="home_work" />Projects</h3>
        {!authed && (
          <>
            <p>Guest checks are saved only on this device. Sign in when you want saved projects, uploads, exports, and reviewer signoff.</p>
            {guestItems.length === 0 && <div className="state"><Icon name="sparkles" /><span>No guest checks yet — start one from Home by pasting an address.</span></div>}
            {guestItems.length > 0 && (
              <div className="strip" style={{ marginTop: 10 }}>
                {guestItems.map((p) => (
                  <button key={p.id} className="proj" onClick={() => onProjectOpen(p.id)}>
                    <Icon name="home_work" />
                    <span className="t">{p.address ?? p.id}<small>Guest preview · {p.created_at ?? ""}</small></span>
                  </button>
                ))}
              </div>
            )}
            <div className="field">
              <button className="btn" onClick={onNeedSignIn}>Sign in to save projects</button>
            </div>
          </>
        )}
        {authed && result === null && <p>Loading…</p>}
        {result?.kind === "ok" && items.length === 0 && <p>No projects yet — start one from Home by pasting an address.</p>}
        {result?.kind === "ok" && items.length > 0 && (
          <div className="strip" style={{ marginTop: 10 }}>
            {items.map((p) => (
              <button key={p.id} className="proj" onClick={() => onProjectOpen(p.id)}>
                <Icon name="home_work" />
                <span className="t">{p.name ?? p.address ?? p.id}<small>{p.created_at ?? ""}</small></span>
              </button>
            ))}
          </div>
        )}
        {result?.kind === "notBuilt" && (
          <div className="state"><Icon name="construction" /><span>Project creation is coming soon — this screen wires itself up automatically when it lands.</span></div>
        )}
        {result?.kind === "auth" && (
          <div className="state"><Icon name="lock" /><span>Sign in to see your projects. <button className="btn alt" style={{ marginLeft: 8 }} onClick={onNeedSignIn}>Go to sign in</button></span></div>
        )}
        {(result?.kind === "down" || result?.kind === "error" || result?.kind === "missing") && (
          <div className="state"><Icon name="error" /><span>Couldn't load projects ({result.kind}).</span></div>
        )}
      </div>
    </div>
  );
}
