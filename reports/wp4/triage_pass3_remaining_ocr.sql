BEGIN;

-- Final OCR/fragment sweep
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'OCR/extraction artefact (citation fragment, section reference, or table-of-contents stub).',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name LIKE 'Note the %'
       OR instrument_name LIKE 'OF DATE %'
       OR instrument_name LIKE 'OF THE %'
       OR instrument_name LIKE 'OF TITLE %'
       OR instrument_name LIKE 'Part IVA %'
       OR instrument_name LIKE 'Part Three %'
       OR instrument_name LIKE 'Significant Development Pathway %'
       OR instrument_name LIKE 'Statements STATE PLANNING %'
       OR instrument_name LIKE 'STATE PLANNING FRAMEWORK %'
       OR instrument_name LIKE 'Status Under %'
       OR instrument_name LIKE 'Strategies STATE PLANNING %'
       OR instrument_name LIKE 'Tax and the %'
       OR instrument_name LIKE 'Under the %');

-- Strata Titles Amendments (out per CORPUS_SCOPE: Strata Titles Act is out of scope)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Strata Titles Act is tenure, not a drafting-check input.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name LIKE 'Strata Titles Amendment Act %';

-- Term Rental Accommodation Act 2024 (short-term rentals, not residential drafting design rules)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope: short-term rental accommodation legislation, not lot-level design rules.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name LIKE 'Term Rental Accommodation Act %';

-- Biodiversity Conservation Regulations 2018 (BC Regulations 2018) — out per scope
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: biodiversity conservation is process, not lot-level design rules.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'BC Regulations 2018';

-- WA Planning and Development Regulations 2009 — superseded by 2015 Regs
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Superseded: replaced by Planning and Development (Local Planning Schemes) Regulations 2015.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name = 'Western Australia Planning and Development Regulations 2009';

COMMIT;

SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY 1;
SELECT '---REMAINING_BLOCKED---';
SELECT instrument_name, category FROM target_manifest WHERE status='blocked' ORDER BY category, instrument_name;
