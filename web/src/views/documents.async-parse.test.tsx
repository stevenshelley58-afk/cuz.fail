import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DocumentUpload } from "./documents";

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
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

let pollDocuments: (() => void) | null = null;

beforeEach(() => {
  vi.clearAllMocks();
  pollDocuments = null;
  vi.spyOn(window, "setInterval").mockImplementation(((handler: TimerHandler) => {
    if (typeof handler === "function") pollDocuments = handler as () => void;
    return 1;
  }) as unknown as typeof window.setInterval);
  vi.spyOn(window, "clearInterval").mockImplementation(() => undefined);
  apiMock.documents.listForProject
    .mockResolvedValueOnce({ kind: "ok", status: 200, data: { items: [], count: 0 } })
    .mockResolvedValueOnce({
      kind: "ok",
      status: 200,
      data: {
        items: [
          {
            id: "doc-async",
            title: "m1_canary_site_plan_rev_a.dxf",
            document_type: "drawing",
            status: "parse_pending",
            parse_status: "parse_pending",
            created_at: "2026-06-12T20:15:00Z",
            fact_count: 0,
          },
        ],
        count: 1,
      },
    })
    .mockResolvedValue({
      kind: "ok",
      status: 200,
      data: {
        items: [
          {
            id: "doc-async",
            title: "m1_canary_site_plan_rev_a.dxf",
            document_type: "drawing",
            status: "parsed",
            parse_status: "parsed",
            created_at: "2026-06-12T20:15:00Z",
            fact_count: 1,
          },
        ],
        count: 1,
      },
    });
  apiMock.documents.upload.mockResolvedValue({
    kind: "ok",
    status: 202,
    data: {
      document_id: "doc-async",
      filename: "m1_canary_site_plan_rev_a.dxf",
      project_id: "project-golden",
      parse_status: "parse_pending",
      parse_job: { enqueued: true },
      fact_count: 0,
      extracted_facts: [],
    },
  });
  apiMock.documents.facts.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      parse_status: "parsed",
      count: 1,
      items: [
        {
          fact_id: "fact-front-setback",
          fact_key: "front_setback",
          fact_kind: "drawing_dimension",
          numeric_value: 6,
          unit: "m",
          confidence: 0.92,
          source_text: "DIMENSION FRONT_SETBACK=6m",
          review_status: "needs_review",
          promoted_to_measurement: false,
          metadata: { calibration_ref: "DXF INSUNITS metres" },
        },
      ],
    },
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("document upload polls async parser status and loads facts when parsing completes", async () => {
  const { container } = render(<DocumentUpload projectId="project-golden" />);

  await waitFor(() => expect(apiMock.documents.listForProject).toHaveBeenCalledWith("project-golden"));

  const input = container.querySelector('input[type="file"]');
  expect(input).toBeTruthy();
  fireEvent.change(input as HTMLInputElement, {
    target: {
      files: [new File(["0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF"], "m1_canary_site_plan_rev_a.dxf")],
    },
  });

  await screen.findByText(/parser job is queued or running/i);
  expect(screen.getAllByText("Queued").length).toBeGreaterThan(0);
  expect(apiMock.documents.upload).toHaveBeenCalledWith(
    "project-golden",
    expect.objectContaining({ name: "m1_canary_site_plan_rev_a.dxf" }),
  );

  expect(pollDocuments).toBeTruthy();
  await act(async () => {
    pollDocuments?.();
    await Promise.resolve();
  });

  await waitFor(() => expect(apiMock.documents.facts).toHaveBeenCalledWith("doc-async"));
  expect(await screen.findByText(/front setback/i)).toBeTruthy();
  expect(screen.getByText("6")).toBeTruthy();
  expect(screen.getByText("m")).toBeTruthy();
  expect(screen.getByText(/DIMENSION FRONT_SETBACK=6m/i)).toBeTruthy();
});
