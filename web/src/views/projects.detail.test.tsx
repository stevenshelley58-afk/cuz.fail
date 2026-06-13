import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ProjectDetail } from "./projects";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    projects: vi.fn(),
    documents: {
      upload: vi.fn(),
      facts: vi.fn(),
      listForProject: vi.fn(),
      searchEvidence: vi.fn(),
      confirmFact: vi.fn(),
      calibrateFact: vi.fn(),
      promoteFact: vi.fn(),
    },
  },
}));

vi.mock("../api", () => ({ api: apiMock }));
vi.mock("./compliance", () => ({
  CompliancePanel: ({ projectId }: { projectId: string }) => (
    <div data-testid="compliance-panel">Compliance for {projectId}</div>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.documents.listForProject.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      items: [
        {
          id: "doc-site-plan",
          title: "site-plan.pdf",
          document_type: "drawing",
          status: "parsed",
          parse_status: "parsed",
          created_at: "2026-06-13T08:15:00Z",
          fact_count: 2,
        },
      ],
      count: 1,
    },
  });
  apiMock.documents.upload.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      document_id: "doc-new-plan",
      filename: "new-site-plan.pdf",
      project_id: "project-golden",
      parse_status: "parsed",
      parse_job: { enqueued: false },
      fact_count: 0,
      extracted_facts: [],
    },
  });
  apiMock.documents.facts.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: { parse_status: "parsed", count: 0, items: [] },
  });
});

afterEach(() => {
  cleanup();
});

test("project detail gives reopened projects the full document upload workflow", async () => {
  const { container } = render(<ProjectDetail projectId="project-golden" onClose={vi.fn()} />);

  expect(screen.getByTestId("compliance-panel").textContent).toContain("project-golden");
  expect(await screen.findByText("site-plan.pdf")).toBeTruthy();
  expect(screen.getByText("Upload a drawing or document")).toBeTruthy();
  expect(screen.getByLabelText("Search uploaded evidence")).toBeTruthy();
  expect(apiMock.documents.listForProject).toHaveBeenCalledWith("project-golden");

  const input = container.querySelector('input[type="file"]');
  expect(input).toBeTruthy();
  fireEvent.change(input as HTMLInputElement, {
    target: {
      files: [new File(["%PDF-1.7"], "new-site-plan.pdf", { type: "application/pdf" })],
    },
  });

  await waitFor(() =>
    expect(apiMock.documents.upload).toHaveBeenCalledWith(
      "project-golden",
      expect.objectContaining({ name: "new-site-plan.pdf" }),
    ),
  );
});
