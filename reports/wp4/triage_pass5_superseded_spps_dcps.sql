BEGIN;

-- SPP 2.1 / 2.2 / 2.3 / 2.7 / 2.10 — water-policy precursors all consolidated into SPP 2.9 Planning for Water (acquired)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Superseded/consolidated: legacy water-policy SPP rolled into SPP 2.9 Planning for Water (in force Dec 2025; acquired). Not in the current SPP listing at wa.gov.au/government/document-collections/state-planning-policies.',
    updated_at = now()
WHERE status = 'blocked'
  AND category = 'state_planning_policy'
  AND instrument_name IN ('State Planning Policy 2.1', 'State Planning Policy 2.2', 'State Planning Policy 2.3', 'State Planning Policy 2.7', 'State Planning Policy 2.10');

-- SPP 3.1 — consolidated into SPP 7.3 (R-Codes Vol 1 and Vol 2) under Design WA Stage 1 (May 2019)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Superseded: SPP 3.1 Residential Design Codes was split into SPP 7.3 R-Codes Volume 1 + Volume 2 (Apartments) under Design WA Stage 1 (May 2019). SPP 7.3 is acquired.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'State Planning Policy 3.1';

-- SPP 4.3 — historical Poultry Farms policy; revoked
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Superseded/revoked legacy SPP not in the current wa.gov.au SPP listing. Cited only by historical instruments; no current design rule source.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'State Planning Policy 4.3';

-- SPP 7.1 — superseded by current SPP 7.0 (Design of the Built Environment, acquired) under Design WA
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Superseded: rolled into SPP 7.0 Design of the Built Environment (acquired) under Design WA. Not in the current wa.gov.au SPP listing.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'State Planning Policy 7.1';

-- DCP 1.4 (Functional Road Classification, 1988) — legacy DCP not in current wa.gov.au DCP listing; referenced only by other historical instruments
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Legacy DCP (1988) not in current wa.gov.au Development Control Policies listing. Functional road classification guidance now lives in DC1.7 General Road Planning (acquired) and Main Roads WA road hierarchy material.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'Development Control Policy 1.4';

-- DCP 2.3 — legacy public open space DCP, superseded by Liveable Neighbourhoods + SPP 2.6 public open space framework
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Legacy DCP not in current wa.gov.au DCP listing. Public open space guidance now lives in Liveable Neighbourhoods + SPP 2.6 framework.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'Development Control Policy 2.3';

-- DCP 3.7 — citation noise (this number matches SPP 3.7 Bushfire which is acquired; no separate DCP 3.7 exists in current listing)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Citation noise: no DCP 3.7 exists in current wa.gov.au listing. SPP 3.7 Planning in Bushfire Prone Areas (acquired) covers bushfire planning.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'Development Control Policy 3.7';

COMMIT;

SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY 1;
