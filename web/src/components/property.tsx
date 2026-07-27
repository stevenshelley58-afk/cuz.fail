import type { PropertyFactResponse, PropertyImage, PropertyProfileResponse } from "../api";

/* ── property fact formatting ── */

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

export type PropertyDetailRow = { label: string; value: string };

const HEADER_FACT_TYPES = new Set(["address", "local_government"]);
const FACT_ORDER = ["parcel", "lot_area_m2", "lot_area", "zone", "r_code", "overlay"];

function factOrderIndex(factType: string): number {
  const i = FACT_ORDER.indexOf(factType);
  return i === -1 ? FACT_ORDER.length : i;
}

function normalizeRCodeText(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return trimmed;
  let code = trimmed.replace(/^Residential\s+Design\s+Codes?\s*/i, "").trim();
  code = code.replace(/^RR(?=\d)/i, "R");
  code = code.replace(/^R\s+(?=\d)/i, "R");
  if (/^\d/.test(code)) return `R${code}`;
  return code;
}

function formatRCodeValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "object" && !Array.isArray(value)) {
    const o = value as Record<string, unknown>;
    for (const key of ["code", "value", "label", "name"]) {
      const formatted = formatFactValue(o[key]);
      if (formatted) return normalizeRCodeText(formatted);
    }
  }
  const formatted = formatFactValue(value);
  return formatted ? normalizeRCodeText(formatted) : null;
}

export function formatFactValueForType(factType: string, value: unknown): string | null {
  if (factType === "r_code") return formatRCodeValue(value);
  return formatFactValue(value);
}

const IMAGE_FACT_TYPES = new Set(["aerial_image", "property_image", "site_image", "imagery"]);

function httpImageUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return /^https?:\/\//i.test(trimmed) ? trimmed : null;
}

/** Returns provider-backed property imagery when the resolver has supplied it.
 *  No placeholder is fabricated: licensed imagery remains attributable to its source. */
export function propertyImage(property: PropertyProfileResponse | null | undefined): PropertyImage | null {
  const fact = (property?.facts ?? []).find((item) => IMAGE_FACT_TYPES.has(item.fact_type));
  if (!fact) return null;

  if (typeof fact.value === "string") {
    const url = httpImageUrl(fact.value);
    return url ? { url, alt: property?.address ? `Aerial view of ${property.address}` : "Aerial view of the property" } : null;
  }
  if (!fact.value || typeof fact.value !== "object" || Array.isArray(fact.value)) return null;

  const value = fact.value as Record<string, unknown>;
  const url = [value.url, value.image_url, value.thumbnail_url].map(httpImageUrl).find(Boolean);
  if (!url) return null;
  const text = (candidate: unknown): string | null =>
    typeof candidate === "string" && candidate.trim() ? candidate.trim() : null;

  return {
    url,
    alt: text(value.alt) ?? (property?.address ? `Aerial view of ${property.address}` : "Aerial view of the property"),
    provider: text(value.provider) ?? text(value.source),
    captured_at: text(value.captured_at) ?? text(value.capture_date) ?? text(value.date),
    attribution: text(value.attribution),
  };
}

/** Curated, de-duplicated, non-empty property detail rows for the resolution view.
 *  Address and LGA come from the profile fields; the rest are formatted facts with values. */
export function propertyDetailRows(property: PropertyProfileResponse): PropertyDetailRow[] {
  const rows: PropertyDetailRow[] = [];
  if (property.address) rows.push({ label: "Address", value: property.address });
  if (property.local_government) rows.push({ label: "Local government", value: property.local_government });
  const seenRows = new Set(rows.map((row) => `${row.label}\u0000${row.value}`));
  const zoneValues: string[] = [];
  let zoneInsertIndex: number | null = null;

  (property.facts ?? [])
    .filter((f) => !HEADER_FACT_TYPES.has(f.fact_type) && !IMAGE_FACT_TYPES.has(f.fact_type))
    .map((f) => ({ f, value: formatFactValueForType(f.fact_type, f.value) }))
    .filter((x): x is { f: PropertyFactResponse; value: string } => x.value !== null)
    .sort((a, b) => factOrderIndex(a.f.fact_type) - factOrderIndex(b.f.fact_type))
    .forEach(({ f, value }) => {
      const label = factLabel(f.fact_type);
      if (label === "Zone") {
        if (zoneInsertIndex === null) zoneInsertIndex = rows.length;
        if (!zoneValues.includes(value)) zoneValues.push(value);
        return;
      }
      const rowKey = `${label}\u0000${value}`;
      if (seenRows.has(rowKey)) return;
      seenRows.add(rowKey);
      rows.push({ label, value });
    });

  if (zoneValues.length > 0) {
    rows.splice(zoneInsertIndex ?? rows.length, 0, {
      label: zoneValues.length === 1 ? "Zone" : "Zones",
      value: zoneValues.join(", "),
    });
  }

  return rows;
}
