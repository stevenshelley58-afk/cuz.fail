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

type FactsResponse = {
  kind: "ok";
  status: 200;
  data: {
    parse_status: "parsed";
    count: number;
    items: Array<{
      fact_id: string;
      fact_key: string;
      fact_kind: string;
      numeric_value: number;
      unit: string;
      confidence: number;
      source_text: string;
      review_status: string;
      promoted_to_measurement: boolean;
      metadata: Record<string, string>;
    }>;
  };
};

let resolveFacts: ((response: FactsResponse) => void) | null = null;

function parsedFactsResponse(): FactsResponse {
  return {
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
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  resolveFacts = null;
  vi.spyOn(window, "setInterval");
  apiMock.documents.listForProject
    .mockResolvedValueOnce({ kind: "ok", status: 200, data: { items: [], count: 0 } })
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
  apiMock.documents.facts.mockImplementation(() => {
    return new Promise((resolve) => {
      resolveFacts = resolve;
    });
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
  await waitFor(() => expect(apiMock.documents.listForProject).toHaveBeenCalledTimes(2));
  expect(window.setInterval).toHaveBeenCalledWith(expect.any(Function), 3000);
  expect(apiMock.documents.upload).toHaveBeenCalledWith(
    "project-golden",
    expect.objectContaining({ name: "m1_canary_site_plan_rev_a.dxf" }),
  );

  await waitFor(() => expect(apiMock.documents.facts).toHaveBeenCalledWith("doc-async"));
  await act(async () => {
    resolveFacts?.(parsedFactsResponse());
  });
  expect(await screen.findByText(/front setback/i)).toBeTruthy();
  expect(screen.getByText("6")).toBeTruthy();
  expect(screen.getByText("m")).toBeTruthy();
  expect(screen.getByText(/DIMENSION FRONT_SETBACK=6m/i)).toBeTruthy();
});

test("document upload loads facts when the upload response starts as parsing", async () => {
  apiMock.documents.upload.mockResolvedValueOnce({
    kind: "ok",
    status: 202,
    data: {
      document_id: "doc-async",
      filename: "m1_canary_site_plan_rev_a.dxf",
      project_id: "project-golden",
      parse_status: "parsing",
      parse_job: { enqueued: true },
      fact_count: 0,
      extracted_facts: [],
    },
  });

  const { container } = render(<DocumentUpload projectId="project-golden" />);
  await waitFor(() => expect(apiMock.documents.listForProject).toHaveBeenCalledWith("project-golden"));

  const input = container.querySelector('input[type="file"]');
  fireEvent.change(input as HTMLInputElement, {
    target: {
      files: [new File(["0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF"], "m1_canary_site_plan_rev_a.dxf")],
    },
  });

  await screen.findByText(/parser job is queued or running/i);
  expect(screen.getAllByText("Parsing").length).toBeGreaterThan(0);
  await waitFor(() => expect(apiMock.documents.facts).toHaveBeenCalledWith("doc-async"));
  await act(async () => {
    resolveFacts?.(parsedFactsResponse());
  });
  expect(await screen.findByText(/front setback/i)).toBeTruthy();
});

test("uploaded evidence search renders project hits with the advisory notice", async () => {
  apiMock.documents.listForProject.mockReset();
  apiMock.documents.listForProject.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      items: [
        {
          id: "doc-evidence",
          title: "site-plan.pdf",
          document_type: "drawing",
          status: "parsed",
          parse_status: "parsed",
          created_at: "2026-06-12T20:15:00Z",
          fact_count: 3,
        },
      ],
      count: 1,
    },
  });
  apiMock.documents.searchEvidence.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      project_id: "project-golden",
      query: "front setback",
      items: [
        {
          document_id: "doc-evidence",
          document_title: "site-plan.pdf",
          page_number: 2,
          chunk_index: 4,
          text: "Front setback dimension is annotated as 6.0m from the primary street boundary.",
          score: 0.87,
          metadata: { parser: "pdf_vector" },
        },
      ],
      count: 1,
      legal_authority: false,
      advisory_notice: "Uploaded documents are project evidence, not legal authority.",
    },
  });

  render(<DocumentUpload projectId="project-golden" />);

  await screen.findByText("site-plan.pdf");
  fireEvent.change(screen.getByLabelText("Search uploaded evidence"), {
    target: { value: "front setback" },
  });
  fireEvent.click(screen.getByLabelText("Run uploaded evidence search"));

  await waitFor(() =>
    expect(apiMock.documents.searchEvidence).toHaveBeenCalledWith("project-golden", "front setback"),
  );
  expect(await screen.findByText(/Front setback dimension is annotated as 6.0m/i)).toBeTruthy();
  expect(screen.getByText("Page 2")).toBeTruthy();
  expect(screen.getByText("Uploaded documents are project evidence, not legal authority.")).toBeTruthy();
});

test("document upload shows parser failure once the async parser reports failure", async () => {
  apiMock.documents.listForProject.mockReset();
  apiMock.documents.listForProject
    .mockResolvedValueOnce({ kind: "ok", status: 200, data: { items: [], count: 0 } })
    .mockResolvedValue({
      kind: "ok",
      status: 200,
      data: {
        items: [
          {
            id: "doc-failed",
            title: "bad-plan.pdf",
            document_type: "drawing",
            status: "parse_failed",
            parse_status: "parse_failed",
            created_at: "2026-06-12T20:15:00Z",
            fact_count: 0,
          },
        ],
        count: 1,
      },
    });
  apiMock.documents.upload.mockResolvedValue({
    kind: "ok",
    status: 202,
    data: {
      document_id: "doc-failed",
      filename: "bad-plan.pdf",
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
      parse_status: "parse_failed",
      count: 0,
      items: [],
    },
  });

  const { container } = render(<DocumentUpload projectId="project-golden" />);
  await waitFor(() => expect(apiMock.documents.listForProject).toHaveBeenCalledWith("project-golden"));

  const input = container.querySelector('input[type="file"]');
  fireEvent.change(input as HTMLInputElement, {
    target: {
      files: [new File(["not a supported drawing"], "bad-plan.pdf")],
    },
  });

  await screen.findByText(/parser job is queued or running/i);
  await waitFor(() => expect(apiMock.documents.facts).toHaveBeenCalledWith("doc-failed"));
  expect(await screen.findByText(/parser could not extract this document/i)).toBeTruthy();
  expect(screen.getByText("Parse failed")).toBeTruthy();
});
