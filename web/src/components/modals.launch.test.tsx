import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

type PlausibleWindow = Window & {
  plausible?: (eventName: string, options?: { props?: Record<string, string | number | boolean> }) => void;
};

afterEach(() => {
  cleanup();
  vi.resetModules();
  vi.clearAllMocks();
  vi.unstubAllEnvs();
});

function stubLocationAssign() {
  const originalLocation = window.location;
  const assign = vi.fn();
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      ...originalLocation,
      assign,
    },
  });
  return assign;
}

test("paid paywall tracks checkout intent and redirects to the configured Stripe link", async () => {
  vi.stubEnv("VITE_CHECKOUT_URL", "https://buy.stripe.com/launch_fixture");
  vi.stubEnv("VITE_PRICE_LABEL", "AUD $29/month");
  const plausible = vi.fn();
  (window as PlausibleWindow).plausible = plausible as PlausibleWindow["plausible"];
  const assign = stubLocationAssign();
  const { PaywallModal } = await import("./modals");

  render(
    <PaywallModal
      state={{ feature: "chat", used: 8, limit: 8 }}
      onClose={vi.fn()}
      onSignIn={vi.fn()}
    />,
  );

  await userEvent.click(screen.getByRole("button", { name: /unlock more checks/i }));

  expect(plausible).toHaveBeenCalledWith("checkout_clicked", {
    props: { feature: "chat", price: "AUD $29/month" },
  });
  expect(assign).toHaveBeenCalledWith("https://buy.stripe.com/launch_fixture");
});

test("paywall falls back to sign-in when no checkout link is configured", async () => {
  vi.stubEnv("VITE_CHECKOUT_URL", "");
  const onSignIn = vi.fn();
  const { PaywallModal } = await import("./modals");

  render(
    <PaywallModal
      state={{ feature: "address", used: 2, limit: 2 }}
      onClose={vi.fn()}
      onSignIn={onSignIn}
    />,
  );

  await userEvent.click(screen.getByRole("button", { name: /sign in to continue/i }));

  expect(onSignIn).toHaveBeenCalledOnce();
});

test("magic link sign-up tracks signup_requested before requesting email delivery", async () => {
  const magicLinkRequest = vi.fn().mockResolvedValue({ kind: "ok" });
  vi.doMock("../api", () => ({
    api: { magicLinkRequest },
  }));
  const plausible = vi.fn();
  (window as PlausibleWindow).plausible = plausible as PlausibleWindow["plausible"];
  const { MagicLinkForm } = await import("./modals");

  render(<MagicLinkForm variant="modal" onSignedIn={vi.fn()} />);

  await userEvent.type(screen.getByLabelText(/email address/i), "owner@example.test");
  await userEvent.click(screen.getByRole("button", { name: /send sign-in link/i }));

  expect(plausible).toHaveBeenCalledWith("signup_requested", undefined);
  expect(magicLinkRequest).toHaveBeenCalledWith("owner@example.test");
  expect(await screen.findByText(/check your email/i)).toBeTruthy();
});
