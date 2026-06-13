import { useEffect, useState } from "react";
import { api, type ApiResult, type ProjectSummary } from "../api";
import { Icon } from "../components/common";
import { CompliancePanel } from "./compliance";
import { DocumentUpload } from "./documents";

export function projectList(r: ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }>): ProjectSummary[] {
  if (r.kind !== "ok") return [];
  const d = r.data;
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d.projects)) return d.projects;
  return [];
}

/* ── ProjectDetail — opens when a project card is clicked ── */

export function ProjectDetail({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  return (
    <div className="view">
      <div style={{ marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "6px 12px" }} onClick={onClose}>← Back</button>
      </div>
      <div className="panel">
        <CompliancePanel projectId={projectId} />
      </div>
      <div className="panel">
        <DocumentUpload projectId={projectId} />
      </div>
    </div>
  );
}

/* ── projects view ── */

export function Projects({
  isGuest,
  onNeedSignIn,
  onProjectOpen,
}: {
  isGuest: boolean;
  onNeedSignIn: () => void;
  onProjectOpen: (projectId: string) => void;
}) {
  const [result, setResult] = useState<ApiResult<ProjectSummary[] | { projects?: ProjectSummary[] }> | null>(null);
  useEffect(() => {
    void api.projects().then(setResult);
  }, []);
  const items = result ? projectList(result) : [];
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="home_work" />Projects</h3>
        {isGuest && (
          <>
            <p>Free preview checks live in a temporary workspace. Sign in when you want them kept for good, plus uploads and exports.</p>
            <div className="field">
              <button className="btn" onClick={onNeedSignIn}>Sign in to save projects</button>
            </div>
          </>
        )}
        {result === null && <p>Loading…</p>}
        {result?.kind === "ok" && items.length === 0 && <p>No projects yet — start one from Home by pasting an address.</p>}
        {result?.kind === "ok" && items.length > 0 && (
          <div className="strip" style={{ marginTop: 10 }}>
            {items.map((p) => (
              <button key={p.id} className="proj" onClick={() => onProjectOpen(p.id)}>
                <Icon name="home_work" />
                <span className="t">{p.name ?? p.address ?? p.id}<small>{isGuest ? "Free preview · " : ""}{p.created_at ?? ""}</small></span>
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
