import { useCallback, useState } from "react";
import type { ProjectSummary } from "../api";
import { GUEST_USAGE_KEY } from "../config";
import type { GuestCheck, GuestUsage } from "../types";

// Soft counters only — the server enforces the real budget. These exist so the
// usage chip and the Recent strip work; they never block a request.

const MAX_RECENT_CHECKS = 6;

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
    checks: Array.isArray(value?.checks) ? value.checks.slice(0, MAX_RECENT_CHECKS) : [],
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

export function useGuestUsage(isGuest: boolean) {
  const [guestUsage, setGuestUsage] = useState<GuestUsage>(() => loadGuestUsage());

  // Record a successful guest address check (a real project) for the Recent strip.
  const recordGuestAddress = useCallback((address: string, projectId: string) => {
    if (!isGuest) return;
    const now = new Date().toISOString();
    setGuestUsage((prev) => {
      const next = normalizeGuestUsage({
        ...prev,
        addressChecks: prev.addressChecks + 1,
        checks: [
          { id: projectId, address, createdAt: now, mode: "guest" as const },
          ...prev.checks,
        ].slice(0, MAX_RECENT_CHECKS),
        updatedAt: now,
      });
      saveGuestUsage(next);
      return next;
    });
  }, [isGuest]);

  const recordGuestChat = useCallback(() => {
    if (!isGuest) return;
    setGuestUsage((prev) => {
      const next = normalizeGuestUsage({
        ...prev,
        chatMessages: prev.chatMessages + 1,
        updatedAt: new Date().toISOString(),
      });
      saveGuestUsage(next);
      return next;
    });
  }, [isGuest]);

  return { guestUsage, recordGuestAddress, recordGuestChat };
}
