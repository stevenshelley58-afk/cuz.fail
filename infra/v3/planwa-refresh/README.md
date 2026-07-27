# PlanWA spatial refresh

This job keeps a versioned local copy of the official DPLH PlanWA layers used
for address checks:

- DPLH-024 structure-plan boundaries
- DPLH-068 local-planning-scheme special areas
- DPLH-070 R-Codes
- DPLH-071 zones and reserves

The importer requests every ArcGIS feature, compares the downloaded total with
the server-side count, hashes the canonical GeoJSON, creates linked
`source_versions` and `spatial_datasets` records, and loads the new feature
version in one database transaction. The application reads only the latest
approved/licensed version of each logical dataset.

Production installation:

```sh
sudo bash /srv/draftcheck/app/infra/v3/planwa-refresh/install-systemd.sh
sudo systemctl start draftcheck-planwa-refresh.service
sudo journalctl -u draftcheck-planwa-refresh.service --since today --no-pager
```

The timer runs weekly on Sunday morning (Australia/Perth). A transient fetch or
count mismatch fails the job and leaves the previous local version active.

The API also performs a small live point query when
`DRAFTCHECK_PLANWA_LIVE_VERIFY=true`. A live/local disagreement makes the
property `needs_more_info`; an unavailable live service is recorded but does
not disable the versioned local result.

The source records preserve the public ArcGIS endpoint, catalogue URL, licence
label, content hash, feature count, fetch time, and operator approval basis.
This is an operational provenance record, not a claim of final legal or
planning compliance.
