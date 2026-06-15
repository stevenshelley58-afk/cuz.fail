import { useCallback, useState } from "react";
import type { AddressSuggestion } from "../api";
import { Icon } from "../components/common";
import { useAddressSuggestions } from "../hooks/useAddressSuggestions";

type Navigate = (path: string) => void;

function Header({ onNavigate }: { onNavigate: Navigate }) {
  return (
    <header className="launch-head">
      <button className="launch-logo" onClick={() => onNavigate("/")} aria-label="LotFile home">
        Lot<span>File</span>
      </button>
      <nav className="launch-nav" aria-label="Launch navigation">
        <button onClick={() => onNavigate("/privacy")}>Privacy</button>
        <button onClick={() => onNavigate("/terms")}>Terms</button>
        <button className="launch-nav-app" onClick={() => onNavigate("/app")}>Open app</button>
      </nav>
    </header>
  );
}

export function LandingPage({ onNavigate }: { onNavigate: Navigate }) {
  const [address, setAddress] = useState("");
  const {
    suggestions: sugs,
    suggestionIndex: sugIdx,
    setSuggestionIndex: setSugIdx,
    closeSuggestions: closeSugs,
    queueSuggestions: queueSuggest,
  } = useAddressSuggestions(6);

  const startCheck = useCallback((nextAddress = address) => {
    const trimmed = nextAddress.trim();
    closeSugs();
    if (trimmed) sessionStorage.setItem("lotfile_launch_address", trimmed);
    onNavigate("/app");
  }, [address, closeSugs, onNavigate]);

  const pickSuggestion = useCallback((suggestion: AddressSuggestion) => {
    setAddress(suggestion.address);
    startCheck(suggestion.address);
  }, [startCheck]);

  return (
    <div className="launch">
      <Header onNavigate={onNavigate} />
      <main className="launch-main">
        <section className="launch-hero" aria-labelledby="launch-title">
          <div className="launch-copy">
            <p className="launch-kicker">WA residential planning checks</p>
            <h1 id="launch-title">Check a block before the drafting bill lands.</h1>
            <p className="launch-lede">
              LotFile gives address-first planning checks for WA projects with cited source versions,
              uploaded-drawing extraction and clear missing-information flags.
            </p>
            <form className="launch-address" onSubmit={(e) => { e.preventDefault(); startCheck(); }}>
              <label htmlFor="launch-address">Street address</label>
              <div className="launch-address-row">
                <input
                  id="launch-address"
                  value={address}
                  onChange={(e) => {
                    const next = e.target.value;
                    setAddress(next);
                    queueSuggest(next);
                  }}
                  onKeyDown={(e) => {
                    if (!sugs.length) return;
                    if (e.key === "ArrowDown") {
                      e.preventDefault();
                      setSugIdx((idx) => (idx + 1) % sugs.length);
                      return;
                    }
                    if (e.key === "ArrowUp") {
                      e.preventDefault();
                      setSugIdx((idx) => (idx <= 0 ? sugs.length - 1 : idx - 1));
                      return;
                    }
                    if (e.key === "Escape") {
                      closeSugs();
                      return;
                    }
                    if ((e.key === "Enter" && sugIdx >= 0) || e.key === "Tab") {
                      e.preventDefault();
                      pickSuggestion(sugs[sugIdx >= 0 ? sugIdx : 0]);
                    }
                  }}
                  onBlur={() => window.setTimeout(closeSugs, 150)}
                  placeholder="Enter a WA street address"
                  autoComplete="street-address"
                />
                <button className="launch-address-submit" type="submit">
                  <Icon name="location_on" />Check an address free
                </button>
              </div>
              {sugs.length > 0 && (
                <div className="suggest launch-suggest" role="listbox" aria-label="Address suggestions">
                  <span className="suggest-head"><Icon name="location_on" />Addresses - pick one to start a check</span>
                  {sugs.map((suggestion, index) => (
                    <button
                      key={suggestion.gnaf_pid ?? suggestion.address}
                      type="button"
                      role="option"
                      aria-selected={index === sugIdx}
                      className={`suggest-item${index === sugIdx ? " on" : ""}`}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        pickSuggestion(suggestion);
                      }}
                      onMouseEnter={() => setSugIdx(index)}
                    >
                      <Icon name="location_on" />{suggestion.address}
                    </button>
                  ))}
                </div>
              )}
            </form>
          </div>
          <div className="launch-product" aria-label="LotFile check preview">
            <div className="launch-product-top">
              <span>LotFile check</span>
            </div>
            <div className="launch-product-address">
              <Icon name="location_on" />
              <div>
                <b>Address resolved</b>
                <span>Source status, confidence and provenance shown before any result.</span>
              </div>
            </div>
            <div className="launch-product-grid">
              <div><b>R-Code</b><span>cited source</span></div>
              <div><b>Setbacks</b><span>needs drawing</span></div>
              <div><b>Open space</b><span>measurement required</span></div>
              <div><b>Export</b><span>validation gated</span></div>
            </div>
          </div>
        </section>

        <section className="launch-band" aria-label="Trust and governance">
          <div>
            <Icon name="verified" />
            <b>Cited source library</b>
            <span>Answers must cite approved source versions or say the library cannot support them.</span>
          </div>
          <div>
            <Icon name="straighten" />
            <b>Drawing-aware checks</b>
            <span>Uploaded plans are used to extract facts and measurements, not to issue approvals.</span>
          </div>
          <div>
            <Icon name="gavel" />
            <b>Clear next steps</b>
            <span>Results highlight what is known, what needs drawings and what still needs review.</span>
          </div>
        </section>

        <section className="launch-steps" aria-label="How LotFile works">
          <article>
            <span>1</span>
            <h2>Start with the address</h2>
            <p>Resolve the project location, then review council, zone, R-Code and provenance before a check runs.</p>
          </article>
          <article>
            <span>2</span>
            <h2>Upload drawing evidence</h2>
            <p>DXF and plan facts stay reviewable, with measurements promoted only after confirmation.</p>
          </article>
          <article>
            <span>3</span>
            <h2>Read sourced results</h2>
            <p>Issue cards show the relevant source references, extracted facts and missing information.</p>
          </article>
        </section>

        <footer className="launch-footer">
          <span>LotFile helps organise planning checks before you commit to drafting work.</span>
          <nav aria-label="Footer links">
            <button onClick={() => onNavigate("/privacy")}>Privacy</button>
            <button onClick={() => onNavigate("/terms")}>Terms</button>
            <button onClick={() => onNavigate("/app")}>Open app</button>
          </nav>
        </footer>
      </main>
    </div>
  );
}

const PRIVACY_SECTIONS = [
  {
    title: "What we collect",
    body: "LotFile collects account details, session data, addresses, project notes, chat prompts, uploaded drawings, extracted facts and operational logs needed to run the advisory service.",
  },
  {
    title: "Uploaded drawings",
    body: "Uploaded drawings and plans may be stored with your project, parsed for dimensions and facts, and linked to advisory check results. They are not treated as council submissions or certification documents.",
  },
  {
    title: "How data is used",
    body: "We use project data to resolve addresses, retrieve cited sources, extract measurements, run deterministic checks, maintain audit traces, troubleshoot the service and improve reliability.",
  },
  {
    title: "Retention and sharing",
    body: "Project and uploaded-drawing data may be retained while your account or project exists and for operational backup periods. We do not sell uploaded drawings. Service providers may process data for hosting, email, analytics, storage and payment operations.",
  },
];

const TERMS_SECTIONS = [
  {
    title: "Advisory-only service",
    body: "LotFile provides planning research, source retrieval, drawing-fact extraction and advisory check outputs only. It does not provide legal advice, professional certification, building approval, planning approval or council determinations.",
  },
  {
    title: "User responsibility",
    body: "You remain responsible for checking source material, engaging qualified professionals where required and confirming requirements with the relevant authority before relying on any project decision.",
  },
  {
    title: "Uploaded drawings",
    body: "You must have the right to upload any drawing, plan or document you provide. LotFile may parse uploads to extract facts, measurements and evidence references for advisory checks.",
  },
  {
    title: "Liability limits",
    body: "To the maximum extent permitted by law, LotFile is supplied without a guarantee that advisory outputs are complete, current or suitable for a particular submission, approval or transaction.",
  },
];

export function LegalPage({ kind, onNavigate }: { kind: "privacy" | "terms"; onNavigate: Navigate }) {
  const isPrivacy = kind === "privacy";
  const sections = isPrivacy ? PRIVACY_SECTIONS : TERMS_SECTIONS;

  return (
    <div className="launch legal">
      <Header onNavigate={onNavigate} />
      <main className="legal-main">
        <p className="launch-kicker">LotFile {isPrivacy ? "privacy" : "terms"}</p>
        <h1>{isPrivacy ? "Privacy" : "Terms of use"}</h1>
        <p className="legal-lede">
          LotFile is an advisory planning tool. These terms do not turn any output into legal advice,
          professional certification, planning approval, building approval or a council decision.
        </p>
        <div className="legal-list">
          {sections.map((section) => (
            <section key={section.title}>
              <h2>{section.title}</h2>
              <p>{section.body}</p>
            </section>
          ))}
        </div>
        <button className="btn legal-cta" onClick={() => onNavigate("/app")}>
          <Icon name="location_on" />Check an address free
        </button>
      </main>
    </div>
  );
}
