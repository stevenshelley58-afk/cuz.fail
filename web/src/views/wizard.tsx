import { useState } from "react";
import { api, type PropertyFactResponse, type PropertyProfileResponse, type ProposalRequest, type ProposalResponse } from "../api";
import { Icon } from "../components/common";
import { NOT_LEGAL_PROOF_NOTE, ProvenanceAccordion, confidenceBadge, formatFactValue, groupFactsByType, resolutionBadge } from "../components/property";
import type { WizardState, WizardStep } from "../types";
import { CompliancePanel } from "./compliance";
import { DocumentUpload } from "./documents";

/* ── AddressResolverPanel ── */

function AddressResolverPanel({ property, onContinue, onBack }: { property: PropertyProfileResponse; onContinue: () => void; onBack?: () => void }) {
  const factsByType = groupFactsByType(property.facts ?? []);

  const zoneEntry = factsByType.get("zone");
  const rCodeEntry = factsByType.get("r_code");
  const overlayEntries = factsByType.get("overlay");

  return (
    <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h3 style={{ marginBottom: 12 }}><Icon name="location_on" />Property Resolution</h3>

      {NOT_LEGAL_PROOF_NOTE}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
        {resolutionBadge(property.resolution_status)}
        {confidenceBadge(property.confidence)}
      </div>

      {property.address && (
        <div style={{ fontSize: ".85rem", marginBottom: 6 }}><b>Address:</b> {property.address}</div>
      )}
      {property.local_government && (
        <div style={{ fontSize: ".85rem", marginBottom: 6 }}><b>Local government:</b> {property.local_government}</div>
      )}

      {property.resolution_status !== "resolved" && property.issues.length > 0 && (
        <div className="state" style={{ marginTop: 8 }}>
          <Icon name="error" />
          <div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Issues preventing full resolution:</div>
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {property.issues.map((issue, i) => <li key={i}>{issue}</li>)}
            </ul>
          </div>
        </div>
      )}

      {(zoneEntry || rCodeEntry || overlayEntries) && (
        <div style={{ marginTop: 10, fontSize: ".85rem" }}>
          <div style={{ fontWeight: 700, marginBottom: 6, color: "var(--ink)" }}>Planning facts</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {zoneEntry?.map((f) => (
              <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ color: "var(--ink-soft)" }}>Zone</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
              </div>
            ))}
            {rCodeEntry?.map((f) => (
              <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ color: "var(--ink-soft)" }}>R-Code</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
              </div>
            ))}
            {overlayEntries?.map((f) => (
              <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                <span style={{ color: "var(--ink-soft)" }}>Overlay</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {factsByType.size > 0 && (
        <div style={{ marginTop: 10, fontSize: ".85rem" }}>
          <div style={{ fontWeight: 700, marginBottom: 6, color: "var(--ink)" }}>All facts ({property.facts.length})</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {Array.from(factsByType.entries()).map(([factType, entries]) =>
              entries.map((f) => (
                <div key={f.fact_id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                  <span style={{ color: "var(--ink-soft)" }}>{factType}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontWeight: 600 }}>{formatFactValue(f.value)}</span>
                    <span style={{ fontSize: ".66rem", color: "var(--ink-faint)" }}>{f.confidence}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <ProvenanceAccordion provenance={property.provenance} />

      <div className="wizard-actions" style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
        {onBack && (
          <button className="btn alt" onClick={onBack}>← Back</button>
        )}
        <button className="btn" onClick={onContinue}>Next: Proposal details →</button>
      </div>
    </div>
  );
}

/* ── ProposalForm (Step 2) ── */

function ProposalForm({
  projectId,
  initial,
  onSaved,
  onBack,
}: {
  projectId: string;
  initial: ProposalRequest;
  onSaved: (proposal: ProposalResponse, data: ProposalRequest) => void;
  onBack: () => void;
}) {
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
  const canSave = missingFields.length === 0;

  const save = async () => {
    if (!canSave) {
      setError(`Complete ${missingFields.join(", ")} before continuing.`);
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
      onSaved(r.data, proposalPayload);
    } else if (r.kind === "notBuilt") {
      setError("Proposal saving is unavailable. Try again before continuing.");
    } else if (r.kind === "auth") {
      setError("Sign in required to save proposal.");
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
    <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h3 style={{ marginBottom: 16 }}><Icon name="home_work" />Proposal details</h3>

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

      <div className="wizard-actions" style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn alt" onClick={onBack} disabled={busy}>← Back</button>
        <button className="btn" onClick={() => void save()} disabled={busy}>
          {busy ? "Saving…" : "Save & Continue →"}
        </button>
      </div>
    </div>
  );
}

/* ── ConfirmationStep (Step 3) ── */

function ConfirmationStep({
  projectId,
  address,
  property,
  proposal,
  onBack,
  onStart,
}: {
  projectId: string;
  address: string;
  property: PropertyProfileResponse | null;
  proposal: ProposalRequest;
  onBack: () => void;
  onStart: () => void;
}) {
  const factsByType = property ? groupFactsByType(property.facts ?? []) : new Map<string, PropertyFactResponse[]>();
  const zone = factsByType.get("zone")?.[0];
  const rCode = factsByType.get("r_code")?.[0];

  return (
    <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h3 style={{ marginBottom: 16 }}><Icon name="check_circle" />Confirm and review</h3>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: ".72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--ink-faint)", marginBottom: 4 }}>Project</div>
        <div style={{ fontWeight: 700, fontSize: ".95rem" }}>{address}</div>
      </div>

      {NOT_LEGAL_PROOF_NOTE}

      {property && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: ".72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--ink-faint)", marginBottom: 8 }}>Property summary</div>
          <div style={{ fontSize: ".85rem", display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Status</span>
              {resolutionBadge(property.resolution_status)}
            </div>
            {property.local_government && (
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>LGA</span>
                <span style={{ fontWeight: 600 }}>{property.local_government}</span>
              </div>
            )}
            {zone && (
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Zone</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(zone.value)}</span>
              </div>
            )}
            {rCode && (
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>R-Code</span>
                <span style={{ fontWeight: 600 }}>{formatFactValue(rCode.value)}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Confidence</span>
              {confidenceBadge(property.confidence)}
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: ".72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--ink-faint)", marginBottom: 8 }}>Proposal summary</div>
        <div style={{ fontSize: ".85rem", display: "flex", flexDirection: "column", gap: 4 }}>
          {proposal.proposal_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Type</span>
              <span style={{ fontWeight: 600 }}>{proposal.proposal_type}</span>
            </div>
          )}
          {proposal.dwelling_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Dwelling</span>
              <span style={{ fontWeight: 600 }}>{proposal.dwelling_type}</span>
            </div>
          )}
          {proposal.work_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Work type</span>
              <span style={{ fontWeight: 600 }}>{proposal.work_type}</span>
            </div>
          )}
          {proposal.building_class && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Building class</span>
              <span style={{ fontWeight: 600 }}>{proposal.building_class}</span>
            </div>
          )}
          {proposal.new_or_existing && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>New / existing</span>
              <span style={{ fontWeight: 600 }}>{proposal.new_or_existing}</span>
            </div>
          )}
          {proposal.lot_type && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Lot type</span>
              <span style={{ fontWeight: 600 }}>{proposal.lot_type}</span>
            </div>
          )}
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Primary street</span>
            <span style={{ fontWeight: 600 }}>{proposal.primary_street_confirmed ? "Confirmed" : "Not confirmed"}</span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ color: "var(--ink-soft)", minWidth: 120 }}>Secondary street</span>
            <span style={{ fontWeight: 600 }}>{proposal.secondary_street_confirmed ? "Confirmed" : "Not confirmed"}</span>
          </div>
        </div>
      </div>

      <DocumentUpload projectId={projectId} />

      <CompliancePanel projectId={projectId} />

      <div className="wizard-actions" style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn alt" onClick={onBack}>← Back to edit</button>
        <button className="btn" onClick={onStart}>
          <Icon name="home_work" />Open project workspace
        </button>
      </div>
    </div>
  );
}

/* ── WizardShell ── */

export function WizardShell({
  wizard,
  onClose,
  onProjectOpen,
}: {
  wizard: WizardState;
  onClose: () => void;
  onProjectOpen: (projectId: string) => void;
}) {
  const [state, setState] = useState<WizardState>(wizard);

  const setStep = (step: WizardStep) => setState((s) => ({ ...s, step }));

  const steps = ["Address & property", "Proposal details", "Confirm"] as const;

  return (
    <div className="view wizard-view" style={{ paddingTop: 16 }}>
      {/* stepper */}
      <div className="wizard-stepper" style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 20, maxWidth: 640, margin: "0 auto 20px" }} aria-label="Check steps">
        {steps.map((label, idx) => {
          const stepNum = (idx + 1) as WizardStep;
          const isCurrent = state.step === stepNum;
          const isDone = state.step > stepNum;
          return (
            <div key={idx} className="wizard-step" style={{ display: "flex", alignItems: "center", flex: idx < 2 ? 1 : undefined }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 99, display: "flex", alignItems: "center", justifyContent: "center",
                  background: isCurrent ? "var(--green-900)" : isDone ? "var(--green)" : "var(--paper)",
                  border: isCurrent || isDone ? "none" : "1.5px solid var(--line)",
                  color: isCurrent || isDone ? "#fff" : "var(--ink-faint)",
                  fontSize: ".75rem", fontWeight: 800,
                }}>
                  {isDone ? <Icon name="check_circle" /> : stepNum}
                </div>
                <div className="wizard-step-label" style={{ fontSize: ".65rem", fontWeight: 700, color: isCurrent ? "var(--green-800)" : "var(--ink-faint)", whiteSpace: "nowrap" }}>
                  {label}
                </div>
              </div>
              {idx < 2 && (
                <div className="wizard-rail" style={{ flex: 1, height: 2, background: isDone ? "var(--green)" : "var(--line)", margin: "0 6px 16px" }} />
              )}
            </div>
          );
        })}
      </div>

      {state.step === 1 && state.property && (
        <AddressResolverPanel
          property={state.property}
          onContinue={() => setStep(2)}
          onBack={onClose}
        />
      )}

      {state.step === 1 && !state.property && (
        <div className="panel" style={{ maxWidth: 640, margin: "0 auto" }}>
          <div className="state"><Icon name="error" /><span>Property data unavailable. Address was submitted but no profile returned.</span></div>
          <div style={{ marginTop: 12 }}>
            <button className="btn alt" onClick={onClose}>← Back</button>
          </div>
        </div>
      )}

      {state.step === 2 && (
        <ProposalForm
          projectId={state.projectId}
          initial={state.proposal}
          onSaved={(saved, data) => setState((s) => ({ ...s, savedProposal: saved, proposal: data, step: 3 }))}
          onBack={() => setStep(1)}
        />
      )}

      {state.step === 3 && (
        <ConfirmationStep
          projectId={state.projectId}
          address={state.address}
          property={state.property}
          proposal={state.proposal}
          onBack={() => setStep(2)}
          onStart={() => {
            if (state.projectId) onProjectOpen(state.projectId);
            else onClose();
          }}
        />
      )}
    </div>
  );
}
