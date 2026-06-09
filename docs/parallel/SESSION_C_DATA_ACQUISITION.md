# Session C — Free One-Council Data Acquisition Runbook (multi-agent)

Authority: `docs/DATA_SOURCES.md`, `docs/STAGE_2_BUILD.md` §2, `docs/SPATIAL_ENGINE_DESIGN.md`.
Conventions: `docs/MULTI_AGENT_BUILD_PLAN.md` §5–6.
**Sole output:** `docs/DATA_ACQUISITION_RUNBOOK.md` + samples in `data/fixtures/samples/`. Web + data
only. Touch no code.

## Why
Stage 2's first wave is blocked on a human-loop step: getting the free data for City of Vincent.
This session turns that into an exact, verified checklist (+ a proof-of-pipeline sample pull) so the
Stage 2 Spatial agent and Steven can action it without research.

## Goal
A runbook that, for City of Vincent, gives the exact source, dataset ID, endpoint, licence, and pull
method for each of the four free layers — plus a small verified sample of each in
`data/fixtures/samples/` proving the endpoint works.

## Agents
| Agent | Scope | Task |
|---|---|---|
| **G-NAF** (worker) | addresses | data.gov.au G-NAF dataset ID + download; how to extract the City of Vincent address subset; the fields feeding `address_points` (address, lat/long, GDA2020). Pull a handful of Vincent addresses as a sample. |
| **Cadastre/SLIP** (worker, parallel) | parcels | SLIP public "Cadastre (No Attributes)" WFS/WMS endpoint; the City of Vincent bounding box; a sample `GetFeature` request returning parcel polygons; licence note (free SLIP account). Geometry only — **no** lot-on-plan/tenure (paid). |
| **Zoning** (worker, parallel) | R-code/overlays | City of Vincent LPS zoning + R-code source (council IntraMaps / open data, or DPLH display WMS); how to get the R-code + overlays for a parcel. Flag DPLH bulk vector as Government-Use-Only (out of scope). |
| **Licence Reviewer** (fresh, read-only) | read all | Confirm each layer's licence permits the demo use; classify each as free-now vs needs-account vs needs-licence (human loop). No layer enters the runbook as "use" unless its licence clears. |

All three data agents run concurrently; Licence Reviewer closes the session.

## Method notes
- Use `WebSearch`/`web_fetch` for portal pages and open WFS endpoints. If a portal or service won't
  fetch, record the URL + manual step — **do not** work around fetch restrictions with curl/python.
- Account creation (SLIP) and any licence email (Landgate/DPLH) are **human-loop** — list the exact
  step + contact, don't attempt it.
- Keep samples tiny (a few features) — proof the endpoint works, not a bulk download.

## Output
`docs/DATA_ACQUISITION_RUNBOOK.md`: per-layer table (`source | dataset ID | endpoint | licence |
account needed? | pull method | sample path`), a "human-loop actions for Steven" checklist, and the
go-wide note (Landgate paid cadastre + DPLH licence) clearly separated from the free demo path.
Samples land in `data/fixtures/samples/`.

## Acceptance gate
All four layers have a verified endpoint + licence classification + a working sample (or a recorded
blocker with the manual step); free demo path is fully actionable; paid/licensed go-wide items are
separated and flagged human-loop.
