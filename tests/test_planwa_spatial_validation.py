from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx

from draftcheck.checks.engine import (
    _property_spatial_scopes,
    _source_applies_to_spatial_facts,
)
from draftcheck.domain.address.planwa import (
    PLANWA_PROPERTY_AND_PLANNING,
    PlanWALiveResult,
    PlanWALiveVerifier,
    is_usable_zone_code,
    structure_plan_is_current,
)
from draftcheck.domain.address.spatial import (
    AddressResolutionService,
    PlanningFeature,
    ResolutionStatus,
    create_default_spatial_store,
)


def _source(
    title: str,
    *,
    source_type: str = "local_structure_plan",
    metadata: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        source_type=source_type,
        canonical_url="https://example.test/source",
        metadata_json=metadata or {},
    )


def _fact(fact_type: str, value: dict) -> SimpleNamespace:
    return SimpleNamespace(fact_type=fact_type, value_json=value)


def test_glen_iris_rule_does_not_apply_without_parcel_plan_intersection() -> None:
    source = _source("Glen Iris Estate Local Structure Plan - WAPC Reference SPN/2330")

    assert not _source_applies_to_spatial_facts(source, {})


def test_glen_iris_rule_applies_only_to_matching_structure_plan_reference() -> None:
    source = _source("Glen Iris Estate Local Structure Plan - WAPC Reference SPN/2330")
    scopes = _property_spatial_scopes(
        [
            _fact(
                "structure_plan",
                {
                    "code": "SPN/2330",
                    "status": "Endorsed by WAPC",
                    "expiry_date": (datetime.now(UTC) + timedelta(days=30)).timestamp() * 1000,
                },
            )
        ]
    )

    assert _source_applies_to_spatial_facts(source, scopes)
    assert not _source_applies_to_spatial_facts(
        source,
        {"structure_plan": {"SPN/9999"}},
    )


def test_structure_plan_source_without_mappable_reference_fails_closed() -> None:
    source = _source("Example Local Development Plan")

    assert not _source_applies_to_spatial_facts(
        source,
        {"structure_plan": {"SPN/2330"}},
    )


def test_expired_structure_plan_is_not_a_property_scope() -> None:
    facts = [
        _fact(
            "structure_plan",
            {
                "code": "SPN/2330",
                "status": "Endorsed by WAPC",
                "expiry_date": (datetime.now(UTC) - timedelta(days=1)).timestamp() * 1000,
            },
        )
    ]

    assert _property_spatial_scopes(facts) == {}
    assert not structure_plan_is_current(facts[0].value_json)


def test_live_planwa_client_normalizes_all_governed_layers() -> None:
    payloads = {
        32: [],
        109: [{"properties": {"special_no": "DCA 13", "special_na": "Development contribution area"}}],
        111: [{"properties": {"rcode_no": "R20"}}],
        112: [{"properties": {"zone": "Residential", "label_desc": "Residential"}}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        layer_id = int(request.url.path.split("/")[-2])
        return httpx.Response(200, json={"type": "FeatureCollection", "features": payloads[layer_id]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PlanWALiveVerifier(client=client).verify_point(
        lon=115.81639073,
        lat=-32.13476661,
    )

    assert result.available
    assert result.endpoint == PLANWA_PROPERTY_AND_PLANNING
    assert result.codes["structure_plan"] == frozenset()
    assert result.codes["special_area"] == frozenset({"DCA 13"})
    assert result.codes["r_code"] == frozenset({"R20"})
    assert result.codes["zone"] == frozenset({"RESIDENTIAL"})


def test_live_disagreement_is_exact_and_fail_closed_for_black_swan_canary() -> None:
    live = PlanWALiveResult(
        available=True,
        checked_at=datetime.now(UTC),
        endpoint=PLANWA_PROPERTY_AND_PLANNING,
        codes={
            "structure_plan": frozenset(),
            "special_area": frozenset({"DCA 13"}),
            "r_code": frozenset({"R20"}),
            "zone": frozenset({"RESIDENTIAL"}),
        },
    )
    local = {
        "structure_plan": {"SPN/2330"},
        "special_area": {"DCA 13"},
        "r_code": {"R20"},
        "zone": {"Residential", "Local road"},
    }

    assert live.disagreements(local) == {
        "structure_plan": {"local": ["SPN/2330"], "live": []}
    }


def test_transport_and_reserve_polygons_are_not_development_zones() -> None:
    assert is_usable_zone_code("Residential")
    assert not is_usable_zone_code("Local road")
    assert not is_usable_zone_code("Parks and recreation reserve")


class _FakeVerifier:
    def __init__(self, result: PlanWALiveResult) -> None:
        self.result = result

    def verify_point(self, *, lon: float, lat: float) -> PlanWALiveResult:
        assert lon
        assert lat
        return self.result


def test_address_resolution_stays_resolved_when_live_and_local_agree() -> None:
    verifier = _FakeVerifier(
        PlanWALiveResult(
            available=True,
            checked_at=datetime.now(UTC),
            endpoint=PLANWA_PROPERTY_AND_PLANNING,
            codes={
                "structure_plan": frozenset(),
                "special_area": frozenset(),
                "r_code": frozenset(),
                "zone": frozenset({"R40"}),
            },
        )
    )
    service = AddressResolutionService(
        store=create_default_spatial_store(),
        live_verifier=verifier,  # type: ignore[arg-type]
    )

    profile = service.resolve_address(
        org_id="fixture-org",
        project_id="fixture-project",
        address="1 Example Street, Spearwood WA 6163",
    )

    assert profile.resolution_status == ResolutionStatus.RESOLVED
    assert "planwa_live_disagrees_with_local_spatial_data" not in profile.issues


def test_address_resolution_requires_review_when_live_and_local_disagree() -> None:
    verifier = _FakeVerifier(
        PlanWALiveResult(
            available=True,
            checked_at=datetime.now(UTC),
            endpoint=PLANWA_PROPERTY_AND_PLANNING,
            codes={
                "structure_plan": frozenset({"SPN/2330"}),
                "special_area": frozenset(),
                "r_code": frozenset(),
                "zone": frozenset({"R40"}),
            },
        )
    )
    service = AddressResolutionService(
        store=create_default_spatial_store(),
        live_verifier=verifier,  # type: ignore[arg-type]
    )

    profile = service.resolve_address(
        org_id="fixture-org",
        project_id="fixture-project",
        address="1 Example Street, Spearwood WA 6163",
    )

    assert profile.resolution_status == ResolutionStatus.NEEDS_MORE_INFO
    assert "planwa_live_disagrees_with_local_spatial_data" in profile.issues


def test_address_profile_omits_adjacent_road_from_development_zone_facts() -> None:
    store = create_default_spatial_store()
    store.add_planning_feature(
        PlanningFeature(
            feature_id="adjacent-local-road",
            parcel_id="parcel-cockburn-fixture-1",
            fact_type="zone",
            value={"code": "Local road", "label": "Local road"},
            dataset_id="fixture-cockburn-planning-2026-06",
        )
    )
    service = AddressResolutionService(store=store)

    profile = service.resolve_address(
        org_id="fixture-org",
        project_id="fixture-project",
        address="1 Example Street, Spearwood WA 6163",
    )

    zones = [fact.value for fact in profile.facts if fact.fact_type == "zone"]
    assert zones == [{"label": "Residential", "code": "R40"}]
