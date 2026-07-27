import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Building2,
  CarFront,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleHelp,
  ExternalLink,
  Fence,
  FileText,
  ImageIcon,
  LandPlot,
  Leaf,
  MapPinned,
  MessageSquare,
  RefreshCw,
  Ruler,
  Search,
  ShieldCheck,
} from "lucide-react";
import { api, type ComplianceResultItem, type ComplianceRunResponse, type PropertyImage } from "../api";
import { trackEvent } from "../analytics";
import "./compliance.css";

/* ── CompliancePanel ── */

type CompliancePanelProps = {
  projectId: string;
  onUploadDrawing?: () => void;
  onProposalDetails?: () => void;
  proposalReady?: boolean;
  councilName?: string | null;
  propertyImage?: PropertyImage | null;
  /** Run a check automatically when no saved results exist yet (results-first view). */
  autoRun?: boolean;
  /** Increment to trigger a fresh run from outside (e.g. after refining the proposal). */
  runRequest?: number;
};

type StatusFilter = "all" | "likely_pass" | "likely_fail" | "needs_more_info";

function humanizeLabel(value: string): string {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function humanizeSentence(value: string): string {
  return humanizeLabel(value).toLowerCase();
}

function joinSentenceParts(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? "";
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

function missingDataLabels(item: ComplianceResultItem): string[] {
  return (item.missing_data ?? [])
    .map((part) => humanizeSentence(part))
    .filter((part) => part.length > 0);
}

function missingAsk(item: ComplianceResultItem): string {
  const labels = missingDataLabels(item);
  if (labels.length > 0) {
    return `We need ${joinSentenceParts(labels)} to assess this rule.`;
  }
  if (item.missing_info_reason) {
    return `We need ${humanizeSentence(item.missing_info_reason)} to assess this rule.`;
  }
  return "We need more proposal information to assess this rule.";
}

function missingBadgeLabel(item: ComplianceResultItem): string {
  const labels = missingDataLabels(item);
  if (labels.length > 0) return `Need ${labels[0]}`;
  return "More info needed";
}

type RuleGroup = {
  key: string;
  label: string;
  description: string;
};

const RULE_GROUPS: RuleGroup[] = [
  { key: "zoning", label: "Zoning & land use", description: "Zoning, R-Code density and whether a proposed use is permitted." },
  { key: "setbacks", label: "Setbacks & boundaries", description: "Distances from streets, side and rear boundaries." },
  { key: "building", label: "Building form", description: "Height, storeys, roof form and the overall building envelope." },
  { key: "site", label: "Site design & landscaping", description: "Site cover, open space, trees, landscaping and outdoor areas." },
  { key: "access", label: "Parking & access", description: "Garages, parking bays, driveways and vehicle access." },
  { key: "walls", label: "Walls & fences", description: "Boundary walls, retaining walls, screening and fencing." },
  { key: "lot", label: "Lot & subdivision", description: "Lot dimensions, density and subdivision requirements." },
  { key: "amenity", label: "Amenity & safety", description: "Neighbour amenity, environmental constraints and building safety." },
  { key: "other", label: "Other planning requirements", description: "Additional requirements that apply to this property." },
];

function ruleGroup(item: ComplianceResultItem): RuleGroup {
  const category = item.category?.trim().toLowerCase() ?? "";
  const key = `${item.check_key} ${item.display_name ?? ""}`.toLowerCase();
  let groupKey = "other";
  const categoryGroup: Record<string, string> = {
    zoning: "zoning",
    land_use: "zoning",
    setback: "setbacks",
    height: "building",
    storeys: "building",
    site_cover: "site",
    open_space: "site",
    site: "site",
    landscape: "site",
    garage: "access",
    parking: "access",
    driveway: "access",
    boundary_wall: "walls",
    wall: "walls",
    fence: "walls",
    lot: "lot",
    subdivision: "lot",
    amenity: "amenity",
    building_safety: "amenity",
    environmental: "amenity",
  };

  if (categoryGroup[category]) groupKey = categoryGroup[category];
  else if (/land[_ ]use|zoning|permissib|dwelling[_ ]density|r[_ -]?code|density[_ ]code|special[_ ]use/.test(key)) groupKey = "zoning";
  else if (category === "setback" || /\bsetback|boundary distance/.test(key)) groupKey = "setbacks";
  else if (/wall|fence|screening/.test(key)) groupKey = "walls";
  else if (/garage|parking|car ?park|driveway|vehicle access/.test(key)) groupKey = "access";
  else if (/lot width|lot area|density|subdivision/.test(key)) groupKey = "lot";
  else if (/\bheight|storey|storeys|ceiling|roof|building envelope/.test(key)) groupKey = "building";
  else if (/site cover|open space|landscap|tree|deep soil/.test(key)) groupKey = "site";
  else if (/amenity|privacy|overlooking|bushfire|flood|noise|safety|environment/.test(key)) groupKey = "amenity";

  return RULE_GROUPS.find((group) => group.key === groupKey) ?? RULE_GROUPS[RULE_GROUPS.length - 1];
}

function ruleTopic(item: ComplianceResultItem): string {
  return ruleGroup(item).label;
}

function RuleGroupIcon({ groupKey }: { groupKey: string }) {
  const props = { size: 18, strokeWidth: 1.8, "aria-hidden": true } as const;
  if (groupKey === "zoning") return <MapPinned {...props} />;
  if (groupKey === "setbacks") return <Ruler {...props} />;
  if (groupKey === "building") return <Building2 {...props} />;
  if (groupKey === "site") return <Leaf {...props} />;
  if (groupKey === "access") return <CarFront {...props} />;
  if (groupKey === "walls") return <Fence {...props} />;
  if (groupKey === "lot") return <LandPlot {...props} />;
  if (groupKey === "amenity") return <ShieldCheck {...props} />;
  return <FileText {...props} />;
}

function modalityLabel(modality: string): string {
  const key = modality.trim();
  const labels: Record<string, string> = {
    mandatory: "Mandatory standard",
    deemed_to_comply: "Deemed-to-comply standard",
    design_principle: "Design principle",
    advisory: "Advisory / guidance",
  };
  return labels[key] ?? humanizeLabel(key);
}

function externalDocumentUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return /^https?:\/\//i.test(trimmed) ? trimmed : null;
}

function hasProposalEvidence(item: ComplianceResultItem): boolean {
  const evidence = item.drawing_evidence ?? {};
  const method = typeof evidence.method === "string" ? evidence.method.toLowerCase() : "";
  return (
    method === "manual_override" ||
    method.includes("document") ||
    method.includes("drawing") ||
    typeof evidence.document_fact_id === "string" ||
    typeof evidence.source_document_id === "string"
  );
}

function hasPostProposalSignal(item: ComplianceResultItem): boolean {
  return hasProposalEvidence(item) || Boolean(item.missing_data?.length);
}

function StatusBadge({ item }: { item: ComplianceResultItem }) {
  if (item.status === "likely_pass")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#16a34a", fontWeight: 600 }}>
        <CheckCircle2 size={16} /> Likely pass
      </span>
    );
  if (item.status === "likely_fail")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#dc2626", fontWeight: 600 }}>
        <CircleAlert size={16} /> Likely fail
      </span>
    );
  if (item.status === "needs_more_info")
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#ca8a04", fontWeight: 600 }}>
        <CircleHelp size={16} /> {missingBadgeLabel(item)}
      </span>
    );
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#6b7280", fontWeight: 600 }}>
      — Unsupported
    </span>
  );
}

function RuleSourceDetails({ item, preProposal = false }: { item: ComplianceResultItem; preProposal?: boolean }) {
  const whatItMeans = item.what_it_means?.trim();
  const source = item.source;
  const sourceUrl = externalDocumentUrl(source?.url);

  return (
    <div className="rule-details">
      {whatItMeans && (
        <div className="rule-details__summary">
          <div className="rule-details__eyebrow">In plain English</div>
          <div>{whatItMeans}</div>
        </div>
      )}

      {item.rule_quote && (
        <blockquote className="rule-details__quote">
          {item.rule_quote}
        </blockquote>
      )}

      {source && (
        <div className="rule-details__source">
          <FileText size={15} aria-hidden="true" />
          <div className="rule-details__source-copy">
            <span>{source.title}</span>
            {source.section && <small>{source.section}</small>}
          </div>
          {sourceUrl && (
            <a href={sourceUrl} target="_blank" rel="noreferrer" aria-label={`Open source document: ${source.title}`}>
              View document <ExternalLink size={13} aria-hidden="true" />
            </a>
          )}
        </div>
      )}

      {item.modality?.trim() && (
        <div className="rule-details__meta">
          {modalityLabel(item.modality)}
        </div>
      )}

      {preProposal && (
        <div className="rule-details__next">
          Add your proposal details or house plans when you’re ready to check your design against this requirement.
        </div>
      )}
    </div>
  );
}

function RuleBrowserRow({ item }: { item: ComplianceResultItem }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className={`rule-row${expanded ? " rule-row--expanded" : ""}`}>
      <button
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        className="rule-row__toggle"
      >
        <span>{item.display_name ?? humanizeLabel(item.check_key)}</span>
        <span className="rule-row__chevron">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>
      {expanded && (
        <div className="rule-row__body">
          <RuleSourceDetails item={item} preProposal />
        </div>
      )}
    </div>
  );
}

function RulesBrowser({
  results,
  summaryResults,
  totalCount,
  councilName,
  onUploadDrawing,
  onProposalDetails,
  selectedTopic = "all",
  onSelectTopic,
  filterActive = false,
}: {
  results: ComplianceResultItem[];
  summaryResults?: ComplianceResultItem[];
  totalCount?: number;
  councilName?: string | null;
  onUploadDrawing?: () => void;
  onProposalDetails?: () => void;
  selectedTopic?: string;
  onSelectTopic?: (topic: string) => void;
  /** An active search/topic filter expands the list so matches are visible. */
  filterActive?: boolean;
}) {
  const [showRules, setShowRules] = useState(false);
  const applicableRules = results.filter((item) => item.status !== "unsupported");
  const summaryRules = (summaryResults ?? results).filter((item) => item.status !== "unsupported");
  const foundCount = totalCount ?? applicableRules.length;
  const grouped = new Map<string, ComplianceResultItem[]>();
  for (const item of applicableRules) {
    const group = ruleGroup(item);
    grouped.set(group.key, [...(grouped.get(group.key) ?? []), item]);
  }
  const summaryGrouped = new Map<string, ComplianceResultItem[]>();
  for (const item of summaryRules) {
    const group = ruleGroup(item);
    summaryGrouped.set(group.key, [...(summaryGrouped.get(group.key) ?? []), item]);
  }
  const visibleGroups = RULE_GROUPS.filter((group) => grouped.has(group.key));
  const visibleSummaryGroups = RULE_GROUPS.filter((group) => summaryGrouped.has(group.key));
  const planningContext = councilName ? `Planning context: ${councilName}` : "Planning context resolved for this address.";
  const rulesVisible = showRules || filterActive;

  if (foundCount === 0) {
    return (
      <div style={{ color: "#6b7280", fontSize: 14 }}>
        No source-backed planning rules are available for this property yet.
      </div>
    );
  }

  return (
    <div className="rules-browser">
      <div className="rules-summary">
        <div className="rules-summary__eyebrow">Property planning summary</div>
        <div className="rules-summary__title">
          We found {foundCount} planning rule{foundCount === 1 ? "" : "s"} that apply to this property
        </div>
        <div className="rules-summary__context">
          {planningContext}
          {applicableRules.length !== foundCount ? ` · Showing ${applicableRules.length}` : ""}
        </div>
        <div className="rules-summary__topics" aria-label={`${visibleSummaryGroups.length} planning topics`}>
          {visibleSummaryGroups.map((group) => {
            const count = summaryGrouped.get(group.key)?.length ?? 0;
            const selected = selectedTopic === group.label;
            return (
              <button
                key={group.key}
                type="button"
                aria-label={`${group.label}: ${count} rule${count === 1 ? "" : "s"}`}
                aria-pressed={selected}
                onClick={() => onSelectTopic?.(selected ? "all" : group.label)}
              >
                <RuleGroupIcon groupKey={group.key} />
                {group.label}
                <strong>{count}</strong>
              </button>
            );
          })}
        </div>
      </div>

      {!filterActive && (
        <button
          onClick={() => setShowRules((v) => !v)}
          aria-expanded={rulesVisible}
          className="rules-browser__toggle"
        >
          {rulesVisible ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          {rulesVisible ? "Hide planning details" : `Explore all ${foundCount} rule${foundCount === 1 ? "" : "s"}`}
        </button>
      )}

      {rulesVisible && (
        <>
          {applicableRules.length === 0 && (
            <div style={{ color: "#6b7280", fontSize: 14, marginBottom: 12 }}>No rules match your filter.</div>
          )}

          <div className="rule-groups">
            {visibleGroups.map((group) => {
              const items = grouped.get(group.key) ?? [];
              return (
              <section className="rule-group" key={group.key}>
                <header className="rule-group__header">
                  <span className="rule-group__icon"><RuleGroupIcon groupKey={group.key} /></span>
                  <div>
                    <h4>{group.label}</h4>
                    <p>{group.description}</p>
                  </div>
                  <span className="rule-group__count">{items.length}</span>
                </header>
                <div className="rule-group__items">
                  {items.map((item) => (
                    <RuleBrowserRow key={item.result_id} item={item} />
                  ))}
                </div>
              </section>
              );
            })}
          </div>
        </>
      )}

      {(onProposalDetails || onUploadDrawing) && (
        <div style={{ marginTop: 14, display: "flex", justifyContent: "flex-end", gap: 8, flexWrap: "wrap" }}>
          {onProposalDetails && (
            <button
              onClick={onProposalDetails}
              style={{
                fontSize: 13,
                padding: "7px 14px",
                background: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: 5,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Next: Proposal details →
            </button>
          )}
          {!onProposalDetails && onUploadDrawing && (
            <button
              onClick={onUploadDrawing}
              style={{
                fontSize: 13,
                padding: "7px 14px",
                background: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: 5,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Next: Upload house plans
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function PropertyImageCard({ image }: { image: PropertyImage }) {
  const details = [image.provider, image.captured_at ? `Captured ${image.captured_at}` : null].filter(Boolean).join(" · ");
  return (
    <figure className="property-image">
      <img src={image.url} alt={image.alt ?? "Aerial view of the property"} loading="lazy" referrerPolicy="no-referrer" />
      <figcaption>
        <span className="property-image__icon"><ImageIcon size={16} aria-hidden="true" /></span>
        <span>
          <strong>Property aerial</strong>
          {details && <small>{details}</small>}
        </span>
        {image.attribution && <span className="property-image__attribution">{image.attribution}</span>}
      </figcaption>
    </figure>
  );
}

function ComplianceResultRow({
  item,
  onUploadDrawing,
  onReviewRecorded,
}: {
  item: ComplianceResultItem;
  onUploadDrawing?: () => void;
  onReviewRecorded: (item: ComplianceResultItem) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [reviewDraft, setReviewDraft] = useState(item.review_reason ?? "");
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const drawingEvidence = item.drawing_evidence ?? {};
  const hasDrawingEvidence = Object.keys(drawingEvidence).length > 0;
  const evidenceFactType = typeof drawingEvidence.fact_type === "string" ? drawingEvidence.fact_type : null;
  const evidenceMethod = typeof drawingEvidence.method === "string" ? drawingEvidence.method : null;
  const evidenceDocumentFactId =
    typeof drawingEvidence.document_fact_id === "string" ? drawingEvidence.document_fact_id : null;
  const reviewAction = typeof item.human_override?.action === "string" ? item.human_override.action.replace(/_/g, " ") : null;

  useEffect(() => {
    setReviewDraft(item.review_reason ?? "");
    setReviewError(null);
  }, [item.result_id, item.review_reason]);

  async function recordReview() {
    const reason = reviewDraft.trim();
    if (!reason) {
      setReviewError("Review note is required.");
      return;
    }
    setReviewSaving(true);
    setReviewError(null);
    const response = await api.compliance.recordReview(item.result_id, "operator_note", reason);
    setReviewSaving(false);
    if (response.kind === "ok") {
      onReviewRecorded(response.data);
    } else if (response.kind === "auth") {
      setReviewError("Owner or operator access required.");
    } else if (response.kind === "missing") {
      setReviewError("This result is no longer available.");
    } else if (response.kind === "error") {
      setReviewError(response.message);
    } else {
      setReviewError("Could not record review.");
    }
  }

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        marginBottom: 8,
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontWeight: 500, fontSize: 14 }}>{item.display_name ?? item.check_key}</span>
        <StatusBadge item={item} />
      </button>

      {expanded && (
        <div style={{ padding: "0 14px 14px", fontSize: 13, color: "#374151" }}>
          {(item.measured_value !== null || item.threshold_value !== null) && (
            <div
              style={{
                display: "flex",
                gap: 24,
                background: "#f9fafb",
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 10,
              }}
            >
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Measured</div>
                <div style={{ fontWeight: 600 }}>
                  {item.measured_value ?? "—"}{" "}
                  {item.threshold_unit ? <span style={{ fontWeight: 400, color: "#6b7280" }}>{item.threshold_unit}</span> : null}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Threshold</div>
                <div style={{ fontWeight: 600 }}>
                  {item.threshold_value ?? "—"}{" "}
                  {item.threshold_unit ? <span style={{ fontWeight: 400, color: "#6b7280" }}>{item.threshold_unit}</span> : null}
                </div>
              </div>
            </div>
          )}

          <RuleSourceDetails item={item} />

          {hasDrawingEvidence && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: 6,
                padding: "8px 12px",
                marginBottom: 8,
                fontSize: 12,
                color: "#166534",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 3 }}>Drawing evidence</div>
              <div>
                {[evidenceFactType, evidenceMethod, evidenceDocumentFactId ? `fact ${evidenceDocumentFactId}` : null]
                  .filter(Boolean)
                  .join(" · ") || "Promoted drawing evidence recorded for this check."}
              </div>
            </div>
          )}

          {item.status === "needs_more_info" && (
            <div
              style={{
                background: "#fffbeb",
                border: "1px solid #fde68a",
                borderRadius: 6,
                padding: "8px 12px",
                marginTop: 8,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4, color: "#92400e" }}>{missingAsk(item)}</div>
              {item.missing_data && item.missing_data.length > 0 ? (
                <ul style={{ margin: "0 0 8px", paddingLeft: 16 }}>
                  {item.missing_data.map((d) => (
                    <li key={d} style={{ fontSize: 12 }}>{humanizeLabel(d)}</li>
                  ))}
                </ul>
              ) : null}
              {onUploadDrawing && (
                <button
                  onClick={onUploadDrawing}
                  style={{
                    fontSize: 12,
                    padding: "4px 10px",
                    background: "#f59e0b",
                    color: "#fff",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                  }}
                >
                  Upload drawing to provide this data
                </button>
              )}
            </div>
          )}

          <div
            style={{
              borderTop: "1px solid #e5e7eb",
              marginTop: 12,
              paddingTop: 12,
            }}
          >
            {item.review_reason && (
              <div style={{ fontSize: 12, color: "#4b5563", marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>Review:</span> {item.review_reason}
                {reviewAction ? <span style={{ color: "#6b7280" }}> ({reviewAction})</span> : null}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <textarea
                value={reviewDraft}
                onChange={(event) => setReviewDraft(event.target.value)}
                rows={2}
                aria-label={`Review note for ${item.display_name ?? item.check_key}`}
                style={{
                  flex: 1,
                  minWidth: 0,
                  resize: "vertical",
                  border: "1px solid #d1d5db",
                  borderRadius: 6,
                  padding: "7px 9px",
                  font: "inherit",
                  fontSize: 12,
                  color: "#111827",
                }}
              />
              <button
                onClick={() => void recordReview()}
                disabled={reviewSaving}
                title="Record review"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "7px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: 6,
                  background: reviewSaving ? "#f3f4f6" : "#fff",
                  color: reviewSaving ? "#6b7280" : "#111827",
                  cursor: reviewSaving ? "not-allowed" : "pointer",
                  fontSize: 12,
                  whiteSpace: "nowrap",
                }}
              >
                <MessageSquare size={14} />
                {reviewSaving ? "Saving" : "Record"}
              </button>
            </div>
            {reviewError && <div style={{ fontSize: 12, color: "#b91c1c", marginTop: 6 }}>{reviewError}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

export function CompliancePanel({
  projectId,
  onUploadDrawing,
  onProposalDetails,
  proposalReady = false,
  councilName,
  propertyImage,
  autoRun = false,
  runRequest,
}: CompliancePanelProps) {
  const [runResult, setRunResult] = useState<ComplianceRunResponse | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(true);
  const [matrixLoadMessage, setMatrixLoadMessage] = useState<string | null>(null);
  const [matrixLoadTone, setMatrixLoadTone] = useState<"info" | "error">("info");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadPrompted, setUploadPrompted] = useState(false);
  const [ranAssessment, setRanAssessment] = useState(false);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [topicFilter, setTopicFilter] = useState("all");
  const resultVersionRef = useRef(0);
  const autoRanRef = useRef(false);
  const lastRunRequestRef = useRef(runRequest ?? 0);

  const runCheck = useCallback(async (opts?: { auto?: boolean }) => {
    resultVersionRef.current += 1;
    setLoading(true);
    setError(null);
    const r = await api.compliance.run(projectId);
    setLoading(false);
    if (r.kind === "ok") {
      setRunResult(r.data);
      setMatrixLoadMessage(null);
      if (!opts?.auto) setRanAssessment(true);
      trackEvent("compliance_run", { result_count: r.data.results.length, status: r.data.status });
    } else if (opts?.auto) {
      // Silent first-load run: fall back to the quiet empty state instead of an error banner.
      setMatrixLoadTone("info");
      setMatrixLoadMessage("No results for this address yet.");
    } else if (r.kind === "notBuilt") {
      setError("Compliance check endpoint not yet available on this server.");
    } else if (r.kind === "auth") {
      setError("Sign in required.");
    } else if (r.kind === "error") {
      setError(r.message);
    } else {
      setError("Could not reach server.");
    }
  }, [projectId]);

  const loadMatrix = useCallback(async () => {
    const requestVersion = resultVersionRef.current;
    setMatrixLoading(true);
    setMatrixLoadMessage(null);
    const r = await api.compliance.matrix(projectId);
    setMatrixLoading(false);
    if (requestVersion !== resultVersionRef.current) {
      return;
    }
    if (r.kind === "ok") {
      setRunResult(r.data);
      return;
    }
    if (r.kind === "missing" && autoRun && !autoRanRef.current) {
      autoRanRef.current = true;
      await runCheck({ auto: true });
      return;
    }
    if (r.kind === "auth") {
      setMatrixLoadTone("error");
      setMatrixLoadMessage("Sign in required to load saved compliance results.");
    } else if (r.kind === "missing") {
      setMatrixLoadTone("info");
      setMatrixLoadMessage("No results for this project yet.");
    } else if (r.kind === "notBuilt") {
      setMatrixLoadTone("info");
      setMatrixLoadMessage("Saved compliance matrix loading is not available on this server yet.");
    } else if (r.kind === "error") {
      setMatrixLoadTone("error");
      setMatrixLoadMessage(r.message);
    } else {
      setMatrixLoadTone("error");
      setMatrixLoadMessage("Could not reach server to load saved compliance results.");
    }
  }, [projectId, autoRun, runCheck]);

  useEffect(() => {
    void loadMatrix();
  }, [loadMatrix]);

  useEffect(() => {
    const next = runRequest ?? 0;
    if (next > lastRunRequestRef.current) {
      lastRunRequestRef.current = next;
      void runCheck();
    }
  }, [runRequest, runCheck]);

  async function retryMatrixLoad() {
    setError(null);
    await loadMatrix();
  }

  function updateReviewedResult(updated: ComplianceResultItem) {
    setRunResult((current) => {
      if (!current) return current;
      return {
        ...current,
        results: current.results.map((item) => (item.result_id === updated.result_id ? updated : item)),
      };
    });
  }

  function handleUploadDrawing() {
    setUploadPrompted(true);
    onUploadDrawing?.();
  }

  const results = runResult?.results ?? [];
  const hasPostProposalEvidence = results.some(hasPostProposalSignal);
  const isPostProposal = ranAssessment || hasPostProposalEvidence;
  const canRunAssessment = proposalReady || isPostProposal;
  const passCount = results.filter((r) => r.status === "likely_pass").length;
  const failCount = results.filter((r) => r.status === "likely_fail").length;
  const moreInfoCount = results.filter((r) => r.status === "needs_more_info").length;
  const unsupportedCount = results.filter((r) => r.status === "unsupported").length;
  const actionableCount = passCount + failCount;

  const applicableResults = useMemo(() => results.filter((item) => item.status !== "unsupported"), [results]);
  const topics = useMemo(() => {
    const set = new Set<string>();
    for (const item of applicableResults) set.add(ruleTopic(item));
    return Array.from(set).sort();
  }, [applicableResults]);
  const filteredResults = useMemo(() => {
    const q = query.trim().toLowerCase();
    return applicableResults.filter((item) => {
      if (topicFilter !== "all" && ruleTopic(item) !== topicFilter) return false;
      if (statusFilter !== "all" && item.status !== statusFilter) return false;
      if (q) {
        const haystack = [
          item.display_name,
          item.check_key,
          item.citation,
          item.rule_quote,
          item.what_it_means,
          item.note,
          ruleTopic(item),
        ].filter(Boolean).join(" ").toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [applicableResults, query, statusFilter, topicFilter]);
  const showFilters = applicableResults.length > 3;
  const showRulesBrowser = results.length > 0 && !isPostProposal;
  const browserFilterActive = query.trim().length > 0 || topicFilter !== "all";

  return (
    <div style={{ padding: "0 0 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Compliance check</h3>
          {isPostProposal && results.length > 0 && (
            <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
              {actionableCount > 0
                ? `${passCount} likely pass · ${failCount} likely fail${moreInfoCount > 0 ? ` · ${moreInfoCount} need a measurement` : ""}`
                : moreInfoCount > 0
                  ? `Ready to check ${moreInfoCount + actionableCount} rules — upload a drawing to fill in measurements`
                  : `${unsupportedCount} check${unsupportedCount === 1 ? "" : "s"} have no rule loaded yet`}
            </div>
          )}
        </div>
        {canRunAssessment && (
          <button
            onClick={() => void runCheck()}
            disabled={loading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",
              background: loading ? "#e5e7eb" : "#2563eb",
              color: loading ? "#6b7280" : "#fff",
              border: "none",
              borderRadius: 6,
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 500,
              fontSize: 14,
            }}
          >
            <RefreshCw size={15} style={loading ? { animation: "spin 1s linear infinite" } : {}} />
            {loading ? "Running…" : "Run compliance check"}
          </button>
        )}
      </div>

      {results.length > 0 && propertyImage && <PropertyImageCard image={propertyImage} />}

      {error && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#b91c1c",
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {matrixLoading && !runResult && (
        <div style={{ color: "#6b7280", fontSize: 14, marginBottom: 12 }}>
          Loading saved compliance results...
        </div>
      )}

      {matrixLoadMessage && !runResult && (
        <div
          style={{
            background: matrixLoadTone === "error" ? "#fef2f2" : "#eff6ff",
            border: `1px solid ${matrixLoadTone === "error" ? "#fecaca" : "#bfdbfe"}`,
            borderRadius: 6,
            padding: "8px 12px",
            color: matrixLoadTone === "error" ? "#b91c1c" : "#1e40af",
            fontSize: 13,
            marginBottom: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          <span>{matrixLoadMessage}</span>
          <button
            onClick={() => void retryMatrixLoad()}
            disabled={matrixLoading}
            style={{
              flexShrink: 0,
              border: "1px solid currentColor",
              borderRadius: 5,
              background: "transparent",
              color: "inherit",
              padding: "4px 8px",
              fontSize: 12,
              cursor: matrixLoading ? "not-allowed" : "pointer",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {results.length === 0 && !loading && !matrixLoading && !matrixLoadMessage && !error && (
        <div style={{ color: "#6b7280", fontSize: 14 }}>
          {canRunAssessment
            ? "No compliance results yet. Run a check to get started."
            : "No source-backed planning rules are available for this property yet."}
        </div>
      )}

      {showFilters && (showRulesBrowser || isPostProposal) && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 14 }}>
          <div style={{ position: "relative", flex: "1 1 220px", minWidth: 180 }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#9ca3af" }} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter rules — setbacks, open space, height…"
              aria-label="Filter rules"
              style={{
                width: "100%",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: "8px 10px 8px 30px",
                fontSize: 13,
                outline: "none",
                fontFamily: "inherit",
              }}
            />
          </div>
          {topics.length > 1 && (
            <select
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
              aria-label="Filter by topic"
              style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: "8px 10px", fontSize: 13, background: "#fff", fontFamily: "inherit" }}
            >
              <option value="all">All topics</option>
              {topics.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          )}
          {isPostProposal && (
            <div style={{ display: "flex", gap: 6 }}>
              {([
                ["all", `All (${applicableResults.length})`],
                ["likely_pass", `Pass (${passCount})`],
                ["likely_fail", `Fail (${failCount})`],
                ["needs_more_info", `Needs info (${moreInfoCount})`],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setStatusFilter(value)}
                  aria-pressed={statusFilter === value}
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    padding: "6px 10px",
                    borderRadius: 99,
                    border: `1px solid ${statusFilter === value ? "#111827" : "#e5e7eb"}`,
                    background: statusFilter === value ? "#111827" : "#fff",
                    color: statusFilter === value ? "#fff" : "#374151",
                    cursor: "pointer",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {showRulesBrowser && (
        <RulesBrowser
          results={filteredResults}
          summaryResults={applicableResults}
          totalCount={applicableResults.length}
          councilName={councilName}
          onUploadDrawing={onUploadDrawing ? handleUploadDrawing : undefined}
          onProposalDetails={onProposalDetails}
          selectedTopic={topicFilter}
          onSelectTopic={setTopicFilter}
          filterActive={browserFilterActive}
        />
      )}

      {isPostProposal && filteredResults.length === 0 && applicableResults.length > 0 && (
        <div style={{ color: "#6b7280", fontSize: 14 }}>No rules match your filter.</div>
      )}

      {isPostProposal && filteredResults
        .map((item) => (
          <ComplianceResultRow
            key={item.result_id}
            item={item}
            onUploadDrawing={item.status === "needs_more_info" ? handleUploadDrawing : undefined}
            onReviewRecorded={updateReviewedResult}
          />
        ))}

      {runResult?.advisory_disclaimer && (
        <div
          style={{
            marginTop: 16,
            fontSize: 11,
            color: "#9ca3af",
            textAlign: "center",
            fontStyle: "italic",
          }}
        >
          {runResult.advisory_disclaimer}
        </div>
      )}

      {uploadPrompted && (
        <div
          style={{
            marginTop: 12,
            padding: "10px 14px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 8,
            fontSize: 13,
            color: "#1e40af",
          }}
        >
          Use the Documents upload area to add a drawing or plan for this check.
        </div>
      )}
    </div>
  );
}
