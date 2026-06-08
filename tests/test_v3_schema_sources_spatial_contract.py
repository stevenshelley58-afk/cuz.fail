from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy import ColumnDefault

from draftcheck.db import models as models_module
from draftcheck.db.models import (
    Base,
    GDA2020_SRID,
    SOURCE_CHUNK_EMBEDDING_DIMENSION,
    Geometry,
)


def column_names(table_name: str) -> set[str]:
    return set(Base.metadata.tables[table_name].c.keys())


def test_v3_sources_spatial_foundation_tables_present() -> None:
    tables = Base.metadata.tables

    assert {
        "projects",
        "properties",
        "proposals",
        "sources",
        "source_versions",
        "source_chunks",
        "source_citations",
        "source_reviews",
        "source_fetch_log",
        "artifacts",
        "job_traces",
        "spend_events",
        "spatial_datasets",
        "lg_areas",
        "address_points",
        "parcels",
        "planning_features",
        "property_facts",
    } <= set(tables)


def test_v3_source_artifact_trace_and_spend_columns() -> None:
    tables = Base.metadata.tables

    assert {
        "source_id",
        "sha256",
        "storage_manifest_json",
        "licence",
        "licence_status",
        "review_status",
        "superseded_by_version_id",
    } <= column_names("source_versions")

    assert {
        "source_version_id",
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "embedding",
    } <= column_names("source_chunks")

    assert {"subject_type", "subject_id", "kind", "storage_path", "sha256"} <= column_names("artifacts")
    assert {
        "org_id",
        "source_id",
        "source_version_id",
        "reviewer_user_id",
        "review_status",
        "licence_status",
        "reviewed_at",
    } <= column_names("source_reviews")
    assert {
        "org_id",
        "source_id",
        "source_version_id",
        "requested_by_user_id",
        "fetch_kind",
        "status",
        "requested_at",
        "completed_at",
    } <= column_names("source_fetch_log")
    assert {
        "job_id",
        "adapter_name",
        "model",
        "skill_version_id",
        "input_artifact_ids_json",
        "output_artifact_ids_json",
        "status",
        "spend_cap_cents",
        "spend_cap_tokens",
    } <= set(tables["job_traces"].c.keys())
    assert {"job_trace_id", "provider", "model", "total_tokens", "cost_usd"} <= column_names("spend_events")


def test_v3_spatial_and_property_fact_columns() -> None:
    tables = Base.metadata.tables

    assert {"dataset_id", "licence", "licence_status", "source_crs", "version", "fetched_at"} <= column_names(
        "spatial_datasets",
    )
    assert {"name", "lg_code", "spatial_dataset_id", "source_version_id", "geom"} <= column_names("lg_areas")
    assert {"gnaf_pid", "address_text", "parcel_id", "spatial_dataset_id", "geom"} <= set(
        tables["address_points"].c.keys(),
    )
    assert {"cadastre_id", "lot_plan", "area_m2", "spatial_dataset_id", "geom"} <= column_names("parcels")
    assert {"layer_type", "code", "label", "spatial_dataset_id", "geom"} <= set(
        tables["planning_features"].c.keys(),
    )
    assert {
        "org_id",
        "fact_type",
        "value_json",
        "provenance_json",
        "source_dataset_id",
        "source_version_id",
        "planning_feature_id",
        "parcel_id",
        "review_status",
    } <= column_names("property_facts")

    for table_name in ("source_reviews", "source_fetch_log", "job_traces", "spend_events", "property_facts"):
        table = tables[table_name]
        assert "org_id" in table.c
        assert table.c.org_id.foreign_keys

    job_trace_table = tables["job_traces"]
    assert job_trace_table.c.job_id.nullable is False
    assert job_trace_table.c.skill_version_id.nullable is False
    assert job_trace_table.c.input_artifact_ids_json.nullable is False
    assert job_trace_table.c.output_artifact_ids_json.nullable is False


def test_v3_project_property_and_proposal_columns_are_tenant_scoped() -> None:
    assert {
        "org_id",
        "created_by_user_id",
        "name",
        "status",
        "as_of_date",
        "assessment_basis",
        "metadata_json",
    } <= column_names("projects")
    assert {
        "org_id",
        "project_id",
        "address_text",
        "resolution_status",
        "address_point_id",
        "parcel_id",
        "target_crs",
        "resolution_metadata_json",
    } <= column_names("properties")
    assert {
        "org_id",
        "project_id",
        "proposal_type",
        "dwelling_type",
        "building_class",
        "work_type",
        "new_or_existing",
        "lot_type",
        "primary_street_confirmed",
        "metadata_json",
    } <= column_names("proposals")

    tables = Base.metadata.tables
    for table_name in ("projects", "properties", "proposals"):
        table = tables[table_name]
        assert "org_id" in table.c
        assert table.c.org_id.foreign_keys


def test_v3_source_chunk_vector_dimension_is_pinned() -> None:
    chunk_table = Base.metadata.tables["source_chunks"]
    embedding_dimension_default = cast(ColumnDefault, chunk_table.c.embedding_dimension.default)

    assert chunk_table.c.embedding_provider.nullable is False
    assert chunk_table.c.embedding_model.nullable is False
    assert embedding_dimension_default is not None
    assert embedding_dimension_default.arg == SOURCE_CHUNK_EMBEDDING_DIMENSION
    assert chunk_table.c.embedding.nullable is False
    assert getattr(chunk_table.c.embedding.type, "dim", None) == SOURCE_CHUNK_EMBEDDING_DIMENSION


def test_v3_spatial_geometry_types_use_gda2020() -> None:
    tables = Base.metadata.tables

    address_geom = cast(Geometry, tables["address_points"].c.geom.type)
    parcel_geom = cast(Geometry, tables["parcels"].c.geom.type)
    planning_geom = cast(Geometry, tables["planning_features"].c.geom.type)
    lg_area_geom = cast(Geometry, tables["lg_areas"].c.geom.type)

    assert address_geom.get_col_spec() == f"geometry(Point,{GDA2020_SRID})"
    assert parcel_geom.get_col_spec() == f"geometry(MultiPolygon,{GDA2020_SRID})"
    assert planning_geom.get_col_spec() == f"geometry(MultiPolygon,{GDA2020_SRID})"
    assert lg_area_geom.get_col_spec() == f"geometry(MultiPolygon,{GDA2020_SRID})"


def test_v3_models_have_no_schema_creation_or_init_side_effects() -> None:
    models_path = Path(models_module.__file__)
    source = models_path.read_text(encoding="utf-8")

    assert ".create_all(" not in source
    assert "init_database(" not in source
    assert "init_db(" not in source
    assert "create_engine(" not in source
    assert getattr(Base.metadata, "bind", None) is None
