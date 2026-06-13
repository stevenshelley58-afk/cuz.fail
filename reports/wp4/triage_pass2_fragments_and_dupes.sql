BEGIN;

-- 7. More OCR/fragment titles (section references, prefix junk, citation snippets)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'OCR/extraction artefact (section reference or fragment of a citation, not a separate instrument).',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* '^(part [iv]+|of |of the |page |statements |strategies |state planning framework|schedule and |note the |under the |if the |status under |w k h |citation |significant development pathway|legislation legislation|legislation b|tax and the|term rental accommodation act|wk h)\b'
       OR instrument_name ~* '^iv of the|^the interpretation act|^management act 2006$|^success development act'
       OR instrument_name ~* '^species common name status'
       OR instrument_name ~* '\bw k h\b'
       OR instrument_name ~* 'page western australian legislation'
       OR instrument_name ~* '^western australia(n)? legislation '
       OR instrument_name ~* '^western australia(n)? planning and development act'  -- dup of P&D Act 2005
       OR instrument_name ~* '^western australian planning commission act 1985'
       OR instrument_name ~* '^wattleup redevelopment act'  -- dup of Hope Valley Wattleup
       );

-- 8. "The X" duplicates of already-acquired Acts
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Duplicate citation: parent Act already acquired (this is the same instrument with "The " prefix or minor variation).',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* '^the planning and development act 2005'
       OR instrument_name ~* '^the mining act 1978'
       OR instrument_name ~* '^the conservation and land management'
       OR instrument_name ~* '^the waterways conservation act'
       OR instrument_name ~* '^the environmental protection act 1986'
       OR instrument_name ~* '^the land administration act 1997'
       OR instrument_name ~* '^the strata titles amendment'
       OR instrument_name ~* '^the biosecurity and agriculture management'
       OR instrument_name ~* '^the biodiversity conservation regulations'
       OR instrument_name ~* '^the planning and development regulations 2009'  -- superseded by 2015
       OR instrument_name ~* '^the town planning regulations 1967'  -- superseded
       OR instrument_name ~* '^water and irrigation act 1914'  -- dup of Rights In Water and Irrigation Act
       OR instrument_name ~* '^water service act 2012'  -- typo of Water Services Act 2012
       );

-- 9. Out-of-scope topics per CORPUS_SCOPE.md (mining, fishing, telecom, tax, native title, biodiv, etc.)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope per CORPUS_SCOPE.md: topic not relevant to residential planning drafting checks.',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* 'income tax|legal profession|public sector reform|reprints act|road traffic|totalisator|betting|radiocommunications|telecommunications act 1997|national broadband|native title|swan river conservation|fisheries (act|regulations)|wildlife conservation|biodiversity conservation (act|regulations)|land act 1933|land and public works|mining act 190[0-9]|mining act 198[0-9]|state environmental protection|environmental protection act 1986|biosecurity and agriculture management|water and irrigation regulations 2000|policy and regulations 2004|water services legislation amendment');

-- 10. Amendment / superseded Acts and Regulations (rolled into consolidated parent)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Superseded/amendment instrument: consolidated parent already acquired (amendments are rolled into the in-force consolidated text on legislation.wa.gov.au).',
    updated_at = now()
WHERE status = 'blocked'
  AND (instrument_name ~* '^planning and development amendment (act|regulations)'
       OR instrument_name ~* 'planning regulations amendment regulations'
       OR instrument_name ~* '^amendment regulations 20[0-9]{2}'
       OR instrument_name ~* '^citation published commencement '
       OR instrument_name ~* '^date planning and development regulations'
       OR instrument_name ~* '^town planning amendment regulations'
       OR instrument_name ~* '^metropolitan region town planning scheme act 1959'  -- pre-MRS
       OR instrument_name ~* '^town planning and development act 1928'  -- repealed by P&D 2005
       OR instrument_name ~* '^town planning regulations 1967'
       OR instrument_name ~* '^transfer of land act 19(8|9)3'  -- wrong dates / superseded
       OR instrument_name ~* '^swan valley planning legislation amendment'
       OR instrument_name ~* '^schedule and the swan valley planning'
       );

-- 11. Heritage of WA Act 1990 — superseded by Heritage Act 2018 (which is out-of-scope per scope doc)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Out of scope: heritage process is out of scope per CORPUS_SCOPE.md; heritage mapping is in scope as spatial layer only.',
    updated_at = now()
WHERE status = 'blocked'
  AND instrument_name ~* '^heritage of western australia act|^if the heritage act|^the heritage act';

-- 12. Local Planning Scheme No. 3 — orphan citations (Cockburn TPS 3 already acquired as City of Cockburn local_planning_scheme)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Orphan citation: scheme number without council context. City of Cockburn TPS 3 (pilot LGA) already acquired.',
    updated_at = now()
WHERE status = 'blocked'
  AND category = 'local_planning_scheme'
  AND instrument_name ~* '^local planning scheme no\.? 3\s*$';

-- 13. SPP duplicates (case-insensitive: keep "State Planning Policy X.Y", drop UPPERCASE/lowercase variants)
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Duplicate citation: same SPP exists as acquired or canonical-cased manifest row.',
    updated_at = now()
WHERE status = 'blocked'
  AND category = 'state_planning_policy'
  AND id IN (
    SELECT b.id
    FROM target_manifest b
    JOIN target_manifest other ON other.id != b.id
      AND lower(regexp_replace(other.instrument_name, '\s+', ' ', 'g')) = lower(regexp_replace(b.instrument_name, '\s+', ' ', 'g'))
      AND other.status IN ('acquired', 'blocked')
    WHERE b.status = 'blocked'
      AND b.instrument_name ~ '[A-Z]{3,}'  -- has uppercase run
  );

-- 14. SPP 2 / SPP 3 / SPP 5 unqualified — drop in favour of versioned acquired siblings
UPDATE target_manifest
SET status = 'out_of_scope',
    notes = 'Unqualified SPP citation (no version suffix). Versioned SPPs (e.g. 2.0, 3.0) already acquired or covered.',
    updated_at = now()
WHERE status = 'blocked'
  AND category = 'state_planning_policy'
  AND lower(instrument_name) ~ '^state planning policy (2|3|5)\s*$';

COMMIT;

SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY 1;
