import type { PropertyProfileResponse, ProposalRequest } from "./api";

export type GuestFeature = "address" | "chat";

export type GuestCheck = {
  id: string;
  address: string;
  createdAt: string;
  mode: "guest" | "fallback";
};

export type GuestUsage = {
  addressChecks: number;
  chatMessages: number;
  checks: GuestCheck[];
  updatedAt: string;
};

export type PaywallState = {
  feature: GuestFeature;
  used: number;
  limit: number;
};

/* ── check view state ── */

export type WizardState = {
  projectId: string;
  address: string;
  property: PropertyProfileResponse | null;
  proposal: ProposalRequest;
};
