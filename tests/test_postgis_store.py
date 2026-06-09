"""Tests for PostGISSpatialDatasetStore.

These tests verify:
1.  ``PostGISSpatialDatasetStore`` implements the same interface as
    ``InMemorySpatialDatasetStore`` (duck-type inspection).
2.  The licence gate blocks UNLICENSED datasets with a clear ValueError.
3.  PostGIS-specific behaviour (requires a real DB) is skipped unless
    ``DATABASE_URL`` is set.
"""

from __future__ import annotations

import inspect
import os

import pytest

from draftcheck.domain.address.spatial import (
    GDA2020_TARGET_CRS,
    AddressPoint,
    DatasetImportResult,
    InMemorySpatialDatasetStore,
    LicenceStatus,
    Parcel,
    PlanningFeature,
    PropertyProfile,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POSTGIS_AVAILABLE = bool(os.environ.get("DATABASE_URL"))


def _make_licensed_metadata(dataset_id: str = "test-dataset") -> SpatialDatasetMetadata:
    return SpatialDatasetMetadata(
        dataset_id=dataset_id,
        name="Test dataset",
        provider="test",
        version="1.0",
        licence="CC BY 4.0",
        licence_status=LicenceStatus.LICENSED,
        source_crs=GDA2020_TARGET_CRS,
        approval_status=SourceApprovalStatus.APPROVED,
        source_version_id="test:version:1.0",
    )


def _make_unlicensed_metadata(dataset_id: str = "unlicensed-ds") -> SpatialDatasetMetadata:
    return SpatialDatasetMetadata(
        dataset_id=dataset_id,
        name="Unlicensed dataset",
        provider="test",
        version="1.0",
        licence="none",
        licence_status=LicenceStatus.UNLICENSED,
        source_crs=GDA2020_TARGET_CRS,
        approval_status=SourceApprovalStatus.PENDING_REVIEW,
        source_version_id=None,
    )


# ---------------------------------------------------------------------------
# 1. Interface duck-type check (no DB required)
# ---------------------------------------------------------------------------

class TestPostGISStoreInterface:
    """Verify PostGISSpatialDatasetStore exposes the same public interface as
    InMemorySpatialDatasetStore.

    We inspect method signatures rather than importing the class to avoid
    requiring PostGIS at test collection time.
    """

    _REQUIRED_METHODS = [
        "import_dataset",
        "add_address_point",
        "add_parcel",
        "add_planning_feature",
        "dataset_for",
        "is_authoritative_dataset",
        "exact_address_points",
        "planning_for_parcel",
        "save_profile",
        "profile_for_project",
    ]

    def test_postgis_store_module_importable(self) -> None:
        """The module itself must import without errors (even without a live DB)."""
        from draftcheck.domain.address import postgis_store  # noqa: F401

    def test_postgis_store_has_all_required_methods(self) -> None:
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        for method_name in self._REQUIRED_METHODS:
            assert hasattr(PostGISSpatialDatasetStore, method_name), (
                f"PostGISSpatialDatasetStore is missing method: {method_name}"
            )

    def test_postgis_store_method_signatures_match_in_memory_store(self) -> None:
        """Key method signatures must be compatible with InMemorySpatialDatasetStore."""
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        # Methods whose signatures we check for parameter-name compatibility
        methods_to_check = [
            "import_dataset",
            "exact_address_points",
            "planning_for_parcel",
            "save_profile",
        ]
        for name in methods_to_check:
            in_memory_sig = inspect.signature(getattr(InMemorySpatialDatasetStore, name))
            postgis_sig = inspect.signature(getattr(PostGISSpatialDatasetStore, name))
            in_memory_params = set(in_memory_sig.parameters) - {"self"}
            postgis_params = set(postgis_sig.parameters) - {"self"}
            assert in_memory_params <= postgis_params, (
                f"{name}: PostGISSpatialDatasetStore is missing params "
                f"{in_memory_params - postgis_params} vs InMemorySpatialDatasetStore"
            )

    def test_in_memory_store_licence_gate_blocks_unlicensed(self) -> None:
        """InMemorySpatialDatasetStore blocks unlicensed datasets (existing behaviour)."""
        store = InMemorySpatialDatasetStore()
        result = store.import_dataset(_make_unlicensed_metadata())
        assert result.accepted is False
        assert result.authoritative is False

    def test_postgis_store_licence_gate_raises_for_unlicensed(self) -> None:
        """PostGISSpatialDatasetStore MUST raise ValueError for UNLICENSED datasets
        (safety invariant 3) regardless of whether a DB is connected."""
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        # We pass a sentinel engine that is never called — the licence check
        # happens before any DB access.
        class _FakeEngine:
            pass

        store = PostGISSpatialDatasetStore(_FakeEngine())  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="(?i)licence"):
            store.import_dataset(_make_unlicensed_metadata())

    def test_postgis_store_licence_gate_raises_for_unknown_licence(self) -> None:
        """UNKNOWN licence is also blocked."""
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        class _FakeEngine:
            pass

        store = PostGISSpatialDatasetStore(_FakeEngine())  # type: ignore[arg-type]
        unknown_metadata = SpatialDatasetMetadata(
            dataset_id="unknown-ds",
            name="Unknown licence dataset",
            provider="test",
            version="1.0",
            licence="unknown",
            licence_status=LicenceStatus.UNKNOWN,
            source_crs=GDA2020_TARGET_CRS,
        )
        with pytest.raises(ValueError, match="(?i)licence"):
            store.import_dataset(unknown_metadata)

    def test_postgis_store_licence_gate_allows_licensed(self) -> None:
        """LICENSED datasets pass the licence gate (though import needs a real DB)."""
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        class _FakeEngine:
            def connect(self):
                raise RuntimeError("no DB")

        store = PostGISSpatialDatasetStore(_FakeEngine())  # type: ignore[arg-type]
        # The licence gate should NOT raise — it fails later at DB access.
        metadata = _make_licensed_metadata()
        with pytest.raises(Exception) as exc_info:
            store.import_dataset(metadata)
        assert "ValueError" not in type(exc_info.value).__name__, (
            "ValueError from licence gate must not fire for LICENSED dataset"
        )

    def test_postgis_store_licence_gate_allows_restricted(self) -> None:
        """RESTRICTED datasets (advisory/display) pass the licence gate."""
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        class _FakeEngine:
            pass

        store = PostGISSpatialDatasetStore(_FakeEngine())  # type: ignore[arg-type]
        restricted_metadata = SpatialDatasetMetadata(
            dataset_id="restricted-ds",
            name="Restricted dataset",
            provider="test",
            version="1.0",
            licence="display only",
            licence_status=LicenceStatus.RESTRICTED,
            source_crs=GDA2020_TARGET_CRS,
            approval_status=SourceApprovalStatus.PENDING_REVIEW,
        )
        # Must not raise ValueError — the DB call may fail for other reasons
        with pytest.raises(Exception) as exc_info:
            store.import_dataset(restricted_metadata, require_authoritative=False)
        assert "ValueError" not in type(exc_info.value).__name__


# ---------------------------------------------------------------------------
# 2. Licence gate — approval_status / approval interaction
# ---------------------------------------------------------------------------

class TestLicenceGateApprovalStatus:
    """Verify approval_status is stored correctly in dataset metadata."""

    def test_gnaf_dataset_has_approved_status(self) -> None:
        """G-NAF metadata must be LICENSED + APPROVED."""
        meta = _make_licensed_metadata("gnaf_wa_2026-06-01")
        assert meta.licence_status == LicenceStatus.LICENSED
        assert meta.approval_status == SourceApprovalStatus.APPROVED
        assert meta.is_authoritative()

    def test_dplh_dataset_is_never_authoritative(self) -> None:
        """DPLH display data (RESTRICTED + PENDING_REVIEW) must not be authoritative."""
        meta = SpatialDatasetMetadata(
            dataset_id="dplh-display",
            name="DPLH display",
            provider="DPLH",
            version="2026",
            licence="display only",
            licence_status=LicenceStatus.RESTRICTED,
            source_crs=GDA2020_TARGET_CRS,
            approval_status=SourceApprovalStatus.PENDING_REVIEW,
        )
        assert not meta.is_authoritative()

    def test_in_memory_store_does_not_overwrite_approved_with_rejected(self) -> None:
        """Existing test from test_v3_spatial_address.py — replicated here for
        PostGIS-independent verification of the guard logic."""
        store = InMemorySpatialDatasetStore()
        approved = _make_licensed_metadata("shared-id")
        store.import_dataset(approved)
        rejected = store.import_dataset(
            SpatialDatasetMetadata(
                dataset_id="shared-id",
                name="Rejected replacement",
                provider="test",
                version="2.0",
                licence="none",
                licence_status=LicenceStatus.UNLICENSED,
                approval_status=SourceApprovalStatus.REJECTED,
                source_crs=GDA2020_TARGET_CRS,
                source_version_id="test:version:2.0",
            )
        )
        assert rejected.accepted is False
        assert store.dataset_for("shared-id") == approved


# ---------------------------------------------------------------------------
# 3. PostGIS integration tests (skipped without DATABASE_URL)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _POSTGIS_AVAILABLE,
    reason="PostGIS database required (set DATABASE_URL env var)",
)
class TestPostGISStoreIntegration:
    """Live PostGIS tests — only run when DATABASE_URL is set."""

    @pytest.fixture()
    def store(self):
        from sqlalchemy import create_engine
        from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

        engine = create_engine(os.environ["DATABASE_URL"])
        return PostGISSpatialDatasetStore(engine)

    def test_import_dataset_returns_accepted_true(self, store) -> None:
        result = store.import_dataset(_make_licensed_metadata("integration-test-ds"))
        assert result.accepted is True
        assert result.authoritative is True
        assert result.target_crs == GDA2020_TARGET_CRS

    def test_dataset_for_returns_imported_metadata(self, store) -> None:
        meta = _make_licensed_metadata("integration-test-ds-2")
        store.import_dataset(meta)
        retrieved = store.dataset_for("integration-test-ds-2")
        assert retrieved is not None
        assert retrieved.dataset_id == "integration-test-ds-2"
        assert retrieved.licence_status == LicenceStatus.LICENSED

    def test_exact_address_points_returns_empty_for_unknown_address(self, store) -> None:
        results = store.exact_address_points("999 Nowhere Road, Unknown WA 9999")
        assert isinstance(results, list)
        assert results == []

    def test_planning_for_parcel_returns_empty_for_unknown_parcel(self, store) -> None:
        results = store.planning_for_parcel("no-such-parcel-id")
        assert isinstance(results, list)
        assert results == []

    def test_profile_for_project_returns_none_when_not_saved(self, store) -> None:
        import uuid

        result = store.profile_for_project(
            org_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
        )
        assert result is None
