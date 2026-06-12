import { checkoutUrlFailures } from "./checkout-url.mjs";
import { fetchText } from "./live-fetch.mjs";

const origin = String(process.env.LAUNCH_ORIGIN ?? "https://lotfile.app").replace(/\/+$/, "");
const strict = process.argv.includes("--strict") || process.env.LAUNCH_STRICT === "1";
const expectedCheckoutUrl = String(process.env.LIVE_CHECKOUT_URL ?? process.env.VITE_CHECKOUT_URL ?? "").trim();
const failures = [];
const warnings = [];
const checkoutUrlLabel = process.env.LIVE_CHECKOUT_URL ? "LIVE_CHECKOUT_URL" : "VITE_CHECKOUT_URL";

function fail(message) {
  failures.push(message);
}

function warn(message) {
  warnings.push(message);
}

function assertIncludes(text, needle, label) {
  if (!text.includes(needle)) fail(`${label} missing '${needle}'`);
}

const routes = ["/", "/privacy", "/terms", "/app"];
for (const failure of checkoutUrlFailures(expectedCheckoutUrl, checkoutUrlLabel)) {
  fail(failure);
}

const pages = new Map();
for (const path of routes) {
  const response = await fetchText(`${origin}${path}`);
  pages.set(path, response);
  if (response.status !== 200) fail(`${path} returned HTTP ${response.status}`);
  assertIncludes(response.text, "LotFile - WA R-Code & Planning Compliance Checker", `${path} SEO title`);
  assertIncludes(response.text, 'name="description"', `${path} description meta`);
  assertIncludes(response.text, 'property="og:title"', `${path} Open Graph title`);
  assertIncludes(response.text, 'data-domain="lotfile.app"', `${path} Plausible script`);
}

for (const path of ["/api/v1/health", "/api/v1/ready"]) {
  const response = await fetchText(`${origin}${path}`);
  if (response.status !== 200) fail(`${path} returned HTTP ${response.status}`);
  try {
    const body = JSON.parse(response.text);
    if (body.status !== "ok") fail(`${path} status was ${String(body.status)}`);
  } catch (err) {
    fail(`${path} did not return JSON: ${err instanceof Error ? err.message : String(err)}`);
  }
}

const rootHtml = pages.get("/")?.text ?? "";
const assetMatches = [...rootHtml.matchAll(/assets\/([^"]+\.js)/g)].map((match) => match[0]);
if (!assetMatches.length) {
  fail("root page did not reference a JS bundle");
} else {
  const bundleParts = [];
  for (const asset of assetMatches) {
    const response = await fetchText(`${origin}/${asset}`);
    if (response.status !== 200) fail(`${asset} returned HTTP ${response.status}`);
    bundleParts.push(response.text);
  }
  const bundleText = bundleParts.join("\n");
  for (const needle of [
    "/privacy",
    "/terms",
    "Check an address free",
    "Advisory research only",
    "signup_requested",
    "project_created",
    "compliance_run",
    "checkout_clicked",
    "AUD $29/month",
  ]) {
    assertIncludes(bundleText, needle, "live JS bundle");
  }
  if (expectedCheckoutUrl) {
    assertIncludes(bundleText, expectedCheckoutUrl, "live checkout URL");
  } else if (strict) {
    fail("LIVE_CHECKOUT_URL or VITE_CHECKOUT_URL is required for strict live launch verification");
  } else {
    warn("checkout URL was not checked; set LIVE_CHECKOUT_URL for paid-launch verification");
  }
}

for (const warning of warnings) console.warn(`Live launch verification warning: ${warning}`);
if (failures.length) {
  console.error("Live launch verification failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Live launch verification passed for ${origin}.`);
