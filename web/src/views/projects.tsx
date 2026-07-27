import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ApiResult, type ProjectSummary, type PropertyProfileResponse } from "../api";
import { Icon } from "../components/common";
import { formatFactValueForType, groupFactsByType, propertyImage } from "../components/property";
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

function ProjectPropertyContext({
  projectId,
  onLoaded,
}: {
  projectId: string;
  onLoaded?: (property: PropertyProfileResponse | null) => void;
}) {
  const [property, setProperty] = useState<PropertyProfileResponse | null>(null);
  const [resultKind, setResultKind] = useState<ApiResult<PropertyProfileResponse>["kind"] | "loading">("loading");

  useEffect(() => {
    let active = true;
    setResultKind("loading");
    setProperty(null);
    onLoaded?.(null);
    void api.getProperty(projectId).then((r) => {
      if (!active) return;
      const loadedProperty = r.kind === "ok" ? r.data : null;
      setResultKind(r.kind);
      setProperty(loadedProperty);
      onLoaded?.(loadedProperty);
    });
    return () => {
      active = false;
    };
  }, [projectId, onLoaded]);

  if (resultKind === "loading") {
    return <div className="state"><Icon name="hourglass_empty" /><span>Loading property context...</span></div>;
  }

  if (!property) {
    const recoverable = resultKind === "missing" || resultKind === "notBuilt";
    return (
      <div className="state">
        <Icon name={recoverable ? "info" : "error"} />
        <span>
          {recoverable
            ? "Property context is not available for this project yet."
            : "Could not load property context for this project."}
        </span>
      </div>
    );
  }

  const factsByType = groupFactsByType(property.facts ?? []);
  const factGroups = Array.from(factsByType.entries()).slice(0, 4);

  return (
    <div>
      {property.address ? (
        <h3 style={{ margin: "0 0 10px" }}><Icon name="location_on" />{property.address}</h3>
      ) : (
        <h3 style={{ margin: "0 0 10px" }}><Icon name="location_on" />Property</h3>
      )}
      {property.local_government && (
        <div style={{ fontSize: ".85rem", marginBottom: 10 }}>
          <span style={{ color: "var(--ink-soft)" }}>Local government </span>
          <b>{property.local_government}</b>
        </div>
      )}

      {property.issues.length > 0 && (
        <div className="state" style={{ alignItems: "flex-start", marginBottom: 10 }}>
          <Icon name="warning" />
          <span>{property.issues.join("; ")}</span>
        </div>
      )}

      {factGroups.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
          {factGroups.map(([type, facts]) => (
            <div key={type} style={{ background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 10, padding: "8px 10px" }}>
              <div style={{ fontSize: ".72rem", fontWeight: 700, color: "var(--ink-faint)", textTransform: "uppercase", marginBottom: 4 }}>
                {type.replace(/_/g, " ")}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {facts.slice(0, 2).map((fact) => (
                  <div key={fact.fact_id} style={{ fontSize: ".82rem", fontWeight: 650 }}>
                    {formatFactValueForType(fact.fact_type, fact.value) ?? "—"}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ProjectDetail({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const documentSectionRef = useRef<HTMLDivElement>(null);
  const [documentFocusRequest, setDocumentFocusRequest] = useState(0);
  const [property, setProperty] = useState<PropertyProfileResponse | null>(null);
  const handlePropertyLoaded = useCallback((loadedProperty: PropertyProfileResponse | null) => {
    setProperty(loadedProperty);
  }, []);

  function focusDocumentUpload() {
    setDocumentFocusRequest((value) => value + 1);
    window.setTimeout(() => {
      documentSectionRef.current?.scrollIntoView({ block: "start", behavior: "smooth" });
    }, 0);
  }

  return (
    <div className="view">
      <div style={{ marginBottom: 12 }}>
        <button className="btn alt" style={{ fontSize: ".75rem", padding: "6px 12px" }} onClick={onClose}>← Back</button>
      </div>
      <div className="panel">
        <ProjectPropertyContext projectId={projectId} onLoaded={handlePropertyLoaded} />
      </div>
      <div className="panel">
        <CompliancePanel
          projectId={projectId}
          onUploadDrawing={focusDocumentUpload}
          councilName={property?.local_government}
          propertyImage={propertyImage(property)}
        />
      </div>
      <div className="panel" ref={documentSectionRef}>
        <DocumentUpload projectId={projectId} focusRequest={documentFocusRequest} />
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
