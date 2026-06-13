import { checkoutUrlFailures } from "./checkout-url.mjs";
import { fetchText } from "./live-fetch.mjs";

const origin = String(process.env.LAUNCH_ORIGIN ?? "https://lotfile.app").replace(/\/+$/, "");
const strict = process.argv.includes("--strict") || process.env.LAUNCH_STRICT === "1";
const jsonOutput = process.argv.includes("--json");
const expectedCheckoutUrl = String(process.env.LIVE_CHECKOUT_URL ?? process.env.VITE_CHECKOUT_URL ?? "").trim();
const failures = [];
const warnings = [];
const checkoutUrlLabel = process.env.LIVE_CHECKOUT_URL ? "LIVE_CHECKOUT_URL" : "VITE_CHECKOUT_URL";
const evidence = {
  origin,
  strict,
  checkout_checked: Boolean(expectedCheckoutUrl),
  routes: {},
  public_assets: {},
  api: {},
  bundles: [],
};

function fail(message) {
  failures.push(message);
}

function warn(message) {
  warnings.push(message);
}

function assertIncludes(text, needle, label) {
  if (!text.includes(needle)) fail(`${label} missing '${needle}'`);
}

function assertNotIncludes(text, needle, label) {
  if (text.includes(needle)) fail(`${label} must not include '${needle}'`);
}

const routes = [
  {
    path: "/",
    title: "LotFile - WA R-Code & Planning Compliance Checker",
    canonical: "https://lotfile.app/",
  },
  {
    path: "/privacy",
    title: "Privacy - LotFile",
    canonical: "https://lotfile.app/privacy",
  },
  {
    path: "/terms",
    title: "Terms - LotFile",
    canonical: "https://lotfile.app/terms",
  },
  {
    path: "/app",
    title: "LotFile - WA R-Code & Planning Compliance Checker",
    canonical: "https://lotfile.app/",
  },
];
const publicAssets = [
  {
    path: "/robots.txt",
    includes: ["Allow: /privacy", "Allow: /terms", "Disallow: /app", "Sitemap: https://lotfile.app/sitemap.xml"],
  },
  {
    path: "/sitemap.xml",
    includes: ["https://lotfile.app/", "https://lotfile.app/privacy", "https://lotfile.app/terms"],
  },
  { path: "/favicon.svg", includes: ["<svg"] },
  { path: "/og-image.svg", includes: ["<svg"] },
];

for (const failure of checkoutUrlFailures(expectedCheckoutUrl, checkoutUrlLabel)) {
  fail(failure);
}

const pages = new Map();
for (const route of routes) {
  const path = route.path;
  const response = await fetchText(`${origin}${path}`);
  pages.set(path, response);
  evidence.routes[path] = { status: response.status, title: route.title, canonical: route.canonical };
  if (response.status !== 200) fail(`${path} returned HTTP ${response.status}`);
  assertIncludes(response.text, `<title>${route.title}</title>`, `${path} SEO title`);
  assertIncludes(response.text, 'name="description"', `${path} description meta`);
  assertIncludes(response.text, `property="og:title" content="${route.title}"`, `${path} Open Graph title`);
  assertIncludes(response.text, `rel="canonical" href="${route.canonical}"`, `${path} canonical`);
  assertIncludes(response.text, `property="og:url" content="${route.canonical}"`, `${path} Open Graph URL`);
  assertIncludes(response.text, 'data-domain="lotfile.app"', `${path} Plausible script`);
}

for (const asset of publicAssets) {
  const response = await fetchText(`${origin}${asset.path}`);
  evidence.public_assets[asset.path] = { status: response.status };
  if (response.status !== 200) fail(`${asset.path} returned HTTP ${response.status}`);
  for (const needle of asset.includes) {
    assertIncludes(response.text, needle, `${asset.path} content`);
  }
}

for (const path of ["/api/v1/health", "/api/v1/ready"]) {
  const response = await fetchText(`${origin}${path}`);
  evidence.api[path] = { status: response.status, service_status: null };
  if (response.status !== 200) fail(`${path} returned HTTP ${response.status}`);
  try {
    const body = JSON.parse(response.text);
    evidence.api[path].service_status = body.status ?? null;
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
    evidence.bundles.push({ path: `/${asset}`, status: response.status });
    if (response.status !== 200) fail(`${asset} returned HTTP ${response.status}`);
    bundleParts.push(response.text);
  }
  const bundleText = bundleParts.join("\n");
  for (const needle of [
    "/privacy",
    "/terms",
    "Check an address free",
    "WA residential planning checks",
    "Clear next steps",
    "Read sourced results",
    "signup_requested",
    "project_created",
    "compliance_run",
    "checkout_clicked",
    "AUD $29/month",
  ]) {
    assertIncludes(bundleText, needle, "live JS bundle");
  }
  for (const removedNeedle of [
    "Advisory research only",
    "does not issue approvals.",
    "LotFile advisory check preview",
    ">Advisory</span>",
    "No finality claims",
    "Read cited advisory results",
    "LotFile provides advisory planning research only",
  ]) {
    assertNotIncludes(bundleText, removedNeedle, "live JS bundle removed disclaimer copy");
  }
  if (expectedCheckoutUrl) {
    assertIncludes(bundleText, expectedCheckoutUrl, "live checkout URL");
  } else if (strict) {
    fail("LIVE_CHECKOUT_URL or VITE_CHECKOUT_URL is required for strict live launch verification");
  } else {
    warn("checkout URL was not checked; set LIVE_CHECKOUT_URL for paid-launch verification");
  }
}

const result = {
  status: failures.length ? "failed" : "passed",
  evidence,
  warnings,
  failures,
};

if (jsonOutput) {
  console.log(JSON.stringify(result, null, 2));
  process.exit(failures.length ? 1 : 0);
}

for (const warning of warnings) console.warn(`Live launch verification warning: ${warning}`);
if (failures.length) {
  console.error("Live launch verification failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Live launch verification passed for ${origin}.`);
