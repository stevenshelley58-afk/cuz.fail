"""Deterministic live verification against DPLH's public PlanWA ArcGIS layers.

The local, versioned PostGIS copy remains the primary source.  This client is
an optional second opinion used to detect stale or incomplete local spatial
data.  Network failures are reported separately from data disagreements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from typing import Any, Mapping

import httpx

PLANWA_PROPERTY_AND_PLANNING = (
    "https://public-services.slip.wa.gov.au/public/rest/services/"
    "SLIP_Public_Services/Property_and_Planning/MapServer"
)


@dataclass(frozen=True)
class PlanWALayer:
    layer_id: int
    fact_type: str
    code_fields: tuple[str, ...]
    label_fields: tuple[str, ...]


PLANWA_LAYERS: tuple[PlanWALayer, ...] = (
    PlanWALayer(32, "structure_plan", ("filenumber",), ("alt_title", "title")),
    PlanWALayer(109, "special_area", ("special_no",), ("special_na",)),
    PlanWALayer(111, "r_code", ("rcode_no",), ("rcode_no",)),
    PlanWALayer(112, "zone", ("zone", "label"), ("label_desc", "zone")),
)
_NON_DEVELOPMENT_ZONE_RE = re.compile(
    r"road|reserve|laneway|right.of.way|drainage",
    re.IGNORECASE,
)


def normalize_spatial_code(value: object) -> str:
    """Normalize identifiers without changing their legal/content meaning."""
    return " ".join(str(value or "").strip().upper().split())


def is_usable_zone_code(value: object) -> bool:
    """Exclude transport/reserve boundary artefacts from development zoning."""
    code = str(value or "").strip()
    return bool(code) and _NON_DEVELOPMENT_ZONE_RE.search(code) is None


def _first(properties: Mapping[str, Any], names: tuple[str, ...]) -> str:
    lowered = {str(key).lower(): value for key, value in properties.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def structure_plan_is_current(
    properties: Mapping[str, Any],
    *,
    at: datetime | None = None,
) -> bool:
    """Accept only endorsed/adopted, unexpired structure-plan boundaries.

    Checks both the top-level keys and a nested ``metadata`` sub-dict, since
    the resolver stores overlay metadata nested inside value_json.
    """
    lowered = {str(key).lower(): value for key, value in properties.items()}
    # Also flatten a nested metadata dict (resolver writes metadata_json inside
    # value_json["metadata"]) so status/expiry_date are found regardless of shape.
    nested = lowered.get("metadata")
    if isinstance(nested, dict):
        for key, value in nested.items():
            lk = str(key).lower()
            if lk not in lowered or lowered[lk] is None:
                lowered[lk] = value
    status = str(lowered.get("status") or "").strip().lower()
    if status and "endorsed" not in status and "adopted" not in status:
        return False
    expiry = lowered.get("expiry_date")
    if expiry not in (None, ""):
        try:
            expiry_ms = float(str(expiry))
            now_ms = (at or datetime.now(UTC)).timestamp() * 1000
            if expiry_ms <= now_ms:
                return False
        except (TypeError, ValueError):
            return False
    return True


@dataclass(frozen=True)
class PlanWALiveResult:
    available: bool
    checked_at: datetime
    endpoint: str
    codes: dict[str, frozenset[str]] = field(default_factory=dict)
    features: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    error: str | None = None

    def disagreements(
        self,
        local_codes: Mapping[str, set[str] | frozenset[str]],
    ) -> dict[str, dict[str, list[str]]]:
        """Return exact local/live differences for the governed PlanWA layers."""
        if not self.available:
            return {}
        mismatches: dict[str, dict[str, list[str]]] = {}
        for layer in PLANWA_LAYERS:
            local = {normalize_spatial_code(code) for code in local_codes.get(layer.fact_type, set())}
            if layer.fact_type == "zone":
                local = {code for code in local if is_usable_zone_code(code)}
            live = set(self.codes.get(layer.fact_type, frozenset()))
            if local != live:
                mismatches[layer.fact_type] = {
                    "local": sorted(local),
                    "live": sorted(live),
                }
        return mismatches


class PlanWALiveVerifier:
    """Small synchronous client suitable for the existing sync address API."""

    def __init__(
        self,
        *,
        base_url: str = PLANWA_PROPERTY_AND_PLANNING,
        timeout_seconds: float = 4.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            headers={"User-Agent": "DraftCheck-WA/planwa-live-verifier"},
        )

    def verify_point(self, *, lon: float, lat: float) -> PlanWALiveResult:
        checked_at = datetime.now(UTC)
        codes: dict[str, frozenset[str]] = {}
        features: dict[str, tuple[dict[str, Any], ...]] = {}
        try:
            for layer in PLANWA_LAYERS:
                payload = self._query_layer(layer, lon=lon, lat=lat)
                normalized_features: list[dict[str, Any]] = []
                layer_codes: set[str] = set()
                for feature in payload.get("features", []):
                    properties = feature.get("properties") or feature.get("attributes") or {}
                    if (
                        layer.fact_type == "structure_plan"
                        and not structure_plan_is_current(properties, at=checked_at)
                    ):
                        continue
                    code = normalize_spatial_code(_first(properties, layer.code_fields))
                    label = _first(properties, layer.label_fields)
                    if layer.fact_type == "zone" and not is_usable_zone_code(code):
                        continue
                    if code:
                        layer_codes.add(code)
                    normalized_features.append(
                        {
                            "code": code,
                            "label": label,
                            "properties": properties,
                        }
                    )
                codes[layer.fact_type] = frozenset(layer_codes)
                features[layer.fact_type] = tuple(normalized_features)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return PlanWALiveResult(
                available=False,
                checked_at=checked_at,
                endpoint=self.base_url,
                error=f"{type(exc).__name__}: {exc}",
            )
        return PlanWALiveResult(
            available=True,
            checked_at=checked_at,
            endpoint=self.base_url,
            codes=codes,
            features=features,
        )

    def _query_layer(self, layer: PlanWALayer, *, lon: float, lat: float) -> dict[str, Any]:
        params = {
            "f": "geojson",
            "where": "1=1",
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "7844",
            "outSR": "7844",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
        }
        url = f"{self.base_url}/{layer.layer_id}/query"
        response = self._client.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PlanWA returned a non-object response")
        if payload.get("error"):
            raise ValueError(f"PlanWA ArcGIS error: {payload['error']}")
        return payload
