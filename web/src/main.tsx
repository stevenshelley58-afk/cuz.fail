import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  FileUp,
  Loader2,
  MapPin,
  MessageSquare,
  Play,
  ShieldCheck,
} from "lucide-react";
import { apiClient, type ApiProbeResult, type ParserAccuracyReport, type ProbeName } from "./api";
import "./styles.css";

type ProbeState = {
  phase: "loading" | "checked";
  probes: Partial<Record<ProbeName, ApiProbeResult>>;
};

type ReviewItem = {
  title: string;
  status: "Needs review" | "Missing info" | "Not assessed";
  detail: string;
  evidence: string;
};

type ParserCheckState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "checked"; report: ParserAccuracyReport }
  | { phase: "error"; message: string };

const reviewItems: ReviewItem[] = [
  {
    title: "Site cover",
    status: "Needs review",
    detail: "Lot area and footprint were found in the sample drawing. A reviewer still has to confirm the rule source.",
    evidence: "sv_artificial_measurement_protocol_2026_v1",
  },
  {
    title: "Open space",
    status: "Missing info",
    detail: "The sample drawing has an open-space area, but the exclusion classification is not supplied.",
    evidence: "classification_required",
  },
  {
    title: "Primary street setback",
    status: "Needs review",
    detail: "A front setback measurement was found. Contextual judgement remains reviewer-gated.",
    evidence: "trace_fixture_primary_street_setback",
  },
  {
    title: "Boundary wall",
    status: "Not assessed",
    detail: "The sample does not assert a boundary-wall proposal.",
    evidence: "proposal_confirmation_required",
  },
];

function probesToRecord(results: ApiProbeResult[]): Partial<Record<ProbeName, ApiProbeResult>> {
  return results.reduce<Partial<Record<ProbeName, ApiProbeResult>>>((record, probe) => {
    record[probe.name] = probe;
    return record;
  }, {});
}

function isLive(state: ProbeState): boolean {
  return Boolean(state.probes.health?.ok && state.probes.ready?.ok);
}

function StatusDot({ state }: { state: ProbeState }) {
  if (state.phase === "loading") {
    return (
      <span className="status-dot loading">
        <Loader2 size={15} aria-hidden="true" />
        Checking API
      </span>
    );
  }

  return (
    <span className={isLive(state) ? "status-dot live" : "status-dot down"}>
      <span aria-hidden="true" />
      {isLive(state) ? "Live" : "Offline"}
    </span>
  );
}

function ReviewBadge({ status }: { status: ReviewItem["status"] }) {
  const className = `review-badge ${status.toLowerCase().replaceAll(" ", "-")}`;
  return <span className={className}>{status}</span>;
}

function parserMessage(state: ParserCheckState): string {
  switch (state.phase) {
    case "idle":
      return "Parsers live: text, PDF text, DOCX, DXF, CSV, IFC preview. Image measurements need calibration.";
    case "loading":
      return "Checking the live parser against the sample pack...";
    case "checked":
      return `Live parser matched ${state.report.matched_fact_count}/${state.report.expected_fact_count} sample facts.`;
    case "error":
      return state.message;
  }
}

function App() {
  const [probeState, setProbeState] = useState<ProbeState>({ phase: "loading", probes: {} });
  const [address, setAddress] = useState("10 Canary Lane, Demo Bay WA 6000");
  const [addressResolved, setAddressResolved] = useState(true);
  const [drawingLoaded, setDrawingLoaded] = useState(false);
  const [reviewRun, setReviewRun] = useState(false);
  const [question, setQuestion] = useState("Can I submit this?");
  const [parserCheck, setParserCheck] = useState<ParserCheckState>({ phase: "idle" });

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([apiClient.health(controller.signal), apiClient.ready(controller.signal)]).then(
      (results) => {
        if (!controller.signal.aborted) {
          setProbeState({ phase: "checked", probes: probesToRecord(results) });
        }
      }
    );

    return () => controller.abort();
  }, []);

  async function loadSampleDrawing() {
    setParserCheck({ phase: "loading" });
    setDrawingLoaded(false);
    setReviewRun(false);
    try {
      const report = await apiClient.parserAccuracy();
      setParserCheck({ phase: "checked", report });
      setDrawingLoaded(report.demo_fixture_status === "passed");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Parser accuracy check failed.";
      setParserCheck({ phase: "error", message });
    }
  }

  return (
    <main className="simple-shell">
      <header className="topbar">
        <div className="brand">
          <ShieldCheck size={24} aria-hidden="true" />
          <div>
            <strong>DraftCheck WA</strong>
            <span>Simple review demo</span>
          </div>
        </div>
        <StatusDot state={probeState} />
      </header>

      <section className="intro">
        <p className="eyebrow">Start here</p>
        <h1>Check a WA planning pack without getting lost.</h1>
        <p>
          Enter an address, add drawings, run a review, then ask what is still missing. This demo
          keeps every outcome reviewer-gated.
        </p>
      </section>

      <section className="flow">
        <article className="step-card">
          <div className="step-head">
            <span>1</span>
            <div>
              <h2>Address</h2>
              <p>Confirm the property first.</p>
            </div>
          </div>
          <label htmlFor="address">Project address</label>
          <div className="input-row">
            <input
              id="address"
              value={address}
              onChange={(event) => {
                setAddress(event.target.value);
                setAddressResolved(false);
              }}
            />
            <button type="button" onClick={() => setAddressResolved(true)}>
              <MapPin size={17} aria-hidden="true" />
              Resolve
            </button>
          </div>
          {addressResolved && (
            <div className="result-strip good">
              <CheckCircle2 size={18} aria-hidden="true" />
              Demo Bay Local Government, R30 fixture value, 450.0 m2 lot area.
            </div>
          )}
        </article>

        <article className="step-card">
          <div className="step-head">
            <span>2</span>
            <div>
              <h2>Drawings</h2>
              <p>Add a plan or use the sample pack.</p>
            </div>
          </div>
          <button
            className="upload-zone"
            type="button"
            onClick={() => void loadSampleDrawing()}
            disabled={parserCheck.phase === "loading"}
          >
            {parserCheck.phase === "loading" ? (
              <Loader2 size={22} aria-hidden="true" className="spin-icon" />
            ) : (
              <FileUp size={22} aria-hidden="true" />
            )}
            <strong>{drawingLoaded ? "Sample parser check passed" : "Use sample drawing"}</strong>
            <small>Site plan, dimensions, footprint, frontage, setback.</small>
          </button>
          <p className={parserCheck.phase === "error" ? "parser-note error" : "parser-note"}>
            {parserMessage(parserCheck)}
          </p>
        </article>

        <article className="step-card action-card">
          <div className="step-head">
            <span>3</span>
            <div>
              <h2>Review</h2>
              <p>Generate plain review tasks.</p>
            </div>
          </div>
          <button
            className="primary-action"
            type="button"
            disabled={!addressResolved || !drawingLoaded}
            onClick={() => setReviewRun(true)}
          >
            <Play size={18} aria-hidden="true" />
            Run review
          </button>
          {!drawingLoaded && <p className="hint">Load the sample drawing first.</p>}
        </article>
      </section>

      <section className="results">
        <div className="section-title">
          <div>
            <p className="eyebrow">Result</p>
            <h2>{reviewRun ? "Review tasks" : "Waiting for review"}</h2>
          </div>
          <span>{reviewRun ? "4 items" : "No result yet"}</span>
        </div>

        {reviewRun ? (
          <div className="review-list">
            {reviewItems.map((item) => (
              <article className="review-row" key={item.title}>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.detail}</p>
                  <code>{item.evidence}</code>
                </div>
                <ReviewBadge status={item.status} />
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <AlertTriangle size={19} aria-hidden="true" />
            Resolve the address, load the sample drawing, then run review.
          </div>
        )}
      </section>

      <section className="ask-box">
        <div className="section-title">
          <div>
            <p className="eyebrow">Ask</p>
            <h2>Plain answer</h2>
          </div>
          <MessageSquare size={21} aria-hidden="true" />
        </div>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
        <div className="answer">
          <strong>Answer</strong>
          <p>
            Not yet. This fixture can organize the review tasks, but it cannot make a final
            planning, building, legal, or certification compliance claim. A reviewer still needs to
            confirm the source versions and missing information.
          </p>
        </div>
      </section>

      <footer>
        Demo only. Real projects require current approved sources, traceable evidence, and human
        signoff.
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
