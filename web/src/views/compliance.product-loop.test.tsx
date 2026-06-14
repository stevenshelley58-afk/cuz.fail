import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
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

test("compliance panel keeps a fresh run when an older matrix load resolves later", async () => {
  let resolveMatrix: ((value: unknown) => void) | undefined;
  apiMock.compliance.matrix.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveMatrix = resolve;
      }),
  );
  apiMock.compliance.run.mockResolvedValueOnce({
    kind: "ok",
    status: 201,
    data: {
      run_id: "run-fresh",
      project_id: "project-golden",
      status: "likely_compliant",
      as_of_date: "2026-06-13T11:10:00Z",
      advisory_disclaimer: "Results are advisory only and are not final compliance determinations.",
      results: [
        {
          result_id: "result-fresh-site-cover",
          check_key: "site_cover",
          display_name: "Fresh site cover",
          status: "likely_pass",
          threshold_value: 50,
          threshold_unit: "%",
          measured_value: 48.44,
          rule_id: "rule-site-cover",
          rule_quote: "Fresh fixture site-cover rule atom.",
          citation: "site_cover | source_version:fresh-source-version",
          note: null,
          missing_info_reason: null,
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
      ],
    },
  });

  render(<CompliancePanel projectId="project-golden" />);

  await userEvent.click(screen.getByRole("button", { name: /run compliance check/i }));
  expect(await screen.findByText(/fresh site cover/i)).toBeTruthy();

  await act(async () => {
    resolveMatrix?.({
      kind: "ok",
      status: 200,
      data: {
        run_id: "run-stale",
        project_id: "project-golden",
        status: "likely_compliant",
        as_of_date: "2026-06-12T11:10:00Z",
        advisory_disclaimer: "Older saved result.",
        results: [
          {
            result_id: "result-stale-site-cover",
            check_key: "site_cover",
            display_name: "Stale site cover",
            status: "likely_pass",
            threshold_value: 50,
            threshold_unit: "%",
            measured_value: 49,
            rule_id: "rule-site-cover",
            rule_quote: "Stale fixture site-cover rule atom.",
            citation: "site_cover | source_version:stale-source-version",
            note: null,
            missing_info_reason: null,
            drawing_evidence: {},
            review_reason: null,
            human_override: {},
            reviewed_by_user_id: null,
            reviewed_at: null,
          },
        ],
      },
    });
  });

  await waitFor(() => {
    expect(screen.getByText(/fresh site cover/i)).toBeTruthy();
    expect(screen.queryByText(/stale site cover/i)).toBeNull();
    expect(screen.queryByText(/older saved result/i)).toBeNull();
  });
});

test("compliance panel surfaces saved matrix load failures with retry", async () => {
  apiMock.compliance.matrix
    .mockResolvedValueOnce({ kind: "down", message: "network error" })
    .mockResolvedValueOnce({
      kind: "ok",
      status: 200,
      data: {
        run_id: "run-empty",
        project_id: "project-golden",
        status: "complete",
        as_of_date: "2026-06-13T10:35:00Z",
        advisory_disclaimer: "Results are advisory only and are not final compliance determinations.",
        results: [],
      },
    });

  render(<CompliancePanel projectId="project-golden" />);

  expect(await screen.findByText(/could not reach server to load saved compliance results/i)).toBeTruthy();
  expect(screen.queryByText(/no compliance results yet/i)).toBeNull();

  await userEvent.click(screen.getByRole("button", { name: /^retry$/i }));

  await waitFor(() => expect(apiMock.compliance.matrix).toHaveBeenCalledTimes(2));
  expect(await screen.findByText(/no compliance results yet/i)).toBeTruthy();
  expect(screen.queryByText(/could not reach server to load saved compliance results/i)).toBeNull();
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

test("compliance panel collapses an all-needs-info run into a single upload prompt", async () => {
  const onUploadDrawing = vi.fn();
  apiMock.compliance.run.mockResolvedValue({
    kind: "ok",
    status: 201,
    data: {
      run_id: "run-missing",
      project_id: "project-golden",
      status: "needs_more_info",
      as_of_date: "2026-06-12T20:35:00Z",
      advisory_disclaimer: "Results are advisory only and are not final compliance determinations.",
      results: [
        {
          result_id: "result-front-setback",
          check_key: "front_setback",
          display_name: "Primary street setback",
          status: "needs_more_info",
          threshold_value: null,
          threshold_unit: "m",
          measured_value: null,
          rule_id: null,
          rule_quote: null,
          citation: null,
          note: null,
          missing_info_reason: "missing_drawing_measurement",
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
          missing_data: ["front_setback", "primary_street"],
        },
      ],
    },
  });

  render(<CompliancePanel projectId="project-golden" onUploadDrawing={onUploadDrawing} />);

  await userEvent.click(await screen.findByRole("button", { name: /run compliance check/i }));

  // When every check needs a measurement the summary leads with the actionable
  // next step rather than an alarmist "needs info" count.
  expect(await screen.findByText(/ready to check 1 rules/i)).toBeTruthy();
  expect(trackEventMock).toHaveBeenCalledWith("compliance_run", {
    result_count: 1,
    status: "needs_more_info",
  });

  // The per-check yellow cards collapse into a single blue upload prompt; the
  // individual result row is hidden in favour of it.
  expect(screen.getByText("Add measurements to see your results")).toBeTruthy();
  expect(screen.getByText(/we have 1 approved rule/i)).toBeTruthy();
  expect(screen.queryByRole("button", { name: /primary street setback/i })).toBeNull();

  await userEvent.click(screen.getByRole("button", { name: "Upload drawing" }));
  expect(onUploadDrawing).toHaveBeenCalledTimes(1);
  expect(await screen.findByText(/use the documents upload area/i)).toBeTruthy();
});

test("compliance panel surfaces per-check missing data when other checks are actionable", async () => {
  const onUploadDrawing = vi.fn();
  apiMock.compliance.run.mockResolvedValue({
    kind: "ok",
    status: 201,
    data: {
      run_id: "run-mixed",
      project_id: "project-golden",
      status: "needs_more_info",
      as_of_date: "2026-06-12T20:35:00Z",
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
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
        {
          result_id: "result-front-setback",
          check_key: "front_setback",
          display_name: "Primary street setback",
          status: "needs_more_info",
          threshold_value: null,
          threshold_unit: "m",
          measured_value: null,
          rule_id: null,
          rule_quote: null,
          citation: null,
          note: null,
          missing_info_reason: "missing_drawing_measurement",
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
          missing_data: ["front_setback", "primary_street"],
        },
      ],
    },
  });

  render(<CompliancePanel projectId="project-golden" onUploadDrawing={onUploadDrawing} />);

  await userEvent.click(await screen.findByRole("button", { name: /run compliance check/i }));

  // Actionable results are present, so the needs-info row stays visible (it is
  // not collapsed into the aggregate prompt) and exposes its missing data.
  const summary = await screen.findByText(/1 likely pass/i);
  expect(summary.textContent).toMatch(/1 need a measurement/i);
  expect(screen.queryByText("Add measurements to see your results")).toBeNull();

  await userEvent.click(screen.getByRole("button", { name: /primary street setback/i }));
  expect(screen.getByText("Missing information")).toBeTruthy();
  expect(screen.getByText(/reason: missing drawing measurement/i)).toBeTruthy();
  expect(screen.getByText("front_setback")).toBeTruthy();
  expect(screen.getByText("primary_street")).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /upload drawing to provide this data/i }));
  expect(onUploadDrawing).toHaveBeenCalledTimes(1);
  expect(await screen.findByText(/use the documents upload area/i)).toBeTruthy();
});
