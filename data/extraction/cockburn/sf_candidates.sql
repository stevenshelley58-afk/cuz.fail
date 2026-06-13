BEGIN;
-- WP6 Sonnet (3rd-family) candidate slice. Idempotent: re-run safe (PK is uuid5'd).

INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  'fcf7bc13-0542-57a6-bdd3-289ff4d79b5a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '5e06707d-7f5b-442a-bd69-b5d1d86ce321',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Buildings setback from any boundary adjoining public parkland; setback area shall include space for landscaping and if necessary an outdoor living area"}'::jsonb, 'Buildings shall be setback 4m from any boundary adjoining public parkland.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '43076d1d8c203f5452d9a8113015d9ba77ca29495dd009af5ec6372c5ffa565c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '065416e9-33f5-5a7c-8884-72c141e03d6f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2a8419bc-d77e-5caa-a045-133464e0f836', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '3c9c42f2-675c-4e45-ae9e-3ac63c2a67b1',
  'building_height', 'standard', 'none', 'lte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Building on Mixed Business lots which abut residential lots, at the residential boundary (wall may increase 1m for every 1m setback from residential boundary)"}'::jsonb, 'Building on the Mixed Business lots which abut residential lots should not be higher than 3.0m in height at the residential boundary.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5c85d61942a1ba7ae28345a5522e74fd83fde77aad7b9d4c2f4579a47e61fc04',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '2d9e65c7-9bf0-5463-845e-4c4b38adf49f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '81150610-7220-554f-994f-1bc0533ec635', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd0329abc-e488-4195-9851-11364ea2fc11', '212e1e11-2bd8-402b-a9f0-bac650b0050e',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "All setbacks from front boundary unless noted otherwise (Glen Iris Estate bulk earthworks plan note)"}'::jsonb, 'ALL SETBACKS TO BE 6m FROM FRONT BOUNDARY UNLESS NOTED OTHERWISE.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b3e8bfb980213f1f2d4a0ff79ac073b54ffe918b1d3860da71fe95dc94923d51',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '27c1651b-bc7b-5f10-b93a-d775470f7864', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd2b22107-e0c1-542c-8d8d-dc876365028b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '82347695-1655-4c46-a2cd-1933639a7f6c', '86ad5db5-f9d5-478e-9461-6c360c765ed0',
  'building_storeys', 'design_principle', 'design_principle', 'lte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Internal residential development (not along Rosalind Way and Benedick Road frontages)"}'::jsonb, 'Development internally may extend to a maximum of 3 storeys in height', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0cf6bad8f118a1959316e3eeceb4f2cce5b02d399e3fed86019bc7d16c8bc154',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '40d38f5c-c1ec-58f9-9e52-01e7d07d3822', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'dfdee3d9-5c1b-51c8-8488-a893345d6df8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd5ed399e-d1d9-4dbb-9f80-3aad1d46cf54', '1b4a32e7-8ccd-4d60-b418-123be4ba0362',
  'outdoor_living_area', 'standard', 'none', 'pct_gte', '{"value": 10.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "OLA area as percentage of lot size, or 20m2 whichever is greater"}'::jsonb, 'An outdoor living area (OLA) with an area of 10% of the lot size or
20m2, whichever is greater', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4c957c29e48b8e91afff13c2b7f26520e617eb997099834781cb08d46c76f138',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a60db9e1-f542-5518-8497-8c7c164a33eb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 10.0 % vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8ad46926-1d3f-5f4a-94e3-213936dd20d8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd5ed399e-d1d9-4dbb-9f80-3aad1d46cf54', '1b4a32e7-8ccd-4d60-b418-123be4ba0362',
  'outdoor_living_area', 'standard', 'none', 'gte', '{"value": 20.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum OLA area, or 10% of lot size whichever is greater"}'::jsonb, 'An outdoor living area (OLA) with an area of 10% of the lot size or
20m2, whichever is greater', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5c55439c0ed9012f58c5fd4809a885d17afffcc7b6574d0f1929afff7956a0b9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a60db9e1-f542-5518-8497-8c7c164a33eb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 20.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f6fea746-2393-51a0-95b5-f8684f05cae3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd5ed399e-d1d9-4dbb-9f80-3aad1d46cf54', '1b4a32e7-8ccd-4d60-b418-123be4ba0362',
  'outdoor_living_area', 'standard', 'none', 'pct_gte', '{"value": 70.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "At least 70% of the OLA must be uncovered"}'::jsonb, 'At least 70% of the OLA must be uncovered and includes areas
under eaves which adjoin uncovered areas.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ace795101e01d5f94b37b250b206bca560005689c92d686474da22629b1830b6',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a60db9e1-f542-5518-8497-8c7c164a33eb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 70.0 % vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '91c21a1d-f4dd-5c5a-ae7e-876fc507855c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd5ed399e-d1d9-4dbb-9f80-3aad1d46cf54', '1b4a32e7-8ccd-4d60-b418-123be4ba0362',
  'outdoor_living_area', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum length or width dimension of OLA"}'::jsonb, 'The OLA has a minimum 3.0m length or width dimension.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0f760ad8206c0df3cf60b4dd526cf7dfa1ffbd4b3f26c56346a17282c3e6abbb',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a60db9e1-f542-5518-8497-8c7c164a33eb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 3.0 m vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8ef7c320-0020-5504-b136-afabd1a68290', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd5ed399e-d1d9-4dbb-9f80-3aad1d46cf54', '1b4a32e7-8ccd-4d60-b418-123be4ba0362',
  'building_height', 'standard', 'none', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Wall height threshold below which no maximum overshadowing applies"}'::jsonb, 'No maximum overshadowing for wall height 3.5m or less.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f1710b4fdb0c3d8352758ceca653a82d5dad5370997f8037eb9ea5ed3f7ecb30',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a60db9e1-f542-5518-8497-8c7c164a33eb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '90ca7fce-b2cb-57a3-a995-4f7085ca7703', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category A - Maximum height of wall"}'::jsonb, 'Category A 3.5 5 7', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9cae6002756e6113fbbee3fbb7da31cc179932adcd17d35b54004f532cb38907',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category A - Maximum total building height, gable/skillion/concealed roof"}'::jsonb, 'Category A 3.5 5 7', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '69ece47440ed9541f3ccfcc06734799e166b4bc59ec2b565581823bb6844799c',
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category A - Maximum total building height, hipped/pitched roof"}'::jsonb, 'Category A 3.5 5 7', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c2bafa3721c8323b741c295d792d7b9c32477aab4ee9035c299872c12d7788dc',
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
  'b3003cd4-64c0-5082-82e2-91e7aa398c50', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 7.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category B - Maximum height of wall"}'::jsonb, 'Category B 7 8 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd068c1487065945967e083bd71f82f9baa5b279e0c729df4c6482bf139cf0e71',
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
  'ea43e522-6a83-54be-9aad-6244f323d04c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 8.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category B - Maximum total building height, gable/skillion/concealed roof"}'::jsonb, 'Category B 7 8 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '670150873024d350d5fbf9f8ecbf8cc345f315f11475f6a295893658cecc54f5',
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category B - Maximum total building height, hipped/pitched roof"}'::jsonb, 'Category B 7 8 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1eeaa19ef0a2699d09c3ba21972c66e5813ad65515baa4ffcc1fe09c8b11f566',
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
  '2ba21fb2-8b46-55a5-9660-e5bb7a34ce33', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '881a5440-5f08-43ad-bafc-ad72b64fd6f2',
  'building_height', 'standard', 'none', 'lte', '{"value": 9.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category C - Maximum height of wall"}'::jsonb, 'Category C 9 10 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd665ad4a7b0c0eef4dbcf83a106d58fabfe162612e62668cc37b8a5bb3c8b93b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5f9d1df7-ab20-5058-8ebc-127f7f66a39f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 9.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category C - Maximum total building height, gable/skillion/concealed roof"}'::jsonb, 'Category C 9 10 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '549b16572d57242a0548d543be40dd4aff096cd69491683f38243b4dff6caf36',
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
  '{"density_codes": [], "dwelling_type": "any", "condition": "Category C - Maximum total building height, hipped/pitched roof"}'::jsonb, 'Category C 9 10 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0c121ba38526b2a4789d18a2c5749add0cd629cc1ef7e9a6be4cbd9ba0fa6d30',
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
  '65688c1d-b469-5734-a89c-239632ef4a95', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5c4add6c-524c-440a-a009-5c61d2d1b684',
  'site_area', 'exception', 'none', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "minimum site area where Table D reduction applied"}'::jsonb, 'for 
single houses and grouped dwellings, no 
site is less than 100m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b52de772957f468b5d87ac2dadca1aaad9df4902f5ae841fbe142662d2839e5e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '082f5e63-4724-57c6-98cd-e3baaa3b9d54', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cac9424c-5d52-5777-9e8a-4f1eedb0e17d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5c4add6c-524c-440a-a009-5c61d2d1b684',
  'site_area', 'exception', 'none', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "minimum site area where Table D reduction applied"}'::jsonb, 'for 
single houses and grouped dwellings, no 
site is less than 100m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'be99b533b9afba2cdbed5e9afba9e21c3a05c62c0ff978b8d431e18fcd728c52',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '082f5e63-4724-57c6-98cd-e3baaa3b9d54', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '146a147a-2126-50ac-a4ab-56062eb14ec4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd17b2128-8ae6-4f8d-ba54-5cee27f0d519',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "single consolidated uncovered primary garden area minimum area"}'::jsonb, 'a single consolidated uncovered primary garden area with a minimum area of 15m 2 and a minimum dimension of 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3872358cf6d0cb7387f0c12dcdfbeae5641591fb251392466d57332444be7e5a',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4987f8e1-9617-5c64-93a8-4d1f9f9cfdcc', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''a single consolidated uncovered primary garden area with a minimum area of 15m 2 and a minimum dimension of 3m''"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd17c73a7-5a6f-5233-9628-1dd35baa61f3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd17b2128-8ae6-4f8d-ba54-5cee27f0d519',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimum dimension of primary garden area"}'::jsonb, 'a single consolidated uncovered primary garden area with a minimum area of 15m 2 and a minimum dimension of 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fe0b535444cfbfb336a3fe92861aae46ec3234d9557f86687150f209a4e44970',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4987f8e1-9617-5c64-93a8-4d1f9f9cfdcc', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''a single consolidated uncovered primary garden area with a minimum area of 15m 2 and a minimum dimension of 3m''"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 3.0 m vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '372112f0-4904-557f-80db-0175bcbdfd5e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 40.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Site area greater than 220 m2; primary garden area minimum (single houses and grouped dwellings)"}'::jsonb, 'Greater 
than 220 40', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '748a537804bb2d88d035cf8d4c7ddeb9e947f87cf9e01486cb7ff949e9e6a56c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 40.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '63123691-d1c4-5c29-ac7b-821d1e5f7992', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 35.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Site area 191-220 m2; primary garden area minimum"}'::jsonb, '191-220 35', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3f3b49377bd6b437e13b952c1c23876d68373a49a85a0b7597f87ac57add01e3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 35.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'dc3c40a0-ae0c-55bb-88d5-2b485eba0275', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Site area 161-190 m2; primary garden area minimum"}'::jsonb, '161-190 30', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fd720d5071b5e7e2dc5629ab0cc5037dd46480351367d1f0ac5b9b933bd230a8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 30.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7036363c-6cf3-5305-b6cb-7b074c0e6cf5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 25.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Site area 131-160 m2; primary garden area minimum"}'::jsonb, '131-160 25', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '646a5244c759e38db42a86a69a57e93c9bba89e7229ec5b4458a8516074261e9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 25.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3f079d2c-8377-540a-be6a-48ca8cbbb16b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 20.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Site area 100-130 m2; primary garden area minimum"}'::jsonb, '100-130 20', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a722f5eddf45c76c8704a8ad84205da33fab1894071788bdf5178766e6357088',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 20.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'db96eb51-8ffa-594b-997a-8dc895fa161f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 8.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Studio / 1 bedroom dwelling - minimum private open space area per dwelling"}'::jsonb, 'Studio / 1 
bedroom 8m2 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5dfdb0285a17b0a5cfaea1d62bc6979b6f5127e43b2d51b3118fae641e232d07',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 8.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3ed970ec-1b87-5938-a2ce-fe1d0bc45dbf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "2 bedrooms dwelling - minimum private open space area per dwelling"}'::jsonb, '2 bedrooms 10m2 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '30a0e6c5d8f5b7dd52d1c58cd5c715e14f28eb26b56c3352998596cbb2216fbd',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3c36c643-b0fe-58b6-87ad-e32fa86ec218', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 12.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "3 or more bedrooms dwelling - minimum private open space area per dwelling"}'::jsonb, '3 or more 
bedrooms 12m
2 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '904d458fda1bfce2cc1889082b9ad797f8219b4193fee45a3c6b6d44ea5bdced',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a6f4926c-fbbc-52e7-8122-8c4b7b0882d0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Ground floor dwelling - minimum private open space area per dwelling"}'::jsonb, 'Ground floor 
dwelling 15m
2 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a70fe12707f1083d8ba324e6bc1e528a5995cf14be6347cb5ac5bc7aa3ebe878',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '571e6639-5de6-504f-b2cf-f40d9438fca9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ee2873ac-5af1-4e48-87ac-ef28a64b177a',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Each multiple dwelling - minimum balcony (or equivalent) area opening directly from the primary living space"}'::jsonb, 'balcony or the equivalent, opening directly from the 
primary living space and with a minimum area of 
10m2 and minimum dimension of 2.4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ab4224ce0a9f35e8aaea40ed0983e18fa5e66336034766693c69fb74041c5adc',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '52d2a1dd-4674-52f9-8e3b-9edac1233a79', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b5f8ef16-24fb-5e7c-a936-feb0d3ee96f4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_storeys', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R30", "R35", "R40"], "dwelling_type": "any", "condition": "Maximum number of storeys for R30 - 40"}'::jsonb, 'R30 - 40 2 8m 7m 10m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4a121f351a0aeb56827f683e7e1c1e9b42e31a3e2934ddf9630aa131938ab501',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fd42f14e-1aa4-5b3a-80e5-64056a4eedb3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 8.0}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35", "R40"], "dwelling_type": "any", "condition": "Concealed or skillion roof - Maximum building height for R30 - 40"}'::jsonb, 'R30 - 40 2 8m 7m 10m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5950df7c33cb900ecbe854e3e4c6f7f7a0a9dc2d6f5f6ebcd8d2bd1a9beb508c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 8.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9cd6e9c9-aa98-54bd-b80d-10af4c778c36', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35", "R40"], "dwelling_type": "any", "condition": "Pitched, hipped or gabled roof - Maximum total building height for R30 - 40"}'::jsonb, 'R30 - 40 2 8m 7m 10m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '705c91d990eed4eb2db23f077131f45991ec54d4c78faccc2067b53cef19d503',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '189c2f8d-bf57-5dcd-b817-1f31bc8c56b4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_storeys', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": ["R50", "R60"], "dwelling_type": "any", "condition": "Maximum number of storeys for R50 - 60"}'::jsonb, 'R50 - 60 3 11m 10m 13m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '95c4a27b872d09f902c77f20a109bd2954954cd513ae3c74d8429e388e226226',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '51e1ac28-8557-5896-89a1-10c4e533a99d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 11.0}'::jsonb, 'm',
  '{"density_codes": ["R50", "R60"], "dwelling_type": "any", "condition": "Concealed or skillion roof - Maximum building height for R50 - 60"}'::jsonb, 'R50 - 60 3 11m 10m 13m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b483de77872a121d097a321d7635545102ffaa225753487949a0737c32d6242e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 11.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '50c2d73e-2b23-536c-b39a-8014b3a051c4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 13.0}'::jsonb, 'm',
  '{"density_codes": ["R50", "R60"], "dwelling_type": "any", "condition": "Pitched, hipped or gabled roof - Maximum total building height for R50 - 60"}'::jsonb, 'R50 - 60 3 11m 10m 13m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7023d437b49886b2f543ea10323759198e9296de26cf9a8736849c6690407b07',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 13.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1647a4df-d4e1-5e1a-bf12-d1afd0098780', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_storeys', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 4.0}'::jsonb, 'storeys',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Maximum number of storeys for R80"}'::jsonb, 'R80 4 14m 13m 16m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1cc424573934aa3b3a78d6859338fbf19ac77725a812ddd31d266f44845046c4',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4f5423ad-946f-5ae1-b8bc-93bc3cff9f87', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 14.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Concealed or skillion roof - Maximum building height for R80"}'::jsonb, 'R80 4 14m 13m 16m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'bb1d996a1bbf035d87957c9ba5e16e604ae9e9be3e41707a19eb30555e7e2659',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f91c9c53-eb86-550a-a543-38c55093325c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'af7b2b9a-663f-4a27-8a43-b43dccd05fc2',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 16.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Pitched, hipped or gabled roof - Maximum total building height for R80"}'::jsonb, 'R80 4 14m 13m 16m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2c5ef541924f67ecb8de12c067b9befabfd0b9fc15bd82c526f0b8abdd407c5a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4c7a997a-fdd7-571c-9767-faed8bbfcccd', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 16.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5fad8995-899a-53d4-87b5-08efbd478b2f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": ["R30"], "dwelling_type": "any", "condition": "Minimum primary street setback for R30"}'::jsonb, 'Primary street 4m 4m 3m 2m 2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '555fdf57863574b8e197170c37455d8be59fb5935090de623be361c6d1b1123e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c5de7685-2a0c-5f89-ace3-1ce12a3b1be9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": ["R35"], "dwelling_type": "any", "condition": "Minimum primary street setback for R35"}'::jsonb, 'Primary street 4m 4m 3m 2m 2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '93210081e402fb94b65aa7c17a66af0674c88ac7e0fb5c8985bb3e6719f5f95f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '02cac08f-f27d-587a-ac8a-dabd1e506f44', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Minimum primary street setback for R40"}'::jsonb, 'Primary street 4m 4m 3m 2m 2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1e4fb84feeab011ee92c71ebd8752029f6f4f57237bb39ac9aaedb7b146299e1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a4de9cee-b855-57c6-9a31-286765c880bf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Minimum primary street setback for R50"}'::jsonb, 'Primary street 4m 4m 3m 2m 2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4230ee033e993c0e84c2f91cf6fb62ae25f2717ebbaeb0d136ca9bffa78a31ca',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'afb16bc6-e94f-55cd-a34e-d8d3e069c947', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Minimum primary street setback for R60"}'::jsonb, 'Primary street 4m 4m 3m 2m 2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6c14c363f4601e055242b67abdf91762c2520b4c2f5702496715fe3871dd95ee',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bd502245-d720-581f-8e21-11f7c303eeb6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Minimum primary street setback for R80"}'::jsonb, 'Primary street 4m 4m 3m 2m 2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7de3cc31b0233a2bb7fa3667f407f98b3d55bbebbe2298e69272278b154657ee',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '59a07514-298f-5d2d-83a5-4be922c3a134', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R30"], "dwelling_type": "any", "condition": "Minimum secondary street setback for R30"}'::jsonb, 'Secondary street 1.5m 1.5m 1m 1m 1m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '71c1b681cec5e26f31808e2d1abd4fbdb32f9d38848fdba48080602f78f3a45a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '35e1f1d0-d0d5-5be5-81a5-09c66ecdeb5f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R35"], "dwelling_type": "any", "condition": "Minimum secondary street setback for R35"}'::jsonb, 'Secondary street 1.5m 1.5m 1m 1m 1m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '558c40902708991eaa1d82bd6d240476c6a124d3dfa2f5c252fdf7962772484e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8d43eb21-3287-54bc-bff3-32211d5c5969', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Minimum secondary street setback for R40"}'::jsonb, 'Secondary street 1.5m 1.5m 1m 1m 1m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8aee5061dad7a21e8665ffb8ca4448d9848960567f2cc585205f1ea685f012a3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '62ad096a-f728-5353-a647-a3e1eaf12695', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Minimum secondary street setback for R50"}'::jsonb, 'Secondary street 1.5m 1.5m 1m 1m 1m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1f8aa6598b164340dd68ef89f3a4ff350c6d1e979e6af3d5a0b796d80a292ff8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b648bf6c-1bc6-5014-ab6c-b2ebb91656af', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Minimum secondary street setback for R60"}'::jsonb, 'Secondary street 1.5m 1.5m 1m 1m 1m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'bae32509baae4ccf80259887dce90039e135874d5979cf55d3dcfe223d03488d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1d01799f-6a2b-577a-9590-0c293c630d34', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '95564dba-f83d-4ff9-a560-d319e0a7b861',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Minimum secondary street setback for R80"}'::jsonb, 'Secondary street 1.5m 1.5m 1m 1m 1m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b3daa4ab1355d6d35e73c50d93a17e45717c75dbe763425d00aeeb986ce53670',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9519ce05-c515-5c2e-afef-7f82b825f35a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '22f99547-e9e0-54e2-b52b-572d9229bedd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 260.0}'::jsonb, 'm2',
  '{"density_codes": ["R30"], "dwelling_type": "grouped_dwelling", "condition": "Minimum site area per grouped dwelling at R30"}'::jsonb, 'R30 Grouped dwelling Min 260', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f386dcc2e2f99896fad1ff3b5dc5a3cec52fb5b68afc7f7e65fab175e222421d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b8da7d63-6cdf-5927-a384-d6278be7837b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 300.0}'::jsonb, 'm2',
  '{"density_codes": ["R30"], "dwelling_type": "grouped_dwelling", "condition": "Average site area per grouped dwelling at R30"}'::jsonb, 'Av 300', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd24cdb99f6eafcbdbc4771f510f3c5638338accf3fdc4e5d7ddaf4c3566cbf0d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 300.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9cdc1898-ccf4-5f25-b03f-2edc041e0e8a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 300.0}'::jsonb, 'm2',
  '{"density_codes": ["R30"], "dwelling_type": "multiple_dwelling", "condition": "Average site area per multiple dwelling at R30"}'::jsonb, 'Multiple dwelling Av 300', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '928510b32af1b527d45e7b41e0229d3d039d7588b4caa764d3349578887f2f10',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 300.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3e6bb86d-b89c-5d28-9356-c8da291d5dc6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 220.0}'::jsonb, 'm2',
  '{"density_codes": ["R35"], "dwelling_type": "grouped_dwelling", "condition": "Minimum site area per grouped dwelling at R35"}'::jsonb, 'R35 Grouped dwelling Min 220', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'edd19518cd8849e11d5b45d488eb8bd0c89af7574982f40bc71adbcc6c8cb4d1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 220.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9ed1bf78-a75f-50ba-bd3c-424cba6d74ee', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 260.0}'::jsonb, 'm2',
  '{"density_codes": ["R35"], "dwelling_type": "grouped_dwelling", "condition": "Average site area per grouped dwelling at R35"}'::jsonb, 'Av 260', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '80c1b4e4cda67f76f073e02d4737c83848ff7f9108c398b77eaa291d0677cd91',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5a45b1a2-8b79-57ae-84eb-4185dbf9a399', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 260.0}'::jsonb, 'm2',
  '{"density_codes": ["R35"], "dwelling_type": "multiple_dwelling", "condition": "Average site area per multiple dwelling at R35"}'::jsonb, 'Multiple dwelling Ave 260', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd4d70b8da1d381823e7424173749ee50da5a3691fd5f56f46fcc7d41b7248815',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '743cc3b1-7610-51a6-a953-a39976aa7cf0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 180.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "grouped_dwelling", "condition": "Minimum site area per grouped dwelling at R40"}'::jsonb, 'R40 Grouped dwelling Min 180', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9622734750daabbc9e83252a9e432058000abd49cc95581c9dc2ace93c5cdc85',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 180.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3090eb41-c9ba-546d-bcef-541a97217d72', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 220.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "grouped_dwelling", "condition": "Average site area per grouped dwelling at R40"}'::jsonb, 'Ave 220', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0b529788174d72f451cc7622a04792208f415be3edd88464ec52e42b5fc0ce35',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 220.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0de5b085-08ce-5341-a58e-2c5a26da4fd2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 115.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "multiple_dwelling", "condition": "Average site area per multiple dwelling at R40"}'::jsonb, 'Multiple dwelling Ave 115', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f15cdbfe454ccb94b363b8b6ffd887a91abb6b73e3538001f3d4905aa970730d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 115.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6ba471e5-796f-5ff9-976d-d19fc68f6df6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 160.0}'::jsonb, 'm2',
  '{"density_codes": ["R50"], "dwelling_type": "single_house", "condition": "Minimum site area per single house or grouped dwelling at R50"}'::jsonb, 'Min 160', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '16a1cf85d2a2793533a3745f7863228f8e9ea19e9bb628c0028be713ebcdbfe7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 160.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9cc82784-d4bc-59b3-bb2d-67c7177691a8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 180.0}'::jsonb, 'm2',
  '{"density_codes": ["R50"], "dwelling_type": "single_house", "condition": "Average site area per single house or grouped dwelling at R50"}'::jsonb, 'Ave 180', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4eb7dc8ba2e2ad185902d13675c2c9585fc28c277b9b043a82ce2d636bc8bac5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 180.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bd8da045-d191-5b7a-a506-442ac9e473cd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": ["R50"], "dwelling_type": "multiple_dwelling", "condition": "Average site area per multiple dwelling at R50"}'::jsonb, 'Multiple dwelling Ave 100', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '03ad3fc573f88d0806e8fce839c183da2571310267c4b5ac8a41d278c5fb950d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ff0d17b4-9491-58a8-911b-c55f83a2926b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 120.0}'::jsonb, 'm2',
  '{"density_codes": ["R60"], "dwelling_type": "single_house", "condition": "Minimum site area per single house or grouped dwelling at R60"}'::jsonb, 'Min 120', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fc014213cac16778f656e834306925f4d5cb16fab2952254bc49b1d01efb4006',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 120.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'adf109be-7f99-5af7-825f-211a6103ead0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 150.0}'::jsonb, 'm2',
  '{"density_codes": ["R60"], "dwelling_type": "single_house", "condition": "Average site area per single house or grouped dwelling at R60"}'::jsonb, 'Ave 150', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f7d8980fa02dec641ed7ccd385fb4f733568abe8633c123508b384146001e2e7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 150.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1ec8dc32-d198-570f-b283-2a0b10afc6d6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 85.0}'::jsonb, 'm2',
  '{"density_codes": ["R60"], "dwelling_type": "multiple_dwelling", "condition": "Average site area per multiple dwelling at R60"}'::jsonb, 'Multiple dwelling Ave 85', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '88f6ee7424228272aa63dd7e84b8c6223fe52a6bacbc30e54c144e62dbbbaea4',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 85.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7d3ede9e-922f-5355-83a4-1bc48ff3ab3d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": ["R80"], "dwelling_type": "single_house", "condition": "Minimum site area per single house or grouped dwelling at R80"}'::jsonb, 'Min 100', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6a473e9528738bdede90ef1dfd476bf6a48c09fe8ae06073ea73bd97ec92877e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f5b0bec7-81b4-5dcb-9eeb-04bb56b15576', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 120.0}'::jsonb, 'm2',
  '{"density_codes": ["R80"], "dwelling_type": "single_house", "condition": "Average site area per single house or grouped dwelling at R80"}'::jsonb, 'Ave 120', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4fde293e87d103806e698ad17bcdb9c71b7811f8548a0a404e5a2346dc9cc718',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 120.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd270e045-96c0-5335-8706-37b3a4745d92', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7586cc09-adb7-4450-9619-635a53636001',
  'site_area', 'standard', 'none', 'gte', '{"value": 80.0}'::jsonb, 'm2',
  '{"density_codes": ["R100-SL"], "dwelling_type": "single_house", "condition": "Minimum site area per single house or grouped dwelling at R100-SL"}'::jsonb, 'Min 80', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '83fdfe715c0b11c62bd1e057ef00c9e63464f2b0aa8fe3c405efd5c258aebde7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0dc5fce7-b188-5003-be00-37d9a6279de6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 80.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();

COMMIT;

-- Summary (this slice):
-- {"clauses_seen": 37, "clauses_no_atoms": 23, "atoms_emitted": 71, "atoms_validators_passed": 66, "atoms_validator_failed": 5, "atoms_missing_clause_context": 0}
