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

const FACT_LABELS: Record<string, string> = {
  address: "Address",
  parcel: "Parcel",
  local_government: "Local government",
  lot_area_m2: "Lot area",
  lot_area: "Lot area",
  zone: "Zone",
  r_code: "R-Code",
  overlay: "Overlay",
};

const UNIT_LABELS: Record<string, string> = { m2: "m²", sqm: "m²" };

export function factLabel(factType: string): string {
  return FACT_LABELS[factType] ?? factType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatNumber(n: number): string {
  if (!Number.isFinite(n)) return String(n);
  const rounded = Math.round(n * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/** Renders a fact value as readable text. Returns null when there is nothing meaningful to show
 *  (null/empty/blank), so callers can skip the row instead of printing "—" or raw JSON. */
export function formatFactValue(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "string") return v.trim() || null;
  if (typeof v === "number") return formatNumber(v);
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (Array.isArray(v)) {
    const parts = v.map((x) => formatFactValue(x)).filter((x): x is string => x !== null);
    return parts.length ? parts.join(", ") : null;
  }
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    if ("value" in o) {
      const base = formatFactValue(o.value);
      if (base === null) return null;
      const unit = o.unit != null ? String(o.unit) : "";
      return unit ? `${base} ${UNIT_LABELS[unit] ?? unit}` : base;
    }
    const primaryKey = ["formatted_address", "name", "label", "code", "parcel_id", "id"].find(
      (k) => o[k] != null && o[k] !== "",
    );
    if (primaryKey) {
      let s = String(o[primaryKey]);
      if (o.verification_status) s += ` · ${String(o.verification_status)}`;
      return s;
    }
    const pairs = Object.entries(o)
      .map(([k, val]) => [k, formatFactValue(val)] as const)
      .filter((entry): entry is readonly [string, string] => entry[1] !== null)
      .map(([k, val]) => `${k.replace(/_/g, " ")}: ${val}`);
    return pairs.length ? pairs.join(" · ") : null;
  }
  return String(v);
}

export type PropertyDetailRow = { label: string; value: string; hint?: string };

const HEADER_FACT_TYPES = new Set(["address", "local_government"]);
const FACT_ORDER = ["parcel", "lot_area_m2", "lot_area", "zone", "r_code", "overlay"];

function factOrderIndex(factType: string): number {
  const i = FACT_ORDER.indexOf(factType);
  return i === -1 ? FACT_ORDER.length : i;
}

/** Curated, de-duplicated, non-empty property detail rows for the resolution view.
 *  Address and LGA come from the profile fields; the rest are formatted facts with values. */
export function propertyDetailRows(property: PropertyProfileResponse): PropertyDetailRow[] {
  const rows: PropertyDetailRow[] = [];
  if (property.address) rows.push({ label: "Address", value: property.address });
  if (property.local_government) rows.push({ label: "Local government", value: property.local_government });

  (property.facts ?? [])
    .filter((f) => !HEADER_FACT_TYPES.has(f.fact_type))
    .map((f) => ({ f, value: formatFactValue(f.value) }))
    .filter((x): x is { f: PropertyFactResponse; value: string } => x.value !== null)
    .sort((a, b) => factOrderIndex(a.f.fact_type) - factOrderIndex(b.f.fact_type))
    .forEach(({ f, value }) =>
      rows.push({
        label: factLabel(f.fact_type),
        value,
        hint: f.confidence === "low" || f.confidence === "none" ? `${f.confidence} confidence` : undefined,
      }),
    );

  return rows;
}

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
