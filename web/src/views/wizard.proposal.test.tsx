import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { api } from "../api";
import type { WizardState } from "../types";
import { WizardShell } from "./wizard";

vi.mock("../api", () => ({
  api: {
    upsertProposal: vi.fn(),
  },
}));

vi.mock("./documents", () => ({
  DocumentUpload: () => <div data-testid="document-upload" />,
}));

vi.mock("./compliance", () => ({
  CompliancePanel: () => <div data-testid="compliance-panel" />,
}));

const apiMock = vi.mocked(api);

const wizard: WizardState = {
  step: 2 as const,
  projectId: "project-1",
  address: "3 Black Swan Rise, Beeliar",
  property: {
    org_id: "org-1",
    project_id: "project-1",
    address: "3 Black Swan Rise, Beeliar",
    local_government: "Cockburn",
    resolution_status: "resolved" as const,
    confidence: "high" as const,
    target_crs: "EPSG:7844",
    issues: [],
    provenance: [],
    facts: [],
  },
  proposal: {},
  savedProposal: null,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("proposal save success advances to the confirmation step", async () => {
  const user = userEvent.setup();
  apiMock.upsertProposal.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      id: "proposal-1",
      org_id: "org-1",
      project_id: "project-1",
      proposal_type: "residential",
      dwelling_type: "single_house",
      building_class: "class_1a",
      work_type: "new_construction",
      lot_type: "green_title",
      primary_street_confirmed: true,
      secondary_street_confirmed: false,
      created_at: "2026-06-13T00:00:00Z",
      updated_at: "2026-06-13T00:00:00Z",
    },
  });

  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  await user.selectOptions(screen.getByLabelText("Proposal type"), "residential");
  await user.selectOptions(screen.getByLabelText("Dwelling type"), "single_house");
  await user.selectOptions(screen.getByLabelText("Building class"), "class_1a");
  await user.selectOptions(screen.getByLabelText("Work type"), "new_construction");
  await user.click(screen.getByLabelText("New"));
  await user.selectOptions(screen.getByLabelText("Lot type"), "green_title");
  await user.click(screen.getByLabelText(/primary street frontage is confirmed/i));
  await user.click(screen.getByRole("button", { name: /save & continue/i }));

  await waitFor(() => {
    expect(apiMock.upsertProposal).toHaveBeenCalledWith("project-1", {
      proposal_type: "residential",
      dwelling_type: "single_house",
      building_class: "class_1a",
      work_type: "new_construction",
      new_or_existing: "new",
      lot_type: "green_title",
      primary_street_confirmed: true,
      secondary_street_confirmed: false,
    });
  });
  expect(await screen.findByText("Confirm and review")).toBeTruthy();
  expect(screen.getByText("class_1a")).toBeTruthy();
  expect(screen.getByText("Confirmed")).toBeTruthy();
  expect(screen.getByTestId("document-upload")).toBeTruthy();
  expect(screen.getByTestId("compliance-panel")).toBeTruthy();
});

test("confirmation CTA opens the project workspace", async () => {
  const user = userEvent.setup();
  const onProjectOpen = vi.fn();

  render(<WizardShell wizard={{ ...wizard, step: 3, proposal: { proposal_type: "residential" } }} onClose={vi.fn()} onProjectOpen={onProjectOpen} />);

  await user.click(screen.getByRole("button", { name: /open project workspace/i }));

  expect(onProjectOpen).toHaveBeenCalledWith("project-1");
});

test("proposal save requires launch-critical fields before calling the API", async () => {
  const user = userEvent.setup();

  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  await user.click(screen.getByRole("button", { name: /save & continue/i }));

  expect(await screen.findByText(/complete proposal type/i)).toBeTruthy();
  expect(apiMock.upsertProposal).not.toHaveBeenCalled();
  expect(screen.getByRole("heading", { name: /proposal details/i })).toBeTruthy();
});

test("proposal save not-built response stays on proposal step with an error", async () => {
  const user = userEvent.setup();
  apiMock.upsertProposal.mockResolvedValue({
    kind: "notBuilt",
    detail: "not implemented",
  });

  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  await user.selectOptions(screen.getByLabelText("Proposal type"), "residential");
  await user.selectOptions(screen.getByLabelText("Dwelling type"), "single_house");
  await user.selectOptions(screen.getByLabelText("Building class"), "class_1a");
  await user.selectOptions(screen.getByLabelText("Work type"), "new_construction");
  await user.click(screen.getByLabelText("New"));
  await user.selectOptions(screen.getByLabelText("Lot type"), "green_title");
  await user.click(screen.getByRole("button", { name: /save & continue/i }));

  expect(await screen.findByText("Proposal saving is unavailable. Try again before continuing.")).toBeTruthy();
  expect(screen.getByRole("heading", { name: /proposal details/i })).toBeTruthy();
  expect(screen.queryByText("Confirm and review")).toBeNull();
});
