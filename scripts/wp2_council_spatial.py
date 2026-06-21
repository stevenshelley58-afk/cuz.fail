#!/usr/bin/env python3
"""WP2 — load cadastre + planning_features for one council bbox.

Re-uses the SLIP public ArcGIS endpoints from wp2_spatial_load.py but fetches
only the envelope of the requested LGA.  Run on the VPS host.

Example:
    python3 /srv/draftcheck/app/scripts/wp2_council_spatial.py --council 'City of Melville'
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://services.slip.wa.gov.au/public/rest/services"
PSQL = [
    "docker", "compose", "exec", "-T", "db",
    "psql", "-v", "ON_ERROR_STOP=1", "-U", "draftcheck", "-d", "draftcheck",
]
COMPOSE_DIR = "/srv/draftcheck/app/infra/v3"
ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
USER_ID = "393277fe-3581-4a29-b394-a41cfc26f01b"
TODAY = datetime.now(timezone.utc)
VERSION = TODAY.strftime("%Y-%m-%d")
REFRESH_DUE = (TODAY + timedelta(days=90)).strftime("%Y-%m-%d")


def psql(sql: str, input_data: str | None = None) -> str:
    full_input = sql if input_data is None else sql + input_data
    r = subprocess.run(PSQL, cwd=COMPOSE_DIR, input=full_input,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr[-4000:]}")
    return r.stdout


def fetch_json(url: str, attempts: int = 3) -> dict:
    last = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=300) as f:
                data = json.loads(f.read().decode())
            if "error" in data:
                raise RuntimeError(f"arcgis error: {data['error']}")
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"fetch failed after {attempts} attempts: {url}: {last}")


def fetch_features(layer_url: str, where: str = "1=1", bbox: tuple | None = None,
                   page: int = 2000) -> list[dict]:
    feats = []
    offset = 0
    while True:
        params = {
            "where": where, "outFields": "*", "f": "geojson",
            "resultOffset": offset, "resultRecordCount": page,
            "orderByFields": "objectid",
        }
        if bbox:
            params.update({
                "geometry": ",".join(str(c) for c in bbox),
                "geometryType": "esriGeometryEnvelope",
                "inSR": "7844", "spatialRel": "esriSpatialRelIntersects",
            })
        url = f"{layer_url}/query?{urllib.parse.urlencode(params)}"
        data = fetch_json(url)
        batch = data.get("features", [])
        feats.extend(batch)
        print(f"    fetched {len(feats)} features", flush=True)
        if not batch:
            break
        offset += len(batch)
    cparams = {"where": where, "returnCountOnly": "true", "f": "json"}
    if bbox:
        cparams.update({
            "geometry": ",".join(str(c) for c in bbox),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "7844", "spatialRel": "esriSpatialRelIntersects",
        })
    expected = fetch_json(f"{layer_url}/query?{urllib.parse.urlencode(cparams)}").get("count")
    print(f"    server count={expected}, fetched={len(feats)}", flush=True)
    if expected is not None and len(feats) != expected:
        tolerance = max(100, int(expected * 0.01)) if expected else 100
        if abs(len(feats) - expected) > tolerance:
            raise RuntimeError(f"incomplete fetch: got {len(feats)}, server says {expected}")
        print(f"    WARNING: count mismatch within tolerance ({tolerance}); continuing", flush=True)
    return feats


def lit(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def csv_stream(feats: list[dict]) -> str:
    buf = io.StringIO()
    for f in feats:
        geom = f.get("geometry")
        if not geom:
            continue
        buf.write(_esc(json.dumps(f.get("properties") or {})))
        buf.write("\t")
        buf.write(_esc(json.dumps(geom)))
        buf.write("\n")
    return buf.getvalue()


DATASETS = {
    "lgate-001": {
        "name": "Cadastre (No Attributes) (LGATE-001)",
        "provider": "Landgate (SLIP)",
        "licence": "Custom (Other) - Landgate terms; commercial use unconfirmed",
        "licence_status": "review",
        "layer": f"{BASE}/SLIP_Public_Services/Property_and_Planning/MapServer/2",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/cadastre-no-attributes-lgate-001",
    },
    "dplh-071": {
        "name": "Local Planning Scheme - Zones and Reserves (DPLH-071)",
        "provider": "DPLH (SLIP)",
        "licence": "Custom (Active Acceptance) - DPLH terms",
        "licence_status": "review",
        "layer": f"{BASE}/SLIP_Public_Services/Property_and_Planning/MapServer/112",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-zones-and-reserves",
    },
    "dplh-070": {
        "name": "Local Planning Scheme - R Codes (DPLH-070)",
        "provider": "DPLH (SLIP)",
        "licence": "Custom (Active Acceptance) - DPLH terms",
        "licence_status": "review",
        "layer": f"{BASE}/SLIP_Public_Services/Property_and_Planning/MapServer/111",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-r-codes",
    },
    "obrm-001": {
        "name": "Bush Fire Prone Areas (OBRM-001)",
        "provider": "DFES / Office of Bushfire Risk Management (SLIP)",
        "licence": "CC-BY 4.0",
        "licence_status": "approved",
        "layer": f"{BASE}/SLIP_Public_Services/Bush_Fire_Prone_Areas/MapServer/17",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/bush-fire-prone-areas",
    },
    "dplh-006": {
        "name": "Heritage Council WA - State Register (DPLH-006)",
        "provider": "Heritage Council WA / DPLH (SLIP)",
        "licence": "Custom (Active Acceptance) - DPLH terms",
        "licence_status": "review",
        "layer": f"{BASE}/SLIP_Public_Services/People_and_Society/MapServer/7",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/heritage-council-wa-state-register-of-heritage-places",
    },
    "dplh-008": {
        "name": "Heritage Council WA - Local Heritage Survey (DPLH-008)",
        "provider": "Heritage Council WA / DPLH (SLIP)",
        "licence": "Custom (Active Acceptance) - DPLH terms",
        "licence_status": "review",
        "layer": f"{BASE}/SLIP_Public_Services/People_and_Society/MapServer/9",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/heritage-council-local-heritage-surveys",
    },
    "dplh-090": {
        "name": "Heritage List (DPLH-090)",
        "provider": "DPLH (SLIP)",
        "licence": "Custom (Active Acceptance) - DPLH terms",
        "licence_status": "review",
        "layer": f"{BASE}/SLIP_Public_Services/People_and_Society/MapServer/16",
        "catalogue": "https://catalogue.data.wa.gov.au/dataset/heritage-list",
    },
}

GEOM_EXPR = ("ST_Multi(ST_CollectionExtract(ST_MakeValid("
             "ST_SetSRID(ST_GeomFromGeoJSON(gj), 7844)), 3))")


def upsert_dataset(key: str, extra_meta: dict) -> None:
    d = DATASETS[key]
    meta = {"endpoint": d["layer"], "catalogue": d["catalogue"],
            "native_crs": "EPSG:7844", **extra_meta}
    sql = f"""
INSERT INTO spatial_datasets (id, dataset_id, name, provider, licence, licence_status,
    approval_status, source_crs, version, fetched_at, refresh_due, metadata_json,
    created_at, updated_at)
VALUES (gen_random_uuid(), {lit(key)}, {lit(d['name'])}, {lit(d['provider'])},
    {lit(d['licence'])}, {lit(d['licence_status'])}, 'pending_review', 'EPSG:7844',
    {lit(VERSION)}, now(), {lit(REFRESH_DUE)}::timestamptz, {lit(json.dumps(meta))}::jsonb,
    now(), now())
ON CONFLICT (dataset_id, version) DO UPDATE SET
    fetched_at = now(), licence = EXCLUDED.licence,
    licence_status = EXCLUDED.licence_status,
    metadata_json = EXCLUDED.metadata_json, updated_at = now();
"""
    psql(sql)


def log_fetch(key: str, n: int, status: str, error: str | None = None) -> None:
    d = DATASETS[key]
    meta = json.dumps({"dataset_id": key, "endpoint": d["layer"],
                       "feature_count": n, "version": VERSION})
    err = "NULL" if error is None else lit(error[:2000])
    sql = f"""
INSERT INTO source_documents (id, org_id, title, jurisdiction, authority,
    source_type, canonical_url, access_type, status, metadata_json, created_at, updated_at)
VALUES (gen_random_uuid(), {lit(ORG_ID)}::uuid, {lit(d['name'])}, 'WA',
    {lit(d['provider'])}, 'spatial_dataset', {lit(d['layer'])}, 'public', 'active',
    '{{}}'::jsonb, now(), now())
ON CONFLICT (authority, canonical_url) DO UPDATE SET updated_at = now();
INSERT INTO source_fetch_log (id, org_id, source_id, requested_by_user_id, fetch_kind,
    status, requested_at, completed_at, error, metadata_json)
SELECT gen_random_uuid(), {lit(ORG_ID)}::uuid, sd.id, {lit(USER_ID)}::uuid,
    'spatial_layer', {lit(status)}, now(), now(), {err}, {lit(meta)}::jsonb
FROM source_documents sd
WHERE sd.authority = {lit(d['provider'])} AND sd.canonical_url = {lit(d['layer'])};
"""
    psql(sql)


def load_features(key: str, feats: list[dict], target_sql: str) -> None:
    head = """
BEGIN;
CREATE TEMP TABLE _stage (props jsonb, gj text);
COPY _stage (props, gj) FROM STDIN;
"""
    tail = f"""\\.

WITH ds AS (
    SELECT id FROM spatial_datasets
    WHERE dataset_id = {lit(key)} AND version = {lit(VERSION)}
)
SELECT set_config('wp2.ds_id', (SELECT id::text FROM ds), true);
{target_sql}
COMMIT;
"""
    psql(head + csv_stream(feats) + tail)


def council_bbox(council_name: str) -> tuple[float, ...]:
    out = psql(f"""
SELECT ST_XMin(e)||','||ST_YMin(e)||','||ST_XMax(e)||','||ST_YMax(e)
FROM (SELECT ST_Envelope(geom) e FROM lg_areas WHERE name ILIKE {lit(f'%{council_name}%')} LIMIT 1) s;
""")
    lines = [ln.strip() for ln in out.splitlines() if "," in ln]
    if not lines:
        raise SystemExit(f"LGA boundary not found for {council_name}")
    return tuple(float(x) for x in lines[0].split(","))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True, help="council name substring matching lg_areas.name")
    args = ap.parse_args()

    bbox = council_bbox(args.council)
    print(f"{args.council} bbox: {bbox}", flush=True)

    report = {}

    # Cadastre
    key = "lgate-001"
    print(f"== {key}", flush=True)
    upsert_dataset(key, {"extent": args.council, "bbox": bbox})
    feats = fetch_features(DATASETS[key]["layer"], bbox=bbox)
    load_features(key, feats, """
DELETE FROM parcels WHERE spatial_dataset_id = current_setting('wp2.ds_id')::uuid;
INSERT INTO parcels (id, cadastre_id, lot_plan, local_government, area_m2,
    spatial_dataset_id, geom, metadata_json, created_at, updated_at)
SELECT gen_random_uuid(), props->>'objectid', NULL,
    COALESCE(lga.name, 'Unknown'),
    ST_Area(g::geography), current_setting('wp2.ds_id')::uuid, g, props, now(), now()
FROM (SELECT props, """ + GEOM_EXPR + """ AS g FROM _stage) s
LEFT JOIN LATERAL (
    SELECT name
    FROM lg_areas
    WHERE ST_Covers(lg_areas.geom, ST_PointOnSurface(g))
    ORDER BY ST_Area(lg_areas.geom)
    LIMIT 1
) lga ON true
WHERE NOT ST_IsEmpty(g);
""")
    log_fetch(key, len(feats), "succeeded")
    report[key] = len(feats)

    # Planning features
    pf = [
        ("dplh-071", "zone",
         "COALESCE(props->>'zone', props->>'label')",
         "COALESCE(props->>'label_desc', props->>'zone', 'Unknown zone')"),
        ("dplh-070", "r_code",
         "COALESCE(props->>'r_code', props->>'density_code', props->>'rcode_no')",
         "'Residential Design Code ' || COALESCE(props->>'r_code', props->>'density_code', props->>'rcode_no')"),
        ("obrm-001", "bushfire",
         "props->>'type'",
         "COALESCE('Bush Fire Prone Area designated ' || (props->>'designation'), 'Bush Fire Prone Area')"),
        ("dplh-006", "heritage",
         "props->>'place_no'",
         "COALESCE(props->>'place_name', 'State Register place ' || (props->>'place_no'))"),
        ("dplh-008", "heritage",
         "props->>'place_no'",
         "COALESCE(props->>'place_name', 'Local Heritage Survey place ' || (props->>'place_no'))"),
        ("dplh-090", "heritage",
         "props->>'place_no'",
         "COALESCE(props->>'place_name', 'Heritage List place ' || (props->>'place_no'))"),
    ]
    for key, layer_type, code_expr, label_expr in pf:
        print(f"== {key}", flush=True)
        upsert_dataset(key, {"extent": args.council, "bbox": bbox,
                             "layer_type": layer_type})
        try:
            feats = fetch_features(DATASETS[key]["layer"], bbox=bbox)
        except Exception as e:  # noqa: BLE001
            log_fetch(key, 0, "failed", str(e))
            psql(f"UPDATE spatial_datasets SET licence_status='blocked', updated_at=now() "
                 f"WHERE dataset_id={lit(key)} AND version={lit(VERSION)};")
            report[key] = f"BLOCKED: {e}"
            continue
        load_features(key, feats, f"""
DELETE FROM planning_features WHERE spatial_dataset_id = current_setting('wp2.ds_id')::uuid;
INSERT INTO planning_features (id, layer_type, code, label, spatial_dataset_id, geom,
    metadata_json, created_at, updated_at)
SELECT gen_random_uuid(), {lit(layer_type)}, {code_expr}, {label_expr},
    current_setting('wp2.ds_id')::uuid, g, props, now(), now()
FROM (SELECT props, {GEOM_EXPR} AS g FROM _stage) s
WHERE NOT ST_IsEmpty(g);
""")
        log_fetch(key, len(feats), "succeeded")
        report[key] = len(feats)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
