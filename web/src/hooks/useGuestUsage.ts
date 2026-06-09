import { useCallback, useState } from "react";
import type { ProjectSummary } from "../api";
import { GUEST_ADDRESS_LIMIT, GUEST_CHAT_LIMIT, GUEST_USAGE_KEY } from "../config";
import type { GuestCheck, GuestUsage, PaywallState } from "../types";

function emptyGuestUsage(): GuestUsage {
  return {
    addressChecks: 0,
    chatMessages: 0,
    checks: [],
    updatedAt: new Date().toISOString(),
  };
}

function normalizeGuestUsage(value: Partial<GuestUsage> | null | undefined): GuestUsage {
  const empty = emptyGuestUsage();
  return {
    addressChecks: Math.max(0, Number(value?.addressChecks ?? 0) || 0),
    chatMessages: Math.max(0, Number(value?.chatMessages ?? 0) || 0),
    checks: Array.isArray(value?.checks) ? value.checks.slice(0, 4) : [],
    updatedAt: typeof value?.updatedAt === "string" ? value.updatedAt : empty.updatedAt,
  };
}

function isGuestCheck(value: unknown): value is GuestCheck {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "string" &&
    typeof v.address === "string" &&
    typeof v.createdAt === "string" &&
    (v.mode === "guest" || v.mode === "fallback")
  );
}

function loadGuestUsage(): GuestUsage {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(GUEST_USAGE_KEY) ?? "null");
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return emptyGuestUsage();
    const candidate = parsed as Partial<GuestUsage>;
    return normalizeGuestUsage({
      ...candidate,
      checks: Array.isArray(candidate.checks) ? candidate.checks.filter(isGuestCheck) : [],
    });
  } catch {
    return emptyGuestUsage();
  }
}

function saveGuestUsage(usage: GuestUsage) {
  window.localStorage.setItem(GUEST_USAGE_KEY, JSON.stringify(usage));
}

export function guestProjectList(usage: GuestUsage): ProjectSummary[] {
  return usage.checks.map((check) => ({
    id: check.id,
    name: check.address,
    address: check.address,
    created_at: new Date(check.createdAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
    status: check.mode,
  }));
}

export function useGuestUsage(authed: boolean, onLimitReached: (state: PaywallState) => void) {
  const [guestUsage, setGuestUsage] = useState<GuestUsage>(() => loadGuestUsage());

  const startGuestAddress = useCallback((address: string): boolean => {
    if (authed) return true;
    if (guestUsage.addressChecks >= GUEST_ADDRESS_LIMIT) {
      onLimitReached({ feature: "address", used: guestUsage.addressChecks, limit: GUEST_ADDRESS_LIMIT });
      return false;
    }
    const now = new Date().toISOString();
    const next = normalizeGuestUsage({
      ...guestUsage,
      addressChecks: guestUsage.addressChecks + 1,
      checks: [
        {
          id: `guest-${Date.now().toString(36)}`,
          address,
          createdAt: now,
          mode: "guest" as const,
        },
        ...guestUsage.checks,
      ].slice(0, 4),
      updatedAt: now,
    });
    saveGuestUsage(next);
    setGuestUsage(next);
    return true;
  }, [authed, guestUsage, onLimitReached]);

  const startGuestChat = useCallback((): boolean => {
    if (authed) return true;
    if (guestUsage.chatMessages >= GUEST_CHAT_LIMIT) {
      onLimitReached({ feature: "chat", used: guestUsage.chatMessages, limit: GUEST_CHAT_LIMIT });
      return false;
    }
    const next = normalizeGuestUsage({
      ...guestUsage,
      chatMessages: guestUsage.chatMessages + 1,
      updatedAt: new Date().toISOString(),
    });
    saveGuestUsage(next);
    setGuestUsage(next);
    return true;
  }, [authed, guestUsage, onLimitReached]);

  return { guestUsage, startGuestAddress, startGuestChat };
}
