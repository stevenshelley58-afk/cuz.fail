import { expect, test } from "vitest";
import type { PropertyProfileResponse } from "../api";
import { propertyDetailRows } from "./property";

const provenance = {
  kind: "spatial_dataset" as const,
  method: "planning_layer_intersection",
  target_crs: "EPSG:7844",
  dataset_id: "wa-planning",
  licence_status: "approved",
};

test("property detail rows dedupe zones and render clean R-Code labels", () => {
  const property: PropertyProfileResponse = {
    org_id: "org-test",
    project_id: "project-test",
    resolution_status: "resolved",
    confidence: "high",
    address: "3 Black Swan Rise, Beeliar",
    local_government: "City of Cockburn",
    target_crs: "EPSG:7844",
    issues: [],
    provenance: [provenance],
    facts: [
      { fact_id: "zone-1", fact_type: "zone", value: "Residential", confidence: "high", review_status: "accepted", provenance },
      { fact_id: "zone-2", fact_type: "zone", value: "Residential", confidence: "high", review_status: "accepted", provenance },
      { fact_id: "zone-3", fact_type: "zone", value: "Local road", confidence: "high", review_status: "accepted", provenance },
      { fact_id: "zone-4", fact_type: "zone", value: "Local road", confidence: "high", review_status: "accepted", provenance },
      {
        fact_id: "rcode-1",
        fact_type: "r_code",
        value: { name: "Residential Design Code RR20", code: "R20" },
        confidence: "high",
        review_status: "accepted",
        provenance,
      },
    ],
  };

  const rows = propertyDetailRows(property);

  expect(rows.filter((row) => row.label === "Zone")).toHaveLength(0);
  expect(rows).toContainEqual({ label: "Zones", value: "Residential, Local road", hint: undefined });
  expect(rows).toContainEqual({ label: "R-Code", value: "R20", hint: undefined });
});

test("property detail rows preserve R-AC and split R-Code formats", () => {
  const baseProperty: PropertyProfileResponse = {
    org_id: "org-test",
    project_id: "project-test",
    resolution_status: "resolved",
    confidence: "high",
    address: "3 Black Swan Rise, Beeliar",
    local_government: "City of Cockburn",
    target_crs: "EPSG:7844",
    issues: [],
    provenance: [provenance],
    facts: [],
  };

  const racRows = propertyDetailRows({
    ...baseProperty,
    facts: [
      { fact_id: "rcode-rac", fact_type: "r_code", value: { code: "R-AC3" }, confidence: "high", review_status: "accepted", provenance },
    ],
  });
  const splitRows = propertyDetailRows({
    ...baseProperty,
    facts: [
      { fact_id: "rcode-split", fact_type: "r_code", value: { code: "R12.5/20" }, confidence: "high", review_status: "accepted", provenance },
    ],
  });

  expect(racRows).toContainEqual({ label: "R-Code", value: "R-AC3", hint: undefined });
  expect(splitRows).toContainEqual({ label: "R-Code", value: "R12.5/20", hint: undefined });
});
