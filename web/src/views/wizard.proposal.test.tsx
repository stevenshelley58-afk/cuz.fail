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
  CompliancePanel: ({ runRequest }: { runRequest?: number }) => (
    <div data-testid="compliance-panel" data-run-request={runRequest ?? 0} />
  ),
}));

const apiMock = vi.mocked(api);

const wizard: WizardState = {
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
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("check view shows results with subtle hero actions for refine and upload", async () => {
  const user = userEvent.setup();
  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  expect(screen.getByText("3 Black Swan Rise, Beeliar")).toBeTruthy();
  expect(screen.getByTestId("compliance-panel")).toBeTruthy();
  // Refine and upload stay tucked behind hero actions until asked for
  expect(screen.queryByTestId("document-upload")).toBeNull();
  expect(screen.queryByRole("button", { name: /tell us about your project/i })).toBeNull();

  await user.click(screen.getByRole("button", { name: /upload plans/i }));
  expect(screen.getByTestId("document-upload")).toBeTruthy();

  await user.click(screen.getByRole("button", { name: /add project details/i }));
  expect(screen.getByRole("button", { name: /tell us about your project/i })).toBeTruthy();

  // No stepper, no confirmation gate
  expect(screen.queryByText(/confirm and review/i)).toBeNull();
  expect(screen.queryByText(/next: proposal details/i)).toBeNull();
});

test("refine save success updates results via a fresh compliance run", async () => {
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

  await user.click(screen.getByRole("button", { name: /add project details/i }));
  await user.selectOptions(screen.getByLabelText("Proposal type"), "residential");
  await user.selectOptions(screen.getByLabelText("Dwelling type"), "single_house");
  await user.selectOptions(screen.getByLabelText("Building class"), "class_1a");
  await user.selectOptions(screen.getByLabelText("Work type"), "new_construction");
  await user.click(screen.getByLabelText("New"));
  await user.selectOptions(screen.getByLabelText("Lot type"), "green_title");
  await user.click(screen.getByLabelText(/primary street frontage is confirmed/i));
  await user.click(screen.getByRole("button", { name: /update results/i }));

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
  // The compliance panel is asked to re-run
  await waitFor(() => {
    expect(screen.getByTestId("compliance-panel").getAttribute("data-run-request")).toBe("1");
  });
});

test("open project workspace CTA hands off the project id", async () => {
  const user = userEvent.setup();
  const onProjectOpen = vi.fn();

  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={onProjectOpen} />);

  await user.click(screen.getByRole("button", { name: /open project workspace/i }));

  expect(onProjectOpen).toHaveBeenCalledWith("project-1");
});

test("refine save requires launch-critical fields before calling the API", async () => {
  const user = userEvent.setup();

  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  await user.click(screen.getByRole("button", { name: /add project details/i }));
  await user.click(screen.getByRole("button", { name: /update results/i }));

  expect(await screen.findByText(/complete proposal type/i)).toBeTruthy();
  expect(apiMock.upsertProposal).not.toHaveBeenCalled();
});

test("check view still works without property context", async () => {
  const user = userEvent.setup();
  render(<WizardShell wizard={{ ...wizard, property: null }} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  expect(screen.getByText(/couldn't load property details/i)).toBeTruthy();
  expect(screen.getByTestId("compliance-panel")).toBeTruthy();

  await user.click(screen.getByRole("button", { name: /upload plans/i }));
  expect(screen.getByTestId("document-upload")).toBeTruthy();
});

test("refine save not-built response surfaces an error and keeps the panel open", async () => {
  const user = userEvent.setup();
  apiMock.upsertProposal.mockResolvedValue({
    kind: "notBuilt",
    detail: "not implemented",
  });

  render(<WizardShell wizard={wizard} onClose={vi.fn()} onProjectOpen={vi.fn()} />);

  await user.click(screen.getByRole("button", { name: /add project details/i }));
  await user.selectOptions(screen.getByLabelText("Proposal type"), "residential");
  await user.selectOptions(screen.getByLabelText("Dwelling type"), "single_house");
  await user.selectOptions(screen.getByLabelText("Building class"), "class_1a");
  await user.selectOptions(screen.getByLabelText("Work type"), "new_construction");
  await user.click(screen.getByLabelText("New"));
  await user.selectOptions(screen.getByLabelText("Lot type"), "green_title");
  await user.click(screen.getByRole("button", { name: /update results/i }));

  expect(await screen.findByText(/proposal saving is unavailable/i)).toBeTruthy();
  expect(screen.getByTestId("compliance-panel").getAttribute("data-run-request")).toBe("0");
});
