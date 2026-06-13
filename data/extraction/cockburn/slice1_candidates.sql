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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 15.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 6.0 m2 vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 300.0 m2 vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fde6bde9-debc-58a5-8801-b56e537f6b05', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'e066a193-fe0e-4d85-9f72-06b2e8576cab',
  'soft_landscaping', 'standard', 'none', 'pct_gte', '{"value": 15.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimum soft landscaping requirement per site, applies to single house, grouped dwelling and multiple dwelling"}'::jsonb, 'minimum 15% soft landscaping requirement per site', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '328db38da837f4437234e63b74ad93b868c8246cea69301922b4d448cd70a130',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd96c833c-693d-53db-b794-dd373cf93cb2', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 15.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b8a70aad-63d2-5e4c-be41-59c6a444ffc0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '20acb924-6cd9-49d3-85f1-3134f51e5649',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 85.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum site cover"}'::jsonb, 'C3.1.1 Maximum site cover of 85%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ba3714a4827a84243878ae230b9b3eeed185bc737f512617fbf4dc29c6d702ba',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '81bc2969-5a30-57bf-ad6f-db825b67df19', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 85.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '93dca3c8-8001-5fcd-a816-7ddad4a59e43', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '9de08cc7-9588-4cef-86cc-4feaf8334614',
  'building_storeys', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum building height"}'::jsonb, 'Minimum two storey building height', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'daf0928af575ff95fce477d72f3e9cf17376b7f8fe5974d2e30d7a7e5ba0b503',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9c53543e-653f-5bdf-aced-5ed77b74bd1a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '70f68777-1271-5fd6-bd8e-ca22130d1082', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '9de08cc7-9588-4cef-86cc-4feaf8334614',
  'building_storeys', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 4.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum building height in accordance with Table 3.2a"}'::jsonb, 'Maximum four storey building height in accordance with Table 3.2a', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9020d59d92c30b5fd89d9a3c5c25f82a3099e84624f60abdd6d3a26406dc2cc6',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9c53543e-653f-5bdf-aced-5ed77b74bd1a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c4d5056e-31f5-5f38-a326-e1b1a11445a9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R30-R35"}'::jsonb, 'R30 – R35 3.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6cfda468fd624ba36c2f313d0bde4cd1fd6722b6e2cec04317b0d7c892dc21ed',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '766ce4e5-0fe3-5ee1-9fcd-e8f54057e3a9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R40 and above"}'::jsonb, 'R40 and above 3.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '72d4abb5e1f13142f00449cbf007f403725998e19eaa5b6fe1dc22c1598f32a3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6870c150-2700-5f15-be0c-b3cd0f8220b8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R50 and above where frontage is 8.5m or less"}'::jsonb, 'Where frontage
is 8.5m or less 7m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8d5393123114a37e627865a07b8b7392d22973538f39c206081f1f16986450d5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8fa9b224-f139-5955-b2f7-413d785f68b1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'boundary_wall_length', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 14.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Maximum boundary wall length for R50 and above where frontage is 8.5m or less"}'::jsonb, 'Maximum 14m length, at which point the wall  is to be set back a 
minimum of 3m measured from the lot boundary  for a minimum length 
of 3m. Applicable to all lot boundaries.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '25dfe08fbb3cd09556ebd9830f04161830ba8928e258ba1f5a6a016c6f826735',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1b9d5e13-465f-5c3a-8a5b-0e5ada13f8e9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R50 and above where frontage is greater than 8.5m"}'::jsonb, 'Where frontage
is greater than
8.5m
7m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '309c302dccdaeaed5d952f04c419fd2519e7cc1a738e6401ad7bec29901a6b9d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '297a8684-a785-5035-8725-088284768789', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'boundary_wall_length', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 14.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Maximum boundary wall length for R50 and above where frontage is greater than 8.5m"}'::jsonb, 'Maximum 14m length, at which point the wall  is to be set back a 
minimum of 3m measured from the lot boundary  for a minimum length 
of 3m, with a cumulative maximum of two-thirds the length of the lot 
boundary the wall abuts measured from behind the street setback 
line.  Applicable to all lot boundaries.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2c02fea0af17888deba7b59dca957689bdd90933f7670e78fb4c39b7fd6a8ab8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ad61faf7-7990-57c2-abb3-6652ef9594ca', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3ce72f43-5897-42c9-b338-6863f3f05171',
  'garage_width', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Garage door and supporting structure occupying the frontage width"}'::jsonb, 'Garage door and supporting structure may 
occupy up to 50% of the frontage width', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f5c1b47672e8ed988b35e7337be56754d8c6954d3a2ed4188203de9ed2afdad7',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '705c3da7-362f-5500-b47f-5f3a05b49b6b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 50.0 % vs prior [1.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  'ec9760fc-83e0-5753-9d24-d6e4dd2a6b2a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3ce72f43-5897-42c9-b338-6863f3f05171',
  'garage_width', 'exception', 'deemed_to_comply', 'pct_lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "where upper floor or balcony extends more than half the width of the garage"}'::jsonb, 'Garage door and supporting structure 
may occupy up to 60% where upper 
floor or balcony extends more than 
half the width of the garage', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0176abc8d21c75e03e5a7efd32e9bdd88711b8f096ba5990d52d6864d66bf19b',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '705c3da7-362f-5500-b47f-5f3a05b49b6b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 60.0 % vs prior [1.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();

COMMIT;

-- Summary (this slice):
-- {"clauses_seen": 120, "clauses_no_atoms": 113, "atoms_emitted": 15, "atoms_validators_passed": 9, "atoms_validator_failed": 6, "atoms_missing_clause_context": 0}
