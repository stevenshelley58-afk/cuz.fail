"""G-NAF WA address point importer.

Parses the G-NAF CSV for WA (tab-separated) and loads address points into
any store that implements the ``InMemorySpatialDatasetStore`` interface.

Licence:    CC BY 4.0 (data.gov.au) — LicenceStatus.LICENSED
CRS:        G-NAF coordinates are GDA2020-compatible (EPSG:7844 / EPSG:4283
            are coincident for address-level precision; no reprojection needed).
approval_status: "approved"

G-NAF column layout expected (tab-separated, with header row):
    GNAF_PID  STREET_LOCALITY_PID  LOCALITY_PID  BUILDING_NAME
    NUMBER_FIRST  NUMBER_LAST  STREET_NAME  STREET_TYPE_CODE
    LOCALITY_NAME  STATE_ABBREVIATION  POSTCODE
    LATITUDE  LONGITUDE  GEOCODE_TYPE  RELIABILITY  DATE_CREATED

Usage::

    from draftcheck.domain.address.importers.gnaf_importer import import_gnaf_wa
    from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore

    count = import_gnaf_wa("/data/gnaf/WA_ADDRESS_DEFAULT_GEOCODE_psv.psv", store)
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from draftcheck.domain.address.spatial import (
    GDA2020_TARGET_CRS,
    AddressPoint,
    DatasetImportResult,
    LicenceStatus,
    SourceApprovalStatus,
    SpatialDatasetMetadata,
)

if TYPE_CHECKING:
    from draftcheck.domain.address.spatial import InMemorySpatialDatasetStore

logger = logging.getLogger(__name__)

_GNAF_LICENCE = "CC BY 4.0 (data.gov.au / PSMA Australia)"
_GNAF_PROVIDER = "PSMA Australia / data.gov.au"


def _build_address_text(row: dict[str, str]) -> str:
    """Construct a normalised address string from a G-NAF row."""
    parts: list[str] = []
    if row.get("BUILDING_NAME", "").strip():
        parts.append(row["BUILDING_NAME"].strip())
    number = row.get("NUMBER_FIRST", "").strip()
    if row.get("NUMBER_LAST", "").strip():
        number = f"{number}-{row['NUMBER_LAST'].strip()}"
    street = f"{row.get('STREET_NAME', '').strip()} {row.get('STREET_TYPE_CODE', '').strip()}".strip()
    parts.append(f"{number} {street}".strip())
    locality = row.get("LOCALITY_NAME", "").strip()
    state = row.get("STATE_ABBREVIATION", "").strip()
    postcode = row.get("POSTCODE", "").strip()
    parts.append(f"{locality} {state} {postcode}".strip())
    return ", ".join(p for p in parts if p)


def import_gnaf_wa(
    csv_path: str | Path,
    store: "InMemorySpatialDatasetStore",
    *,
    batch_size: int = 5000,
) -> int:
    """Import G-NAF WA address points from ``csv_path`` into ``store``.

    The dataset is registered as ``gnaf_wa_{import_date}`` where
    ``import_date`` is taken from the first row's ``DATE_CREATED`` field.

    Returns the count of successfully imported address-point rows.

    Safety note: imported coordinates are indicative geocodes — not legal
    proof of property ownership or boundaries.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"G-NAF CSV not found: {csv_path}")

    count = 0
    dataset_metadata: SpatialDatasetMetadata | None = None
    import_result: DatasetImportResult | None = None

    with csv_path.open(newline="", encoding="utf-8") as fh:
        # G-NAF PSV files use pipe | but the task spec says tab-separated;
        # detect automatically from the header row.
        sample = fh.read(4096)
        fh.seek(0)
        dialect = "excel-tab" if "\t" in sample.split("\n")[0] else "excel"
        delimiter = "\t" if dialect == "excel-tab" else "|"

        reader = csv.DictReader(fh, delimiter=delimiter)
        for row in reader:
            if dataset_metadata is None:
                date_created = row.get("DATE_CREATED", "unknown").strip()[:10]
                dataset_id = f"gnaf_wa_{date_created}"
                dataset_metadata = SpatialDatasetMetadata(
                    dataset_id=dataset_id,
                    name=f"G-NAF WA address points {date_created}",
                    provider=_GNAF_PROVIDER,
                    version=date_created,
                    licence=_GNAF_LICENCE,
                    licence_status=LicenceStatus.LICENSED,
                    source_crs=GDA2020_TARGET_CRS,
                    # G-NAF uses GDA2020-compatible coordinates (WGS84/GDA2020
                    # are coincident at address-level precision).
                    approval_status=SourceApprovalStatus.APPROVED,
                    source_version_id=f"gnaf:wa:{date_created}",
                )
                import_result = store.import_dataset(dataset_metadata)
                if not import_result.accepted:
                    logger.error(
                        "gnaf_importer: dataset %r not accepted: %s",
                        dataset_id,
                        import_result.reason,
                    )
                    return 0

            try:
                lat = float(row["LATITUDE"])
                lon = float(row["LONGITUDE"])
            except (KeyError, ValueError):
                logger.debug("gnaf_importer: skipping row with bad coordinates: %r", row)
                continue

            address_text = _build_address_text(row)
            gnaf_pid = row.get("GNAF_PID", "").strip()

            point = AddressPoint(
                address_id=gnaf_pid or f"gnaf_{count}",
                formatted_address=address_text,
                lon=lon,
                lat=lat,
                parcel_id="",  # parcel linkage done post-import via cadastre matching
                dataset_id=dataset_metadata.dataset_id,
                gnaf_pid=gnaf_pid or None,
                target_crs=GDA2020_TARGET_CRS,
            )
            store.add_address_point(point)
            count += 1
            if count % batch_size == 0:
                logger.info("gnaf_importer: imported %d address points so far", count)

    logger.info("gnaf_importer: imported %d address points total from %s", count, csv_path)
    return count
