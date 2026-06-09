# DraftCheck WA — Free One-Council Data Acquisition Runbook (City of Vincent)

Version: 2026-06-09
Scope: City of Vincent demo (LGA code 58570, ABS 2021). Three spatial layers required by the V3 target schema.

---

## 1. Summary Table

| Layer | Source | Dataset ID | Endpoint | Licence | Account needed? | Pull method | Sample path |
|---|---|---|---|---|---|---|---|
| address_points | G-NAF MAY 2026 — Geoscape Australia | 19432f89-dc3a-4ef3-b943-5326ef1dbecc | https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc/resource/f8666213-4079-44da-bede-ebda3a4363e0/download/g-naf_may26_allstates_gda2020_psv_1023.zip | CC BY 4.0 | None for bulk ZIP; free Geoscape Hub account for REST API | Bulk ZIP download (~1.59 GB); load PSV tables into staging; SQL filter to Vincent | data/fixtures/samples/gnaf_vincent_sample.json |
| parcels | Cadastre No Attributes LGATE-001 — Landgate/SLIP | LGATE-001 / c6b9be34-d22a-45d7-bc33-66944a83a0e4 | https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer | SLIP Personal Use Licence — **non-commercial only** | None for WFS query (account for bulk file download) | WFS 1.1.0 GetFeature with lat/lon BBOX — GML3 output only | data/fixtures/samples/cadastre_slip_sample.geojson |
| zone / overlay | DPLH-071 (Zones & Reserves) + DPLH-070 (R-Codes) — DPLH via SLIP | DPLH-071: bd528c56-5fd0-4341-b46a-1c14c352529d; DPLH-070: 3a69bc8a-ef36-4dc4-b7e5-d9922efee004 | Public REST: https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/112 (zones) and /111 (R-codes) | CC Non-Commercial display; bulk/commercial requires DPLH licence | None for REST display queries | ArcGIS REST point query (on-demand only, no bulk DB ingest permitted without licence) | data/fixtures/samples/vincent_zoning_sample.json |

---

## 2. Pull Methods

### 2.1 Layer 1: Address Points (G-NAF)

**Status: FREE — usable now (CC BY 4.0)**

**Endpoint URL:**
```
https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc/resource/f8666213-4079-44da-bede-ebda3a4363e0/download/g-naf_may26_allstates_gda2020_psv_1023.zip
```

**Download command:**
```bash
wget -O /tmp/gnaf_may26.zip \
  "https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc/resource/f8666213-4079-44da-bede-ebda3a4363e0/download/g-naf_may26_allstates_gda2020_psv_1023.zip"

unzip /tmp/gnaf_may26.zip -d /tmp/gnaf_may26/
```

Approximate sizes: ZIP 1.59 GB; extracted 4–5 GB. Files are pipe-delimited PSV with a header row.

**WA files to load (within the extracted tree):**
```
G-NAF_MAY26_AllStates_GDA2020_PSV_1023/G-NAF/G-NAF CORE/Standard/WA/
  WA_ADDRESS_DETAIL_psv.psv
  WA_ADDRESS_DEFAULT_GEOCODE_psv.psv
  WA_LOCALITY_psv.psv
  WA_STREET_LOCALITY_psv.psv

G-NAF_MAY26_AllStates_GDA2020_PSV_1023/G-NAF/G-NAF CORE/Authority Code/
  GEOCODE_TYPE_AUT_psv.psv
  STATE_AUT_psv.psv
```

**Load into staging (PostgreSQL example):**
```sql
-- Create staging tables first (all varchar/numeric as appropriate)
\copy staging.address_detail FROM 'WA_ADDRESS_DETAIL_psv.psv' WITH (FORMAT csv, DELIMITER '|', HEADER true, NULL '');
\copy staging.address_default_geocode FROM 'WA_ADDRESS_DEFAULT_GEOCODE_psv.psv' WITH (FORMAT csv, DELIMITER '|', HEADER true, NULL '');
\copy staging.locality FROM 'WA_LOCALITY_psv.psv' WITH (FORMAT csv, DELIMITER '|', HEADER true, NULL '');
\copy staging.street_locality FROM 'WA_STREET_LOCALITY_psv.psv' WITH (FORMAT csv, DELIMITER '|', HEADER true, NULL '');
```

**Alternative: gnaf-loader automated pipeline**
```bash
# github.com/minus34/gnaf-loader — automates all PSV loading into PostgreSQL
# Also available as a pre-built PostgreSQL dump:
wget https://minus34.com/opendata/geoscape-202605/gnaf-202605.dmp
pg_restore -d <dbname> gnaf-202605.dmp
```

**Filter to City of Vincent (Option A — raw PSV tables, preferred):**
```sql
INSERT INTO address_points (gnaf_pid, address, lon, lat)
SELECT
    ad.ADDRESS_DETAIL_PID AS gnaf_pid,
    ad.NUMBER_FIRST || ' ' || sl.STREET_NAME || ' ' || sl.STREET_TYPE_CODE
        || ', ' || l.LOCALITY_NAME || ' WA ' || ad.POSTCODE AS address,
    adg.LONGITUDE AS lon,
    adg.LATITUDE  AS lat
FROM staging.ADDRESS_DETAIL ad
JOIN staging.ADDRESS_DEFAULT_GEOCODE adg ON adg.ADDRESS_DETAIL_PID = ad.ADDRESS_DETAIL_PID
JOIN staging.LOCALITY l ON l.LOCALITY_PID = ad.LOCALITY_PID
JOIN staging.STATE s    ON s.STATE_PID    = l.STATE_PID
LEFT JOIN staging.STREET_LOCALITY sl ON sl.STREET_LOCALITY_PID = ad.STREET_LOCALITY_PID
WHERE s.STATE_ABBREVIATION = 'WA'
  AND UPPER(l.LOCALITY_NAME) IN (
    'LEEDERVILLE','MOUNT HAWTHORN','NORTH PERTH','NORTHBRIDGE',
    'WEST PERTH','HIGHGATE','MOUNT LAWLEY','COOLBINIA','MENORA','KYILLA'
  )
  AND ad.DATE_RETIRED  IS NULL
  AND adg.DATE_RETIRED IS NULL;
```

**Filter to City of Vincent (Option B — gnaf-loader address_principals view):**
```sql
INSERT INTO address_points (gnaf_pid, address, lon, lat)
SELECT
    gnaf_pid,
    address || ', ' || locality_name || ' ' || state || ' ' || postcode AS address,
    longitude AS lon,
    latitude  AS lat
FROM gnaf_202605.address_principals
WHERE state = 'WA'
  AND locality_name IN (
    'LEEDERVILLE','MOUNT HAWTHORN','NORTH PERTH','NORTHBRIDGE',
    'WEST PERTH','HIGHGATE','MOUNT LAWLEY','COOLBINIA','MENORA','KYILLA'
  );
```

**Filter to City of Vincent (Option C — LGA spatial tag, if bdy_tag table is built):**
```sql
INSERT INTO address_points (gnaf_pid, address, lon, lat)
SELECT p.gnaf_pid, p.address, p.longitude AS lon, p.latitude AS lat
FROM gnaf_202605.address_principals p
JOIN gnaf_202605.address_bdy_tags t ON t.gnaf_pid = p.gnaf_pid
WHERE t.lga_code_2021 = '58570';
```

**Field mapping:**

| G-NAF field | DB column | Notes |
|---|---|---|
| ADDRESS_DETAIL.ADDRESS_DETAIL_PID | gnaf_pid | varchar(15), e.g. GAWA_417331643 |
| Constructed from NUMBER_FIRST + STREET_NAME + STREET_TYPE_CODE + LOCALITY_NAME + POSTCODE | address | Full formatted address string |
| ADDRESS_DEFAULT_GEOCODE.LONGITUDE | lon | numeric(11,8), GDA2020 |
| ADDRESS_DEFAULT_GEOCODE.LATITUDE | lat | numeric(10,8), GDA2020 |
| ADDRESS_DEFAULT_GEOCODE.GEOCODE_TYPE_CODE | (quality filter) | BAP/BC/FDA/PC/DF — prefer BAP or FDA |

**Verify after load:**
```sql
SELECT COUNT(*) FROM address_points WHERE address LIKE '% WA %';
-- Expected: roughly 18,000–22,000 active address points
```

**Release cadence:** quarterly (February, May, August, November). Current: MAY 2026 (202605), released 2026-05-18.

---

### 2.2 Layer 2: Parcels / Cadastre (LGATE-001)

**Status: LICENCE REQUIRED — DO NOT INGEST UNTIL LANDGATE GRANTS WRITTEN APPROVAL**
(See Section 4: Human-loop actions, item 1)

**Endpoint URL (WFS):**
```
https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer
```

**GetCapabilities:**
```
https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetCapabilities
```

**CRITICAL — WFS version and BBOX axis order:**
- Use WFS **1.1.0** with BBOX in **lat/lon** order (e.g. `-31.935,115.845,-31.920,115.860`).
- WFS 2.0.0 with lon/lat BBOX returns 0 features.
- Output format: **GML3 only** (`application/json` returns HTTP 400).

**Example GetFeature request (City of Vincent full extent):**
```
https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAMES=esri:Cadastre__No_Attributes___LGATE-001_&BBOX=-31.958,115.836,-31.875,115.882,EPSG:4326&OUTPUTFORMAT=GML3
```

**Pagination (if server imposes feature limits):**
```
...&COUNT=1000&STARTINDEX=0
...&COUNT=1000&STARTINDEX=1000
```
Tile the full BBOX into sub-tiles if a single request is rejected.

**Filter to City of Vincent:**
No server-side LGA attribute filter is available on this layer (geometry only, no attributes). Retrieve all parcels within the Vincent BBOX, then apply a spatial join against the City of Vincent LGA boundary polygon after load:
```sql
DELETE FROM parcels
WHERE NOT ST_Within(
    ST_Centroid(geom),
    (SELECT geom FROM lga_boundaries WHERE lga_code = '58570')
);
```

**Field mapping:**

| WFS property | DB column | Notes |
|---|---|---|
| SHAPE (GML MultiSurface, EPSG:7844) | geom | `ST_Multi(ST_GeomFromGML(shape_gml))::geometry(MultiPolygon,7844)` |
| OBJECTID | (not stored) | Server row ID, unstable |
| view_scale | (not stored) | Display hint only |
| st_area_shape_ | (discard) | In decimal degrees squared — unreliable; compute from PostGIS: `ST_Area(ST_Transform(geom,7856))` |
| (none) | lot_plan | NULL — this layer has no lot/plan attributes |
| (derived) | local_government | Derive via spatial join against LGA boundary |
| (computed) | area_m2 | `ST_Area(ST_Transform(geom,7856))` |

**GML parse example (Python/OGR):**
```python
from osgeo import ogr
ds = ogr.Open(gml_response_path)
layer = ds.GetLayer(0)
for feature in layer:
    geom = feature.GetGeometryRef()
    geom.TransformTo(srs_7856)
    area_m2 = geom.Area()
    wkt = geom.ExportToWkt()
    # INSERT INTO parcels (geom, area_m2) VALUES (ST_GeomFromText(wkt, 7844), area_m2)
```

**Commercial use note:** The SLIP Personal Use Licence (Clause 1.1) restricts use to personal and non-commercial purposes only. Storing geometry in a PostGIS database to power a commercial application requires a separate Landgate licence. Contact: licensing@landgate.wa.gov.au, (08) 9273 7210.

---

### 2.3 Layer 3: Zoning and R-Codes (DPLH-071 / DPLH-070)

**Status: BULK INGEST BLOCKED — use on-demand REST queries only during demo phase. DB ingest requires DPLH or City of Vincent licence.**
(See Section 4: Human-loop actions, items 2 and 3)

**REST endpoint URLs:**

| Resource | URL |
|---|---|
| Zones (DPLH-071) | https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/112 |
| R-Codes (DPLH-070) | https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/111 |
| WMS (display) | https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning/MapServer/WMSServer |

**On-demand point-in-polygon query (demo path — no DB copy of geometry):**
```
# Zone lookup for a given lon/lat:
https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/112/query?geometry=115.8412,−31.9346&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&f=geojson

# R-Code lookup:
https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/111/query?geometry=115.8412,−31.9346&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&f=geojson
```
Replace `115.8412,−31.9346` with actual lon,lat. Returns GeoJSON.

**Filter to City of Vincent (attribute filter for bulk use, post-licence):**
```
&where=scheme_nam+LIKE+'%25Vincent%25'
```
Or spatially clip to LGA code 117 (City of Vincent internal DPLH scheme identifier).

**Field mapping:**

| DPLH field | DB column | Notes |
|---|---|---|
| zone | code | e.g. 'Residential', 'Commercial' |
| zone_label | label | Human-readable label |
| scheme_nam | (context) | LGA name, confirms City of Vincent |
| lpscheme_i | (context) | Scheme identifier |
| geometry (POLYGON, EPSG:7844) | geom | MULTIPOLYGON GDA2020 |
| rcode_no | code (R-Codes layer) | e.g. 'R40', 'R20' |
| gazettal_d | (effective date) | Confirm LPS2 gazettal 2018-05-16 |

**layer_type mapping:**
- DPLH-071 Zones -> `layer_type = 'zone'`
- DPLH-070 R-Codes -> `layer_type = 'overlay'`

**Applicable scheme:** Local Planning Scheme No. 2 (LPS2), gazetted 2018-05-16. An amended Local Planning Strategy was endorsed for public advertising as of March 2026 — confirm with City of Vincent whether any scheme amendment is currently operative before data ingest.

**Restricted bulk WFS (post-licence only):**
```
https://services.slip.wa.gov.au/arcgis/services/DPLH_Restricted_Services/DPLH_Restricted_Government_Services_FS/MapServer/WFSServer
```
Government-Use-Only. Requires signed DPLH licence agreement.

---

## 3. Human-Loop Actions for Steven

Complete these manually before proceeding with blocked layers.

**Layer 2 — Cadastre (LGATE-001):**

- [ ] **1. Email Landgate to request a commercial licence for LGATE-001.**
  To: licensing@landgate.wa.gov.au
  Phone backup: (08) 9273 7210 (Business and Government Solutions, Landgate, PO Box 2222 Midland WA 6936)
  Subject: `Licence request — DraftCheck WA commercial planning application — SLIP Cadastre LGATE-001`
  Body: "We are building DraftCheck WA, a private planning compliance application for the City of Vincent (demo phase, aiming for commercial launch). We require a licence to: (1) download the LGATE-001 Cadastre (No Attributes) layer via the public WFS endpoint; (2) store the Vincent-area parcel polygons in a private PostGIS database; and (3) run spatial queries (ST_Intersects, point-in-polygon) to identify which parcel an address falls on, with derived compliance results displayed to end users (we do not re-serve or redistribute the raw geometry). Please advise the appropriate licence type (VAR Agreement or SLIP Subscription) and any fees. Dataset: Cadastre No Attributes LGATE-001, accessed via https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer."
  **Do not ingest into PostGIS until written approval is received.**

**Layer 3 — Zoning/R-Codes, Path A (DPLH licence):**

- [ ] **2. Email DPLH to request a licence for DPLH-071 and DPLH-070.**
  To: spatialdata@dplh.wa.gov.au
  Subject: `Data licence request — DraftCheck WA — DPLH-071 Local Planning Scheme Zones and DPLH-070 R-Codes, City of Vincent`
  Body: "We are developing DraftCheck WA, a private planning compliance application. We require a data licence to: (1) download or extract City of Vincent zones (scheme_nam LIKE '%Vincent%', DPLH-071, dataset ID bd528c56-5fd0-4341-b46a-1c14c352529d) and R-codes (DPLH-070, dataset ID 3a69bc8a-ef36-4dc4-b7e5-d9922efee004); (2) store the Vincent zone and R-code polygons in a private PostGIS database; and (3) perform point-in-polygon queries to return the zone and R-code for a given address, with results displayed to end users (no redistribution of raw geometry). We understand these datasets are Government-Use-Only for bulk access. We would also accept written confirmation that use of the public ArcGIS REST query endpoint (layers 111/112 at public-services.slip.wa.gov.au) for live on-demand point queries without DB storage is permitted for a commercial application. Please advise the applicable licence terms and any fees."
  **Do not bulk-ingest until written approval is received.**

**Layer 3 — Zoning/R-Codes, Path B (City of Vincent direct — PREFERRED, pursue in parallel with Path A):**

- [ ] **3. Email City of Vincent Planning team to request LPS2 zoning data directly.**
  To: mail@vincent.wa.gov.au (or phone (08) 9273 6000 — Planning team available 9am–12pm and 1pm–4pm)
  Subject: `GIS data request — LPS2 zoning layer for DraftCheck WA planning compliance tool`
  Body: "We are building DraftCheck WA, a planning compliance application covering the City of Vincent. We would like to request the Local Planning Scheme No. 2 (LPS2) zoning layer (zones and R-codes) as a GeoJSON or Shapefile for use in a private PostGIS database. The data would be used to perform point-in-polygon lookups to identify the planning zone and R-code for a given address, with derived compliance information displayed to users. We would not redistribute the raw spatial data. City of Vincent is the legal custodian of this data and we are happy to enter into any data sharing agreement you require. Also, if you are able to provide a scheduled GeoJSON/Shapefile refresh cadence or a Pozi WFS endpoint, this would allow DraftCheck WA to stay current with scheme amendments automatically. Please advise the applicable terms and any conditions of use."
  City of Vincent is the legal custodian of their own LPS2 data. This path avoids DPLH licence negotiation and is typically faster.
  **Use whichever of Path A or Path B grants permission first.**

**G-NAF setup (optional — REST API complement to bulk ZIP):**

- [ ] **4. Register for a free Geoscape Hub account to obtain a REST API key (optional, not required for bulk ZIP ingest).**
  URL: https://hub.geoscape.com.au
  Select Free tier (20,000 credits/month). Generate an API key. Useful for real-time address validation and geocoding beyond the static DB copy. The same CC BY 4.0 attribution applies.

---

## 4. Go-Wide Path (Paid/Licensed — Separate From Demo)

These items are out of scope for the City of Vincent free demo but must be assessed before production launch.

**4.1 Landgate Full Cadastre With Attributes (LGATE-217)**

The free LGATE-001 layer is geometry-only (no lot/plan number, tenure, or owner fields). If DraftCheck WA needs lot/plan attributes for compliance checks (e.g. lot area, street address from title), the full cadastre is LGATE-217.

- Licence type: SLIP Subscription Licence or Value Added Reseller (VAR) Agreement.
- Contact: licensing@landgate.wa.gov.au, (08) 9273 7210.
- Fees apply. Assess before production launch.

**4.2 DPLH Bulk Vector WFS (Unrestricted — Statewide)**

The restricted WFS at `services.slip.wa.gov.au` (Government-Use-Only) provides bulk access to DPLH-071 and DPLH-070 across all WA councils, enabling a full statewide load and scheduled refresh.

- This is the preferred production architecture once a DPLH licence is in place (see human-loop item 2 above).
- Endpoint: `https://services.slip.wa.gov.au/arcgis/services/DPLH_Restricted_Services/DPLH_Restricted_Government_Services_FS/MapServer/WFSServer`
- Once a licence is granted, switch the ingestion pipeline from the on-demand REST query path to a scheduled bulk sync.

**4.3 Geoscape REST API (Address Validation — Complement to G-NAF)**

The Geoscape REST API at `api.geoscape.com.au` provides real-time address lookup and geocoding beyond the static DB copy. Free tier: 20,000 credits/month after registration at hub.geoscape.com.au. Paid tiers available for higher volume. Same CC BY 4.0 attribution applies.

---

## 5. Licence Classifications

| Layer | Licence | Classification | Storage in PostGIS OK? | AI Processing OK? | Attribution Required |
|---|---|---|---|---|---|
| address_points (G-NAF, Geoscape, MAY 2026) | CC BY 4.0 | free-now | Yes | Yes | Yes — "Incorporates or developed using G-NAF © Geoscape Australia licensed by the Commonwealth of Australia under CC BY 4.0." Must appear in the UI wherever address data is displayed. |
| parcels (Cadastre LGATE-001, Landgate/SLIP) | SLIP Personal Use Licence (non-commercial only) | needs-licence | NO — requires written Landgate approval | NO — not permitted without commercial licence | Required; exact form to be confirmed in licence agreement. Contact: licensing@landgate.wa.gov.au |
| zone (DPLH-071 Zones/Reserves, DPLH) | DPLH Data Licensing Agreement — display only / non-commercial | needs-licence | NO — bulk ingest requires licence | NO — not permitted without licence | Required; exact form: "Planning zones and R-codes data © State of Western Australia (Department of Planning, Lands and Heritage) [year]. Based on information provided by DPLH." |
| overlay (DPLH-070 R-Codes, DPLH) | DPLH Data Licensing Agreement — display only / non-commercial | needs-licence | NO — bulk ingest requires licence | NO — not permitted without licence | As above. Same attribution as DPLH-071. |

---

## 6. Endpoint Verification Log

| Layer | Date Tested | Endpoint Tested | Result | Notes |
|---|---|---|---|---|
| address_points (G-NAF ZIP) | 2026-06-09 | https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc/resource/f8666213-4079-44da-bede-ebda3a4363e0/download/g-naf_may26_allstates_gda2020_psv_1023.zip | VERIFIED | HTTP 200, Content-Length: 1,706,838,674 bytes (1.59 GB), Last-Modified: Mon 18 May 2026, Content-Type: application/zip. Served via CloudFront (PER50-P3, Perth). Resource ID: f8666213-4079-44da-bede-ebda3a4363e0 (GDA2020 variant). |
| address_points (CKAN datastore API) | 2026-06-09 | https://data.gov.au/api/3/action/datastore_search?resource_id=f8666213-... | BLOCKED | data.gov.au migrated to Drupal 11; all /api/3/action/ endpoints return HTML 404. No queryable datastore exists for G-NAF. |
| parcels (Cadastre WFS 1.1.0) | 2026-06-09 | https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer (GetCapabilities + GetFeature BBOX) | VERIFIED | GetCapabilities returned HTTP 200 with 19 FeatureTypes including esri:Cadastre__No_Attributes___LGATE-001_. GetFeature with lat/lon BBOX returned 3 valid parcel polygons for Leederville test area. WFS 2.0.0 BBOX (lon/lat order) returns 0 features — must use WFS 1.1.0. Only GML3 output format supported. |
| parcels (WFS 2.0.0) | 2026-06-09 | Same WFS endpoint, VERSION=2.0.0, lon/lat BBOX | BLOCKED | Returns 0 features. Use WFS 1.1.0 with lat/lon BBOX instead. |
| parcels (ArcGIS REST layer 2) | 2026-06-09 | https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/2 | NOT_TESTED | Confirmed to exist; WFS endpoint is the primary pull method. |
| zone/overlay (DPLH REST MapServer layers 111/112) | 2026-06-09 | https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer (layers 111, 112) | VERIFIED | REST MapServer confirmed live. Layers 111 (R-Codes DPLH-070) and 112 (Zones DPLH-071) respond without authentication. GetCapabilities returns valid XML. |
| zone/overlay (DPLH restricted WFS) | 2026-06-09 | https://services.slip.wa.gov.au/arcgis/services/DPLH_Restricted_Services/DPLH_Restricted_Government_Services_FS/MapServer/WFSServer | BLOCKED | Government-Use-Only. Confirmed to exist but requires signed DPLH licence agreement. |
| zone/overlay (City of Vincent IntraMaps) | 2026-06-09 | https://mapping.vincent.wa.gov.au/IntraMaps22B/ | BLOCKED | HTTP 403. Display-only portal; no open WFS available. |
| zone/overlay (City of Vincent Pozi map) | 2026-06-09 | https://mapping-vincent.pozi.com/ | NOT_TESTED (display only) | Display-only application; no open data export endpoint found. |

---

## Acceptance Gate

All three layers have a verified endpoint + licence classification + a working sample (or a recorded blocker with the manual step). The free demo path is fully actionable for G-NAF (Layer 1). Layers 2 and 3 have verified endpoints but require licence actions (see Section 4 human-loop checklist) before DB ingest. Paid/licensed go-wide items are separated and flagged human-loop.

> Free demo path is fully actionable for Layer 1 (address points). Layers 2 and 3 are endpoint-verified with samples provided; DB ingest is blocked pending licence actions listed in Section 4.
