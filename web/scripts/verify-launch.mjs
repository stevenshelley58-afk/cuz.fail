import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const dist = join(root, "dist");
const src = join(root, "src");
const publicDir = join(root, "public");

const failures = [];

function fail(message) {
  failures.push(message);
}

function read(path) {
  return readFileSync(path, "utf8");
}

function assertExists(path, label) {
  if (!existsSync(path)) fail(`${label} missing: ${path}`);
}

function assertIncludes(text, needle, label) {
  if (!text.includes(needle)) fail(`${label} missing '${needle}'`);
}

const indexPath = join(dist, "index.html");
assertExists(indexPath, "Built index");
const index = existsSync(indexPath) ? read(indexPath) : "";

assertIncludes(index, "LotFile - WA R-Code & Planning Compliance Checker", "SEO title");
assertIncludes(index, 'name="description"', "SEO description meta");
assertIncludes(index, 'property="og:title"', "Open Graph title");
assertIncludes(index, 'property="og:image"', "Open Graph image");
assertIncludes(index, 'name="twitter:card"', "Twitter card");
assertIncludes(index, 'rel="canonical"', "Canonical link");
assertIncludes(index, 'data-domain="lotfile.app"', "Plausible domain");

for (const asset of ["favicon.svg", "og-image.svg", "robots.txt", "sitemap.xml"]) {
  assertExists(join(publicDir, asset), `Public asset ${asset}`);
}

const sourceFiles = [
  join(src, "analytics.ts"),
  join(src, "components", "modals.tsx"),
  join(src, "views", "home.tsx"),
  join(src, "views", "compliance.tsx"),
].map(read).join("\n");

for (const eventName of ["signup_requested", "project_created", "compliance_run", "checkout_clicked"]) {
  assertIncludes(sourceFiles, eventName, "Plausible event");
}

const modalSource = read(join(src, "components", "modals.tsx"));
for (const label of ['aria-label="Username"', 'aria-label="Password"', 'aria-label="Email address"']) {
  assertIncludes(modalSource, label, "Sign-in accessible label");
}

const checkoutUrl = String(process.env.VITE_CHECKOUT_URL ?? "").trim();
const allowEmptyCheckout = process.env.ALLOW_EMPTY_CHECKOUT === "1";
if (!checkoutUrl && !allowEmptyCheckout) {
  fail("VITE_CHECKOUT_URL is required for launch verification. Set ALLOW_EMPTY_CHECKOUT=1 for local static-only checks.");
}

if (checkoutUrl) {
  const assetName = index.match(/assets\/([^"]+\.js)/)?.[1];
  if (!assetName) {
    fail("Built JS asset missing from dist/index.html");
  } else {
    const bundleText = index + "\n" + read(join(dist, "assets", assetName));
    assertIncludes(bundleText, checkoutUrl, "Built checkout URL");
  }
}

if (failures.length) {
  console.error("Launch verification failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Launch verification passed.");
