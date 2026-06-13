BEGIN;
-- WP6 Sonnet (3rd-family) candidate slice. Idempotent: re-run safe (PK is uuid5'd).

INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  'ac5819fe-ef5f-5b7a-80f1-f8403063d418', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '047f0c9d-9902-4646-9bb4-225da3d2c700', 'f16eab79-f44c-48f0-98fe-d9bcac2e595a',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Single house, including extensions and ancillary outbuildings, in the Rural Zone and Rural Living Zone, contained within a building envelope"}'::jsonb, 'A single house, including extensions and ancillary outbuildings with an 
area of less than 100m2 and a wall height not exceeding 4.5 in the Rural 
Zone and Rural Living Zone and the proposal is contained within a 
building envelope.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a3cb44017fdd6e83b23c53f0b441010ea21971567fb69ab66c5454569d683036',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '544ffe95-82a1-5325-9bb8-6909db4cb9cd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'aee53d32-9470-5827-9b43-987e1e025d32', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '047f0c9d-9902-4646-9bb4-225da3d2c700', 'f16eab79-f44c-48f0-98fe-d9bcac2e595a',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Single house, including extensions and ancillary outbuildings, in the Resource Zone, contained within a building envelope"}'::jsonb, 'A single house, including extensions and ancillary outbuildings with an 
area of less than 200m2 and a wall height not exceeding 4.5 in the 
Resource Zone and the proposal is contained within a building envelope.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2e50127d714a7af710c143d256950a3ef98158139498faf7c11e758b990c6a1e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '544ffe95-82a1-5325-9bb8-6909db4cb9cd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e43d90b5-bdc5-54bc-81cb-e06c8cbfaca1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '047f0c9d-9902-4646-9bb4-225da3d2c700', '21db95bb-9c23-4c10-a2d7-7c3b6c7b2c8f',
  'site_area', 'standard', 'none', 'gte', '{"value": 20000.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Subdivision within the Resource Zone (not subject to clause 1.5); minimum lot size for created lots"}'::jsonb, 'A minimum lot size of 2ha;', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7171c36fee3818e27975f29151eb1194d5f0ab48dfc2a4306e3f8a6cf8c12da8',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3510ba61-7159-5abc-9284-7d3b329ab67e', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''20000''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 20000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c491526f-cbc8-5fbf-89a2-1eda674847d3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '047f0c9d-9902-4646-9bb4-225da3d2c700', '088c0bb5-5039-40b0-9c37-137a31a90973',
  'site_area', 'exception', 'none', 'lt', '{"value": 20000.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Precinct 1 (Lot 98 Prinsep Road and Lots 51, 99 and 9 Jandakot Road, Jandakot); lots smaller than 2 ha only supported where reduction is required to facilitate construction of subdivisional roads"}'::jsonb, 'The City shall only support the creation of lots less than 2 
hectares to the extent that the reduction in lot area is required to 
facilitate the construction of subdivisional roads.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'df636a8cb89fb854f404565054601719b5013a63c866455902b6b5bb5cb1c10e',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '66ac0e3a-1f6c-54f1-a028-991d16e7fc69', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''20000''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lt''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 20000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bc20f5e7-8a7e-5b4e-b114-cd1fecc49b23', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '44e54663-150a-40f5-b37e-734316991c82', '6ce05b68-5917-4009-8cab-fbea5b9fa671',
  'site_area', 'standard', 'none', 'gte', '{"value": 1000.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Child care premises site"}'::jsonb, 'The site is to have a regular shape, with a minimum lot area of 
1,000m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '084082fe8e0d5bff90a9d76bfea1a7bc0c2a5845b95995cfa01a2962cf3c00c7',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd0d85907-c9d3-5382-9e0f-c1bb5259c100', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''1000''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '17c91b57-7799-5180-b8a3-421d525c5f00', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '44e54663-150a-40f5-b37e-734316991c82', '6ce05b68-5917-4009-8cab-fbea5b9fa671',
  'minimum_frontage', 'standard', 'none', 'gte', '{"value": 20.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Child care premises site"}'::jsonb, 'an effective frontage of 20m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '491999a4a19cef0f172f5d43a80fa8560e809fe6081dd07618a22b00e65cb32b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd0d85907-c9d3-5382-9e0f-c1bb5259c100', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd67d0900-25ef-5cdd-b709-a7353a37c4d1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '44e54663-150a-40f5-b37e-734316991c82', '6ce05b68-5917-4009-8cab-fbea5b9fa671',
  'site_cover', 'standard', 'none', 'lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Child care premises site coverage maximum"}'::jsonb, 'Site coverage is required to be a maximum of fifty per cent (50%)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd4e5e281890c5f222ed68ccf2efb6e471f4c8edceb67b2305b29238672b69eda',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd0d85907-c9d3-5382-9e0f-c1bb5259c100', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c2ed3c66-06a9-509f-a2ed-355000266c00', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '3ca73a24-ebed-4a47-8f12-e13fa1583c22', 'c0e94341-f879-4762-adb3-3cb1ce4a7feb',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 15.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum primary street setback for industrial/mixed business zones under LPP 3.8 (may be reduced where consistent with existing streetscape, outside Strategic Industry zone)"}'::jsonb, '15m (may be reduced 
where it can be clearly 
demonstrated that it is 
consistent with the 
existing streetscape for 
land zoned outside the 
Strategic Industry zone).', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '693654fe3393ed8c1172d85ca496794e82af2edbbebfd79c120c9792213c09ef',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '2c3d9ce3-9d7d-5d19-9dda-d6c3817e23c9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 15.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f00b674d-18c1-5c25-838d-324ac76e8ed2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '3ca73a24-ebed-4a47-8f12-e13fa1583c22', 'c0e94341-f879-4762-adb3-3cb1ce4a7feb',
  'secondary_street_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum secondary street setback for industrial/mixed business zones under LPP 3.8 (unless reduction is consistent with existing streetscape and not detrimental)"}'::jsonb, '3m (unless it can 
be demonstrated 
that a reduced 
setback is 
consistent with 
the existing 
streetscape 
and/or that a 
reduction will not 
result in a 
detrimental 
impact on the 
streetscape).', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '185724cf7bdda43913774bdf9337105e250d5a71234cf8a625298fa3ecccba0e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '2c3d9ce3-9d7d-5d19-9dda-d6c3817e23c9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8a39e137-5fc6-5c51-b9db-77fd3251b78f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '3ca73a24-ebed-4a47-8f12-e13fa1583c22', '064eb9ab-6167-4adf-81ba-961fe675853a',
  'site_area', 'standard', 'none', 'gte', '{"value": 1000.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Industrial subdivision where reticulated sewerage is available"}'::jsonb, 'Where reticulated sewerage is available, the minimum recommended lot size is 1000m2, with a minimum frontage width of 25m.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '343c81ef1a054784fab714e848cf719ecea2638233b63404d7be7de693ab795f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'cff2e560-756b-588f-8841-fc65bd434018', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3d40bfd8-6593-58a1-819b-208da53943ac', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '3ca73a24-ebed-4a47-8f12-e13fa1583c22', '064eb9ab-6167-4adf-81ba-961fe675853a',
  'minimum_frontage', 'standard', 'none', 'gte', '{"value": 25.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Industrial subdivision where reticulated sewerage is available"}'::jsonb, 'Where reticulated sewerage is available, the minimum recommended lot size is 1000m2, with a minimum frontage width of 25m.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '09bf61712333c79f41afd2b100dc7bab9ef7a65bcfc23ed4f92c8e12ed11112f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'cff2e560-756b-588f-8841-fc65bd434018', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 25.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '818ddbac-7394-5c32-868b-07524349a331', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Low Density Zone R40 - Minimum primary street setback"}'::jsonb, 'Minimum primary and secondary street setbacks Primary – 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dac8d0fbad37702498efb7d4afbe036c845cc32b061d69086698bb5a7d521da2',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e40564b7-1332-54e9-8ece-23a46ccb395c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'secondary_street_setback', 'standard', 'none', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Low Density Zone R40 - Minimum secondary street setback"}'::jsonb, 'Secondary – 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fd65685587b8c0b7c3bbef738dcfb221f2234ac0bcf84b0f2f1403994ff011fc',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '540a43fa-2f4c-578e-ae06-fc3ac244f7d0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Medium/High Density Zone R60 - Minimum building height storeys"}'::jsonb, 'Building height (storeys) 
Minimum
Two storeys Two storeys Two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f0be35897376c9ff6e021841f2b01d7f11f1c31c8c0557378dd22653cdf243f9',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bfdf891d-c341-533b-8c98-2d04be99be81', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Medium/High Density Zone R80 - Minimum building height storeys"}'::jsonb, 'Building height (storeys) 
Minimum
Two storeys Two storeys Two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7f104638401f1b749cf91e01abf8b6cacf0c7f8bef3700ed40a920dcad4155c6',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f9b0ae20-ca51-523a-a141-58b0a4c72bf5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R160"], "dwelling_type": "any", "condition": "Medium/High Density Zone R160 - Minimum building height storeys"}'::jsonb, 'Building height (storeys) 
Minimum
Two storeys Two storeys Two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2534ccb9a5b8819474ab8a935e988edea8c030a02971c2a81f4a402c1b9dfd7a',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2efb3a6a-f05a-59f4-82d3-3ee32e74cdcb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 4.0}'::jsonb, 'storeys',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Medium/High Density Zone R60 - Maximum building height storeys"}'::jsonb, 'Building height (Storeys) 
Maximum
Four storeys Four storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2fd986cf0a25842454b934570e1d8f7896babaec53b0b85e3aa124d321805048',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0f6aeab9-b468-5294-ad94-8afff081d4cc', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 4.0}'::jsonb, 'storeys',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Medium/High Density Zone R80 - Maximum building height storeys"}'::jsonb, 'Building height (Storeys) 
Maximum
Four storeys Four storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '28c69272b3349326f4900b9b43611fda29b3128f740019b641988fe423083567',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6fe2788e-15fa-5fc6-a1b2-a5d54da11ffa', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Medium/High Density Zone R60 - Minimum primary street setback"}'::jsonb, 'Primary - 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f3caddc839bbbb2ee9b5aa4ff058ca59f7b6ee7476de694f0b17dda79d7b7bfe',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '465ea181-39ab-5260-aa91-cd3097ddc25e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'secondary_street_setback', 'standard', 'none', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Medium/High Density Zone R60 - Minimum secondary street setback"}'::jsonb, 'Secondary – 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4a0a83b12becca85a0d716b4a1e7096f7977da5c7815a6ee8e4d76c0c165bef8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ac63e3f3-7a74-52e8-befc-2f6c43758644', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'side_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Business Restricted Use - Office/Residential - Minimum side setbacks"}'::jsonb, 'Minimum side 
setbacks
3m As per BCA. Nil', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'df5241ec32ce053bea31283ea657d9702161b2cdd00ab55a5323ce73d9ecc290',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '78d24bd1-8958-55b8-bd05-6ddd85f7d2c5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'rear_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Business Restricted Use - Office/Residential - Minimum rear setback"}'::jsonb, 'Minimum rear setback 3m 10m Nil', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fdb5886038c235dbc0473bf4b54bc7c2d0b0ac72d62adee1807bac893e916340',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0cf8658a-4962-58ea-8002-57a22e64f65a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'rear_setback', 'standard', 'none', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Business Restricted Use - Non-Residential - Minimum rear setback"}'::jsonb, 'Minimum rear setback 3m 10m Nil', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '71f8e013a57cc37fb3dc39f4aa516e98cad067ec1e4f43c3ac74ab9d57c863d9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8975d41a-604a-5376-8524-5e23c836119e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Business Restricted Use - Office/Residential - Minimum building height storeys"}'::jsonb, 'Building height 
(storeys) Minimum
Three storeys Nil Two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b8eea1908fc2bd6f09bf6dd2ae956f988dcd2728cc5cefc996d39c7b3ebb81d3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5f61c411-13d2-5a83-902e-14029c71eaf3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Local Centre - Minimum building height storeys"}'::jsonb, 'Building height 
(storeys) Minimum
Three storeys Nil Two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c500b842cc98d6a7f0387599bc3f305f779d91fa4b0a70ff114caa24217ea12c',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '335dbb76-85eb-5c5f-8a9a-c67c5e956288', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '447d9048-6939-4872-be96-d91ae323c76c', '886c6d78-9464-4b05-89b7-ba5c0e7e2d97',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 4.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Local Centre - Maximum building height storeys"}'::jsonb, 'Four Storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '17706134f3bc4095b0b345104f30a742e9a4dfd9b5ae65a2e56ff8b505798330',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bba533d8-ea83-5188-bc9c-00a257e6b16f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '69893062-0eb2-5a73-89b6-d01ec8338121', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'bdf1ec53-f4a0-4ed0-a296-0c7fbecc2b62',
  'ceiling_height', 'standard', 'none', 'gte', '{"value": 3.6}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "ground floor dwellings fronting Cockburn Road and Rockingham Road"}'::jsonb, 'In relation to ground floor dwellings fronting Cockburn Road and Rockingham 
Road, as a minimum, 3.6m floor to ceiling should be provided.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'eab85a6f36f9af0ce010f762d201746d41e94ef4c169aadc81c073468ba4f0d8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e1d7a91d-f518-5728-be5d-f5bc4132b011', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.6 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8a9a75bd-47fb-5ee6-bc2b-54869c97627d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 4.0}'::jsonb, 'storeys',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU25 sub-precinct (Residential R60); building height 3-4 storeys (17m)"}'::jsonb, '3-4 (17m)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7d39a02c63b654356a7946e15ee196339f0e57a33cea1fd724fc76a162da339c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '53e9a3d9-ec6a-5a41-a901-f14e5d5b62f7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'building_height', 'standard', 'none', 'lte', '{"value": 17.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU25 sub-precinct (Residential R60); building height limit"}'::jsonb, '3-4 (17m)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6586907eb33f691cd341153c65cd8b8da33c9cde25011ca86ff805bc1901df1a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 17.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8e52b63c-edbc-5d09-a37d-2684373de339', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 5.0}'::jsonb, 'storeys',
  '{"density_codes": ["R160"], "dwelling_type": "any", "condition": "SU27 sub-precinct (Mixed Use R160); building height 4-5 storeys (21m)"}'::jsonb, '4-5 (21m)*', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0b30d7209175a99d2f38ae159326f2a7a1e66b48aa9ff972db06548b8f004725',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1f4101e3-c9da-59da-be24-45cc974a90ed', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'building_height', 'standard', 'none', 'lte', '{"value": 21.0}'::jsonb, 'm',
  '{"density_codes": ["R160"], "dwelling_type": "any", "condition": "SU27 sub-precinct (Mixed Use R160); building height limit"}'::jsonb, '4-5 (21m)*', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c3561f6838330fe82a8f5bb3f9cead8623f24d7abfd9f2f6b94b7d707f5966d0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 21.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '87f48b99-a09e-535a-b767-0645d63abe1e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'side_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU24 sub-precinct (Mixed Use/R60); minimum side setback"}'::jsonb, 'Minimum Side 
Setback
2m 3m Nil 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6f910d74dff9e56fd90413766a95572643891e8c4109023b6b39c11d08c16c0c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f0e47d6e-5411-5e7e-b35a-266f20e253a7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'side_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU25 sub-precinct (Residential R60); minimum side setback"}'::jsonb, 'Minimum Side 
Setback
2m 3m Nil 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b05bc9ab5bffe41b3c49dc53cb17f973976478e3b3540f19c426a8c6158b0c3b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3acd2d34-6e2d-586c-b4b1-bb5e155965a9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'side_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU29 sub-precinct (Local Activity Node R60); minimum side setback"}'::jsonb, 'Minimum Side 
Setback
2m 3m Nil 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c0c911a5e03e61b685033003182ed861307a5494a0a6235654c37ae18e276ea7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8bb5bede-0736-591f-afca-c2262480daf0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'rear_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU24, SU25, SU29 sub-precincts (R60); minimum rear setback"}'::jsonb, 'Minimum Rear 
Setback
3m 3m 3m 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ada65fb731ff236ab213b993a230110437dfe3bcdf353fc63a6b6a0de829407d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f95ae796-01d3-58da-af34-437749950585', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'rear_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R160"], "dwelling_type": "any", "condition": "SU27 sub-precinct (Mixed Use R160); minimum rear setback"}'::jsonb, 'Minimum Rear 
Setback
3m 3m 3m 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2ef0be3590640594c2229ee46894fee91c010cf12b844e084d341c16eb7e8f5c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f5bac695-21cc-5055-b292-84351811d97e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU25 sub-precinct (Residential R60); minimum primary & secondary street setback"}'::jsonb, '2m Nil Nil (ground floor 
commercial)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8112a37265add89e4c20e55b9f1bf9963c3d3b95dc217561051d3ea74e0ceb8c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b26ca56e-a982-535c-ab43-c3c6c8683495', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'secondary_street_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU25 sub-precinct (Residential R60); minimum primary & secondary street setback"}'::jsonb, '2m Nil Nil (ground floor 
commercial)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '215d3ab178602bbe7e61dbc731d91337d11af9070ddb68ddc14c43876df514c3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c0751a14-01ba-54b9-bb96-682dae721c04', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'plot_ratio', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, NULL,
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU24 sub-precinct (Mixed Use/R60); abutting Cockburn & Rockingham Roads"}'::jsonb, 'Abutting Cockburn 
& Rockingham 
Roads – 2.0', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd7c27a8302163ff77aa94885a98b181cf776ed356e369defd0f10d1df9650b9e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''plot_ratio'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 None vs prior [0.1,15.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'feb36f7d-3e08-5e96-ad67-fd8bcffeb899', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', 'f0e90911-6a8e-4d6b-8eaa-b881a3d3f6c8',
  'plot_ratio', 'standard', 'none', 'lte', '{"value": 0.8}'::jsonb, NULL,
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "SU24 sub-precinct (Mixed Use/R60); other (not abutting Cockburn & Rockingham Roads)"}'::jsonb, 'Other - 0.8', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7c6a89b288d32134956db8a546e40c21eca0883e2858344ea98e4b29d729c17e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4371602c-917f-529d-890a-7f1471391bd8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''plot_ratio'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 0.8 None vs prior [0.1,15.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bd2b4066-a69e-5315-ae7b-4a44be5e8ee4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', '4144182d-7cbe-4a90-9fe3-e06265bc029d',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 16.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "landmark site development within Newmarket Precinct"}'::jsonb, 'The landmark site development is permitted to be up to 16 storeys 
(and not exceeding 49m in height).', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4283f468a8a9aba850ea72d29124a47ffa22ffdc00abe8e84af32b79c1918207',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e7c66457-c9c2-5d06-8ef6-e9819eac1fdb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 16.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '97884d64-1f5d-5e66-ae4c-075d6b494d62', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', '4144182d-7cbe-4a90-9fe3-e06265bc029d',
  'building_height', 'standard', 'none', 'lte', '{"value": 49.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "landmark site development within Newmarket Precinct"}'::jsonb, 'The landmark site development is permitted to be up to 16 storeys 
(and not exceeding 49m in height).', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '79ab5ccf52e2334ef3bd40275d02deef9dc78eb612e1c90c9f01881e0bb50534',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e7c66457-c9c2-5d06-8ef6-e9819eac1fdb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 49.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1abaff85-81e9-58b4-ab2d-360ff2c53789', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', '4144182d-7cbe-4a90-9fe3-e06265bc029d',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 8.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "gateway site development (north-east of Cockburn Road / Rollinson Road extension intersection)"}'::jsonb, 'The gateway site development is permitted to be up to eight storeys 
(and not exceeding 32m in height).', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ee6ab470f41f69eac2fbcbf3cefd69426d47e853fe05e646d0ca96379381bd74',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e7c66457-c9c2-5d06-8ef6-e9819eac1fdb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''8''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 8.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7f942fc4-f359-518c-8519-2e4ed8dabaab', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '23165d75-774f-498f-b967-c317f63e5412', '4144182d-7cbe-4a90-9fe3-e06265bc029d',
  'building_height', 'standard', 'none', 'lte', '{"value": 32.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "gateway site development (north-east of Cockburn Road / Rollinson Road extension intersection)"}'::jsonb, 'The gateway site development is permitted to be up to eight storeys 
(and not exceeding 32m in height).', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c3b66109d9eb16f618d1584a36aa10756f3323c7a252c53813e2420e8eda3a7b',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e7c66457-c9c2-5d06-8ef6-e9819eac1fdb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 32.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0c3fa20e-2c7c-5969-a135-cb0bf44a13b5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '2229c7ca-1073-4c35-b56a-4c49cc35d4e9',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Cockburn Coast Robb Jetty & Emplacement Precincts - minimum building height per Assessment Criteria"}'::jsonb, 'Development shall be a minimum of three storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'bda992b8b980ccf56510f37a5506b3d79c6dcca8c49b7db39a5a0367e515a66d',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'f18a8c97-a358-5932-9e2b-68894ef8dd03', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bb0cbf7c-7eeb-5043-8551-41a90da041af', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '2835ee3a-2300-47ae-8315-4810b3e225d5',
  'side_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Levels 6+ in Activity Centre typology"}'::jsonb, 'Levels 6+ 5m to wall and 
2m to balconies 
(cantilevered/ligh
t weight only
3m 3m 5m to wall and 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '13f53e1e732ed3eefd624452e182f56339af516e7ac87ac44c6380b474fb3d8a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6c028c38-9f91-5714-be5d-4b413c3f7847', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '72083801-e03c-5749-9b8f-27f27e0e599d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '2835ee3a-2300-47ae-8315-4810b3e225d5',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Levels 6+ in Activity Centre typology"}'::jsonb, 'Levels 6+ 5m to wall and 
2m to balconies 
(cantilevered/ligh
t weight only
3m 3m 5m to wall and 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '60fa6ed6364fa7e4284d9ee3a9221ac7b3d1d3b9da3346a9f0f8bdb376e29bac',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6c028c38-9f91-5714-be5d-4b413c3f7847', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0a5d33d5-ac4b-5fa8-b688-de8e90759d2f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'cedc1cda-d424-4e8d-8d00-a72bcc9c955e',
  'ground_floor_height', 'design_principle', 'design_principle', 'eq', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Ground floor for commercial use in Activity Centre typology"}'::jsonb, 'Floor to floor heights on the ground floor should be 4.5m to allow for 
commercial use', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a0db6e6fb7558cf2be1c0df2a4c0d89369aadbfcbfb0817eb96d419f031052d7',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e6f88f71-d425-5bd6-a7d2-39419eb088f0', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''eq''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": false, "detail": "value 4.5 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4be4e7a6-c3fd-5110-bc92-8eb557231057', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'ea8d582d-35ad-415b-abff-61323b64a7a5',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "High density residential development, Levels 1-3, street setback (minimum)"}'::jsonb, 'Levels 1-3 3m Nil Nil 4m to wall and 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'eb8419a50034ece4438a061664d0619f741f163904f061103a3da245cf67e8ba',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0ced2414-fd7b-5019-920c-72e1e211d27f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b7848227-4265-549e-8024-925e9735dc1e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'ea8d582d-35ad-415b-abff-61323b64a7a5',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 5.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "High density residential development, Levels 4+, street setback to wall (minimum)"}'::jsonb, 'Levels 4+ 5m to wall and 
2m to balconies', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8cb27c772a5b22d42758f04638cda1d287da66b854f584156ae07fc64b65d41e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0ced2414-fd7b-5019-920c-72e1e211d27f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '22cbb372-6cab-55bf-8ec6-d642a39b3074', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'ea8d582d-35ad-415b-abff-61323b64a7a5',
  'side_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "High density residential development, Levels 4+, side/rear setback (minimum)"}'::jsonb, 'weight only
3m 3m 5m to wall and 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd9ad40ca8c4ca5d09dbfba79c6364b017e6b1b47fcb3efb1b0dbb3a27313282a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0ced2414-fd7b-5019-920c-72e1e211d27f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '863d4850-d88b-5004-8c1f-1beda5c73d4b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'ea8d582d-35ad-415b-abff-61323b64a7a5',
  'rear_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "High density residential development, Levels 4+, side/rear setback (minimum)"}'::jsonb, 'weight only
3m 3m 5m to wall and 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a42691272ac1d633f85d5c1ec2cd4aa9d2c9488b7c1b1cb1a6bc1954a2516a34',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0ced2414-fd7b-5019-920c-72e1e211d27f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fe3644e1-8f6d-5b23-b7c7-dd841a9fbe1a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'efe5907b-39db-44ef-a3d9-a6fea91113f4',
  'ground_floor_height', 'standard', 'none', 'gte', '{"value": 3.1}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum floor to floor height for all development"}'::jsonb, 'All development shall maintain a minimum floor to floor height of 3.1m.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dac504cb5bbafc4395bcb2bfc03a90a455fa26da127c67d54e8fe3e4a56fd87d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5ae4e501-966b-5555-b5f0-2bbc6ad54c9b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.1 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'df7dc243-e894-5224-b801-53f3dfbc5dcb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '07318820-b625-4420-adb9-1096950f4b1b',
  'fence_height_front', 'standard', 'none', 'lte', '{"value": 1.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Interface between private lots and public open space, fencing maximum height from natural ground level"}'::jsonb, 'The interface between private lots and the public open space may be fenced 
to a maximum height of 1.2m from natural ground level, but must be visually 
permeable above a height of 1.0m above natural ground level', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c64ce15f35634719e2da56d59391c19871eacf904b3499f79d8227ebbd8af501',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'aebaf13a-47a5-5522-b5a5-06b4d47d2729', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b0baf0d0-74f5-5ea7-bf8d-ba566c6b12e8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'f36707d9-8a54-48fc-bea1-c1269eda3b92',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Medium density residential development, Levels 1-3, primary street setback (minimum)"}'::jsonb, 'Levels 1-3 2m (primary)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '63a5c1ddd71aba0c107847ba57610d1a1acf8aeaa08d5dcb50e46718a407debb',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd34e2f25-5ffd-5d23-9ad9-4b4906ffae6c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7b6df7d6-930d-52b6-b9fa-94be1a43fee2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'f36707d9-8a54-48fc-bea1-c1269eda3b92',
  'secondary_street_setback', 'standard', 'none', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Medium density residential development, Levels 1-3, secondary street setback (minimum)"}'::jsonb, '1m (secondary)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '71e4de9eceb82af3b2cfe0722ba74bcb7e4aa44a5a9344fa20ed7d45c1386c04',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd34e2f25-5ffd-5d23-9ad9-4b4906ffae6c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f32c05ac-e724-5582-9b85-5bb2c032de8d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'f36707d9-8a54-48fc-bea1-c1269eda3b92',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 5.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Medium density residential development, Levels 4+, street setback to wall (minimum)"}'::jsonb, 'Levels 4+ 5m to wall and 
2m to balconies', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4ee8a16fa73460d13c7000f265310fdbee03e75e2921fd4d92e4a25769f3f2e5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd34e2f25-5ffd-5d23-9ad9-4b4906ffae6c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '54355d2e-f1ee-55fb-ade0-f8a5468ecf2f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'f36707d9-8a54-48fc-bea1-c1269eda3b92',
  'side_setback', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Medium density residential development, Levels 4+, side setback (minimum)"}'::jsonb, 'weight only
3m 3m 5m to wall and 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5cb49cfe033dc30c88d51cf5932953d2fa93934f57cc807becb3003420a0b576',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd34e2f25-5ffd-5d23-9ad9-4b4906ffae6c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd869c061-3b15-5815-a124-b9da5c91cbde', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'a7ac10b5-d1e3-4de8-9ef0-08819b21d0ee',
  'ground_floor_height', 'standard', 'none', 'gte', '{"value": 3.1}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum floor to floor height for all development"}'::jsonb, 'All development shall maintain a minimum floor to floor height of 3.1m.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'e8403b1bdfae1abb1181e9219055457d0d3b08bb35a4eab172a0552c9e4deb4d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'fdb3b6d2-3a36-5925-b265-3d2ffd310625', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.1 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '67638cd2-f5fa-5694-b5d6-f7dcc5403478', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'a7ac10b5-d1e3-4de8-9ef0-08819b21d0ee',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum development height (general rule, excluding listed exception lots)"}'::jsonb, 'Development shall be a minimum of three storeys, with the exception of Lots 
235-239 and 247-259 where the minimum height is two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'edf84ddb1101554df643a29340c678c9d33632c5d430fb31287de122fed6ff3e',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'fdb3b6d2-3a36-5925-b265-3d2ffd310625', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '040a152f-d614-5626-a85e-71f554857350', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'a7ac10b5-d1e3-4de8-9ef0-08819b21d0ee',
  'building_storeys', 'exception', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum height exception for Lots 235-239 and 247-259"}'::jsonb, 'with the exception of Lots 
235-239 and 247-259 where the minimum height is two storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '16afe132046c53853fe3c6bec9862c3709301264fe79f4e1597ba1d9925109d3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'fdb3b6d2-3a36-5925-b265-3d2ffd310625', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '38c35fff-49f7-5afa-963d-5c5b9b648afd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '761dfd9d-c61e-4caf-8504-47e8d9df9d03',
  'garage_width', 'standard', 'none', 'lte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Where garage doors service only one dwelling"}'::jsonb, 'Where garage doors service only one dwelling they should be no 
wider than 6m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7873cbd307b510b4cce05c4c5962ed704eb95725f57af52bc3341dc1daf8a695',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'c072428d-0b6f-5013-b1d9-a5a624482db3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [1.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '14b1f02e-cc57-5ae3-a6c3-725db1c82ced', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'b2b11a23-d884-48d3-a799-2a5aad60664c', '75facf68-a8f8-42c3-906c-35f94d308cd6',
  'ground_floor_height', 'design_principle', 'design_principle', 'gte', '{"value": 3.9}'::jsonb, 'm',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Where commercial uses are not viable in the short term; recommended minimum ground floor tenancy/dwelling height for adaptability to future commercial uses"}'::jsonb, 'incorporating a 
 recommended minimum ground floor tenancy/dwelling height of 3.9 
 metres above the finished ground floor level.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '83199ecb387a367676f51487fac75661174a677cdfaaa46a91a5e874c6b9e16c',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e12d1cf3-de99-58ce-a623-827c310e9da5', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": true, "detail": "value 3.9 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  'd6f424da-c530-50b7-8c8d-7542a3398f55', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'b2b11a23-d884-48d3-a799-2a5aad60664c', '3b401376-90ec-4742-9635-88b4f744f693',
  'building_storeys', 'design_principle', 'design_principle', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Buildings adjacent to Rockingham Road, to frame the street and encourage passive surveillance"}'::jsonb, 'buildings adjacent to Rockingham Road are encouraged to be a 
 minimum of two storeys in height', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '15393fccc1f0b12f7a2d184ef0dff2ccd7fcebff94f046b33e034c17988cb7e9',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'efdb8d59-592b-584d-b6b7-558891310987', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  'b598d8e1-402c-508b-9cc6-cade05c3f726', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '269c77a6-7a15-4948-ad47-ae37b8a0db6e', '8b2a5a3a-f676-47ee-b885-ba17a27f99d7',
  'retaining_wall_height', 'standard', 'none', 'gt', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Planning approval required for subdivision retaining walls exceeding this height above natural ground level which abut areas of public domain including primary and/or secondary streets and/or public open space"}'::jsonb, 'Planning approval is required for subdivision retaining walls that exceed 2m in 
height above natural ground level which abut areas of public domain including a 
primary and/or secondary streets and/or public open space.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '55405949f74069d25abd7ee2420aeeb5587717cfcf7616f2cb94fc8a6c8823e9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '89feff6a-bda1-5cc1-b848-59c61ae89105', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gt''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'de3a4d13-ed3e-5e3a-88d3-ae025d05c583', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '269c77a6-7a15-4948-ad47-ae37b8a0db6e', '8b2a5a3a-f676-47ee-b885-ba17a27f99d7',
  'retaining_wall_height', 'standard', 'none', 'gt', '{"value": 0.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Planning approval required for subdivision retaining walls exceeding this height above natural ground level which abut existing residential development outside the subdivision area"}'::jsonb, 'Planning approval is required for subdivision retaining walls that exceed 0.5m in 
height above natural ground level which abut existing residential development 
outside the subdivision area.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '81a37882f5af87d688e58ff50d2f15fb9c745c43f913eb2788d77eed28098377',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '89feff6a-bda1-5cc1-b848-59c61ae89105', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gt''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 0.5 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cac11fe6-3d1f-5ec3-bec1-5da4dfe68894', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'ab4d97fb-5f44-45bf-9867-813332523d8b', '38019e6d-3782-4367-b154-47eb79269708',
  'fence_height_front', 'standard', 'none', 'lte', '{"value": 0.75}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Fencing within 1.5m of a vehicle crossover that may impede visual sightlines and pedestrian/vehicular movement"}'::jsonb, 'Fencing which may impede visual sightlines and pedestrian /or 
vehicular movement is required to be no higher than 750mm within 
1.5m of a vehicle crossover.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '86f33f003301ee5892dfda7f74b4603416ff068961d93e52a38cd2d546acb045',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '61ec5235-0072-5b73-b7e1-c04d805bfa10', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0.75''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 0.75 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1e28540a-3058-5e5f-be78-df86324e8458', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '3d036ede-9927-4c4e-b7b1-7ce3a7178cd6', '3589d8c3-d916-42de-9a92-04cfc00825cb',
  'garage_width', 'standard', 'none', 'lte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Garages/carports fronting laneways under a Local Development Plan"}'::jsonb, 'Garage/carports to laneways limited to 6m in width or as per the R-Codes, whichever is the lesser requirement.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9460a8c26c1c31bd5a007801d42ad69f09e72a6f1248a3c88483cf332a138151',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '739d63e6-c3aa-514d-81c8-d341b22bd09f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [1.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd6a67fab-2ff5-5cef-8f9b-a343c54cba1d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '016c2373-3348-41c0-a811-4b239c339b54', '5e5f9e96-ca9c-437e-9d9a-810f9dfe5bfe',
  'building_height', 'standard', 'none', 'lte', '{"value": 73.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum height (AHD) under Jandakot Airport Obstacle Limitation Surfaces for the subject area"}'::jsonb, 'This  stipulates a maximum height of 73.5m AHD for the subject area', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '266b780ee4016465292a9761bae00cbd37e5c5e104177d2eac35f3ded5d65681',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd7cfc908-18f3-5f7b-be9a-90c1d7110ce5', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 73.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8f4d2c18-ebde-5e4f-bd5e-7800f77a4602', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', '2a818701-499a-454d-bc77-27235a1e1a79',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 17.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum building height guided by Jandakot Airport flight path contours across Structure Plan Area"}'::jsonb, 'the maximum height will be guided by the limitations imposed by the Jandakot Airport flight path contours (approximately 17 storeys)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '958964a4ce6f0cd7e9b61c916272679abdd55955ed84644fd9de24dc142967ad',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6201cbb6-d469-5d7a-9187-9f7645afb36b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 17.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a931a7ad-af87-5c10-9ba9-95f0e5c6e057', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', '2a818701-499a-454d-bc77-27235a1e1a79',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum building height across the whole Structure Plan Area"}'::jsonb, 'set a minimum building height of 3 storeys across the whole Structure Plan Area', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ed8019297ccddfddb92e2c8960ccd7f086e790794667e2935c7c31fd4d8a60de',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6201cbb6-d469-5d7a-9187-9f7645afb36b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2a4d3159-1e84-542e-88ae-b4c6686242d9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', '2a818701-499a-454d-bc77-27235a1e1a79',
  'building_storeys', 'exception', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "Reduced minimum for attached grouped dwellings (terraces) restricted to land zoned Mixed Use (Residential, Retail and Commercial)"}'::jsonb, 'In some locations the building height may be reduced to two storeys to allow for attached
grouped dwellings (ie. terraces), however this would be restricted to land zoned Mixed Use (Residential,
Retail and Commercial)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd42b23e48ff0dd9b31eb2615af11f8116111d5e2403aafb9b07af59abc34207f',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6201cbb6-d469-5d7a-9187-9f7645afb36b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cf6d4708-66b6-585c-895b-9d2f046155d5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '118aaab9-e1d1-4106-a407-77084164e987',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 160.0}'::jsonb, 'm2',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "R50 site area requirements - minimum site area (battleaxe and minimum)"}'::jsonb, '(min 160m/two.numerator avg 180m/two.numerator/comma.numerator battleaxe 160m/two.numerator)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5ff6afe1ef6f6ce027aa07237acfaa1b20f71629b89c0a094b9d569da22b8f88',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '80db7a10-7bcf-551b-aefd-9c3b3e83ed6a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 160.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a786e272-b153-58c8-a48a-d1c2644e2c11', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '0dc8408f-0c7c-4504-92e4-9ab48841f4f7',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "Secondary private open space minimum area for grouped dwellings"}'::jsonb, 'Minimum area of 10m/two.numr', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a34aace1a8733bbceefecc30230e327302f0bb3483af542fd11ada54867c1a6f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9ed3c8c7-3e0c-58c2-abcb-2593a2b60f04', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '654d639a-62a6-50ee-8f4c-1961573201a0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'e066a193-fe0e-4d85-9f72-06b2e8576cab',
  'soft_landscaping', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 15.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum soft landscaping requirement per site, applies to single house, grouped dwelling and multiple dwelling"}'::jsonb, 'minimum 15% soft landscaping requirement per site', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '328db38da837f4437234e63b74ad93b868c8246cea69301922b4d448cd70a130',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'd96c833c-693d-53db-b794-dd373cf93cb2', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b203ff2a-dafd-5fd5-b752-9a9477be948b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '739f840b-dc92-4500-8d26-5e9e79b6469f',
  'communal_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "More than 10 dwellings - minimum communal open space requirement per dwelling, up to maximum 300m2"}'::jsonb, '6m2 per dwelling up to 
maximum 300m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '572651fc7b0cfb7f3105710b4c05c0b570cef7f4c32a30b91da74327b6bf9dc3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3a51db96-3fbe-564a-b1ac-357085e5c284', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''communal_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 6.0 m2 vs prior [10.0,2000.0] [''%'', ''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum site cover"}'::jsonb, '3.1 Site cover C3.1.1 Maximum site cover of 85%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ba3714a4827a84243878ae230b9b3eeed185bc737f512617fbf4dc29c6d702ba',
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum two storey building height"}'::jsonb, 'C3.2.1 Minimum two storey building height', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'daf0928af575ff95fce477d72f3e9cf17376b7f8fe5974d2e30d7a7e5ba0b503',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9c53543e-653f-5bdf-aced-5ed77b74bd1a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum four storey building height in accordance with Table 3.2a"}'::jsonb, 'Maximum four storey building height in accordance with Table 3.2a', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9020d59d92c30b5fd89d9a3c5c25f82a3099e84624f60abdd6d3a26406dc2cc6',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9c53543e-653f-5bdf-aced-5ed77b74bd1a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1868d07b-9ee6-5372-b688-031c4efe88bb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8ae8f1e-8d09-452a-a2f6-ad5708151e0e',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Adjoining laneway or right-of-way where it is the primary street to the dwelling"}'::jsonb, 'Adjoining laneway or right-of-way where 
it is the primary street to the dwelling 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0aaac51233e3a193d01d7ef6cdffbc03c19b846bf9a3d50e396b4b6b1bf3001a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '484c41d2-8537-5e14-b980-355d119e694a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'da6709a8-2fc1-5e34-88d9-a8c400e11a17', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R30-R35"}'::jsonb, 'R30 – R35 3.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6cfda468fd624ba36c2f313d0bde4cd1fd6722b6e2cec04317b0d7c892dc21ed',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd1e2356d-b731-5aab-8e2a-4ef573044ed2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R40 and above"}'::jsonb, 'R40 and above 3.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '72d4abb5e1f13142f00449cbf007f403725998e19eaa5b6fe1dc22c1598f32a3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e281f780-861a-5643-84fa-ff0711680828', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "R50 and above where frontage is 8.5m or less"}'::jsonb, 'Where frontage
is 8.5m or less 7m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8d5393123114a37e627865a07b8b7392d22973538f39c206081f1f16986450d5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ae067a1c-26ce-5793-b5d1-cdf1d5e9ff0b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "R50 and above where frontage is greater than 8.5m"}'::jsonb, 'Where frontage
is greater than
8.5m
7m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '25dfe08fbb3cd09556ebd9830f04161830ba8928e258ba1f5a6a016c6f826735',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c08f343f-b9eb-56f0-9741-f179af40baad', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'boundary_wall_length', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 14.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "R50 and above - maximum wall length before required setback"}'::jsonb, 'Maximum 14m length, at which point the wall  is to be set back a 
minimum of 3m measured from the lot boundary  for a minimum length 
of 3m. Applicable to all lot boundaries.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '309c302dccdaeaed5d952f04c419fd2519e7cc1a738e6401ad7bec29901a6b9d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd535e441-a004-5cc1-a4f9-4d287e7f2515', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '2e8d74c5-c0ab-48da-8e6a-fa700477f159',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "1 storey boundary wall"}'::jsonb, '3.5m 
(1 storey)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f4b48e21a16d06aff78d94397d8b781be6799dd754e1fc2ed674588358a9202d',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ca014156-2392-5076-980c-39b713e42b98', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": false, "detail": "no normative word found in clause text; searched for: at least, maximum, minimum, must, no more than, not exceed, not less than, required, requirement, shall"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd240cbb8-afe0-57db-9c8f-b42117421d67', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '2e8d74c5-c0ab-48da-8e6a-fa700477f159',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "2 storey boundary wall"}'::jsonb, '7m 
(2 storey)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b76169c438dba4f9f5e8b96203b97bf215a7aad24721fd73b745a02201d26658',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ca014156-2392-5076-980c-39b713e42b98', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": false, "detail": "no normative word found in clause text; searched for: at least, maximum, minimum, must, no more than, not exceed, not less than, required, requirement, shall"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9b9dce01-8e7a-5876-9fd8-3666e0e36b21', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '2e8d74c5-c0ab-48da-8e6a-fa700477f159',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 13.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "4 storey boundary wall"}'::jsonb, '13m 
(4 storey)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3f1523e7e516a827401200628d2a4f731e5a5b6ff2e3aafe12ba061fe18a323f',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ca014156-2392-5076-980c-39b713e42b98', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": false, "detail": "no normative word found in clause text; searched for: at least, maximum, minimum, must, no more than, not exceed, not less than, required, requirement, shall"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 13.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '971d2d3b-8096-5009-91c0-663580673783', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '222a5d6d-a031-4464-aca9-f76b1681b04d',
  'fence_height_front', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 0.9}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Street fences"}'::jsonb, 'C3.6.7 Street fences to not exceed 900mm in height.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0d03fc4c34304bef83d64b21bd9ebd8f1e07b38c463bda97f7837c637e320aa6',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '1d12fed6-bc9d-5c4e-8b5b-ca521086f92b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0.9''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.9 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5f291543-96f4-5089-be7a-45796f0cb6de', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3ce72f43-5897-42c9-b338-6863f3f05171',
  'garage_dominance', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "garage door and supporting structure as proportion of frontage width"}'::jsonb, 'Garage door and supporting structure may 
occupy up to 50% of the frontage width', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f5c1b47672e8ed988b35e7337be56754d8c6954d3a2ed4188203de9ed2afdad7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '705c3da7-362f-5500-b47f-5f3a05b49b6b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_dominance'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '09f31a29-47c7-509c-9514-0415596cb2ba', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3ce72f43-5897-42c9-b338-6863f3f05171',
  'garage_dominance', 'exception', 'deemed_to_comply', 'pct_lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "where upper floor or balcony extends more than half the width of the garage"}'::jsonb, 'Garage door and supporting structure 
may occupy up to 60% where upper 
floor or balcony extends more than 
half the width of the garage', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0176abc8d21c75e03e5a7efd32e9bdd88711b8f096ba5990d52d6864d66bf19b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '705c3da7-362f-5500-b47f-5f3a05b49b6b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_dominance'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a24dfdd8-b826-5657-9e95-242b4c6e0d1f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'wall_height', 'standard', 'none', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category A building - maximum height of wall"}'::jsonb, 'Category A 3.5 5 7', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9cae6002756e6113fbbee3fbb7da31cc179932adcd17d35b54004f532cb38907',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '64aee86f-adcb-5746-90d9-37b5633960b3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 5.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category A - maximum total building height for gable, skillion and concealed roof"}'::jsonb, 'Category A 3.5 5 7', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '69ece47440ed9541f3ccfcc06734799e166b4bc59ec2b565581823bb6844799c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7242cfe4-3b13-5805-b44f-d28ada0a94e4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category A - maximum total building height for hipped and pitched roof"}'::jsonb, 'Category A 3.5 5 7', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c2bafa3721c8323b741c295d792d7b9c32477aab4ee9035c299872c12d7788dc',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8ddbf740-3b14-52db-bbbb-3a704fcb40df', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'wall_height', 'standard', 'none', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category B building - maximum height of wall"}'::jsonb, 'Category B 7 8 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd068c1487065945967e083bd71f82f9baa5b279e0c729df4c6482bf139cf0e71',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ea43e522-6a83-54be-9aad-6244f323d04c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 8.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category B - maximum total building height for gable, skillion and concealed roof"}'::jsonb, 'Category B 7 8 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '670150873024d350d5fbf9f8ecbf8cc345f315f11475f6a295893658cecc54f5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 8.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'be1a80be-3b1c-5213-a9e9-7fa4992cff74', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category B - maximum total building height for hipped and pitched roof"}'::jsonb, 'Category B 7 8 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1eeaa19ef0a2699d09c3ba21972c66e5813ad65515baa4ffcc1fe09c8b11f566',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '98b41371-fd51-5a32-bbce-9ced7ffb76dc', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'wall_height', 'standard', 'none', 'lte', '{"value": 9.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category C building - maximum height of wall"}'::jsonb, 'Category C 9 10 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd665ad4a7b0c0eef4dbcf83a106d58fabfe162612e62668cc37b8a5bb3c8b93b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 9.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ee50af94-e2dc-536b-8036-fa6ac3063845', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category C - maximum total building height for gable, skillion and concealed roof"}'::jsonb, 'Category C 9 10 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '549b16572d57242a0548d543be40dd4aff096cd69491683f38243b4dff6caf36',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6f8f5d0c-851b-5fa0-9c72-bd58ae9e34c0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 12.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category C - maximum total building height for hipped and pitched roof"}'::jsonb, 'Category C 9 10 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0c121ba38526b2a4789d18a2c5749add0cd629cc1ef7e9a6be4cbd9ba0fa6d30',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 12.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '04362011-1ab6-5bcc-b568-d4f82c0d2efc', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '0f3d8e45-4b51-4076-8248-c550f12e6739',
  'garage_dominance', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Garage door (or garage wall) facing primary street not to occupy more than 50% of frontage at the setback line"}'::jsonb, 'A gara ge door and its supporting structures (or 
a garage wall where a garage is aligned parallel 
to the street) facing the primary street is not to 
occupy more than 50 per cent of the frontage at the 
setback line as viewed from the street', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '95165371c40dff05dd134aa227e209fcff778e4e9a3865d4f8720321c40b6c3d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '73146b04-04bf-52bc-ae2c-e61c99b7d6ab', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_dominance'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a8150d57-ec6b-5ad2-8b51-bd278346451c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '0f3d8e45-4b51-4076-8248-c550f12e6739',
  'garage_dominance', 'exception', 'deemed_to_comply', 'pct_lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Increased allowance where an upper floor or balcony extends for more than half the width of the garage and the dwelling entrance is clearly visible from the primary street"}'::jsonb, 'This may be increased up to 60 per cent where 
an upper floor or balcony extends for more than half 
the width of the garage and its supporting structures', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fdf08fcfe4b08a4a94dbf333baa573565acfa09bce6249fc4ecccae7f266391f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '73146b04-04bf-52bc-ae2c-e61c99b7d6ab', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_dominance'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a923b84d-2656-5f52-8e42-71f5da89c1e5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '9ebfd036-5742-4607-9785-aa727ddc9e59',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum dimension for a space to contribute to outdoor living area"}'::jsonb, '(M x M) = Minimum dimension (4m) for a space 
to contribute to outdoor living area.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '77ac920a903b7a086318e57c501595898ba7c939f36725ab72ae27716bfc766a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '51cc59a7-a26b-5c7f-bde2-10ee164bf5e1', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c3306602-a272-53f3-ad0b-75e236723847', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c5d9c6c5-48ed-440f-a33e-40e15fae9c09',
  'fence_height_front', 'standard', 'none', 'lte', '{"value": 1.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "maximum height of visually impermeable fencing on primary street"}'::jsonb, 'H ma
ximum height of visually impermeable fencing 1.2m*', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '10e5f3350583486c625cd76ff06e1eec9e310803edc6fd7cf91904183efb391b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '1333cade-3f0f-5328-8477-1ae5ddb8398d', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd5993d32-199f-5259-9a1f-15bd51deb7b0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5a27db93-d539-4ba4-a7ac-ef3a85f0f67f',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 2.7}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "small outbuilding wall height"}'::jsonb, 'does not exceed a wall height of 2.7m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1f7b8f6dec6cd4f0ddda0bfce0a1005df7c7d69f132a106dd77e7d6fca1dadd8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '140b9bb6-0eef-51d4-a5c0-72d9a52d69a9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.7 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd05663a8-8fb8-5f1e-89e7-897628fd35e7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5a27db93-d539-4ba4-a7ac-ef3a85f0f67f',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 2.4}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "large and multiple outbuildings wall height"}'::jsonb, 'does not exceed a wall height of 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '500a210bfc0a0af0adda0c0d79aa8b3cedf9d6f039aadda8d4bca231d7082da7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '140b9bb6-0eef-51d4-a5c0-72d9a52d69a9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.4 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1a83c5bb-3455-539e-99f1-a3a2691be352', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5f3f2e12-f453-4f6e-a08d-82b35b43f12c',
  'garage_width', 'standard', 'none', 'pct_lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum width of garage doors and supporting structures as a percentage of frontage (Figure 8c illustrating clause 5.2.2 C2)"}'::jsonb, 'garage doors and its supporting structures not more than 50% of frontage', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b9f55b52fce78a4b172cea8e84fe8b9c3b0c21490db43017cb1c50959102bd57',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '635ab512-7547-5f44-b1fb-d7e5872338a9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 50.0 % vs prior [1.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0772a3b8-e75c-5a34-8e8f-53f7c233a2d4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '968af17b-e024-408a-9ca9-adcb02a2f19c',
  'outdoor_living_area', 'standard', 'none', 'pct_lte', '{"value": 10.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum unenclosed covered outdoor living area counted toward open space, expressed as percentage of site area (Figure 6a, clause 5.1.4 C4) - lesser of 10% site area or 50m2"}'::jsonb, 'Unenclosed , covered outdoor living area  
(to a maximum 10 per cent site area  or 50m2, whichever is lesser)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2ca85c97ddfbed12e580ff92afedb1f0c2e4be52478d3c937a6a1c9eb1eeba9f',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '752265cc-4e7f-5be2-b64e-bfa190ef349c', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Unenclosed , covered outdoor living area (to a maximum 10 per cent site area or 50m2, whichever is lesser)''"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 10.0 % vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '39fe4214-60b6-5a97-9db9-088e716e05ed', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '968af17b-e024-408a-9ca9-adcb02a2f19c',
  'outdoor_living_area', 'standard', 'none', 'lte', '{"value": 50.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum unenclosed covered outdoor living area counted toward open space (Figure 6a, clause 5.1.4 C4) - lesser of 10% site area or 50m2"}'::jsonb, 'Unenclosed , covered outdoor living area  
(to a maximum 10 per cent site area  or 50m2, whichever is lesser)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f0845b52b9406297f2a1571e809a8fe6190cc76181f9ce58d25c40567dec9228',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '752265cc-4e7f-5be2-b64e-bfa190ef349c', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Unenclosed , covered outdoor living area (to a maximum 10 per cent site area or 50m2, whichever is lesser)''"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 50.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b2ce58f9-7663-53d1-b0aa-32f6cbdccab8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5c4add6c-524c-440a-a009-5c61d2d1b684',
  'site_area', 'exception', 'deemed_to_comply', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "minimum site area when reduction provision applied; applies to single houses and grouped dwellings"}'::jsonb, 'for 
single houses and grouped dwellings, no 
site is less than 100m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b52de772957f468b5d87ac2dadca1aaad9df4902f5ae841fbe142662d2839e5e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '082f5e63-4724-57c6-98cd-e3baaa3b9d54', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '05cbac22-c38f-54f1-aad3-1783f2643496', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5c4add6c-524c-440a-a009-5c61d2d1b684',
  'site_area', 'exception', 'deemed_to_comply', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "minimum site area when reduction provision applied; applies to single houses and grouped dwellings"}'::jsonb, 'for 
single houses and grouped dwellings, no 
site is less than 100m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'be99b533b9afba2cdbed5e9afba9e21c3a05c62c0ff978b8d431e18fcd728c52',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '082f5e63-4724-57c6-98cd-e3baaa3b9d54', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f0d9eb8a-b7ed-5bad-9050-6c67234cc5dd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '83a8a761-48ae-4f8b-9bb9-52c76d7313fe',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimum length and width dimension of outdoor living area"}'::jsonb, 'wit
h a minimum length and width dimension
of 4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ab7afc954445b9a73288785f2934fefd36821c0e59dbce400842a160c733dac0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '8f032384-d204-5157-a468-9163520d50ec', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b50ef117-a95e-5753-875f-09da63dbbe4a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'e3af4f06-6ad7-42df-9573-76b0a8aa65e7',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "garage setback from the primary street"}'::jsonb, 'Garages s et back 4.5m from the primary street', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dddefb062d63d0f4a963e6257ef886f950a681894b65fe094a3ba430aa3e0382',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'b4b8f599-f3b4-5cd5-8b5d-8c9449b90b40', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '88275786-0b35-5a73-8cc8-1f1920407a8e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'e3af4f06-6ad7-42df-9573-76b0a8aa65e7',
  'primary_street_setback', 'exception', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "reduced garage setback where garage allows vehicles to be parked parallel to the street with openings in the wall parallel to the street"}'::jsonb, 'to 3
m where the garage allows vehicles to be 
parked parallel to the street', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1f308a77a5526f6601d0b65f4d39754dc9a44855898fdd97f468fed884c0dc1c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'b4b8f599-f3b4-5cd5-8b5d-8c9449b90b40', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cc785418-31ba-5891-8e79-e465d707bc8d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 40.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Site area greater than 220m2; primary garden area per dwelling"}'::jsonb, 'Greater 
than 220 40', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '748a537804bb2d88d035cf8d4c7ddeb9e947f87cf9e01486cb7ff949e9e6a56c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 40.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b533079b-717e-51fc-ab8e-21f68dbcdf18', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 35.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Site area 191-220m2; primary garden area per dwelling"}'::jsonb, '191-220 35', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3f3b49377bd6b437e13b952c1c23876d68373a49a85a0b7597f87ac57add01e3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 35.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '23c04c6b-e722-59da-9aa3-9a469fa0a89e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Site area 161-190m2; primary garden area per dwelling"}'::jsonb, '161-190 30', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fd720d5071b5e7e2dc5629ab0cc5037dd46480351367d1f0ac5b9b933bd230a8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 30.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '960cff19-dc99-5d10-a1e9-1aa6087b8f9e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 25.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Site area 131-160m2; primary garden area per dwelling"}'::jsonb, '131-160 25', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '646a5244c759e38db42a86a69a57e93c9bba89e7229ec5b4458a8516074261e9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 25.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '72cfd76c-5da4-59f6-abe0-0901883330bc', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 20.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Site area 100-130m2; primary garden area per dwelling"}'::jsonb, '100-130 20', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a722f5eddf45c76c8704a8ad84205da33fab1894071788bdf5178766e6357088',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 20.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '957aaf5d-174e-598b-a8cb-ba64a08f075b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd17b2128-8ae6-4f8d-ba54-5cee27f0d519',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Single consolidated uncovered primary garden area minimum area"}'::jsonb, 'a sin
gle consolidated uncovered primary garden area with a minimum area of 15m 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3872358cf6d0cb7387f0c12dcdfbeae5641591fb251392466d57332444be7e5a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4987f8e1-9617-5c64-93a8-4d1f9f9cfdcc', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b9035cd3-36ec-508d-a8d5-7ca24f943a68', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '84f3b725-050b-4c07-912c-694f4d8432f6',
  'private_open_space', 'exception', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "Secondary ground level private open space for grouped dwellings with site area 161m2 or greater"}'::jsonb, 'a min
imum area of 10m2 and minimum dimension 
of 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f2ecdda5dfcd9c1a2445bf30f6ac59257129979a4dae9e53247550747456e7ab',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '45949fb2-ebff-551f-a3b0-f8fb2e179dd4', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd0525dc8-0d9f-533c-87b3-8f5c9869e891', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 8.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Studio / 1 bedroom dwelling"}'::jsonb, 'Studio / 1 
bedroom 8m2 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5dfdb0285a17b0a5cfaea1d62bc6979b6f5127e43b2d51b3118fae641e232d07',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 8.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '18b4b011-ea59-5474-971f-bff7d071e6b2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "2 bedroom dwelling"}'::jsonb, '2 bedrooms 10m2 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '30a0e6c5d8f5b7dd52d1c58cd5c715e14f28eb26b56c3352998596cbb2216fbd',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6c9a7738-e5be-5df6-8758-b7eda183f483', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 12.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "3 or more bedrooms dwelling"}'::jsonb, '3 or more 
bedrooms 12m
2 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '904d458fda1bfce2cc1889082b9ad797f8219b4193fee45a3c6b6d44ea5bdced',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '636dee79-64a5-5f29-b9a8-a38a9a4c0623', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'private_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Ground floor dwelling"}'::jsonb, 'Ground floor 
dwelling 15m
2 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a70fe12707f1083d8ba324e6bc1e528a5995cf14be6347cb5ac5bc7aa3ebe878',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''private_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m2 vs prior [4.0,500.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c57c72d8-74b1-5b56-b3e1-04a433515369', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4f808bea-7829-49c3-91e3-2d96b2cacf3d',
  'site_area', 'exception', 'deemed_to_comply', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": ["R50"], "dwelling_type": "single_house", "condition": "Accessible dwelling (gold level universal design) or small dwelling; site area reduction up to 35% permitted provided no site is less than 100m2"}'::jsonb, 'for single houses and grouped dwellings, no 
site is less than 100m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8c58636a936a6b191d928b3e1e6a5fa66c5a0428dd86896fb914e1b7c28fb805',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '200e9da1-703f-5a7d-b15d-fc1656fd80dc', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '41ff545e-0540-588b-ae84-ed64819131e2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4f808bea-7829-49c3-91e3-2d96b2cacf3d',
  'site_area', 'exception', 'deemed_to_comply', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": ["R50"], "dwelling_type": "grouped_dwelling", "condition": "Accessible dwelling (gold level universal design) or small dwelling; site area reduction up to 35% permitted provided no site is less than 100m2"}'::jsonb, 'for single houses and grouped dwellings, no 
site is less than 100m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5c1904d948be5cd6e7ec2efcc1eda340e1b413e6d8acae043d760ace3bacb1a1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '200e9da1-703f-5a7d-b15d-fc1656fd80dc', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '57b7b1eb-9940-57e1-9923-a42951fc9d84', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ee2873ac-5af1-4e48-87ac-ef28a64b177a',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm2',
  '{"density_codes": ["any"], "dwelling_type": "multiple_dwelling", "condition": "Balcony or equivalent opening directly from primary living space for each multiple dwelling - minimum area"}'::jsonb, 'Each multiple dwelling is provided with at least one 
balcony or the equivalent, opening directly from the 
primary living space and with a minimum area of 
10m2 and minimum dimension of 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ab4224ce0a9f35e8aaea40ed0983e18fa5e66336034766693c69fb74041c5adc',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '52d2a1dd-4674-52f9-8e3b-9edac1233a79', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Each multiple dwelling is provided with at least one balcony or the equivalent, opening directly from the primary living space and with a minimum area of 10m2 and minimum dimension of 2.4m''"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  '637382d8-ce9b-5145-90cc-16df9834625c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c20e0e87-11c6-4683-83bf-e0950400a5a6',
  'garage_dominance', 'exception', 'deemed_to_comply', 'lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Carport setback reduction (up to 50% of minimum primary street setback) permitted where carport width does not exceed 60% of frontage"}'::jsonb, 'the width of the carport does not exceed 60 
per cent of the frontage', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'e06d34b40829c7774f6da9ef5b03e8ab6c9d61e0b64b0b527a075681b5664500',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9e9b6694-50cb-5e0c-80aa-50e68d433844', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''the width of the carport does not exceed 60 per cent of the frontage''"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_dominance'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  '79beda7c-94f2-5acc-8bd1-d1ed347e02bf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'bec362ea-6fb4-4477-8e61-b6f84b419ed7',
  'soft_landscaping', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, '%',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Minimum soft landscaping per site"}'::jsonb, 'Development to provide a minimum 15% soft 
landscaping per site', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '22b1f620ab463d0399f7fec86e0fc5ac7b3b2b1bc43ff7ba8988ef1ad3848bc3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'aa409ae9-1dac-5614-8649-2b141057b6c3', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Development to provide a minimum 15% soft landscaping per site''"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();

COMMIT;

-- Summary (this slice):
-- {"clauses_seen": 55, "clauses_no_atoms": 0, "atoms_emitted": 130, "atoms_validators_passed": 93, "atoms_validator_failed": 37, "atoms_missing_clause_context": 0}
