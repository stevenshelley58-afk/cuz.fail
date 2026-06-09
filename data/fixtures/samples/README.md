# data/fixtures/samples — Spatial Data Samples

Sample files for the three spatial layers required by the DraftCheck WA V3 target schema (City of Vincent demo scope). See `docs/DATA_ACQUISITION_RUNBOOK.md` for full pull instructions, licence details, and human-loop actions.

---

## Files

### gnaf_vincent_sample.json

**Source:** G-NAF (Geocoded National Address File) — Geoscape Australia, MAY 2026 release
**Layer:** `address_points`
**Licence:** CC BY 4.0 — free for commercial use with attribution
**Status:** FREE — endpoint verified, bulk ZIP download available without account

**Demonstrates:**
- The `gnaf_pid`, `address`, `lon`, `lat` field structure that maps into the `address_points` table
- GAWA_ PID prefix format for WA addresses
- GDA2020 coordinates at 8 decimal places
- 3 representative records from Leederville, North Perth, and Mount Hawthorn

**Download command:**
```bash
wget "https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc/resource/f8666213-4079-44da-bede-ebda3a4363e0/download/g-naf_may26_allstates_gda2020_psv_1023.zip"
```

---

### cadastre_slip_sample.geojson

**Source:** Cadastre (No Attributes) LGATE-001 — SLIP Public Services, Landgate
**Layer:** `parcels`
**Licence:** SLIP Personal Use Licence — non-commercial only
**Status:** ENDPOINT VERIFIED — licence required before DB ingest (contact licensing@landgate.wa.gov.au)

**Demonstrates:**
- GeoJSON representation of the 3 parcel polygons from the verified WFS 1.1.0 response for a Leederville test tile
- Which fields are present on LGATE-001 (OBJECTID, view_scale, st_area_shape_) and which are absent (lot_plan, local_government)
- Field mapping notes showing that area_m2 must be computed via PostGIS and local_government must be derived via spatial join
- The BBOX and WFS parameters needed to reproduce the pull (WFS 1.1.0, lat/lon axis order, GML3 output)
- Raw WFS 1.1.0 GML response: `data/fixtures/samples/cadastre_slip_leederville_raw.gml`

**WFS pull command:**
```
https://public-services.slip.wa.gov.au/public/services/SLIP_Public_Services/Property_and_Planning_WFS/MapServer/WFSServer?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAMES=esri:Cadastre__No_Attributes___LGATE-001_&BBOX=-31.935,115.845,-31.920,115.860,EPSG:4326&COUNT=5&OUTPUTFORMAT=GML3
```

---

### vincent_zoning_sample.json

**Source:** DPLH-071 (Zones and Reserves) + DPLH-070 (R-Codes) — Department of Planning, Lands and Heritage via SLIP Public REST
**Layer:** `zone` (DPLH-071) and `overlay` (DPLH-070)
**Licence:** DPLH Data Licensing Agreement — display/identify only; dataset-level restriction: not for commercial purposes; bulk ingest requires signed DPLH licence or City of Vincent direct agreement
**Status:** ENDPOINT VERIFIED — bulk ingest BLOCKED pending licence action (see runbook Section 4 items 2 and 3)

**Demonstrates:**
- The schema and field structure expected from DPLH REST query responses (GeoJSON format)
- On-demand point-in-polygon query URLs for zone and R-code lookups (usable during demo without DB storage)
- Known zone codes and R-code values for City of Vincent
- Geometry is intentionally withheld (cannot store without licence) — only schema/structure is shown
- Human-loop actions required to unblock bulk ingest

**On-demand query (no DB storage required):**
```
https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Property_and_Planning/MapServer/112/query?geometry=<lon>,<lat>&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&f=geojson
```

---

## Licence Summary

| File | Layer | Licence | DB Storage OK? |
|---|---|---|---|
| gnaf_vincent_sample.json | address_points | CC BY 4.0 | Yes — attribution required |
| cadastre_slip_sample.geojson | parcels | SLIP Personal Use (non-commercial) | NO — requires Landgate written approval |
| vincent_zoning_sample.json | zone / overlay | DPLH Licence (non-commercial display) | NO — requires DPLH licence or City of Vincent agreement |

Attribution for G-NAF (must appear in UI wherever address data is displayed):
> Incorporates or developed using G-NAF © Geoscape Australia licensed by the Commonwealth of Australia under CC BY 4.0.
