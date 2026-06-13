-- WP4 Triage 2026-06-13: resolve 179 blocked manifest rows
-- Idempotent: only updates rows still in status='blocked'.

BEGIN;

-- 1. AS/NZS standards -> metadata_only per CORPUS_SCOPE.md (Standards Australia paid)
UPDATE target_manifest
SET status = 'metadata_only',
    notes = 'Paid standard per CORPUS_SCOPE.md (Standards Australia). Unblock: purchase licence from Standards Australia.',
    updated_at = now()
WHERE status = 'blocked'
  AND category = 'standard'
  AND instrument_name ~* '^AS[/ ]?(NZS )?[0-9]';

-- 2. Per CORPUS_SCOPE.md out-of-scope acts
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Aboriginal Cultural Heritage Act is site clearance process, not lot-level design rules. Heritage mapping is in scope as spatial layer only.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* 'aboriginal.+heritage|aboriginal heritage';

UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Building Act 2011 is permit process; NCC carries the technical rules.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* '^the building act|^building act';

UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Heritage Act 2018 is process; heritage mapping is in scope as spatial layer only.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* '^the heritage act|^heritage act';

UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Strata Titles Act is tenure, not a drafting-check input.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* 'strata titles act';

UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Environmental Protection / EPBC Act is assessment process beyond residential drafting checks.',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* 'environment(al)? protection.+biodiversity'
       OR instrument_name ~* '^epbc'
       OR instrument_name ~* 'biodiversity conservation act 1999');

UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: Commonwealth law (except NCC) is not in scope; WA product.',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* '^commonwealth '
       OR instrument_name ~* '^canberra act'
       OR instrument_name ~* 'census and statistics act'
       OR instrument_name ~* 'airports act 1996');

-- 3. OCR garbage / fragment titles
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'OCR/extraction artefact (fragment of a section header or note, not a separate instrument).',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* '^bas under the transfer of land'
       OR instrument_name ~* '^assent commencement'
       OR instrument_name ~* '^framework state planning framework'
       OR instrument_name ~* '^application of interpretation'
       OR instrument_name ~* '^division the local government'
       OR instrument_name ~* '^city of joondalup planning and development'
       OR instrument_name ~* 'pfannt'  -- "PfanntngandDevelopment"
       OR instrument_name ~* '^development act 2005$'  -- truncated P&D Act
       OR instrument_name ~* '^guidelines state planning framework'
       OR instrument_name ~* '^hazard heritage environment protection');

-- 4. State Planning Policies that do not exist (numbers > 7.x base range)
-- Real SPPs: 1, 2.0-2.9, 3.0-3.7, 4.2-4.3, 5.1-5.4, 6.1/6.3, 7.0-7.3.
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'No such State Planning Policy exists at this number (real SPPs end at 7.3). Likely extraction citation error.',
    updated_at = now()
WHERE status = 'blocked'
  AND category = 'state_planning_policy'
  AND instrument_name ~* 'state planning policy (10|16|18|29|57)\s*$';

-- 5. Other clearly-out-of-scope niche acts
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope: niche act not relevant to residential planning drafting checks (per CORPUS_SCOPE.md scope).',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* '(cement works|bunbury pipeline|hope valley wattleup|caravan and camping|explosives and dangerous goods|drainage act 1909|technology development act|commercial arbitration|liquor act|aquatic resources management|associations incorporation)';

-- 6. CALM Act & Contamination Sites — out-of-scope drafting checks
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope: conservation/contamination process, not lot-level design rule source for drafting checks.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* '^calm act|^contamination sites act|^contaminated sites act';

-- Final summary
COMMIT;

SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY 1;
