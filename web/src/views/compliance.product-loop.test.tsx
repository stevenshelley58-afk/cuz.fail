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
          source: {
            title: "Residential Design Codes Volume 1",
            url: "https://example.test/r-codes-volume-1.pdf",
            section: "Clause 5.1.4",
          },
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
  render(<CompliancePanel projectId="project-golden" proposalReady />);

  await waitFor(() => expect(apiMock.compliance.matrix).toHaveBeenCalledWith("project-golden"));
  await userEvent.click(screen.getByRole("button", { name: /run compliance check/i }));

  await screen.findByText(/results are advisory only/i);
  expect(screen.getByText(/1 likely pass/i)).toBeTruthy();
  expect(trackEventMock).toHaveBeenCalledWith("compliance_run", {
    result_count: 1,
    status: "likely_compliant",
  });

  await userEvent.click(screen.getByRole("button", { name: /site cover/i }));
  const resultRegion = screen.getByRole("button", { name: /site cover/i }).parentElement;
  expect(resultRegion).toBeTruthy();
  const result = within(resultRegion as HTMLElement);

  expect(result.getByText("48.44")).toBeTruthy();
  expect(result.getByText("50")).toBeTruthy();
  expect(result.queryByText(/source_version:fixture-source-version/i)).toBeNull();
  expect(
    result.getByRole("link", { name: /open source document: residential design codes volume 1/i }).getAttribute("href"),
  ).toBe("https://example.test/r-codes-volume-1.pdf");
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

  render(<CompliancePanel projectId="project-golden" proposalReady />);

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
  expect(await screen.findByText(/no source-backed planning rules are available/i)).toBeTruthy();
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

  render(<CompliancePanel projectId="project-golden" proposalReady />);

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

test("compliance panel renders an address-only matrix as a positive rules browser", async () => {
  const onUploadDrawing = vi.fn();
  apiMock.compliance.matrix.mockResolvedValue({
    kind: "ok",
    status: 200,
    data: {
      run_id: "run-address-only",
      project_id: "project-golden",
      status: "incomplete",
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
          rule_id: "rule-front-setback",
          rule_quote: "Buildings set back from the primary street as set out in Table 1.",
          citation: "R-Codes Vol. 1 | clause 5.1.2",
          category: "setback",
          check_type: "numeric_threshold",
          what_it_means: "The design needs a primary street setback measurement before this rule can be assessed.",
          modality: "mandatory",
          source: {
            title: "Residential Design Codes Volume 1",
            url: "https://example.test/r-codes-volume-1.pdf",
            section: "Clause 5.1.2",
          },
          note: null,
          missing_info_reason: "missing_drawing_measurement",
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
        {
          result_id: "result-site-cover",
          check_key: "site_cover",
          display_name: "Site cover",
          status: "likely_pass",
          threshold_value: 50,
          threshold_unit: "%",
          measured_value: 48,
          rule_id: "rule-site-cover",
          rule_quote: "Site coverage is not to exceed the table value.",
          citation: "R-Codes Vol. 1 | clause 5.1.4",
          category: "site_cover",
          check_type: "numeric_threshold",
          what_it_means: "Site cover rules apply to the lot once the proposed building footprint is known.",
          modality: "mandatory",
          source: {
            title: "Residential Design Codes Volume 1",
            url: "https://example.test/r-codes-volume-1.pdf",
            section: "Clause 5.1.4",
          },
          note: null,
          missing_info_reason: null,
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
        {
          result_id: "result-land-use",
          check_key: "land_use_permissibility",
          display_name: "Land use permissibility",
          status: "needs_more_info",
          threshold_value: null,
          threshold_unit: null,
          measured_value: null,
          rule_id: "rule-land-use",
          rule_quote: "A single house is a permitted use in the applicable residential zone.",
          citation: "City of Cockburn Town Planning Scheme | zoning table",
          category: "other",
          check_type: "categorical",
          what_it_means: "The proposed land use must be permitted in this property's zone.",
          modality: "mandatory",
          source: {
            title: "City of Cockburn Town Planning Scheme",
            url: "https://example.test/cockburn-town-planning-scheme.pdf",
            section: "Zoning table",
          },
          note: null,
          missing_info_reason: "proposal_type_required",
          drawing_evidence: {},
          review_reason: null,
          human_override: {},
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
      ],
    },
  });

  render(
    <CompliancePanel
      projectId="project-golden"
      onUploadDrawing={onUploadDrawing}
      councilName="City of Cockburn"
      propertyImage={{
        url: "https://imagery.example.test/property.jpg",
        alt: "Aerial view of the test property",
        provider: "Nearmap",
        captured_at: "2026-07-12",
        attribution: "© Nearmap",
      }}
    />,
  );

  expect(await screen.findByText(/we found 3 planning rules that apply to this property/i)).toBeTruthy();
  expect(screen.getByText(/planning context: city of cockburn/i)).toBeTruthy();
  expect(screen.getByRole("img", { name: /aerial view of the test property/i }).getAttribute("src")).toBe(
    "https://imagery.example.test/property.jpg",
  );
  expect(screen.getByText(/nearmap · captured 2026-07-12/i)).toBeTruthy();

  // Rule list starts collapsed behind a clear expand control
  expect(screen.queryByText("Setbacks & boundaries")).toBeTruthy();
  expect(screen.getByRole("button", { name: /zoning & land use: 1 rule/i })).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: /zoning & land use: 1 rule/i }));
  expect(await screen.findByRole("button", { name: /land use permissibility/i })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /primary street setback/i })).toBeNull();
  expect(screen.getByRole("button", { name: /zoning & land use: 1 rule/i }).getAttribute("aria-pressed")).toBe("true");

  await userEvent.click(screen.getByRole("button", { name: /zoning & land use: 1 rule/i }));
  await userEvent.click(screen.getByRole("button", { name: /explore all 3 rules/i }));
  expect(screen.getAllByText("Setbacks & boundaries").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Site design & landscaping").length).toBeGreaterThan(0);
  expect(screen.queryByText(/likely pass/i)).toBeNull();
  expect(screen.queryByText(/more info needed/i)).toBeNull();
  expect(screen.queryByText(/need a measurement/i)).toBeNull();
  expect(screen.queryByRole("button", { name: /run compliance check/i })).toBeNull();

  await userEvent.click(screen.getByRole("button", { name: /primary street setback/i }));
  expect(screen.getByText(/the design needs a primary street setback measurement/i)).toBeTruthy();
  expect(screen.getByText(/buildings set back from the primary street/i)).toBeTruthy();
  expect(screen.queryByText(/r-codes vol\. 1 \| clause 5\.1\.2/i)).toBeNull();
  expect(
    screen.getByRole("link", { name: /open source document: residential design codes volume 1/i }).getAttribute("href"),
  ).toBe("https://example.test/r-codes-volume-1.pdf");
  expect(screen.getByText(/mandatory standard/i)).toBeTruthy();
  expect(screen.getByText(/add your proposal details or house plans/i)).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /next: upload house plans/i }));
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

  render(<CompliancePanel projectId="project-golden" onUploadDrawing={onUploadDrawing} proposalReady />);

  await userEvent.click(await screen.findByRole("button", { name: /run compliance check/i }));

  // Actionable results are present, so the needs-info row stays visible (it is
  // not collapsed into the aggregate prompt) and exposes its missing data.
  const summary = await screen.findByText(/1 likely pass/i);
  expect(summary.textContent).toMatch(/1 need a measurement/i);
  expect(screen.queryByText("Add measurements to see your results")).toBeNull();

  await userEvent.click(screen.getByRole("button", { name: /primary street setback/i }));
  expect(screen.getByText(/we need front setback and primary street to assess this rule/i)).toBeTruthy();
  expect(screen.getByText("Front Setback")).toBeTruthy();
  expect(screen.getByText("Primary Street")).toBeTruthy();

  await userEvent.click(screen.getByRole("button", { name: /upload drawing to provide this data/i }));
  expect(onUploadDrawing).toHaveBeenCalledTimes(1);
  expect(await screen.findByText(/use the documents upload area/i)).toBeTruthy();
});
