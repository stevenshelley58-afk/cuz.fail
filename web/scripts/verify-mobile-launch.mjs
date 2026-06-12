import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, "src");
const failures = [];

function read(path) {
  return readFileSync(path, "utf8");
}

function fail(message) {
  failures.push(message);
}

function assertIncludes(text, needle, label) {
  if (!text.includes(needle)) fail(`${label} missing '${needle}'`);
}

function assertNotIncludes(text, needle, label) {
  if (text.includes(needle)) fail(`${label} must not include '${needle}'`);
}

const appSource = read(join(src, "App.tsx"));
const stylesSource = read(join(src, "styles.css"));
const homeSource = read(join(src, "views", "home.tsx"));
const wizardSource = read(join(src, "views", "wizard.tsx"));
const modalSource = read(join(src, "components", "modals.tsx"));

const mobileTabMatches = [...appSource.matchAll(/\{tab\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\)\}/g)];
const mobileTabLabels = mobileTabMatches.map((match) => match[3]);
if (mobileTabMatches.length !== 5) {
  fail(`Mobile tabbar must render exactly 5 tabs; found ${mobileTabMatches.length}`);
}
for (const label of ["Home", "Projects", "Library", "Rules", "Settings"]) {
  if (!mobileTabLabels.includes(label)) fail(`Mobile tabbar missing ${label}`);
}

for (const appNeedle of [
  'className={`tb${view === v ? " on" : ""}`}',
  'aria-current={view === v ? "page" : undefined}',
  'aria-label={label}',
  '<div className="tabbar">',
]) {
  assertIncludes(appSource, appNeedle, "Mobile tabbar accessibility");
}

for (const stylesNeedle of [
  "@media (max-width:900px)",
  "grid-template-columns:repeat(5,minmax(0,1fr))",
  "calc(62px + env(safe-area-inset-bottom,0px))",
  "min-height:62px",
  "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.05",
  "@media (max-width:390px)",
  ".tb{font-size:.5rem}",
  ".tb .icon{width:18px;height:18px}",
  ".tabbar{grid-template-rows:minmax(62px,auto)}",
  ".wizard-stepper{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))",
  ".wizard-step-label{white-space:normal!important;text-align:center;line-height:1.15;max-width:92px}",
  ".wizard-actions{flex-wrap:wrap!important}",
]) {
  assertIncludes(stylesSource, stylesNeedle, "Mobile launch CSS");
}
assertNotIncludes(stylesSource, "grid-template-columns:repeat(4,1fr)", "Mobile tabbar CSS");

for (const labelNeedle of [
  'aria-label="Address or planning question"',
  'aria-label="Toggle web search"',
  'aria-label="Send address or question"',
]) {
  assertIncludes(homeSource, labelNeedle, "Mobile home controls");
}

for (const modalNeedle of [
  'aria-modal="true"',
  'aria-label="Sign in"',
  'aria-label="Username"',
  'aria-label="Password"',
  'aria-label="Email address"',
]) {
  assertIncludes(modalSource, modalNeedle, "Mobile modal accessibility");
}

for (const wizardNeedle of [
  'aria-label="Check steps"',
  "wizard-stepper",
  "wizard-step-label",
  "wizard-actions",
]) {
  assertIncludes(wizardSource, wizardNeedle, "375px wizard structure");
}

if (failures.length) {
  console.error("Mobile launch sweep failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Mobile launch sweep passed.");
