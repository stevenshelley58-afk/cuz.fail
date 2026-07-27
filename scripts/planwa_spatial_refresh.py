#!/usr/bin/env python3
"""Version and refresh the official PlanWA planning layers in PostGIS.

This is a host-side production utility: it downloads public ArcGIS GeoJSON,
verifies the server count, creates immutable source/dataset versions, and
atomically replaces the feature rows for the new version.  The application
queries only the newest version of each logical dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

BASE = (
    "https://public-services.slip.wa.gov.au/public/rest/services/"
    "SLIP_Public_Services/Property_and_Planning/MapServer"
)
COMPOSE_DIR = os.environ.get("DRAFTCHECK_COMPOSE_DIR", "/srv/draftcheck/app/infra/v3")
PSQL = [
    "docker",
    "compose",
    "exec",
    "-T",
    "db",
    "psql",
    "-q",
    "-At",
    "-v",
    "ON_ERROR_STOP=1",
    "-U",
    os.environ.get("POSTGRES_USER", "draftcheck"),
    "-d",
    os.environ.get("POSTGRES_DB", "draftcheck"),
]
ORG_ID = os.environ.get("DRAFTCHECK_OPERATOR_ORG_ID", "1d31c315-5087-47df-a8d4-ebfd08efad5d")
USER_ID = os.environ.get(
    "DRAFTCHECK_OPERATOR_USER_ID",
    "393277fe-3581-4a29-b394-a41cfc26f01b",
)
LICENCE = "DPLH public ArcGIS service; Creative Commons Non-Commercial (Any)"
GEOM_EXPR = (
    "ST_Multi(ST_CollectionExtract(ST_MakeValid("
    "ST_SetSRID(ST_GeomFromGeoJSON(gj), 7844)), 3))"
)


@dataclass(frozen=True)
class Layer:
    dataset_id: str
    layer_id: int
    name: str
    fact_type: str
    code_field: str
    label_field: str
    catalogue: str

    @property
    def url(self) -> str:
        return f"{BASE}/{self.layer_id}"


LAYERS: tuple[Layer, ...] = (
    Layer(
        "dplh-024",
        32,
        "Structure Plan Boundaries (DPLH-024)",
        "structure_plan",
        "filenumber",
        "alt_title",
        "https://catalogue.data.wa.gov.au/dataset/structure-plan-boundaries-dop-082",
    ),
    Layer(
        "dplh-068",
        109,
        "Local Planning Scheme - Special Area (DPLH-068)",
        "special_area",
        "special_no",
        "special_na",
        "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-special-area-dop-090",
    ),
    Layer(
        "dplh-070",
        111,
        "Local Planning Scheme - R Codes (DPLH-070)",
        "r_code",
        "rcode_no",
        "rcode_no",
        "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-r-codes",
    ),
    Layer(
        "dplh-071",
        112,
        "Local Planning Scheme - Zones and Reserves (DPLH-071)",
        "zone",
        "zone",
        "label_desc",
        "https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-zones-and-reserves",
    ),
)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _copy_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def run_psql(sql: str, copy_data: str | None = None) -> str:
    payload = sql if copy_data is None else sql + copy_data
    result = subprocess.run(
        PSQL,
        cwd=COMPOSE_DIR,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"psql failed: {result.stderr[-4000:]}")
    return result.stdout.strip()


def fetch_json(url: str, *, attempts: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "DraftCheck-WA/planwa-refresh"},
            )
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("error"):
                raise RuntimeError(f"ArcGIS error: {payload['error']}")
            return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"PlanWA fetch failed after {attempts} attempts: {last_error}")


def fetch_features(layer: Layer, *, page_size: int = 4000) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "7844",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "objectid",
        }
        payload = fetch_json(f"{layer.url}/query?{urllib.parse.urlencode(params)}")
        batch = payload.get("features") or []
        if not batch:
            break
        features.extend(batch)
        offset += len(batch)
        print(f"{layer.dataset_id}: fetched {len(features)}", flush=True)

    count_params = {"where": "1=1", "returnCountOnly": "true", "f": "json"}
    expected = fetch_json(
        f"{layer.url}/query?{urllib.parse.urlencode(count_params)}"
    ).get("count")
    if expected is None or int(expected) != len(features):
        raise RuntimeError(
            f"{layer.dataset_id}: incomplete fetch: got {len(features)}, server says {expected}"
        )
    return features


def canonical_digest(features: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        features,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def feature_copy_stream(features: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        properties = feature.get("properties") or {}
        stream.write(_copy_escape(json.dumps(properties, ensure_ascii=True, sort_keys=True)))
        stream.write("\t")
        stream.write(_copy_escape(json.dumps(geometry, ensure_ascii=True, sort_keys=True)))
        stream.write("\n")
    return stream.getvalue()


def register_version(layer: Layer, digest: str, feature_count: int) -> tuple[str, str]:
    fetched_at = datetime.now(timezone.utc)
    version = f"{fetched_at:%Y-%m-%d}-{digest[:12]}"
    refresh_due = fetched_at + timedelta(days=8)
    source_metadata = {
        "official_dataset_id": layer.dataset_id,
        "arcgis_layer_id": layer.layer_id,
        "catalogue": layer.catalogue,
        "refresh_cadence": "weekly",
        "operator_approval_basis": "explicit implementation direction 2026-07-27",
    }
    version_metadata = {
        **source_metadata,
        "endpoint": layer.url,
        "feature_count": feature_count,
        "sha256": digest,
        "source_crs": "EPSG:7844",
    }
    sql = f"""
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM users
        WHERE id = {sql_literal(USER_ID)}::uuid
          AND org_id = {sql_literal(ORG_ID)}::uuid
          AND role::text IN ('owner', 'operator')
    ) THEN
        RAISE EXCEPTION 'Configured PlanWA reviewer is not an owner/operator in the configured org';
    END IF;
END
$$;

INSERT INTO source_documents (
    id, org_id, title, jurisdiction, authority, source_type, canonical_url,
    access_type, status, metadata_json, created_at, updated_at
)
VALUES (
    gen_random_uuid(), {sql_literal(ORG_ID)}::uuid, {sql_literal(layer.name)}, 'WA',
    'Department of Planning, Lands and Heritage', 'spatial_dataset',
    {sql_literal(layer.url)}, 'public', 'active',
    {sql_literal(json.dumps(source_metadata))}::jsonb, now(), now()
)
ON CONFLICT (authority, canonical_url) DO UPDATE SET
    title = EXCLUDED.title,
    metadata_json = source_documents.metadata_json || EXCLUDED.metadata_json,
    updated_at = now();

INSERT INTO source_versions (
    id, source_id, version_label, sha256, storage_manifest_json, licence,
    licence_status, review_status, fetched_at, metadata_json, created_at, updated_at
)
SELECT
    gen_random_uuid(), sd.id, {sql_literal(version)}, {sql_literal(digest)},
    {sql_literal(json.dumps({"kind": "arcgis_geojson", "endpoint": layer.url}))}::jsonb,
    {sql_literal(LICENCE)}, 'licensed', 'approved', now(),
    {sql_literal(json.dumps(version_metadata))}::jsonb, now(), now()
FROM source_documents sd
WHERE sd.authority = 'Department of Planning, Lands and Heritage'
  AND sd.canonical_url = {sql_literal(layer.url)}
ON CONFLICT (source_id, sha256) DO UPDATE SET
    fetched_at = now(),
    metadata_json = source_versions.metadata_json || EXCLUDED.metadata_json,
    updated_at = now();

INSERT INTO source_reviews (
    id, org_id, source_id, source_version_id, reviewed_by_user_id,
    review_status, licence_status, notes, reviewed_at, decision_metadata_json
)
SELECT
    gen_random_uuid(), {sql_literal(ORG_ID)}::uuid, sd.id, sv.id,
    {sql_literal(USER_ID)}::uuid, 'approved', 'licensed',
    'Operator-directed PlanWA spatial source approval recorded 2026-07-27.',
    now(),
    {sql_literal(json.dumps({"basis": "explicit operator implementation direction", "dataset_id": layer.dataset_id}))}::jsonb
FROM source_versions sv
JOIN source_documents sd ON sd.id = sv.source_id
JOIN users reviewer ON reviewer.id = {sql_literal(USER_ID)}::uuid
WHERE sd.canonical_url = {sql_literal(layer.url)}
  AND sv.sha256 = {sql_literal(digest)}
  AND reviewer.org_id = {sql_literal(ORG_ID)}::uuid
  AND reviewer.role::text IN ('owner', 'operator')
  AND NOT EXISTS (
      SELECT 1 FROM source_reviews sr
      WHERE sr.source_version_id = sv.id
        AND sr.review_status = 'approved'
        AND sr.licence_status = 'licensed'
  );

INSERT INTO audit_events (
    id, org_id, actor_user_id, event_type, action, subject_type, subject_id,
    before_json, after_json, metadata_json, created_at
)
SELECT
    gen_random_uuid(), {sql_literal(ORG_ID)}::uuid, {sql_literal(USER_ID)}::uuid,
    'source_review', 'approve_planwa_spatial_version', 'source_version', sv.id,
    '{{}}'::jsonb,
    jsonb_build_object('review_status', 'approved', 'licence_status', 'licensed'),
    {sql_literal(json.dumps({"dataset_id": layer.dataset_id, "sha256": digest}))}::jsonb,
    now()
FROM source_versions sv
JOIN source_documents sd ON sd.id = sv.source_id
WHERE sd.canonical_url = {sql_literal(layer.url)}
  AND sv.sha256 = {sql_literal(digest)}
  AND NOT EXISTS (
      SELECT 1 FROM audit_events ae
      WHERE ae.subject_type = 'source_version'
        AND ae.subject_id = sv.id
        AND ae.action = 'approve_planwa_spatial_version'
  );

UPDATE source_versions older
SET superseded_by_version_id = current.id, updated_at = now()
FROM source_versions current
JOIN source_documents sd ON sd.id = current.source_id
WHERE older.source_id = current.source_id
  AND older.id <> current.id
  AND older.superseded_by_version_id IS NULL
  AND current.sha256 = {sql_literal(digest)}
  AND sd.canonical_url = {sql_literal(layer.url)};

INSERT INTO spatial_datasets (
    id, dataset_id, name, provider, licence, licence_status, approval_status,
    source_crs, version, source_version_id, fetched_at, refresh_due,
    metadata_json, created_at, updated_at
)
SELECT
    gen_random_uuid(), {sql_literal(layer.dataset_id)}, {sql_literal(layer.name)},
    'Department of Planning, Lands and Heritage', {sql_literal(LICENCE)},
    'licensed', 'pending_review', 'EPSG:7844', {sql_literal(version)}, sv.id,
    now(), {sql_literal(refresh_due.isoformat())}::timestamptz,
    {sql_literal(json.dumps(version_metadata))}::jsonb, now(), now()
FROM source_versions sv
JOIN source_documents sd ON sd.id = sv.source_id
WHERE sd.canonical_url = {sql_literal(layer.url)}
  AND sv.sha256 = {sql_literal(digest)}
ON CONFLICT (dataset_id, version) DO UPDATE SET
    source_version_id = EXCLUDED.source_version_id,
    fetched_at = now(),
    refresh_due = EXCLUDED.refresh_due,
    metadata_json = spatial_datasets.metadata_json || EXCLUDED.metadata_json,
    updated_at = now();
COMMIT;

SELECT sv.id::text || '|' || ds.id::text
FROM source_versions sv
JOIN source_documents sd ON sd.id = sv.source_id
JOIN spatial_datasets ds ON ds.source_version_id = sv.id
WHERE sd.canonical_url = {sql_literal(layer.url)}
  AND sv.sha256 = {sql_literal(digest)}
  AND ds.dataset_id = {sql_literal(layer.dataset_id)}
  AND ds.version = {sql_literal(version)}
LIMIT 1;
"""
    output_lines = [line for line in run_psql(sql).splitlines() if "|" in line]
    identifiers = output_lines[-1].split("|") if output_lines else []
    if len(identifiers) != 2:
        raise RuntimeError(f"{layer.dataset_id}: failed to resolve registered version IDs")
    return identifiers[0], identifiers[1]


def load_version(
    layer: Layer,
    *,
    source_version_id: str,
    spatial_dataset_id: str,
    features: list[dict[str, Any]],
) -> None:
    fact_value = (
        "jsonb_build_object("
        f"'code', props->>{sql_literal(layer.code_field)}, "
        f"'label', COALESCE(props->>{sql_literal(layer.label_field)}, "
        f"props->>{sql_literal(layer.code_field)}), "
        f"'layer_type', {sql_literal(layer.fact_type)}, "
        "'status', props->>'status', "
        "'expiry_date', props->'expiry_date', "
        "'objectid', props->'objectid')"
    )
    head = """
BEGIN;
CREATE TEMP TABLE _planwa_stage (props jsonb, gj text);
COPY _planwa_stage (props, gj) FROM STDIN;
"""
    tail = f"""\\.
DELETE FROM planning_features
WHERE spatial_dataset_id = {sql_literal(spatial_dataset_id)}::uuid;

INSERT INTO planning_features (
    id, layer_type, code, label, spatial_dataset_id, source_version_id,
    geom, metadata_json, created_at, updated_at
)
SELECT
    gen_random_uuid(),
    {sql_literal(layer.fact_type)},
    props->>{sql_literal(layer.code_field)},
    COALESCE(
        props->>{sql_literal(layer.label_field)},
        props->>{sql_literal(layer.code_field)},
        {sql_literal(layer.name)}
    ),
    {sql_literal(spatial_dataset_id)}::uuid,
    {sql_literal(source_version_id)}::uuid,
    geometry,
    props || jsonb_build_object(
        'feature_id', COALESCE(props->>'objectid', gen_random_uuid()::text),
        'fact_type', {sql_literal(layer.fact_type)},
        'dataset_id', {sql_literal(layer.dataset_id)},
        'target_crs', 'EPSG:7844',
        'value', {fact_value}
    ),
    now(),
    now()
FROM (
    SELECT props, {GEOM_EXPR} AS geometry
    FROM _planwa_stage
) staged
WHERE NOT ST_IsEmpty(geometry);
UPDATE spatial_datasets
SET approval_status = 'approved', updated_at = now()
WHERE id = {sql_literal(spatial_dataset_id)}::uuid;
COMMIT;
"""
    run_psql(head, feature_copy_stream(features) + tail)


def refresh_layer(layer: Layer) -> dict[str, Any]:
    features = fetch_features(layer)
    digest = canonical_digest(features)
    source_version_id, spatial_dataset_id = register_version(layer, digest, len(features))
    load_version(
        layer,
        source_version_id=source_version_id,
        spatial_dataset_id=spatial_dataset_id,
        features=features,
    )
    return {
        "dataset_id": layer.dataset_id,
        "feature_count": len(features),
        "sha256": digest,
        "source_version_id": source_version_id,
        "spatial_dataset_id": spatial_dataset_id,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--layers",
        nargs="*",
        default=[layer.dataset_id for layer in LAYERS],
        help="Logical dataset IDs to refresh (default: all governed PlanWA layers).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = [layer for layer in LAYERS if layer.dataset_id in set(args.layers)]
    unknown = set(args.layers) - {layer.dataset_id for layer in LAYERS}
    if unknown:
        raise SystemExit(f"Unknown layer IDs: {sorted(unknown)}")
    report: list[dict[str, Any]] = []
    for layer in selected:
        print(f"== Refreshing {layer.dataset_id}: {layer.name}", flush=True)
        report.append(refresh_layer(layer))
    print(json.dumps({"refreshed_at": datetime.now(timezone.utc).isoformat(), "layers": report}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
