# Spatial Engine Design (Phase 1, Gap G1)

> Plan-lock notice (2026-06-06): this is now a historical/background planning document. For
> implementation, use `docs/MASTER_IMPLEMENTATION_PLAN.md`, `MASTER_PLAN_ADDENDUM.md`,
> `REPO_AUDIT.md`, and `docs/PLAN_LOCK_NOTICE.md`. Those files supersede this document where they
> differ.

**Status:** Design proposal. Concrete enough to implement; names/signatures are recommendations.
**Date:** 2026-06-06
**Closes:** `GAP_ANALYSIS.md` → G1 (spatial applicability engine), and unblocks G2's `applies_when`
predicates and G8's address-first profile.
**Conventions honored:** SQLAlchemy 2.0 `Mapped`/`mapped_column`, central `models.py` +
`Base.metadata`, metadata-snapshot Alembic migrations, `record_audit(...)`, service classes taking a
`Session`, Pydantic schemas in `shared_schemas`.

**Decisions taken (chosen for best end-user reliability):**

- **PostgreSQL + PostGIS for dev, CI, and prod.** No SQLite for the spatial path — one geometry code
  path, so the query logic users hit in prod is the same logic CI exercises. (The rest of the app can
  keep SQLite if desired, but `SPATIAL_ENABLED` requires a Postgres `DATABASE_URL`.)
- **DuckDB-spatial / `ogr2ogr` for bulk geometry loading.** Robust, low-memory ingestion of statewide
  cadastre/overlays; the operational store stays PostGIS.

## Goal & non-goals

**Goal.** Turn an address (or coordinate) into a provenance-backed `ApplicabilityContext` — parcel,
zoning, R-code density, region scheme, overlays, hazard flags — and use it to **auto-populate
`Property` and `PlanningOverlay`** with `detected_by="spatial"`, replacing manual entry while keeping
a manual override path.

**Non-goals (this phase).** No national rollout (WA-first, but schema stays jurisdiction-generic);
no frontend; no change to the rule engine itself (G2 consumes the context later); no relaxing of the
cite-or-refuse / conservative-status safety boundary.

## The resolution pipeline

```
address ──► geocode (G-NAF)        ──► AddressPoint  (lon/lat, confidence)
                                         │
coords  ─────────────────────────────────┘
                                         ▼
                          point-in-polygon on cadastre   (ST_Contains)
                                         ▼
                                       Parcel  (lot/plan, lga, area_m2)
                                         ▼
                       spatial join against planning layers (ST_Intersects)
                                         ▼
        ApplicabilityContext { zoning, r_code_density, region_scheme,
                               overlays[], hazard_flags, match_confidence,
                               needs_human_review, provenance[] }
                                         ▼
        write Property + PlanningOverlay (detected_by="spatial") + audit
```

Each arrow can fail safe: no geocode match, multiple parcel candidates, or low confidence yields a
context flagged `needs_human_review` rather than a guess.

## Package layout

Behavior lives in a new package; **models go in the central `draftcheck_core/models.py`** so
`Base.metadata`, `init_database()`, and the existing Alembic env keep working with zero wiring
changes (this matches the current "all models central" convention).

```
packages/spatial/draftcheck_spatial/
  __init__.py
  backend.py       # SpatialBackend protocol + PostgisBackend (the one real impl)
  resolver.py      # SpatialResolver: geocode -> parcel -> layers -> ApplicabilityContext
  service.py       # SpatialService: resolve + persist Property/PlanningOverlay + audit
  loaders.py       # ogr2ogr / DuckDB ingestion for G-NAF, cadastre, planning layers (worker-side)
  crs.py           # GDA2020 constants + area reprojection helpers
```

Register it (mirrors the existing list in `pyproject.toml`):

```toml
[tool.setuptools.packages.find]
where = [ ... , "packages/spatial" ]

[tool.pytest.ini_options]
pythonpath = [ ... , "packages/spatial" ]
```

## Data model

Add to `packages/core/draftcheck_core/models.py`. Geometry uses **GeoAlchemy2** `Geometry` columns —
a single path, since dev, CI, and prod all run PostGIS.

```python
# top of models.py
from geoalchemy2 import Geometry

GDA2020 = 7844          # EPSG geographic CRS native to G-NAF + WA cadastre
MGA_ZONE_50 = 7850      # projected CRS (metres) for Perth-metro area math


class Parcel(Base, TimestampMixin):
    __tablename__ = "parcels"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("pcl"))
    lot_plan: Mapped[str | None] = mapped_column(String, index=True)
    local_government: Mapped[str | None] = mapped_column(String, index=True)
    area_m2: Mapped[float | None] = mapped_column(Float)
    geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=GDA2020), nullable=False)
    attrs_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))


class AddressPoint(Base, TimestampMixin):
    __tablename__ = "address_points"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("adr"))
    gnaf_pid: Mapped[str | None] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=GDA2020), nullable=False)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"), index=True)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))


class PlanningLayerFeature(Base, TimestampMixin):
    __tablename__ = "planning_layer_features"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("plf"))
    layer_type: Mapped[str] = mapped_column(String, nullable=False, index=True)  # zone|region_scheme|overlay|bushfire|heritage|airport|noise
    code: Mapped[str | None] = mapped_column(String)        # e.g. "R40", "BAL-29"
    label: Mapped[str] = mapped_column(String, nullable=False)
    local_government: Mapped[str | None] = mapped_column(String, index=True)
    geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=GDA2020), nullable=False)
    attrs_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
```

Every spatial row points at a `source_version_id`, so the **existing version/supersession/citation
machinery extends to geometry** — a zone polygon is just another versioned, citable source. No new
provenance concept is invented. (`Text`, `Float`, `ForeignKey`, `String` are already imported in
`models.py`; only `geoalchemy2.Geometry` is new.)

## Database & migration

**Dependencies** (add to `pyproject.toml` + `requirements.txt`): `geoalchemy2`, `shapely`, `pyproj`
for the runtime; `duckdb` for the worker loaders. **GDAL/`ogr2ogr`** is a system package — install it
in the **worker** image only (it's the heavy native dependency), not the API image.

**Compose** (`docker-compose.yml`): switch the Postgres service image to `postgis/postgis:16-3.4`.
**CI** must run a `postgis/postgis` service (or use `testcontainers`) so the spatial suite runs
against real PostGIS — never a stub.

**Migration** `infra/alembic/versions/0002_spatial.py` — keeps the metadata-snapshot style of
`0001_initial_metadata.py`, adding the PostGIS extension and GiST indexes `create_all` won't emit:

```python
revision = "0002_spatial"
down_revision = "0001_initial_metadata"

from alembic import op
from draftcheck_core.database import Base
from draftcheck_core import models  # noqa: F401


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=bind)  # checkfirst=True: only adds the new spatial tables
    op.execute("CREATE INDEX IF NOT EXISTS ix_parcels_geom ON parcels USING GIST (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_layers_geom  ON planning_layer_features USING GIST (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_addr_geom    ON address_points USING GIST (geom)")


def downgrade() -> None:
    for t in ("address_points", "planning_layer_features", "parcels"):
        op.drop_table(t)
```

**`database.py`:** no code change needed, but document that when `SPATIAL_ENABLED=true`,
`DATABASE_URL` must point at PostgreSQL/PostGIS. The existing `connect_args` SQLite branch simply
won't be taken in spatial deployments.

**Config additions** (`config.py`, same frozen-dataclass + env pattern):

```python
spatial_enabled: bool = os.getenv("SPATIAL_ENABLED", "false").lower() == "true"
geocoder: str = os.getenv("GEOCODER", "gnaf")             # "gnaf" | "geoscape"
gnaf_dataset_path: str = os.getenv("GNAF_DATASET_PATH", "")
cadastre_dataset_path: str = os.getenv("CADASTRE_DATASET_PATH", "")
match_confidence_floor: float = float(os.getenv("MATCH_CONFIDENCE_FLOOR", "0.7"))
```

## Resolver service

A `SpatialBackend` protocol keeps the resolver unit-testable, but **PostGIS is the only real
implementation** — spatial predicates run as `ST_Contains` / `ST_Intersects` via geoalchemy2:

```python
# backend.py
class SpatialBackend(Protocol):
    def parcel_at(self, lon: float, lat: float) -> list[Parcel]: ...           # may return >1
    def features_intersecting(self, parcel: Parcel) -> list[PlanningLayerFeature]: ...

class PostgisBackend:
    def __init__(self, db: Session):
        self.db = db
    def parcel_at(self, lon, lat):
        pt = func.ST_SetSRID(func.ST_MakePoint(lon, lat), GDA2020)
        return list(self.db.scalars(select(Parcel).where(func.ST_Contains(Parcel.geom, pt))))
    def features_intersecting(self, parcel):
        return list(self.db.scalars(
            select(PlanningLayerFeature).where(func.ST_Intersects(PlanningLayerFeature.geom, parcel.geom))))
```

```python
# resolver.py
@dataclass
class AddressMatch:
    address: str
    lon: float
    lat: float
    gnaf_pid: str | None
    confidence: float

class SpatialResolver:
    def __init__(self, db: Session, backend: SpatialBackend | None = None):
        self.db = db
        self.backend = backend or PostgisBackend(db)

    def resolve(self, *, address: str | None = None,
                lon: float | None = None, lat: float | None = None) -> ApplicabilityContext:
        match = self._geocode(address) if address else AddressMatch(address or "", lon, lat, None, 1.0)
        parcels = self.backend.parcel_at(match.lon, match.lat)
        if not parcels:
            return ApplicabilityContext.unresolved(match, reason="no_parcel_match")
        if len(parcels) > 1 or match.confidence < get_settings().match_confidence_floor:
            return ApplicabilityContext.ambiguous(match, parcels)   # needs_human_review=True
        parcel = parcels[0]
        feats = self.backend.features_intersecting(parcel)
        return ApplicabilityContext.from_features(match, parcel, feats)

    def _geocode(self, address: str) -> AddressMatch:
        ...  # exact/fuzzy lookup against AddressPoint (G-NAF); or Geoscape API if configured
```

`ApplicabilityContext.from_features` maps layer hits to fields: `layer_type="zone"` → `zoning` +
`r_code_density` (parsed from `code` like `R40`); `region_scheme` from the region-scheme layer;
everything else into `overlays`; `bushfire`/`heritage`/`airport` set `hazard_flags`. Every populated
field appends a `Citation` built from the feature's `source_version_id` — so the context is
self-documenting for the eventual "rule card."

**Persistence + integration** with the existing `ProjectService` flow:

```python
# service.py
class SpatialService:
    def __init__(self, db: Session):
        self.db = db
        self.resolver = SpatialResolver(db)

    def resolve_and_write(self, project_id: str, req: PropertyResolveRequest) -> Property:
        ctx = self.resolver.resolve(address=req.address, lon=req.lon, lat=req.lat)
        prop = self.db.scalar(select(Property).where(Property.project_id == project_id)) \
               or Property(project_id=project_id, address=ctx.address)
        if not ctx.needs_human_review:
            prop.address = ctx.address
            prop.zoning = ctx.zoning
            prop.lot_area_m2 = ctx.lot_area_m2
            prop.overlays_json = to_json([o.label for o in ctx.overlays])
            prop.planning_scheme = ctx.region_scheme
        self.db.add(prop); self.db.flush()
        for o in ctx.overlays:
            self.db.add(PlanningOverlay(project_id=project_id, overlay_type=o.overlay_type,
                                        label=o.label, source_url=None, detected_by="spatial"))
        record_audit(self.db, action="property.resolved", target_type="property",
                     target_id=prop.id, project_id=project_id,
                     metadata={"match_confidence": ctx.match_confidence,
                               "needs_human_review": ctx.needs_human_review,
                               "parcel_id": ctx.parcel_id})
        return prop
```

This reuses `PlanningOverlay.detected_by` (today defaults to `"manual"`) to distinguish
spatially-derived overlays from hand-entered ones — no schema change to that table.

## Data loading (worker-side)

Loading is two robust steps: a fast bulk geometry load, then an app-side mapping that attaches
provenance. This keeps Python out of the heavy lifting (the end-user benefit: reliable statewide
coverage), while the `SourceDocument` + `SourceVersion` discipline is preserved.

**Step 1 — provenance first (app code).** Create the dataset edition via the existing ingestion
service so the load is versioned and citable:

```python
src = ingestion.upsert_source(db, title="Landgate Cadastre", authority="Landgate",
                              source_type="map_layer", access_type="licensed", ...)
ver = ingestion.add_version(db, src, version_label="2026-05", retrieved_at=...)
```

**Step 2 — bulk load with `ogr2ogr` into a staging table** (reprojects to GDA2020, streams, no
Python memory pressure):

```bash
ogr2ogr -f PostgreSQL PG:"$DATABASE_URL" cadastre.gpkg \
        -nln stg_cadastre -t_srs EPSG:7844 -nlt MULTIPOLYGON \
        -lco GEOMETRY_NAME=geom -overwrite
```

**Step 3 — map staging → `parcels`** with our id format, provenance, and area in MGA Zone 50. Ids and
timestamps are set in SQL because `new_id()`/`TimestampMixin` defaults are Python-side and don't fire
on bulk `INSERT … SELECT`:

```sql
INSERT INTO parcels (id, lot_plan, local_government, area_m2, geom, source_version_id,
                     attrs_json, created_at, updated_at)
SELECT 'pcl_' || replace(gen_random_uuid()::text, '-', ''),
       lotplan, lga,
       ST_Area(ST_Transform(geom, 7850)),     -- metres²
       ST_Multi(geom), :ver_id, '{}', now(), now()
FROM stg_cadastre;
```

**Large / GeoParquet datasets — DuckDB-spatial** does the read + reproject + write in one pass and can
write straight to PostGIS via its `postgres` extension:

```python
con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial; INSTALL postgres; LOAD postgres;")
con.execute("ATTACH :pg AS pg (TYPE POSTGRES);", {"pg": PG_DSN})
con.execute("""
  INSERT INTO pg.parcels BY NAME
  SELECT 'pcl_' || replace(uuid()::varchar,'-','') AS id,
         lotplan AS lot_plan, lga AS local_government,
         ST_Area(ST_Transform(geom,'EPSG:7844','EPSG:7850')) AS area_m2,
         ST_Multi(geom) AS geom, :ver AS source_version_id
  FROM ST_Read('cadastre.parquet');
""", {"ver": ver_id})
```

Datasets, tiered per `SOURCE_GOVERNANCE.md`: **Tier 1** G-NAF (open, geocoding), Landgate cadastre
(parcels), PlanWA/DPLH layers (zones, region scheme, overlays), DFES bushfire-prone areas; **Tier 2
(optional accelerant)** Geoscape — used to shortcut integration, never as final authority.

## API surface

Two endpoints, matching the existing router style (`Depends(get_db)`, dict return via a serializer
like `property_to_dict`):

```python
@router.post("/properties/resolve", response_model=ApplicabilityContext)
def resolve_property(payload: PropertyResolveRequest, db: Session = Depends(get_db)) -> dict:
    return SpatialResolver(db).resolve(**payload.model_dump()).to_dict()

@router.post("/projects/{project_id}/property/resolve", response_model=PropertyRead)
def resolve_and_set_property(project_id: str, payload: PropertyResolveRequest,
                             db: Session = Depends(get_db)) -> dict:
    prop = SpatialService(db).resolve_and_write(project_id, payload)
    db.commit()
    return property_to_dict(prop)
```

New schemas in `shared_schemas/schemas.py` (reusing the existing `Citation`):

```python
class PropertyResolveRequest(BaseModel):
    address: str | None = None
    lon: float | None = None
    lat: float | None = None

    @model_validator(mode="after")
    def _one_input(self):
        if not self.address and (self.lon is None or self.lat is None):
            raise ValueError("provide address or lon+lat")
        return self

class OverlayHit(BaseModel):
    overlay_type: str
    code: str | None = None
    label: str
    source_version_id: str | None = None

class ApplicabilityContext(BaseModel):
    parcel_id: str | None = None
    lot_plan: str | None = None
    local_government: str | None = None
    zoning: str | None = None
    r_code_density: str | None = None
    region_scheme: str | None = None
    lot_area_m2: float | None = None
    overlays: list[OverlayHit] = Field(default_factory=list)
    hazard_flags: dict[str, bool] = Field(default_factory=dict)
    match_confidence: float = 0.0
    needs_human_review: bool = True
    provenance: list[Citation] = Field(default_factory=list)
```

## Confidence, ambiguity & safety

The spatial layer must fail the same way the rest of the product does — toward review, never toward
a confident guess:

- **No parcel match** → `needs_human_review=True`, authoritative fields left unwritten.
- **Multiple candidate parcels** (strata, boundary point, overlapping cadastre) → `ambiguous`, return
  all candidates for human selection; do not pick one.
- **Geocode below `match_confidence_floor`** → review, and if written at all, tag overlays
  `detected_by="spatial_low_confidence"`.
- **Manual override preserved.** The existing `PUT /projects/{id}/property` path is untouched;
  `detected_by` records provenance so a human edit always wins.
- **Provenance required.** No derived field is set without a `source_version_id`; the resolver cannot
  emit a zone or overlay it can't cite — the spatial analogue of cite-or-refuse.

## Testing plan

- **Resolver unit tests (mock backend):** feed `SpatialResolver` a fake `SpatialBackend` returning 0,
  1, or 2 parcels and assert `unresolved` / resolved / `ambiguous` branches and the confidence floor —
  fast, no DB.
- **Integration (ephemeral PostGIS via `testcontainers` or the compose service):** seed a few real
  parcels + zone/bushfire polygons as WKT, assert `resolve()` returns expected zoning + hazard flags,
  and that `resolve_and_write` creates `PlanningOverlay` rows with `detected_by="spatial"` plus an
  audit event. This runs the **same PostgisBackend prod uses**.
- **Gold set (feeds G7):** `tests/gold/addresses.jsonl` of known WA addresses → expected
  parcel/zone/overlays; report parcel-match accuracy and overlay precision/recall as the spatial
  eval track.

## Rollout (ordered)

1. Add deps (`geoalchemy2`, `shapely`, `pyproj`, `duckdb`) + GDAL in the worker image; switch compose
   to `postgis/postgis`; add a PostGIS service to CI; register `packages/spatial`. *(S)*
2. Add the three models + `0002_spatial` migration; confirm migrate + GiST indexes on PostGIS. *(S)*
3. `PostgisBackend` + `SpatialResolver` + resolver unit tests (mock backend). *(M)*
4. Loaders (`ogr2ogr` + DuckDB) + ingest G-NAF + one LGA's cadastre/zones as a vertical slice. *(M)*
5. Integration tests against the slice on ephemeral PostGIS. *(M)*
6. API endpoints + `SpatialService` writing `Property`/`PlanningOverlay`. *(S)*
7. Gold set + accuracy report; expand LGA coverage. *(M, ongoing)*

Total ≈ **L (6–12 wks)** for one engineer, excluding data-licensing lead time.

## Open decisions

- **Licensing is the critical path:** Landgate cadastre and some PlanWA layers have access/licence
  terms to clear before ingestion — start this in parallel with step 1.
- **Geocoder:** self-host G-NAF (free, quarterly, more ops) vs. Geoscape API (faster, paid). The
  `geocoder` config switch lets you defer this.
- **CRS for non-metro WA:** Perth uses MGA Zone 50; statewide coverage needs Zones 49/51 for area
  math — pick per-parcel zone selection if you expand beyond the metro.

*(Resolved: PostGIS for dev/CI/prod; DuckDB/`ogr2ogr` for loading — see "Decisions taken" above.)*
