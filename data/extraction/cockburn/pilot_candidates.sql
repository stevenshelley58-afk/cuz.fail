BEGIN;
-- WP6 Sonnet (3rd-family) candidate slice. Idempotent: re-run safe (PK is uuid5'd).

INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  'fde6bde9-debc-58a5-8801-b56e537f6b05', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'e066a193-fe0e-4d85-9f72-06b2e8576cab',
  'soft_landscaping', 'standard', 'none', 'pct_gte', '{"value": 15.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum soft landscaping requirement per site applies to single house, grouped dwelling and multiple dwelling"}'::jsonb, 'minimum 15% soft landscaping requirement per site', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '328db38da837f4437234e63b74ad93b868c8246cea69301922b4d448cd70a130',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd96c833c-693d-53db-b794-dd373cf93cb2', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 15.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();
INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  '4ba52f9e-58b8-5efe-9bae-7a4a38213df1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '739f840b-dc92-4500-8d26-5e9e79b6469f',
  'open_space', 'standard', 'none', 'gte', '{"value": 6.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Communal open space minimum per dwelling for developments of more than 10 dwellings (up to a maximum of 300m2)"}'::jsonb, '6m2 per dwelling up to 
maximum 300m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '572651fc7b0cfb7f3105710b4c05c0b570cef7f4c32a30b91da74327b6bf9dc3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3a51db96-3fbe-564a-b1ac-357085e5c284', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 6.0 m2 vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();
INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  '62c8a659-3d06-5073-8f49-2923d5b693b2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '739f840b-dc92-4500-8d26-5e9e79b6469f',
  'open_space', 'standard', 'none', 'lte', '{"value": 300.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Maximum communal open space requirement cap for developments of more than 10 dwellings"}'::jsonb, '6m2 per dwelling up to 
maximum 300m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '16f05826f097837a811ad7e87a50198f134b2e03c50709410d34b44a9681ed8a',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3a51db96-3fbe-564a-b1ac-357085e5c284', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 300.0 m2 vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();

COMMIT;

-- Summary (this slice):
-- {"clauses_seen": 70, "clauses_no_atoms": 68, "atoms_emitted": 3, "atoms_validators_passed": 1, "atoms_validator_failed": 2, "atoms_missing_clause_context": 0}
