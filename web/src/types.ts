import type { PropertyProfileResponse, ProposalRequest, ProposalResponse } from "./api";

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

/* ── wizard types ── */

export type WizardStep = 1 | 2 | 3;

export type WizardState = {
  step: WizardStep;
  projectId: string;
  address: string;
  property: PropertyProfileResponse | null;
  proposal: ProposalRequest;
  savedProposal: ProposalResponse | null;
};
