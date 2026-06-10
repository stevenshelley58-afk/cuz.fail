# LotFile — Data Sources, Access & Sign-up Links

**Status:** Verified against each provider's live dataset/pricing pages, 2026-06-06. Access levels and
prices change — re-check the badge on each `data.wa.gov.au` dataset before you rely on it.
**Companion:** feeds Agent B (source governance / licence gate) and Agent D (spatial spine) in
`MASTER_IMPLEMENTATION_PLAN.md`.

## Bottom line (read this first)

The honest cost picture is not "all free" and not "all paid" — it splits cleanly:

- **A one-council demo can be built almost entirely on FREE data.** Addresses (G-NAF), bushfire,
  heritage, the R-Codes text, and the NCC are all free. Parcel *geometry* is available free. The only
  awkward piece is clean **zoning vector data**, and for a single council you get that from the
  **council itself** (they own their scheme), sidestepping the state restriction.
- **Statewide / commercial production needs two paid or permissioned licences:** the **DPLH** statewide
  planning (zoning) vector data is *Government-Use-Only* (you must request a licence), and the
  **Landgate** full cadastre (lot/plan, tenure, attributes) is a *paid subscription*. Neither publishes
  public pricing — you email them with your use case.

So: **scraping was the wrong tool**, but you don't need it. The free tier gets you a real demo; the two
licences are the cost of going wide. Below is every account and link.

## The "what does it cost" table

| Data need | Best source | Access | Price | Plan owner |
|-----------|-------------|--------|-------|-----------|
| Addresses + lat/long | G-NAF (data.gov.au) | Open, CC BY 4.0 | **Free** | D |
| Address autocomplete | Google Places **or** Geoscape **or** self-host G-NAF | API key / free tier | **Free tier** | H/D |
| Parcel geometry | SLIP "Cadastre (No Attributes)" public layer | Open (public SLIP) | **Free** | D |
| Parcel attributes (lot/plan, tenure) | Landgate Cadastre (LGATE-217/218) | Subscription | **Paid — contact** | D |
| Zoning / R-code density (statewide vector) | DPLH LPS Zones & Reserves (DPLH-071) | **Govt-use-only** (bulk) / Open (display WMS) | **Request licence** | D |
| Zoning (one council) | The council's own GIS / open data / on request | Varies by council | usually **Free** | D |
| Region scheme (MRS etc.) | DPLH Region Scheme Zones & Reserves (DPLH-023) | Mixed | display free / vector restricted | D |
| Bushfire-prone areas | DFES OBRM Bush Fire Prone Areas 2025 (OBRM-024) | Open, CC BY 4.0 | **Free** (free login to download) | D |
| Heritage | Heritage Council State Register (DPLH-006), Heritage List (DPLH-090) | Open (confirm badge) | **Free** | D |
| R-Codes text (SPP 7.3) | wa.gov.au PDF | Open | **Free** | B |
| National Construction Code | ncc.abcb.gov.au | Free account (optional) | **Free** | B |
| Council scheme text + local policies | Each council website / DPLH | Open | **Free** | B |
| Australian Standards (e.g. AS 3959) | Standards Australia | Paid / licensed | **Paid — metadata only in app** | B |

## 1. Addresses & geocoding

**G-NAF (Geocoded National Address File)** — every physical address in Australia with coordinates,
free, updated quarterly (~15.9M addresses as of May 2026), licensed CC BY 4.0. This is your address
validation + geocoding backbone. Download from data.gov.au; the "G-NAF Core" simplified table is the
easy starting format.

- Dataset / download: <https://data.gov.au/data/dataset/geocoded-national-address-file-g-naf>
- Product overview: <https://geoscape.com.au/products/g-naf/>

**Address autocomplete** (the wizard's first field — autocomplete only, never legal proof):

- **Google Places (New)** — ~10,000 free autocomplete events/month (Essentials tier); session-based
  billing; note the old $200/month credit ended in 2025. Get a key in Google Cloud Console.
  Pricing: <https://developers.google.com/maps/documentation/places/web-service/usage-and-billing> ·
  Start: <https://developers.google.com/maps/documentation/places>
- **Geoscape Predictive Address Verification API** — free tier of **500 transactions/month**, then
  pay-as-you-go; government-recognised AU addresses. Sign up at the Geoscape developer portal / Hub.
  <https://geoscape.com.au/geoscape-hub/>
- **Free alternative — self-host on G-NAF.** Because G-NAF is free, you can run your own
  autocomplete/geocoder (e.g. an Addressr-style service) and pay nothing per call. Best if call volume
  grows. (Build effort instead of per-call cost.)

## 2. Parcels / cadastre

Two tiers, and the distinction matters for cost:

- **Free — parcel geometry only.** SLIP's public **Cadastre (No Attributes)** layer gives parcel
  *boundaries* via the public service — enough for point-in-polygon "which parcel is this address in"
  and to compute lot area from the geometry. Served from `SLIP_Public_Services` (free SLIP account).
- **Paid — full cadastre.** **Cadastre (Polygon) LGATE-217** (and Land LGATE-218, Address LGATE-002)
  carry lot-on-plan, tenure, etc., but are **Fees Apply / subscription** under Landgate licence terms.
  Page (note the "Fees Apply" badge): <https://catalogue.data.wa.gov.au/dataset/cadastre-polygon>
  - Landgate cadastral data + licensing + pricing (contact):
    <https://www.landgate.wa.gov.au/location-data-and-services/discovering-landgate-data/cadastral-data/>
    · <https://www.landgate.wa.gov.au/location-data-and-services/discovering-landgate-data/licensing/>
    · email **customerexperience@landgate.wa.gov.au**

Practical call: build the demo on the free geometry layer; licence the full cadastre from Landgate only
when you need verified lot/plan identifiers at scale.

## 3. Zoning, R-codes & overlays

This is the one genuinely awkward piece. The statewide standardised layers from DPLH are **mixed
access**:

- The public **WMS / Map Service** (display + point "identify") is **Open** — free to render and query
  on a map.
- The **WFS and bulk downloads** (GeoJSON/Shapefile/Geopackage) of the statewide vector are
  **Government-Use-Only**, under the DPLH data licensing agreement — a private app must **request a
  licence**.

Datasets (see the access badge per resource):

- LPS Zones & Reserves (DPLH-071): <https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-zones-and-reserves-dop-025>
- LPS R-Codes / density (DPLH-070): <https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-r-codes-dop-101>
- LPS Special Area / control areas (DPLH-068): <https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-special-area-dop-090>
- Region Scheme Zones & Reserves (DPLH-023): <https://catalogue.data.wa.gov.au/dataset/region-scheme-zones-and-reserves-dop-072>
- Request access / licence: **spatialdata@dplh.wa.gov.au** · PlanWA: <https://www.planning.wa.gov.au/mapping-and-data/planwa>

**The cheap path for a single-council demo:** get the zoning from **that council** — they are the legal
custodian of their own Local Planning Scheme and most publish it via their own GIS/IntraMaps, open-data
portal, or on request. This is free or near-free, more current for their area, and avoids the statewide
restriction entirely. It's also why the plan says "scope to one council first."

## 4. Bushfire-prone areas (free)

**DFES / OBRM Bush Fire Prone Areas 2025 (OBRM-024)** — **Open, CC BY 4.0.** The WMS/Map Service are
fully open; the vector downloads (GeoJSON/SHP/GPKG/FGDB) are free with a free SLIP login. This drives
the BAL/bushfire trigger your compliance checks already reference.

- Dataset: <https://catalogue.data.wa.gov.au/dataset/bush-fire-prone-areas-2025>
- Context: <https://www.dfes.wa.gov.au/hazard-information/bushfire/bushfire-prone-areas>

## 5. Heritage (free)

- **Heritage Council State Register (DPLH-006)** — places with statutory protection; multiple formats
  (FGDB/GeoJSON/Geopackage/Shapefile). <https://catalogue.data.wa.gov.au/dataset/heritage-council-wa-state-register>
- **Heritage List (DPLH-090)** — local-scheme heritage places. <https://catalogue.data.wa.gov.au/dataset/heritage-list-dplh-090>
- Search/reference: inHerit — <https://inherit.dplh.wa.gov.au/>

(Confirm the per-resource access badge; State Register data is public.)

## 6. Legal / rule text (free)

- **R-Codes — SPP 7.3 Residential Design Codes Volume 1** (latest April 2026 PDF):
  <https://www.wa.gov.au/system/files/2026-04/r-codes-volume-1-10-april-2026.pdf> ·
  landing page: <https://www.dplh.wa.gov.au/rcodes>
- **National Construction Code (NCC)** — free to read/download; a free ABCB account unlocks online
  features. <https://ncc.abcb.gov.au/>
- **Council planning scheme + Local Planning Policies** — on each council's website (and DPLH). These
  are the per-council legal text Agent C extracts into `RuleRow`s.

## 7. Australian Standards (paid — metadata only)

Standards Australia full text (e.g. **AS 3959** bushfire construction) is **paid/proprietary**. Per the
plan's safety boundary, **do not scrape or store the full text** — store public metadata + an access
note only, and use a lawfully licensed copy for any licensed review. <https://www.standards.org.au/>

## 8. Accounts to create now (the action list)

```text
1. data.gov.au          download G-NAF (free, CC BY 4.0) — no account strictly needed.
2. SLIP free account    https://data.wa.gov.au/slip → "register a free account"
                        (unlocks free downloads: bushfire, heritage, public cadastre geometry).
3. Google Cloud         console.cloud.google.com → enable Places API → get key (free autocomplete tier).
   (or) Geoscape Hub    https://geoscape.com.au/geoscape-hub/ → developer account (500 free/mo).
4. ABCB / NCC account   https://ncc.abcb.gov.au/ (free; optional but handy).
5. Email DPLH           spatialdata@dplh.wa.gov.au → request zoning/planning vector licence
                        (or get zoning from your target council instead).
6. Email Landgate       customerexperience@landgate.wa.gov.au → ask cadastre subscription pricing
                        (only when you outgrow the free geometry layer).
```

## 9. Licence-gate reminder (Agent B)

Every dataset above must get a `SourceLicenceReview` row before its data supports an answer — recording
`allowed_use`, `allowed_storage`, `allowed_redistribution`, and `allowed_ai_processing`. Two specifics:

- **Don't redistribute restricted data.** DPLH "Government-Use-Only" vector and Landgate paid cadastre
  must not be re-published through your app's API or exports unless your licence explicitly allows it —
  use them to *compute* a result and cite the source, don't re-serve the raw layer.
- **CC BY 4.0 data** (G-NAF, bushfire) just needs attribution — easy, but record it.

## Sources

- [G-NAF — data.gov.au](https://data.gov.au/data/dataset/geocoded-national-address-file-g-naf) · [Geoscape G-NAF](https://geoscape.com.au/products/g-naf/)
- [Geoscape Hub / developer](https://geoscape.com.au/geoscape-hub/)
- [Google Places usage & billing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing)
- [SLIP (data.wa.gov.au)](https://data.wa.gov.au/slip)
- [Cadastre (Polygon) LGATE-217 — Fees Apply](https://catalogue.data.wa.gov.au/dataset/cadastre-polygon) · [Landgate cadastral data](https://www.landgate.wa.gov.au/location-data-and-services/discovering-landgate-data/cadastral-data/) · [Landgate licensing](https://www.landgate.wa.gov.au/location-data-and-services/discovering-landgate-data/licensing/)
- [LPS Zones & Reserves DPLH-071 — Mixed/Govt-only vector](https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-zones-and-reserves-dop-025) · [LPS R-Codes DPLH-070](https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-r-codes-dop-101) · [PlanWA](https://www.planning.wa.gov.au/mapping-and-data/planwa)
- [Region Scheme Zones & Reserves DPLH-023](https://catalogue.data.wa.gov.au/dataset/region-scheme-zones-and-reserves-dop-072)
- [Bush Fire Prone Areas 2025 OBRM-024 — Open/CC BY](https://catalogue.data.wa.gov.au/dataset/bush-fire-prone-areas-2025)
- [Heritage State Register DPLH-006](https://catalogue.data.wa.gov.au/dataset/heritage-council-wa-state-register) · [Heritage List DPLH-090](https://catalogue.data.wa.gov.au/dataset/heritage-list-dplh-090)
- [R-Codes Volume 1 (Apr 2026 PDF)](https://www.wa.gov.au/system/files/2026-04/r-codes-volume-1-10-april-2026.pdf) · [DPLH R-Codes](https://www.dplh.wa.gov.au/rcodes)
- [National Construction Code (ABCB)](https://ncc.abcb.gov.au/)
- [Standards Australia](https://www.standards.org.au/)
