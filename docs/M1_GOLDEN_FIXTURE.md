# M1 Golden Fixture — City of Vincent

## Address

**Reference address:** 244 Vincent Street, North Perth WA 6006

**Why this address was chosen:**

- Public-domain civic offices of the City of Vincent — widely published, no privacy concerns.
- Located within an inner-Perth residential zone (R60 under Local Planning Scheme No. 2), making it representative of the most common residential planning context LotFile will handle.
- The City of Vincent is a well-documented LGA with a publicly available local planning scheme, so the fixture values are independently verifiable.
- G-NAF coordinates are well-established for this address (PROPERTY_CENTROID reliability 2).
- The address sits clearly within the City of Vincent boundary, providing an unambiguous LGA assignment.

**Coordinates (GDA2020 / EPSG:7844):** -31.9318, 115.8518

## Expected Resolution Outcome

| Field | Value | Confidence | Reason |
|---|---|---|---|
| Zone | R60 (Residential R60) | medium | DPLH WMS is display-only; licence pending |
| LGA | City of Vincent | high | SLIP LGA boundaries (CC BY 4.0, licensed) |
| R-code | R60 | medium | Derived from WMS zone; same licence caveat |
| Address | 244 Vincent Street, North Perth WA 6006 | high | G-NAF exact match (CC BY 4.0, licensed) |

**Overall resolution status:** `resolved`  
**Overall confidence:** `medium` — because the planning zone source (DPLH WMS) is display-only and has not yet passed the LotFile licence approval gate. Confidence will rise to `high` once an authoritative DPLH licence agreement is in place and the dataset passes the W2 import pipeline.

## Data Sources

| Source | Dataset | Licence | Status in fixture |
|---|---|---|---|
| G-NAF WA | `gnaf_wa_2022-01-01` | CC BY 4.0 (data.gov.au) | Licensed — used for address fact |
| SLIP WA Cadastre | `slip_lga_boundaries` | CC BY 4.0 (Landgate SLIP) | Licensed — used for LGA boundary fact |
| DPLH Display WMS | `dplh_wms_display` | Display-only | **Unlicensed** — zone/r_code facts are `pending_review` |

The DPLH WMS endpoint serves advisory/display-only planning data. Under LotFile's source governance rules, display-only data from DPLH cannot be marked authoritative without a separate licence agreement. The fixture correctly records `licence_status: "unlicensed"` and `review_status: "pending_review"` for all facts derived from this source.

## Invariants Checked

The following invariants must hold for any compliant M1 golden fixture:

1. **`dwelling_type` absent from `facts[]`** — `dwelling_type` is a Proposal-level field (stored in the `proposals` table, column `dwelling_type`). It must never appear in `property_facts` nor in the `facts[]` array of a `PropertyProfile`. The fixture `vincent_property_facts.json` contains no `dwelling_type` key anywhere in its `facts` array, enforcing this separation.

2. **Every fact has `provenance`** — each entry in `facts[]` carries a `provenance` object with at minimum `kind`, `method`, `target_crs`, and `dataset_id`.

3. **Geocode marked advisory** — the address point is sourced from G-NAF (CC BY 4.0), which is licensed and authoritative for address lookup. The fixture records `geocode_type: "PROPERTY_CENTROID"` and `reliability: 2`, consistent with G-NAF's own metadata fields. Any downstream use in compliance calculations must note that GPS-precision claims require survey-grade data.

4. **No banned compliance claims** — no string value in any fixture file contains phrases such as "is compliant", "complies", "non-compliant", "certified", "building approval", "planning approval", "meets all requirements", or "final legal". These phrases are forbidden in all LotFile fixture and output strings.

5. **Display-only WMS data labelled correctly** — zone and r_code facts derived from the DPLH WMS carry `licence_status: "unlicensed"` and `review_status: "pending_review"`, ensuring no automated compliance check treats them as authoritative without human confirmation.

6. **CRS recorded on every provenance** — all `provenance` objects carry `"target_crs": "EPSG:7844"` (GDA2020), the mandatory coordinate reference system for LotFile spatial operations.

## How to Seed

Load the fixtures into a test database with the following Python snippet (requires the test environment to have a live DB session):

```python
from tests.fixtures.golden.vincent_fixtures import (
    load_address_point,
    load_parcel,
    load_lga_boundary,
    load_dplh_response,
    load_property_facts,
    load_seeded_project,
    GOLDEN_ADDRESS,
    GOLDEN_LAT,
    GOLDEN_LON,
    GOLDEN_ZONE,
    GOLDEN_LGA,
)

# Load fixture data
address_point = load_address_point()
parcel = load_parcel()
lga_boundary = load_lga_boundary()
dplh_response = load_dplh_response()
property_facts = load_property_facts()
seeded_project = load_seeded_project()

# Insert into test DB as needed by your integration test harness
```

For a pytest fixture, import `GOLDEN_ADDRESS`, `GOLDEN_LAT`, `GOLDEN_LON`, `GOLDEN_ZONE`, and `GOLDEN_LGA` from `tests.fixtures.golden.vincent_fixtures` as the canonical M1 reference values.

## Known Limitations

1. **Parcel geometry is a simplified stub.** The polygon in `vincent_parcel.geojson` is a ~200m × 190m rectangular approximation of the block around the Vincent Street civic offices. It is not the authoritative cadastral boundary. The real parcel geometry will be imported from the SLIP WFS cadastre feed in the W2 pipeline.

2. **LGA boundary is a coarse bounding box.** The polygon in `vincent_lga_boundary.geojson` is a simplified ~3 km × 3 km bounding box covering the approximate extent of the City of Vincent. It does not reflect the true irregular LGA boundary. The authoritative boundary will be imported from SLIP in W2.

3. **DPLH WMS response is a static stub.** The file `vincent_dplh_wms_response.json` simulates a single-feature WMS GetFeatureInfo response. The real endpoint will be wired in W2. Zone and r_code facts from this source remain `pending_review` until a DPLH licence agreement is in place.

4. **No lot_area_m2 fact.** Because the parcel geometry is a stub and not from an authoritative cadastre import, no `lot_area_m2` fact is included. This fact will be available once the W2 SLIP WFS import is complete.

5. **No frontage or primary_street fact.** These facts require authoritative cadastral geometry and are deferred to W2.

6. **G-NAF coordinates are demo-grade.** The coordinates -31.9318, 115.8518 are a representative centroid for demonstration. Precise coordinates will be sourced from the live G-NAF WA import in W2.
