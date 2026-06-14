import { useRef, useState } from "react";
import { Icon } from "../components/common";

type Navigate = (path: string) => void;

const EXAMPLES = [
  "100 St Georges Tce, Perth",
  "R-Code for my address",
  "Setbacks for a single house",
  "Can I subdivide this block?",
];

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
  const [prompt, setPrompt] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  function send() {
    const trimmed = prompt.trim();
    if (trimmed) sessionStorage.setItem("lotfile_launch_address", trimmed);
    onNavigate("/app");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function fillExample(text: string) {
    setPrompt(text);
    textareaRef.current?.focus();
  }

  return (
    <div className="launch">
      <Header onNavigate={onNavigate} />
      <main className="launch-main">
        <section className="launch-ask" aria-labelledby="launch-title">
          <h1 id="launch-title">Check a block. Ask anything.</h1>
          <form className="launch-prompt" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <label htmlFor="launch-address" className="sr-only">Address or question</label>
            <textarea
              id="launch-address"
              ref={textareaRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Type an address or ask a question about WA planning"
              rows={3}
              autoComplete="off"
            />
            <button type="submit" aria-label="Send">→</button>
          </form>
          <ul className="launch-examples" aria-label="Example prompts">
            {EXAMPLES.map((text) => (
              <li key={text}>
                <button type="button" onClick={() => fillExample(text)}>{text}</button>
              </li>
            ))}
          </ul>
        </section>
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
