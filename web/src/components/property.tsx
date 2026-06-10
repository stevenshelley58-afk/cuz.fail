import { useState } from "react";
import type { PropertyFactResponse, PropertyProfileResponse } from "../api";
import { Icon } from "./common";

/* ── helpers for wizard display ── */

export function resolutionBadge(status: PropertyProfileResponse["resolution_status"]) {
  const map: Record<string, { label: string; bg: string; color: string }> = {
    resolved: { label: "Resolved", bg: "var(--mint)", color: "var(--green-800)" },
    missing_info: { label: "Missing info", bg: "var(--flag-bg)", color: "var(--flag)" },
    needs_more_info: { label: "Needs more info", bg: "#EFF6FF", color: "#1D4ED8" },
    needs_human_review: { label: "Needs human review", bg: "#EFF6FF", color: "#1D4ED8" },
    unsupported: { label: "Unsupported", bg: "#FEF2F2", color: "#B91C1C" },
  };
  const s = map[status] ?? { label: status, bg: "#EFF1F1", color: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 99, background: s.bg, color: s.color, display: "inline-flex", alignItems: "center", gap: 5 }}>
      {s.label}
    </span>
  );
}

export function confidenceBadge(confidence: string) {
  const colors: Record<string, string> = { high: "var(--green-800)", medium: "var(--flag)", low: "#B91C1C", none: "var(--ink-soft)" };
  return (
    <span style={{ fontSize: ".72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 99, background: "var(--paper)", border: "1px solid var(--line)", color: colors[confidence] ?? "var(--ink-soft)", display: "inline-flex", alignItems: "center", gap: 4 }}>
      Confidence: {confidence}
    </span>
  );
}

export function groupFactsByType(facts: PropertyFactResponse[]): Map<string, PropertyFactResponse[]> {
  const m = new Map<string, PropertyFactResponse[]>();
  for (const f of facts) {
    const arr = m.get(f.fact_type) ?? [];
    arr.push(f);
    m.set(f.fact_type, arr);
  }
  return m;
}

export function formatFactValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

export const NOT_LEGAL_PROOF_NOTE = (
  <div style={{ fontSize: ".72rem", fontWeight: 600, color: "var(--flag)", background: "var(--flag-bg)", border: "1px solid #F5DEB9", borderRadius: 10, padding: "6px 12px", margin: "8px 0", display: "flex", alignItems: "flex-start", gap: 6 }}>
    <Icon name="error" />
    <span>Not legal proof of property boundaries. Resolution status is advisory only and must not be used as a substitute for a registered survey or certificate of title.</span>
  </div>
);

/* ── ProvenanceAccordion ── */

export function ProvenanceAccordion({ provenance }: { provenance: PropertyProfileResponse["provenance"] }) {
  const [open, setOpen] = useState(false);
  if (!provenance || provenance.length === 0) return null;
  return (
    <div style={{ marginTop: 8 }}>
      <button
        style={{ fontSize: ".72rem", fontWeight: 700, color: "var(--ink-soft)", display: "flex", alignItems: "center", gap: 5, background: "none", border: "none", cursor: "pointer" }}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <Icon name="verified" />
        {open ? "Hide" : "Show"} data provenance ({provenance.length})
      </button>
      {open && (
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
          {provenance.map((p, i) => (
            <div key={i} style={{ fontSize: ".72rem", background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 10, padding: "8px 12px" }}>
              <div><b>Kind:</b> {p.kind}</div>
              <div><b>Method:</b> {p.method}</div>
              <div><b>CRS:</b> {p.target_crs}</div>
              {p.dataset_id && <div><b>Dataset:</b> {p.dataset_id}</div>}
              {p.licence_status && <div><b>Licence:</b> {p.licence_status}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
