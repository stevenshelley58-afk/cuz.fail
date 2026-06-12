import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { CompliancePanel } from "./compliance";

const { apiMock, trackEventMock } = vi.hoisted(() => ({
  apiMock: {
    compliance: {
      matrix: vi.fn(),
      run: vi.fn(),
      recordReview: vi.fn(),
    },
  },
  trackEventMock: vi.fn(),
}));

vi.mock("../api", () => ({ api: apiMock }));
vi.mock("../analytics", () => ({ trackEvent: trackEventMock }));

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.compliance.matrix.mockResolvedValue({ kind: "missing" });
  apiMock.compliance.run.mockResolvedValue({
    kind: "ok",
    status: 201,
    data: {
      run_id: "run-golden",
      project_id: "project-golden",
      status: "likely_compliant",
      as_of_date: "2026-06-12T19:44:00Z",
      advisory_disclaimer: "Results are advisory only and are not final compliance determinations.",
      results: [
        {
          result_id: "result-site-cover",
          check_key: "site_cover",
          display_name: "Site cover",
          status: "likely_pass",
          threshold_value: 50,
          threshold_unit: "%",
          measured_value: 48.44,
          rule_id: "rule-site-cover",
          rule_quote: "Fixture site-cover rule atom.",
          citation: "site_cover | source_version:fixture-source-version",
          note: null,
          missing_info_reason: null,
          drawing_evidence: {
            fact_type: "proposed_site_cover_pct",
            method: "document_extraction_promoted",
            document_fact_id: "fact-site-cover",
          },
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
      ],
    },
  });
});

afterEach(() => {
  cleanup();
});

test("compliance panel renders cited advisory drawing-backed results after a run", async () => {
  render(<CompliancePanel projectId="project-golden" />);

  await waitFor(() => expect(apiMock.compliance.matrix).toHaveBeenCalledWith("project-golden"));
  await userEvent.click(screen.getByRole("button", { name: /run compliance check/i }));

  await screen.findByText(/results are advisory only/i);
  expect(screen.getByText(/1 likely pass/i)).toBeTruthy();
  expect(trackEventMock).toHaveBeenCalledWith("compliance_run", {
    result_count: 1,
    status: "likely_compliant",
  });

  await userEvent.click(screen.getByRole("button", { name: /site cover/i }));
  const resultRegion = screen.getByText("Fixture site-cover rule atom.").closest("div");
  expect(resultRegion).toBeTruthy();
  const result = within(resultRegion as HTMLElement);

  expect(result.getByText("48.44")).toBeTruthy();
  expect(result.getByText("50")).toBeTruthy();
  expect(result.getByText(/site_cover \| source_version:fixture-source-version/i)).toBeTruthy();
  expect(result.getByText("Drawing evidence")).toBeTruthy();
  expect(result.getByText(/proposed_site_cover_pct/i)).toBeTruthy();
  expect(result.getByText(/document_extraction_promoted/i)).toBeTruthy();
  expect(result.getByText(/fact fact-site-cover/i)).toBeTruthy();
});

test("compliance panel records operator review notes on a result", async () => {
  apiMock.compliance.recordReview.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      result_id: "result-site-cover",
      check_key: "site_cover",
      display_name: "Site cover",
      status: "likely_pass",
      threshold_value: 50,
      threshold_unit: "%",
      measured_value: 48.44,
      rule_id: "rule-site-cover",
      rule_quote: "Fixture site-cover rule atom.",
      citation: "site_cover | source_version:fixture-source-version",
      note: null,
      missing_info_reason: null,
      drawing_evidence: {
        fact_type: "proposed_site_cover_pct",
        method: "document_extraction_promoted",
        document_fact_id: "fact-site-cover",
      },
      review_reason: "Reviewed against uploaded DXF evidence.",
      human_override: { action: "operator_note" },
      reviewed_by_user_id: "operator-1",
      reviewed_at: "2026-06-12T20:05:00Z",
    },
  });

  render(<CompliancePanel projectId="project-golden" />);

  await userEvent.click(await screen.findByRole("button", { name: /run compliance check/i }));
  await userEvent.click(screen.getByRole("button", { name: /site cover/i }));
  await userEvent.type(
    screen.getByLabelText(/review note for site cover/i),
    "Reviewed against uploaded DXF evidence.",
  );
  await userEvent.click(screen.getByRole("button", { name: /^record$/i }));

  await waitFor(() => {
    expect(apiMock.compliance.recordReview).toHaveBeenCalledWith(
      "result-site-cover",
      "operator_note",
      "Reviewed against uploaded DXF evidence.",
    );
  });
  const reviewLabel = await screen.findByText("Review:");
  expect(reviewLabel.parentElement?.textContent).toContain("Reviewed against uploaded DXF evidence.");
  expect(screen.getByText(/operator note/i)).toBeTruthy();
});
