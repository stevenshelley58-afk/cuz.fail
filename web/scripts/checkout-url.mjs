export function checkoutUrlFailures(rawUrl, label = "VITE_CHECKOUT_URL") {
  const value = String(rawUrl ?? "").trim();
  if (!value) return [];

  let url;
  try {
    url = new URL(value);
  } catch {
    return [`${label} must be a valid URL.`];
  }

  const failures = [];
  if (url.protocol !== "https:") {
    failures.push(`${label} must use https.`);
  }
  if (url.hostname !== "buy.stripe.com") {
    failures.push(`${label} must be a Stripe Payment Link on buy.stripe.com.`);
  }
  if (!url.pathname || url.pathname === "/") {
    failures.push(`${label} must include a Stripe Payment Link path.`);
  }
  return failures;
}
