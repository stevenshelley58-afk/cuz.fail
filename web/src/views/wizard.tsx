import { useState } from "react";
import { api, type ProposalRequest } from "../api";
import { Icon } from "../components/common";
import { propertyDetailRows, propertyImage } from "../components/property";
import type { WizardState } from "../types";
import { CompliancePanel } from "./compliance";
import { DocumentUpload } from "./documents";

/* ── shared display bits ── */

function DetailRow({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16, padding: "8px 0", borderBottom: last ? "none" : "1px solid var(--line)" }}>
      <span style={{ color: "var(--ink-soft)", fontSize: ".8rem", flex: "none" }}>{label}</span>
      <span style={{ fontWeight: 600, fontSize: ".85rem", color: "var(--ink)", textAlign: "right", wordBreak: "break-word" }}>{value}</span>
    </div>
  );
}

/* ── PropertySummary — compact, no process chatter ── */

function PropertySummary({
  address,
  property,
  actions,
}: {
  address: string;
  property: WizardState["property"];
  actions?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const rows = property ? propertyDetailRows(property) : [];
  const headline = rows.filter((r) => ["Local government", "Zone", "Zones", "R-Code", "Lot area"].includes(r.label));
  const rest = rows.filter((r) => !headline.includes(r) && r.label !== "Address");

  return (
    <div className="panel">
      <h3 style={{ marginBottom: 10 }}><Icon name="location_on" />{address}</h3>

      {property && property.resolution_status !== "resolved" && property.issues.length > 0 && (
        <div className="state" style={{ marginBottom: 12 }}>
          <Icon name="info" />
          <span>{property.issues.join("; ")}</span>
        </div>
      )}

      {headline.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 18px", marginBottom: rest.length ? 8 : 0 }}>
          {headline.map((r) => (
            <span key={r.label} style={{ fontSize: ".85rem" }}>
              <span style={{ color: "var(--ink-soft)" }}>{r.label} </span>
              <b>{r.value}</b>
            </span>
          ))}
        </div>
      )}

      {rest.length > 0 && (
        <>
          <button
            style={{ fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
          >
            {open ? "Hide details" : "Open details"}
          </button>
          {open && (
            <div style={{ marginTop: 6 }}>
              {rest.map((r, i) => (
                <DetailRow key={`${r.label}-${i}`} label={r.label} value={r.value} last={i === rest.length - 1} />
              ))}
            </div>
          )}
        </>
      )}

      {!property && (
        <div style={{ fontSize: ".85rem", color: "var(--ink-soft)" }}>
          We couldn't load property details for this address, but you can still browse the rules and upload plans.
        </div>
      )}

      {actions}
    </div>
  );
}

/* ── RefinePanel — optional proposal details, collapsed by default ── */

function RefinePanel({
  projectId,
  initial,
  onSaved,
  defaultOpen = false,
}: {
  projectId: string;
  initial: ProposalRequest;
  onSaved: (data: ProposalRequest) => void;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [data, setData] = useState<ProposalRequest>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Partial<ProposalRequest>) => setData((d) => ({ ...d, ...patch }));

  const missingFields = [
    !data.proposal_type ? "proposal type" : null,
    data.proposal_type === "residential" && !data.dwelling_type ? "dwelling type" : null,
    !data.building_class ? "building class" : null,
    !data.work_type ? "work type" : null,
    !data.new_or_existing ? "new or existing building" : null,
    !data.lot_type ? "lot type" : null,
  ].filter(Boolean);

  const save = async () => {
    if (missingFields.length > 0) {
      setError(`Complete ${missingFields.join(", ")} before updating results.`);
      return;
    }
    setBusy(true);
    setError(null);
    const proposalPayload: ProposalRequest = {
      ...data,
      primary_street_confirmed: Boolean(data.primary_street_confirmed),
      secondary_street_confirmed: Boolean(data.secondary_street_confirmed),
    };
    const r = await api.upsertProposal(projectId, proposalPayload);
    setBusy(false);
    if (r.kind === "ok") {
      onSaved(proposalPayload);
      setOpen(false);
    } else if (r.kind === "notBuilt") {
      setError("Proposal saving is unavailable. Try again in a moment.");
    } else if (r.kind === "auth") {
      setError("Sign in required to save proposal details.");
    } else {
      setError(r.kind === "error" ? r.message : `Failed (${r.kind}).`);
    }
  };

  const selectStyle = {
    width: "100%",
    border: "1.5px solid var(--line)",
    borderRadius: 12,
    padding: "10px 14px",
    outline: "none",
    background: "var(--paper)",
    fontSize: ".85rem",
    color: "var(--ink)",
    fontFamily: "inherit",
  } as React.CSSProperties;

  const labelStyle = { fontSize: ".75rem", fontWeight: 700, color: "var(--ink-soft)", display: "block", marginBottom: 4 } as React.CSSProperties;
  const fieldWrap = { marginBottom: 14 } as React.CSSProperties;

  return (
    <div className="panel">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, background: "none", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}
      >
        <span>
          <h3 style={{ margin: 0 }}><Icon name="tune" />Tell us about your project</h3>
          <span style={{ fontSize: ".8rem", color: "var(--ink-soft)" }}>Optional — narrows the results to rules that apply to your build.</span>
        </span>
        <Icon name={open ? "expand_less" : "expand_more"} />
      </button>

      {open && (
        <div style={{ marginTop: 14 }}>
          <div style={fieldWrap}>
            <label style={labelStyle} htmlFor="proposal_type">Proposal type</label>
            <select id="proposal_type" style={selectStyle} value={data.proposal_type ?? ""} onChange={(e) => update({ proposal_type: e.target.value || null })}>
              <option value="">— select —</option>
              <option value="residential">Residential</option>
              <option value="commercial">Commercial</option>
              <option value="mixed_use">Mixed use</option>
            </select>
          </div>

          {data.proposal_type === "residential" && (
            <div style={fieldWrap}>
              <label style={labelStyle} htmlFor="dwelling_type">Dwelling type</label>
              <select id="dwelling_type" style={selectStyle} value={data.dwelling_type ?? ""} onChange={(e) => update({ dwelling_type: e.target.value || null })}>
                <option value="">— select —</option>
                <option value="single_house">Single house</option>
                <option value="grouped_dwelling">Grouped dwelling</option>
                <option value="multiple_dwelling">Multiple dwelling</option>
                <option value="ancillary_dwelling">Ancillary dwelling</option>
                <option value="short_stay">Short stay</option>
              </select>
            </div>
          )}

          <div style={fieldWrap}>
            <label style={labelStyle} htmlFor="building_class">Building class</label>
            <select id="building_class" style={selectStyle} value={data.building_class ?? ""} onChange={(e) => update({ building_class: e.target.value || null })}>
              <option value="">— select —</option>
              <option value="class_1a">Class 1a - house or grouped dwelling</option>
              <option value="class_1b">Class 1b - small boarding/guest accommodation</option>
              <option value="class_2">Class 2 - apartment building</option>
              <option value="class_10a">Class 10a - shed, garage or carport</option>
            </select>
          </div>

          <div style={fieldWrap}>
            <label style={labelStyle} htmlFor="work_type">Work type</label>
            <select id="work_type" style={selectStyle} value={data.work_type ?? ""} onChange={(e) => update({ work_type: e.target.value || null })}>
              <option value="">— select —</option>
              <option value="new_construction">New construction</option>
              <option value="extension">Extension</option>
              <option value="renovation">Renovation</option>
              <option value="demolition">Demolition</option>
              <option value="change_of_use">Change of use</option>
            </select>
          </div>

          <div style={fieldWrap}>
            <span style={labelStyle}>New or existing building</span>
            <div style={{ display: "flex", gap: 16 }}>
              {(["new", "existing"] as const).map((v) => (
                <label key={v} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: ".85rem", cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="new_or_existing"
                    value={v}
                    checked={data.new_or_existing === v}
                    onChange={() => update({ new_or_existing: v })}
                  />
                  {v.charAt(0).toUpperCase() + v.slice(1)}
                </label>
              ))}
            </div>
          </div>

          <div style={fieldWrap}>
            <label style={labelStyle} htmlFor="lot_type">Lot type</label>
            <select id="lot_type" style={selectStyle} value={data.lot_type ?? ""} onChange={(e) => update({ lot_type: e.target.value || null })}>
              <option value="">— select —</option>
              <option value="green_title">Green title</option>
              <option value="strata_title">Strata title</option>
              <option value="survey_strata">Survey strata</option>
            </select>
          </div>

          <div style={fieldWrap}>
            <span style={labelStyle}>Street context</span>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: ".85rem", cursor: "pointer", marginBottom: 8 }}>
              <input
                type="checkbox"
                checked={Boolean(data.primary_street_confirmed)}
                onChange={(e) => update({ primary_street_confirmed: e.target.checked })}
              />
              <span>Primary street frontage is confirmed for this proposal.</span>
            </label>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: ".85rem", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={Boolean(data.secondary_street_confirmed)}
                onChange={(e) => update({ secondary_street_confirmed: e.target.checked })}
              />
              <span>Secondary street frontage applies and is confirmed.</span>
            </label>
          </div>

          {error && (
            <div className="state" style={{ marginBottom: 10 }}>
              <Icon name="error" /><span>{error}</span>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="btn" onClick={() => void save()} disabled={busy}>
              {busy ? "Updating…" : "Update results"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── CheckView — address in, results out, one screen ── */

function heroActionStyle(active: boolean): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    fontSize: ".78rem",
    fontWeight: 700,
    padding: "7px 13px",
    borderRadius: 999,
    border: `1.5px solid ${active ? "var(--green-bright)" : "var(--line)"}`,
    background: "var(--card)",
    color: active ? "var(--green-800)" : "var(--ink-soft)",
    cursor: "pointer",
    fontFamily: "inherit",
  };
}

export function WizardShell({
  wizard,
  onClose,
  onProjectOpen,
}: {
  wizard: WizardState;
  onClose: () => void;
  onProjectOpen: (projectId: string) => void;
}) {
  const [proposalSaves, setProposalSaves] = useState(0);
  const [proposal, setProposal] = useState<ProposalRequest>(wizard.proposal);
  const [refineOpen, setRefineOpen] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);

  void onClose;

  return (
    <div className="view wizard-view" style={{ paddingTop: 16, width: "100%", maxWidth: 760, margin: "0 auto" }}>
      <PropertySummary
        address={wizard.address}
        property={wizard.property}
        actions={
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
            <button
              style={heroActionStyle(refineOpen)}
              onClick={() => setRefineOpen((o) => !o)}
              aria-expanded={refineOpen}
            >
              <Icon name="tune" size={14} />Add project details
            </button>
            <button
              style={heroActionStyle(docsOpen)}
              onClick={() => setDocsOpen((o) => !o)}
              aria-expanded={docsOpen}
            >
              <Icon name="upload_file" size={14} />Upload plans
            </button>
          </div>
        }
      />

      <div className="panel">
        <CompliancePanel
          projectId={wizard.projectId}
          councilName={wizard.property?.local_government}
          propertyImage={propertyImage(wizard.property)}
          proposalReady={proposalSaves > 0}
          runRequest={proposalSaves}
          autoRun
        />
      </div>

      {refineOpen && (
        <RefinePanel
          projectId={wizard.projectId}
          initial={proposal}
          defaultOpen
          onSaved={(data) => {
            setProposal(data);
            setProposalSaves((n) => n + 1);
          }}
        />
      )}

      {docsOpen && (
        <div className="panel">
          <DocumentUpload projectId={wizard.projectId} />
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", padding: "4px 0 24px" }}>
        <button className="btn alt" onClick={() => onProjectOpen(wizard.projectId)}>
          <Icon name="home_work" />Open project workspace
        </button>
      </div>
    </div>
  );
}
