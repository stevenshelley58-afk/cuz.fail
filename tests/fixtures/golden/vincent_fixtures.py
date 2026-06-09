"""City of Vincent M1 golden fixtures for Stage 2 integration tests.

All fixture data is demo/synthetic only. No authoritative cadastral, planning,
or G-NAF data is stored here. Licence and provenance metadata is illustrative
of the real pipeline's expected output once live datasets are wired in W2.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent

GOLDEN_ADDRESS = "244 Vincent Street, North Perth WA 6006"
GOLDEN_LAT = -31.9318
GOLDEN_LON = 115.8518
GOLDEN_ZONE = "R60"
GOLDEN_LGA = "City of Vincent"


def load_address_point() -> dict:
    """Load the M1 golden G-NAF address point record."""
    return json.loads((FIXTURE_DIR / "vincent_address_point.json").read_text(encoding="utf-8"))


def load_parcel() -> dict:
    """Load the M1 golden cadastral parcel GeoJSON feature."""
    return json.loads((FIXTURE_DIR / "vincent_parcel.geojson").read_text(encoding="utf-8"))


def load_lga_boundary() -> dict:
    """Load the simplified City of Vincent LGA boundary GeoJSON feature."""
    return json.loads((FIXTURE_DIR / "vincent_lga_boundary.geojson").read_text(encoding="utf-8"))


def load_dplh_response() -> dict:
    """Load the DPLH WMS GetFeatureInfo stub response for the M1 address."""
    return json.loads((FIXTURE_DIR / "vincent_dplh_wms_response.json").read_text(encoding="utf-8"))


def load_property_facts() -> dict:
    """Load the expected property facts after successful M1 address resolution."""
    return json.loads((FIXTURE_DIR / "vincent_property_facts.json").read_text(encoding="utf-8"))


def load_seeded_project() -> dict:
    """Load the seeded project record for the M1 golden fixture."""
    return json.loads((FIXTURE_DIR / "vincent_seeded_project.json").read_text(encoding="utf-8"))
