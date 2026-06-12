type PlausibleEvent =
  | "signup_requested"
  | "project_created"
  | "compliance_run"
  | "checkout_clicked";

type PlausibleWindow = Window & {
  plausible?: (eventName: string, options?: { props?: Record<string, string | number | boolean> }) => void;
};

export function trackEvent(eventName: PlausibleEvent, props?: Record<string, string | number | boolean>) {
  const plausible = (window as PlausibleWindow).plausible;
  if (typeof plausible === "function") plausible(eventName, props ? { props } : undefined);
}
