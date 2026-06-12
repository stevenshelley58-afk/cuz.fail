export const DEV_LOGIN = false;

export const GUEST_USAGE_KEY = "lotfile_guest_usage_v1";

function envNumber(name: "VITE_GUEST_ADDRESS_LIMIT" | "VITE_GUEST_CHAT_LIMIT", fallback: number): number {
  const raw = import.meta.env[name];
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

export const GUEST_ADDRESS_LIMIT = envNumber("VITE_GUEST_ADDRESS_LIMIT", 2);
export const GUEST_CHAT_LIMIT = envNumber("VITE_GUEST_CHAT_LIMIT", 8);
export const CHECKOUT_URL = String(import.meta.env.VITE_CHECKOUT_URL ?? "").trim();
export const PRICE_LABEL = String(import.meta.env.VITE_PRICE_LABEL ?? "AUD $29/month").trim();
export const PRICE_SUBLABEL = String(import.meta.env.VITE_PRICE_SUBLABEL ?? "Starter launch plan, cancel anytime.").trim();
