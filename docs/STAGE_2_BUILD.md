# Stage 2 Build — Spatial & Address for One Council (multi-agent)

Date: 2026-06-09
Authority: `docs/MASTER_REBUILD_PLAN.md` §5.3/§6.1 (V3) + `docs/ROAD_TO_PROD.md` Stage 2 +
`docs/M1_GOLDEN_FIXTURE.md`. Execution conventions follow `docs/MULTI_AGENT_BUILD_PLAN.md`
(roster, write scopes, invariants, merge protocol). This is the build brief for Claude Code.

**Precondition:** `docs/CONSOLIDATION_PLAN.md` (Stage 0) has landed — single Postgres + single
alembic chain, human-review removed. If it hasn't, finish that first; Stage 2 builds on the V3
schema only.

---

## 1. Goal & current state

Deliver address → property resolution for **one council (City of Vincent)** end-to-end, populate
the spatial tables for that council, and create the golden fixture project.

**What exists:** `src/draftcheck/domain/address/spatial.py` (resolver logic, dataclasses, licence/
resolution/confidence enums, manual-override) — but the store is **in-memory only**
(`InMemorySpatialDatasetStore`, `create_default_spatial_store`). `api/address.py` exposes routes but
binds the in-memory store and still uses `require_reviewer` (removed in Stage 0). The PostGIS tables
(`spatial_datasets`, `parcels`, `address_points`, `planning_features`, `lg_areas`, `projects`,
`proposals`, `properties`, `property_facts`) exist in migration `0001` with GIST indexes in `0002`,
but are **empty and unwired**.

**What Stage 2 adds:** a PostGIS-backed store behind the existing resolver interface, real importers
for free one-council data, the resolver wired to live data, project/property/proposal services + API
per V3 §6.1, the wizard steps 1–3, and the seeded golden fixture.

---

## 2. Data sources (one-council demo = 100% free)

From `docs/DATA_SOURCES.md`. The demo needs **no paid licence**; going statewide later does.

| Layer | Source | Licence | Cost | Used for |
|---|---|---|---|---|
| Addresses + lat/long | G-NAF (data.gov.au) | CC BY 4.0 | Free | `address_points` |
| Parcel geometry | SLIP "Cadastre (No Attributes)" public layer | Open SLIP | Free (free SLIP account) | `parcels` (point-in-polygon, lot area) |
| Zoning / R-code | City of Vincent LPS (council IntraMaps/open data) or DPLH display WMS | Council open / display-only | Free | `planning_features` (R-code, overlays) |
| LGA boundary | SLIP / council | Open | Free | `lg_areas` |

**Do NOT use for the demo (go-wide blockers, human-in-the-loop):** Landgate full cadastre
(LGATE-217/218, paid subscription) and DPLH LPS bulk vector (DPLH-070/071, *Government-Use-Only*).
The Coordinator escalates these to Steven only when statewide/commercial scope is approved. Until
then, parcel *attributes* (lot-on-plan/tenure) are out of scope; geometry + computed lot area is
enough.

**Hard rule:** a geocode / address match is **never legal proof**. Resolution returns provenance and
a status (`resolved | missing_info | needs_human_review | unsupported`) with a separate confidence.

---

## 3. Agent roster & write scopes

Workers are fresh subagents, each in an isolated worktree, each receiving the invariants block (§5).
A worker never writes outside its scope; schema needs go to the Schema Integrator as DDL specs.

| Agent | Write scope | Builds |
|---|---|---|
| **Coordinator** | merges, contracts, escalations | Orchestration; SLIP account + council zoning source confirmation (human loop); OpenAPI freeze |
| **Schema Integrator** | `src/draftcheck/db/models.py`, `db/alembic/` | Verify spatial tables vs store needs; forward migration for any delta (SRID/geometry cols, dataset licence fields, GIST indexes already in 0002); procrastinate import-job tables if needed |
| **Spatial** | `src/draftcheck/domain/address/`, `api/address.py` | PostGIS store + importers (G-NAF, SLIP cadastre, zoning, LGA); wire resolver to live data; remove `require_reviewer` usage |
| **Projects** | `src/draftcheck/domain/projects/` (new), `api/projects.py` (new) | Project create; property resolution per project; `property_facts` row-per-fact with provenance; proposal capture (wizard steps 1–3 API) |
| **Fixtures Owner** | `tests/fixtures/golden/` | City of Vincent fixture: parcel geometry + address point + zoning + LGA + the M1 site-plan stub; seeded project |
| **Frontend** | `web/` | Wizard steps 1–3: address resolver, proposal confirmation, matched-context panel — against the OpenAPI stub |
| **Spec Reviewer / Quality Reviewer** | read-only | Per merge (see §6) |
| **Red-team** | read-only + harness | Attack the resolver (geocode-as-proof, low-confidence-as-authoritative) |

Boundary between Spatial and Projects: Spatial owns the resolver + datasets and exposes
`AddressResolutionService`; Projects consumes it and owns project/property lifecycle. They share only
the resolver interface and the `property_facts` contract — no shared files.

---

## 4. Waves (within Stage 2)

```text
S2.W0  Coordinator: confirm SLIP free account + council zoning source (human loop)
       Schema Integrator: verify/extend spatial schema; freeze OpenAPI §6.1 stub for
       /projects, /projects/{id}/resolve-address, /projects/{id}/property
S2.W1  Spatial: PostGIS store + importers   ||  Projects: project/property/proposal services
       ||  Frontend: wizard shell vs stub   ||  Fixtures Owner: acquire fixture data
S2.W2  Spatial: resolver wired to live data ||  Projects: resolve-address/property endpoints
       ||  Frontend: wizard steps 1–3 vs live API  ||  Fixtures Owner: land golden fixture
S2.GATE Red-team + reviewers; M1 fixture address resolves end-to-end
```

Hard edges: Projects ← Spatial (resolver interface) · Fixtures Owner ← Spatial+Projects (needs the
importers + project create) · Frontend builds against the frozen stub from W0, swaps to live API in
W2. Schema migrations always merge before the service PRs that need them.

---

## 5. Worker invariants (every Stage 2 worker, verbatim)

```text
Authority: docs/MASTER_REBUILD_PLAN.md §5.3/§6.1 (V3); your brief names the paths you own.
Write scope: only the paths in your brief. Schema changes are DDL specs to the Schema
  Integrator — never edit models.py or alembic/ yourself.
Single-writer files you must not touch: pyproject.toml, uv.lock, models.py, alembic/,
  infra/compose.yml, Caddyfile, CI workflows, the OpenAPI contract.
Stage-2 safety invariants:
  - A geocode/address match is NEVER legal proof. Resolution returns status
    ∈ {resolved, missing_info, needs_human_review, unsupported} + separate confidence.
  - Every spatial/property fact carries provenance (dataset_id, method, fetched_at,
    licence_status). No fact without provenance.
  - Parcel attributes (lot-on-plan/tenure) are out of scope until the Landgate licence is
    cleared by the Coordinator — geometry + computed lot area only.
  - Dataset import is blocked unless its licence permits the use; record licence_status
    on every spatial_datasets row.
  - Pipeline is all-AI: no human reviewer/approval gate. Do not add require_reviewer or a
    signoff step. (review_status, where present, is an automated lifecycle field.)
  - Output stays advisory/cited; no final compliance claim. Legal/numeric values in
    examples are illustrative — hardcoding one as truth is a defect.
  - No create_all; no dev-login; no LLM call outside the traced, spend-capped adapter.
Never stage: draftcheck.db, .storage/, .venv/, .vercel/, build/, caches, data/corpus/.
Done = code + tests + handoff note (what changed, contracts touched, follow-ups, V3
  sections satisfied). Tests failing or scope exceeded = not done; say so.
```

---

## 6. Merge protocol (per `MULTI_AGENT_BUILD_PLAN.md` §6)

1. Worker develops in worktree; rebases on main before handoff.
2. CI green: ruff, mypy (src scope), pytest, alembic up+down, import-linter, web build,
   OpenAPI diff, forbidden-pattern grep (`create_all | dev-login | require_reviewer |
   geocode-as-proof paths | uncited regulatory output`).
3. **Spec Reviewer** (fresh, read-only): PR vs V3 §5.3/§6.1 + this brief's acceptance list.
4. **Quality Reviewer** (fresh): runs gates locally; adversarial greps; test quality.
5. Coordinator merges in dependency order; schema PRs before their dependents.
6. **Red-team gate** before S2.GATE closes: attempt to make the resolver treat a geocode as
   authoritative, resolve below confidence threshold as `resolved`, or import a dataset whose
   licence forbids the use. All must fail.
7. **Human-in-the-loop:** SLIP free-account creation + council zoning source (W0); Landgate/DPLH
   licence (only if going beyond the free demo — out of Stage 2 scope by default).

---

## 7. Acceptance gates

### Per agent
- **Schema Integrator:** `alembic upgrade head` + `downgrade` clean on scratch Postgres; spatial
  tables have geometry columns with correct SRID (GDA2020) + GIST indexes; no `signoffs`/reviewer
  remnants from Stage 0.
- **Spatial:** PostGIS store passes the same behavioural tests the in-memory store passes, plus
  point-in-polygon parcel lookup via `ST_Contains/ST_Intersects`; importers load G-NAF + SLIP
  cadastre + zoning + LGA for City of Vincent, each writing a `spatial_datasets` row with
  licence_status; `require_reviewer` removed.
- **Projects:** create project → resolve address → resolve property returns a `PropertyProfile` with
  `property_facts` rows, each provenanced; manual override recorded with provenance; proposal (wizard
  steps 1–3) captured.
- **Fixtures Owner:** the City of Vincent fixture loads deterministically; the fixture address
  resolves to the expected parcel/council/R-code/overlays; the M1 site-plan stub is present.
- **Frontend:** wizard steps 1–3 run against the live API; resolver shows status + confidence +
  provenance; geocode results are visibly labelled "not legal proof".

### Stage 2 GATE (V3 Phase 2 exit)
- The fixture address → parcel + council + zone/R-code + overlays **with provenance**, or
  `missing_info` when data is absent.
- A geocode result is never presented as legal proof (red-team confirms).
- Every property fact has provenance and a licence-checked dataset.
- The wizard creates a project and shows matched spatial context.
- Importers are re-runnable and idempotent; row counts recorded.

---

## 8. API surface (freeze from V3 §6.1 in W0)

```text
POST /api/v1/projects                         create project (name, council scope)
POST /api/v1/projects/{id}/resolve-address    address → parcel/council/zone/overlays + status
GET  /api/v1/projects/{id}/property           resolved PropertyProfile + facts + provenance
POST /api/v1/projects/{id}/property/override   manual fact override (provenance required)
POST /api/v1/projects/{id}/proposal            wizard steps 1–3 capture (dwelling_type etc.)
```

Freeze these as an OpenAPI stub before W1 so Frontend and Projects build against the same contract.
`dwelling_type` is a **proposal** fact, never an address fact (V3 §5.4). Any deviation from §6.1
needs a V3 amendment first.

---

## 9. What to hand each agent

Give every worker: this file, `MASTER_REBUILD_PLAN.md` §5.3–5.4/§6.1, `DATA_SOURCES.md`,
`M1_GOLDEN_FIXTURE.md`, and the invariants block (§5). Spatial also gets the existing
`domain/address/spatial.py` to extend (do not rewrite the resolver — back it with PostGIS). Projects
gets the resolver interface only. Frontend gets the frozen OpenAPI stub. Fixtures Owner gets
`M1_GOLDEN_FIXTURE.md` §1–3.

**First move for the Coordinator:** confirm the free SLIP account + City of Vincent zoning source
(human loop), then have the Schema Integrator freeze the schema + OpenAPI stub so W1 can fan out.
