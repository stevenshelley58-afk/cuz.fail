BEGIN;

-- "Planning and Development Local Planning Scheme Regulations 2015" — dup of acquired with parens
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Duplicate citation of acquired "Planning and Development (Local Planning Schemes) Regulations 2015" (missing parens/plural in citation).',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'Planning and Development Local Planning Scheme Regulations 2015';

-- "Planning and Development Regulations 2015" — no such standalone regs; either dup of LPS Regs 2015 or wrong year of 2009
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'No such standalone regulations exist (in-force WA regs are Planning and Development Regulations 2009 + LPS Regulations 2015). Likely extraction citation error.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'Planning and Development Regulations 2015';

-- Lowercase DCP -> standardize before URL discovery
UPDATE target_manifest
SET instrument_name = 'Development Control Policy 3.7',
    updated_at = now()
WHERE status='blocked'
  AND instrument_name = 'development control policy 3.7';

COMMIT;

SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY 1;
