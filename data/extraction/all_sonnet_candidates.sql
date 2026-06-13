BEGIN;
-- WP6 Sonnet (3rd-family) candidate slice. Idempotent: re-run safe (PK is uuid5'd).

INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  '8fe70d54-15fb-51db-ab0e-c1bb46055767', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'd1fe42eb-b6b8-4dde-b3f5-699d916a29fd', '6e5d4653-6c87-454e-b89e-8c7da843cd08',
  'site_area', 'standard', 'none', 'gte', '{"value": 450.0}'::jsonb, 'm2',
  '{"density_codes": ["R20"], "dwelling_type": "any", "condition": "Net lot area (excluding easement) when sewer easement is contained within residential lots for land coded R20 and below"}'::jsonb, 'the net lot area (excluding the easement)
is not less than 450m2 for land coded
R20 and below', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5af085706ea09b22e2216369deca490e0baf5d342825970a1058df1efeaa5c6c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'b3d307a1-916a-5637-9203-44a6d8c264f9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not less than''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 450.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2367c755-8f56-55db-998d-6e681b56bf20', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'a51f695c-039c-4198-84a5-ce7279d1209d', '9925958f-de4d-4818-9eca-a057c093586e',
  'fence_height_front', 'standard', 'none', 'lte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "fence situated within 7.5 metres of an artificial waterway frontage"}'::jsonb, 'No fence situated within 7.5 metres 
of an artificial waterway frontage shall 
exceed 1 metre above the original 
stabilised surface.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '40787eeca845b32d4c832507c304200cf5903f8d6bda4c2cc4ec6a0b702e7dc0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'c590d69e-86c8-536a-85da-bd9f88bc2572', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fdde506e-f48e-540e-8f2d-d7bfaa80d632', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'a51f695c-039c-4198-84a5-ce7279d1209d', 'b6e0cfc3-9953-48f8-b6c3-01f33e323708',
  'fence_height_side', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Fence situated more than 7.5 metres from an artificial waterway frontage; height measured above original stabilised surface"}'::jsonb, 'No fence situated more than 7.5 
metres from an artificial waterway 
frontage shall exceed 2 metres above 
the original stabilised surface.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c3b1a3517a4dd47e134428c771139f55f866f59767ca10b247df9727687195e6',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '5a3799ad-4c64-5027-abe5-34ee4a8fe7e4', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_side'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.5,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'eb06d217-ef70-5be7-893f-bbc5192200fd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', 'a51f695c-039c-4198-84a5-ce7279d1209d', '0c7c8218-5d15-475f-91e5-ddce832d1f19',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Dwelling setback from road frontage"}'::jsonb, 'All dwellings shall be set back a 
minimum of 6 metres from an artificial 
waterway frontage measured from the 
outer side of the top of the waterway 
wall and 6 metres from a road frontage.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7abb63ab307b71fb150a91ea8422c224eef62a00097593ce6e1f99df1e3d2d0c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9bd3c70d-5639-5081-992c-15f85117351e', 1,
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
  'fafebf29-396f-5d7c-b56a-674fa06d2957', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', '5381f974-d06a-46e1-8571-d092efd8ea41',
  'parking_bays_per_dwelling', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum bays per dwelling unit within Cockburn Central West"}'::jsonb, '0 per dwelling unit, with a maximum of 2 bays per dwelling', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0e0227d18632570967ef531e9bc5dcad9ab941d3275ce07ece182cddf74b67b3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ca81c810-0c39-5d9a-bd64-593af979977a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e45df60a-7f2e-5d96-834c-83f9ce60141b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', '5381f974-d06a-46e1-8571-d092efd8ea41',
  'parking_bays_per_dwelling', 'standard', 'none', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum bays for three or more bedroom dwellings within Cockburn Central West"}'::jsonb, '1 car bay for three (or more) bedroom dwellings with a
maximum of 2 bays per dwelling.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5a966058bb56a72c41d30e900f8f6de30d1940390b5d2d5ada665baac6c510ba',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ca81c810-0c39-5d9a-bd64-593af979977a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '10c7c9c1-0503-5684-ae72-4a27f5c12844', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', '5381f974-d06a-46e1-8571-d092efd8ea41',
  'visitor_parking_per_dwelling', 'standard', 'none', 'pct_gte', '{"value": 10.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Visitor car parking as a percentage of total residential car parking requirement"}'::jsonb, 'Visitor car parking is to be a minimum of 10% of the total
residential car parking requirement', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ea9cc974804e4020bd22bdadf4736e57cb4335e23a7c2e333f414f7b0ad69f8f',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ca81c810-0c39-5d9a-bd64-593af979977a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''visitor_parking_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 10.0 % vs prior [0.0,2.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b68301cc-051a-5137-ac79-db4d33fc0006', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', 'fedbd761-b5e1-4e0f-b7a5-8c32679b0c40',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum residential building height across the Structure Plan Area"}'::jsonb, 'Minimum residential building height will be three storeys across the Structure Plan Area.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ee718682f9a727b845cf8a4e498729c2c0b9331bca96ab65271ec20092052c19',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '7a919ecc-b0b2-5a9d-92fd-00aa4a721b53', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '31f27c43-53d8-5563-8bdd-83a8e3d7b0e5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', 'fedbd761-b5e1-4e0f-b7a5-8c32679b0c40',
  'building_storeys', 'exception', 'none', 'gte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "Land zoned Mixed Use (Residential, Retail and Commercial) for attached grouped dwellings, where grouped dwellings do not exceed 30% of the developable land area"}'::jsonb, 'building height may
be reduced to two storeys to allow for attached grouped dwellings', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '66bf882f980bd67f0ff20c73f2990738d929b54fbedfe8361a3c70ef0a2a8e99',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '7a919ecc-b0b2-5a9d-92fd-00aa4a721b53', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '99b045dc-2a8f-5797-b2a1-342ed7610c99', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', 'b164985e-550b-408f-859a-89db7a356ab1',
  'parking_bays_per_dwelling', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum residential car parking bays per dwelling"}'::jsonb, '0 per dwelling unit, with a maximum of 2 bays per dwelling:
1 car bay for three (or more) bedroom dwellings with a
maximum of 2 bays per dwelling.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fbd53fc871c62e2f7f660c8e54d268f5a9e0ed2797158a3f0c99b3a392b7f199',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '906d19c0-ef81-561d-9c1f-cc89b3a2df87', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f6cff276-26a8-5e2c-8e9a-834a42153985', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', 'b164985e-550b-408f-859a-89db7a356ab1',
  'parking_bays_per_dwelling', 'standard', 'none', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum car bay for three or more bedroom dwellings"}'::jsonb, '1 car bay for three (or more) bedroom dwellings with a
maximum of 2 bays per dwelling.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '174e66ebcec96c0c62ac658d764db1a30a8a9979cf1562d6e31d7f00204c7842',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '906d19c0-ef81-561d-9c1f-cc89b3a2df87', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8626f1a5-5c6d-527a-81f4-9fe51ceaf59b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '7e7faf65-fb02-4616-b492-a325bdfed238', 'b164985e-550b-408f-859a-89db7a356ab1',
  'visitor_parking_per_dwelling', 'standard', 'none', 'pct_gte', '{"value": 10.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Visitor car parking as percentage of total residential car parking requirement, provided in addition to required residential car parking"}'::jsonb, 'Visitor car parking is to be a minimum of 10% of the total
residential car parking requirement and be provided in
addition to the required residential car parking.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4615fe5ba8710a1853b998cc3710c55e7082c25a74597cdffb94f7a289f8c269',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '906d19c0-ef81-561d-9c1f-cc89b3a2df87', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''visitor_parking_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 10.0 % vs prior [0.0,2.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4884a1d9-b763-5c3b-9ae5-7c9a4684c295', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '03c3e2d4-7747-432c-9747-faf6bd46a5af',
  'site_cover', 'standard', 'none', 'pct_lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Building envelope within the Rural Living Zone"}'::jsonb, 'a building envelope within the Rural Living Zone shall not exceed 50% of the lot area or 2000m 2, which ever is the lesser', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'acd51c3ad51993dd752eb105ebc072c707764f8bba1395342c32c42ff63d4305',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e8dec109-4643-53a8-9cd0-36d7486afb1c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4272b92b-084d-5cc4-b648-e3aa625d973b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '03c3e2d4-7747-432c-9747-faf6bd46a5af',
  'site_area', 'standard', 'none', 'lte', '{"value": 2000.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Building envelope within the Rural Living Zone (maximum envelope area)"}'::jsonb, 'a building envelope within the Rural Living Zone shall not exceed 50% of the lot area or 2000m 2, which ever is the lesser', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c2f750afa08917a256d96a3f9a896f0d729580d6af7651e060e0761570890e1c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e8dec109-4643-53a8-9cd0-36d7486afb1c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e0d2d242-f4d6-5fcd-a5dd-5262b1dc1ae7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '03c3e2d4-7747-432c-9747-faf6bd46a5af',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Building envelope within the Rural Living Zone"}'::jsonb, 'shall have a primary street setback of not less than 6 metres and a side setback of not less than 2.5 metres', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '934516fe43b9b857501794af0af1eb454b8a9f0e32df722c439f79c8dea7e5cb',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e8dec109-4643-53a8-9cd0-36d7486afb1c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0a984762-3337-5a0d-b6ab-b92dbdf620e4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '03c3e2d4-7747-432c-9747-faf6bd46a5af',
  'side_setback', 'standard', 'none', 'gte', '{"value": 2.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Building envelope within the Rural Living Zone"}'::jsonb, 'shall have a primary street setback of not less than 6 metres and a side setback of not less than 2.5 metres', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1b6e1018e081dfb8508edce3bb971f9f9340edfd090cfde697f63ad3e4341e76',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'e8dec109-4643-53a8-9cd0-36d7486afb1c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fde6bde9-debc-58a5-8801-b56e537f6b05', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'e066a193-fe0e-4d85-9f72-06b2e8576cab',
  'soft_landscaping', 'standard', 'none', 'pct_gte', '{"value": 15.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimum soft landscaping requirement per site, applies to single house, grouped dwelling and multiple dwelling"}'::jsonb, 'minimum 15% soft landscaping requirement per site', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '328db38da837f4437234e63b74ad93b868c8246cea69301922b4d448cd70a130',
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
  'b203ff2a-dafd-5fd5-b752-9a9477be948b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '739f840b-dc92-4500-8d26-5e9e79b6469f',
  'communal_open_space', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "More than 10 dwellings - minimum communal open space requirement per dwelling, up to maximum 300m2"}'::jsonb, '6m2 per dwelling up to 
maximum 300m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '572651fc7b0cfb7f3105710b4c05c0b570cef7f4c32a30b91da74327b6bf9dc3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3a51db96-3fbe-564a-b1ac-357085e5c284', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''communal_open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 6.0 m2 vs prior [10.0,2000.0] [''%'', ''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3ca4c364-4e90-5412-a897-e504d4bc2058', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '48d272ea-1ac6-407b-a9ac-bd5980886376', 'c3ae4dca-1d34-416b-a90c-b577f587838b',
  'site_area', 'standard', 'none', 'gte', '{"value": 850.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "battleaxe lots in locations not subject to R-Codes provisions; effective lot area"}'::jsonb, 'the WAPC will normally 
require residential battleaxe lots to have 
an effective lot area of at least 850m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4db64c9d14570762acf77eedd433e2471c47043abb23ced9f4268df71c685b53',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0b72c9c9-da11-5730-8817-004d75f693c6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 850.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4c7f140c-bc13-5307-ba42-fc7b39ddb691', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '48d272ea-1ac6-407b-a9ac-bd5980886376', 'c3ae4dca-1d34-416b-a90c-b577f587838b',
  'lot_width', 'standard', 'none', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": ["R2", "R5", "R10", "R12.5", "R15", "R17.5", "R20", "R25", "R30", "R35", "R40"], "dwelling_type": "any", "condition": "battleaxe leg width (R2-R40)"}'::jsonb, 'A battleaxe leg should be a minimum of: 
• 4 metres in width (R2-R40)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'e2785272850df219cfa4d2042ce06d05d79b94e672d09b9a62cb661258f7bf7e',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0b72c9c9-da11-5730-8817-004d75f693c6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''lot_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [4.0,100.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  'fe1e11e2-8c39-596b-b66b-a914cbaffd72', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '48d272ea-1ac6-407b-a9ac-bd5980886376', 'c3ae4dca-1d34-416b-a90c-b577f587838b',
  'lot_width', 'standard', 'none', 'gte', '{"value": 3.6}'::jsonb, 'm',
  '{"density_codes": ["R50", "R60", "R80", "R100", "R160"], "dwelling_type": "any", "condition": "battleaxe leg width (R50 and higher)"}'::jsonb, '• 3.6 metres in width (R50 and higher)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '391c978f974f84ca29cc3af2d49f887343f513aa0b14517fe7d2fe4256c39680',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0b72c9c9-da11-5730-8817-004d75f693c6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''lot_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 3.6 m vs prior [4.0,100.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a8047669-afcd-5dd6-b914-57d3c47b8240', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '48d272ea-1ac6-407b-a9ac-bd5980886376', 'c3ae4dca-1d34-416b-a90c-b577f587838b',
  'driveway_width', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "constructed driveway within battleaxe leg"}'::jsonb, 'to allow for a 3m constructed driveway', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '72f4c0fa072c315d6dda5def7e27fab76871c477cedf227c026bd500d43e14b3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '0b72c9c9-da11-5730-8817-004d75f693c6', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '471d1b0f-8670-590f-a5f7-9b5c6ff58baf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '422f33cf-3b18-46aa-9c15-ac32d18b7681',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Use - Cockburn Road Typology, Levels 1-3, street setback (minimum and maximum)"}'::jsonb, 'Levels 1-3 Nil Nil Nil 4m to wall and 2m 
to balconies', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8e811651d4c8ee7ef471366835af981625466c3b446269a2978e8c3a95ce2808',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '670e7c35-df94-5f21-80af-0f8b71d643ae', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9356a9d5-c058-57c2-b4ab-32f91be4ce3b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '422f33cf-3b18-46aa-9c15-ac32d18b7681',
  'side_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Use - Cockburn Road Typology, Levels 1-3, side/rear minimum setback"}'::jsonb, 'Levels 1-3 Nil Nil Nil 4m to wall and 2m 
to balconies', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6d5700368f86f406a21c08b2c3ef7ab8f0ebdc8fe88580db6bfa6dd0d45be8dd',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '670e7c35-df94-5f21-80af-0f8b71d643ae', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ce5a4dca-6a4b-5d21-8e0e-9c23319f3c66', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '422f33cf-3b18-46aa-9c15-ac32d18b7681',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Use - Cockburn Road Typology, Levels 1-3, side/rear minimum setback"}'::jsonb, 'Levels 1-3 Nil Nil Nil 4m to wall and 2m 
to balconies', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '58bce1fbc39f565c66f77b3d4f7432bc2b9332b34b1070682eb74db28ff6edcc',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '670e7c35-df94-5f21-80af-0f8b71d643ae', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fcf7bc13-0542-57a6-bdd3-289ff4d79b5a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '5e06707d-7f5b-442a-bd69-b5d1d86ce321',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Buildings setback from any boundary adjoining public parkland; setback area shall include space for landscaping and if necessary an outdoor living area"}'::jsonb, 'Buildings shall be setback 4m from any boundary adjoining public parkland.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '43076d1d8c203f5452d9a8113015d9ba77ca29495dd009af5ec6372c5ffa565c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '065416e9-33f5-5a7c-8884-72c141e03d6f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '567219a9-6e3a-5571-847c-d1e2fe019257', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'e8078cf9-2212-449b-9135-3ce274ed0763',
  'ground_floor_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "ground floor floor-to-floor height to allow for commercial use"}'::jsonb, 'Floor to floor heights on the ground floor should be 4.5m to allow for 
commercial use of the ground floor', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd25a43a57378f924c22d16508b28c8e38a6fb870349574d86b51dad601d026eb',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '792442b0-afc0-51f9-a061-b3fc1767adae', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 4.5 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '48ed3b85-ecdc-56b6-b750-e78b710f58cb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'e8078cf9-2212-449b-9135-3ce274ed0763',
  'ceiling_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.1}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "upper floors residential use, floor to floor height"}'::jsonb, 'All other floors shall maintain a 3.1m floor to floor height for residential use', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '93ef5dd621f72b91163785a40ad5b3392d4b911c2086d36aa8f032ca3bd27472',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '792442b0-afc0-51f9-a061-b3fc1767adae', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.1 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '52b493ca-8468-5940-8788-4a2ebda3a613', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'e8078cf9-2212-449b-9135-3ce274ed0763',
  'ceiling_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.6}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "upper floors commercial use, floor to floor height"}'::jsonb, 'a 3.6 metre floor to floor height for commercial use', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2126987c84c7892b08ab32eec287dc3bcb2de93f4e5e9337824077796831d1dc',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '792442b0-afc0-51f9-a061-b3fc1767adae', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.6 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '90edc3da-0b92-5aaa-9ee1-266c91f46f44', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'a491ce4d-8cc1-4fe1-afdd-e51d70c01cd6',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Robb Jetty & Emplacement Precincts - minimum storey requirement"}'::jsonb, 'Development shall be a minimum of three storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fad96b5001420993aa0a018a568fe2d12954d0cc7f973989f4f712d5c5787ada',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '1c6add3d-7bd4-544e-92d6-a98f485b8ba9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5a539580-4bf8-5856-92f2-f3e14c775273', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '95e1ed29-5232-4680-a6de-ce11cfa10954',
  'fence_height_side', 'standard', 'none', 'lte', '{"value": 1.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "interface between residential development and public open space"}'::jsonb, 'The interface between residential development and the public open space may be fenced to a maximum height of 1.2m from natural ground level, but must be visually permeable above a height of 1.0m above natural ground level', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9b82845f97dc69ace7ca5596cdb0b575dcf70df5a92aa8f100c9277ec9a5c366',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '01926e31-4a57-50f2-a583-3c0b55a355e2', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_side'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.5,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f81cf8c1-ecae-5c78-b066-d32586eb45e5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '0821bdb5-813f-403d-81cd-0100ae738f10',
  'fence_height_side', 'standard', 'none', 'lte', '{"value": 1.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "interface between private lots and the public open space"}'::jsonb, 'The interface between private lots and the public open space may be fenced to a maximum height of 1.2m from natural ground level, but must be visually permeable above a height of 1m above natural ground level.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5936e0d9384e0828c72b3c9eeadde645b943c94fb93cc0b6d1f213935aa38db0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '24ce2080-289f-5ba7-850e-5e82c4af3333', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_side'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.5,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '31f9e4db-78df-5e9e-b0f8-44b1d75e97a3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '4a8c62a8-72d1-4c8a-b121-1160da1ee725',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Mixed Residential Typology, Levels 1-3, primary street minimum setback"}'::jsonb, 'Levels 1-
3
3m Nil Nil', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3ad03aaa971afcbe52341cdb6a45d66dc72653634c9a93b8fa747cef36cae4a1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a8965bd3-78a1-5f76-a0ce-e3fc99c55723', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ae8fd3a8-58b5-552b-b113-d47746d9daf0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', 'bd0e4e2a-9841-4b51-9444-e1e777d8d6ac',
  'ground_floor_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.1}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "All development - minimum floor to floor height"}'::jsonb, 'All development shall maintain a minimum floor to floor height of 3.1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c41dd23fd67113d3f8c84a782ffdd3d5e1380d4b26b8971c3dbe14b693323cab',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '2606645d-2a61-525b-83b6-50277d10292b', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.1 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '63c52349-3707-50b5-a0d2-1a1dc6bc0fd6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9554ea37-dd7d-47ad-833b-ebec2e99fcac', '99a22d18-c34a-4e58-a202-273db2ca7862',
  'fence_height_front', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 1.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Fencing at interface between private lots and public open space, measured from natural ground level"}'::jsonb, 'The interface between private lots and the public open space may be fenced to a maximum height of 1.2m from natural ground level', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '393108a9d9f08a33a5fb40a6077c71a858e931469834afd6c45636a322a4b152',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '305edc4a-cb4d-5b7d-bf7d-189867f8c4a2', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6c99c028-66f1-5585-a91b-0786e1f3fab1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '8e670f80-870f-4a01-a395-3470c20d63e9',
  'soft_landscaping', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 30.0}'::jsonb, '%',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "primary street setback area"}'::jsonb, 'The p
rimary street setback area is to provide a 
minimum 30% soft landscaping', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '535b94d7779bd1d4eb5baf2385bc5bf8eecf7e94a4c8cb4a0cb6186ae16e2b2d',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'fcd0a30d-7007-5111-93e9-f299ce37f595', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 30.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  'c9185e24-fea8-5456-b5fe-793caba36137', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '7b1479ae-98d4-4938-862c-c20cd1c84b14',
  'soft_landscaping', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 10.0}'::jsonb, '%',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "minimum 10% of the site provided as soft landscaping with minimum dimension of 1m"}'::jsonb, 'mini
mum of 10% of the site to be provided as soft landscaping , with a minimum dimension of 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '650eb54d934d1937060414947746d293ded2210b6110a28d91b939086f702071',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '366eda9b-34a3-51a2-8a8b-7ee088939ca2', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  'd08bc03c-04f0-54f6-8cac-30d4c9ce827a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'a983fa74-6ff6-43a7-b600-04d464b8588c',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.5}'::jsonb, 'm',
  '{"density_codes": ["R15", "R20", "R25", "R30", "R35", "R40", "R50", "R60", "R80", "R100"], "dwelling_type": "any", "condition": "Areas coded R15 or higher where a grouped dwelling has its main frontage to a secondary street, or a single house results from subdivision of an original corner lot and has its frontage to the original secondary street, or a single house or grouped dwelling has its main frontage to a communal street, right-of-way or shared pedestrian or vehicle access way"}'::jsonb, 'in the c
ase of areas coded R15 or higher, the 
street setback may be reduced to 2.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0863016331208ff55f387ec661e7a6ab16a0538b21d2c93b1d9c548b1d7f5fcb',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bc7b4cdc-1bb9-52bb-95fa-99068b395bf3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9a1ca974-292e-589e-908c-ff65a14c499c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'a983fa74-6ff6-43a7-b600-04d464b8588c',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R15", "R20", "R25", "R30", "R35", "R40", "R50", "R60", "R80", "R100"], "dwelling_type": "any", "condition": "Reduced setback to a porch, balcony, verandah or the equivalent in areas coded R15 or higher under the listed corner/secondary frontage conditions"}'::jsonb, 'the 
street setback may be reduced to 2.5m, or 1.5m 
to a porch, balcony, verandah or the equivalent', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8b98665961e27e432d0d03b8c73b51fe9828ca8a3375a8405bff022bcfda38f5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'bc7b4cdc-1bb9-52bb-95fa-99068b395bf3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '351069fc-a102-5160-87be-064189bb9ed6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '00c20252-6884-4c56-a5df-cfc37fbd76c1',
  'car_bay_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.8}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Aged or dependent persons'' dwellings; first visitors car space being a wheelchair accessible car parking space"}'::jsonb, 'the 
first visitors car space being a wheelchair 
accessible car parking space and a minimum 
width of 3.8m in accordance with AS4299', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'eb714ff589c7a6181c2bc79553862e12c157a9c0f16daf8774112146ea9df6a8',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '130521df-225d-5aff-9440-cc42fcfb0ac3', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''the first visitors car space being a wheelchair accessible car parking space and a minimum width of 3.8m in accordance with AS4299''"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''car_bay_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.8 m vs prior [2.0,5.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5cbdb0c0-11a3-58d0-9042-6ffe02291f01', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'a82a528a-cd4e-44ab-bef5-425e8cd784ab',
  'ceiling_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.65}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "habitable rooms in multiple dwellings, measured from finished floor level to ceiling level"}'::jsonb, '2.6
5m for habitable rooms', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd288a75cd125c4795bc7cb7587ce450f7721330d3b7b55866850c5b6b9fc83d9',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'cd566776-132d-5fa5-943e-c6aec4683365', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2.65''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.65 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fd5f8820-4e92-5e2f-bbb2-9d6f5335dbb5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'a82a528a-cd4e-44ab-bef5-425e8cd784ab',
  'ceiling_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.4}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "non-habitable rooms in multiple dwellings, measured from finished floor level to ceiling level"}'::jsonb, '2.4
m for non-habitable  rooms', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '00092c69ec117667f6dbd50407db5469ebf1e060f47bb610d9b7827b2967ba7e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'cd566776-132d-5fa5-943e-c6aec4683365', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.4 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8341fd9c-811d-5ca3-9b2f-f8cd9ab8ae0a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '974e6a2b-8862-4b36-a287-f35de0cbf970',
  'ceiling_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.65}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "habitable rooms in dwellings, measured from finished floor level to ceiling level"}'::jsonb, '2.6
5m for habitable rooms', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dd06df195efadd4f83993a4477a46ab221d47d70513f82f5f2afbc11c2036f00',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '209fb9f2-71ab-56e0-a7d0-3c3dc55d7612', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2.65''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.65 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6a4ff9b7-5fee-5c69-bae3-7bb16325ba82', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '974e6a2b-8862-4b36-a287-f35de0cbf970',
  'ceiling_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.4}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "non-habitable rooms in dwellings, measured from finished floor level to ceiling level"}'::jsonb, '2.4
m for non-habitable rooms', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a6539bfdf3c0cc271f686ca421911fb1d5ab91980681ca40b2d0c5c54c4623e5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '209fb9f2-71ab-56e0-a7d0-3c3dc55d7612', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ceiling_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.4 m vs prior [2.0,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bbcd7d45-a971-5584-ab8e-e98e2ab8341a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ec1578e3-19d6-46e9-87bc-b2bce7d07398',
  'soft_landscaping', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "street setback area impervious surfaces limit for single houses, grouped dwellings and multiple dwellings"}'::jsonb, 'landscaping of the street setback area, with not 
more than 50 per cent of this area to consist of 
impervious surfaces', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7a8447499f91ffae7e625f2c4d13ee427a424047ce3c2baf78ab7e0071992644',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '04989a50-2c71-5060-8244-bc11f6b1f337', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''landscaping of the street setback area, with not more than 50 per cent of this area to consist of impervious surfaces''"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2370f8f4-fdd5-55cf-9584-84b08b1ccaa3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'b4dbd55e-45a5-470c-a5b3-41ba6bef14c0',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "outbuilding"}'::jsonb, 'does n
ot exceed a wall height of 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f6182baa1f34395919973c0d659b39d5045123f815566e128db50f664716c529',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3179a4de-4d46-5098-b64f-18512fa10867', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3d283d5c-f709-55f8-9cb6-1e3359493e3a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'b4dbd55e-45a5-470c-a5b3-41ba6bef14c0',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 4.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "outbuilding ridge height"}'::jsonb, 'does n
ot exceed a ridge height of 4.2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0d240cb9abadac38b7e2685f637772b475eb52e1028114922180efb54f098deb',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3179a4de-4d46-5098-b64f-18512fa10867', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.2 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '05e99d90-ebd2-5bd6-907e-4e142aedc9f3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "1 bedroom single house, grouped dwelling or special purpose dwelling in Location A"}'::jsonb, '1 bedroom 1 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '141482e85c970290a18643debdbf863ef92450059c5c1451705d0d0f742e0ea4',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c9ce5270-c0ab-5338-bd11-a210ceb3e928', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "1 bedroom single house, grouped dwelling or special purpose dwelling in Location B"}'::jsonb, '1 bedroom 1 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6615b49d65d4a6e3f02360973a0d5e9953dd2426a5e841716ba51e94d7928555',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7b4f881a-8470-5841-8df8-d1e59414a9b1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "2+ bedroom single house, grouped dwelling or special purpose dwelling in Location A"}'::jsonb, '2+ bedroom dwelling 1 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7dba8d9ed5f8d6d5f252658dbe58957b365cd7918d9459536adbeb8f2bf8e49d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '11c81501-7733-5d2a-80d2-90e985852c88', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "2+ bedroom single house, grouped dwelling or special purpose dwelling in Location B"}'::jsonb, '2+ bedroom dwelling 1 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2221d4a0509c5a779a5b542ad214f1e5313568c9a527b529db88301b9f5d3825',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4a202bc0-f28e-51db-a102-857904e90fd8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Aged persons'' dwelling, accessible dwelling or small dwelling in Location A"}'::jsonb, 'Aged persons’ dwelling, 
accessible dwelling or small 
dwelling
1 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5cdce91a9263789a3cecbf2732a217b1193c24962ea20dbba021d32e09611278',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9ebe4662-c65b-5c12-93bb-a52db360a8ec', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Aged persons'' dwelling, accessible dwelling or small dwelling in Location B"}'::jsonb, 'Aged persons’ dwelling, 
accessible dwelling or small 
dwelling
1 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7e830406a3ffc2049bd5aa7dd97f505cfde52ef6c0de6fdf983ec83e01e2eca9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c3fba2ed-0a31-5d12-9078-4556d87a49cf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '258b6660-89a6-468f-923e-fbcbb17bb4c5',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Ancillary dwelling in Location B"}'::jsonb, 'Ancillary dwelling Nil 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '726e7135a86d073032fc4300416d4b62c4641e8e84e6aafc85e2652289414d01',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a35b77a-55a1-5e30-8535-ea9e9a4e492a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cd4873e2-2af1-51aa-a909-60192c0a4b6b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'da19d701-1bc3-4c1a-8699-b617d01e4ff5',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["R30"], "dwelling_type": "any", "condition": "Maximum site cover under Table 3.1a for R30"}'::jsonb, 'R30 R35 R40 R50 R60 R80
60% 60% 65% 65% 70% 70%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '50152ef3466fc76a7d3bed88a627370d6309ab9d80630e28afe704c91f98b0ca',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ef51bda9-6982-5f63-9e25-7430dca20080', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '87175173-e3f3-5cde-9de7-d34fa5c57d6e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'da19d701-1bc3-4c1a-8699-b617d01e4ff5',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["R35"], "dwelling_type": "any", "condition": "Maximum site cover under Table 3.1a for R35"}'::jsonb, 'R30 R35 R40 R50 R60 R80
60% 60% 65% 65% 70% 70%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '24f8c950640591e5e211fc51583570dbf2693d57508d78852754dfc1ef4d9bbe',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ef51bda9-6982-5f63-9e25-7430dca20080', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e9bbf3b7-a2f3-50bc-b7a8-951f92527eb0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'da19d701-1bc3-4c1a-8699-b617d01e4ff5',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 65.0}'::jsonb, '%',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Maximum site cover under Table 3.1a for R40"}'::jsonb, 'R30 R35 R40 R50 R60 R80
60% 60% 65% 65% 70% 70%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f053feb185144ce0e31fe23a2fe3e8e7832abaeab2583c9e979d9e9ba44d657d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ef51bda9-6982-5f63-9e25-7430dca20080', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 65.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8d5b927d-8c66-5bb2-8dd2-b40acfec5c3c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'da19d701-1bc3-4c1a-8699-b617d01e4ff5',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 65.0}'::jsonb, '%',
  '{"density_codes": ["R50"], "dwelling_type": "any", "condition": "Maximum site cover under Table 3.1a for R50"}'::jsonb, 'R30 R35 R40 R50 R60 R80
60% 60% 65% 65% 70% 70%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f60e761d5d689b7d4002d3d878c93e5e6f6bf6f3abb9033145d97ecabb584050',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ef51bda9-6982-5f63-9e25-7430dca20080', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 65.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e044a76c-d6c0-54b9-bafe-21f95b68d5a9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'da19d701-1bc3-4c1a-8699-b617d01e4ff5',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 70.0}'::jsonb, '%',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Maximum site cover under Table 3.1a for R60"}'::jsonb, 'R30 R35 R40 R50 R60 R80
60% 60% 65% 65% 70% 70%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '624afb23f62614b5ee9563b90efc53ece360abe8febae66ad087de14c434936e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ef51bda9-6982-5f63-9e25-7430dca20080', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 70.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '30631199-e8b8-5db1-95bb-768c37e5002d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'da19d701-1bc3-4c1a-8699-b617d01e4ff5',
  'site_cover', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 70.0}'::jsonb, '%',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Maximum site cover under Table 3.1a for R80"}'::jsonb, 'R30 R35 R40 R50 R60 R80
60% 60% 65% 65% 70% 70%', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0327819397bad542689e1b3aff6824fa0ab31d7e2a7f581dc758a9ae2a32a475',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ef51bda9-6982-5f63-9e25-7430dca20080', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 70.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd03b7b55-8e5b-50d2-aef1-c8397621d7f4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd50852fc-fa31-4444-bd6b-0c63d3619ea3',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R20", "R25"], "dwelling_type": "any", "condition": "Boundary walls in areas coded R20 and R25"}'::jsonb, 'in ar
eas coded R20 and R25, walls not higher 
than 3.5m, up to a maximum length of the 
greater of 9m or one-third the length of the 
balance of the site boundary behind the front 
setback, to up to two site boundaries', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '182b2678a03c93a9eb473e3acd362f1a6ce6cb51d487574d077b2ff8e896cbc3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ab3d6d0b-08f1-5a50-86cf-7b93a604ee86', 1,
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
  '22d117e3-1eb9-5d91-8e56-710c9e0d10be', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd50852fc-fa31-4444-bd6b-0c63d3619ea3',
  'boundary_wall_length', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 9.0}'::jsonb, 'm',
  '{"density_codes": ["R20", "R25"], "dwelling_type": "any", "condition": "Maximum boundary wall length (greater of 9m or one-third balance) in R20/R25"}'::jsonb, 'in ar
eas coded R20 and R25, walls not higher 
than 3.5m, up to a maximum length of the 
greater of 9m or one-third the length of the 
balance of the site boundary behind the front 
setback, to up to two site boundaries', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '06c3b01671293f23405f04189f1f5157916057e793fad8e903d7ccc8bfa73f32',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ab3d6d0b-08f1-5a50-86cf-7b93a604ee86', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 9.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b44d674d-e5f1-578c-8b4a-7447f57389bc', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd50852fc-fa31-4444-bd6b-0c63d3619ea3',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35", "R40"], "dwelling_type": "any", "condition": "Boundary walls in areas coded R30 to R40"}'::jsonb, 'in ar
eas coded R30 to R40, walls not higher than 
3.5m for two-thirds the length of the balance of 
the site boundary behind the front setback, to 
up to two site boundaries', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '903e586fcaee9b526948ba5fd10918749a638a4df1f4430bf2bb7f95f431c684',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ab3d6d0b-08f1-5a50-86cf-7b93a604ee86', 1,
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
  '88ba02c1-99e4-5f82-9058-81d9eb9bb548', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ba988a14-1c30-49bb-bc45-627c02569c03',
  'visitor_parking_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.25}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Visitors car parking spaces per dwelling (multiple dwelling) - Location A"}'::jsonb, 'Visitors car parking spaces 
(per dwelling) 0.25 0.25', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '227aa698fef3e87ec4cf3b03c4862da6f26bea667b2437a041f73c49e5df222b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ed50f7fb-c060-55b4-a51b-66985364072f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''visitor_parking_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.25 None vs prior [0.0,2.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '354bf4a9-17b6-5a48-91b8-16a4e579ac77', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ba988a14-1c30-49bb-bc45-627c02569c03',
  'visitor_parking_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.25}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Visitors car parking spaces per dwelling (multiple dwelling) - Location B"}'::jsonb, 'Visitors car parking spaces 
(per dwelling) 0.25 0.25', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '08ae31b32a9ce857a43da59487eb86ab776309378ac9f3922e766dd0b36c8777',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ed50f7fb-c060-55b4-a51b-66985364072f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''visitor_parking_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.25 None vs prior [0.0,2.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fc37b154-48e3-58df-bb62-d50fb2a79470', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ba988a14-1c30-49bb-bc45-627c02569c03',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling less than 110m2 and/or 1 or 2 bedrooms - Location A"}'::jsonb, 'Less than 110m2 and/or 1 or 2 
bedrooms 1 1.25', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '84470d92c79267a4643be243caf53204767f5b9796a154b24fbf36c150f9407a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ed50f7fb-c060-55b4-a51b-66985364072f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2e3e4307-5612-5a09-be73-06db0cd7c037', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ba988a14-1c30-49bb-bc45-627c02569c03',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.25}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling less than 110m2 and/or 1 or 2 bedrooms - Location B"}'::jsonb, 'Less than 110m2 and/or 1 or 2 
bedrooms 1 1.25', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7e8177a81433e3f55926b53dc57cc2ba23643e289ee33e926070aeaa34fcddd8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ed50f7fb-c060-55b4-a51b-66985364072f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.25 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '91c282f1-1824-5401-a515-58c3394ae02e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ba988a14-1c30-49bb-bc45-627c02569c03',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.25}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling 110m2 or greater and/or 3 or more bedrooms - Location A"}'::jsonb, '110m2 or greater and or 3 or 
more bedrooms 1.25 1.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f701e4214e506f0c9498b485ef64fb66459787b7b40a68c3be8222b9e71de766',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ed50f7fb-c060-55b4-a51b-66985364072f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.25 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5e05720f-6d5b-5156-bbfc-d995341de2d5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'ba988a14-1c30-49bb-bc45-627c02569c03',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling 110m2 or greater and/or 3 or more bedrooms - Location B"}'::jsonb, '110m2 or greater and or 3 or 
more bedrooms 1.25 1.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'edd839b1fe6e11c01398dadc89c86cb2494fdd0388e1bb8df1d5889068af52fa',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ed50f7fb-c060-55b4-a51b-66985364072f', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a52af383-e41a-5860-bb75-d876c62062e0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'b77c964f-308a-41c6-b25e-7a086a94e59d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35", "R40"], "dwelling_type": "any", "condition": "Reduction permitted: primary street setback line may be reduced by up to 1m for a total of 30 per cent of the frontage width"}'::jsonb, 'in are
as coded R30, R35 and R40, the primary 
street setback line may be reduced by up to 1m 
for a total of 30 per cent of the frontage width', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '42d4053afe4cc6fcd5a652aa83893609bd3f12fa78266e3efc2b61e18cd3633a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6f108108-d7c5-50ca-9920-4833d682b913', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '67e7bfa3-2613-5e47-b35d-abb4f12c6e26', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4373bcd8-7c55-4091-a481-5a28552f2a0a',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5.0}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35"], "dwelling_type": "any", "condition": "Garage setback from primary street (Table 3.3b); may be reduced to 4.5m where existing or planned footpath, shared path or road alignment is located more than 1m from the street boundary"}'::jsonb, 'R30-R35 Minimum 5.0m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4c847faad68d0e58a80026e0fe18196f8b4b2b3531ad53b4a8f572fb81d00459',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3fc5f263-531e-5aee-9d70-83d93c83c2e3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0cbab7df-fc73-54f7-ac5e-b82cb3754d3d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd880886c-5812-4180-a279-e9816a0518a2',
  'side_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum lot boundary setback where wall height is up to 3.5m (Table 3.4a)"}'::jsonb, 'Up to 3.5m 1m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'af6833290a6ad80ca78bb7a0cb0c6af16700db3fcce8cbfd6e933b32121786b9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ada3472c-a048-5fd3-98bb-830f6ed329bc', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7ce599cf-7cf7-5196-b930-468074f38f32', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '54051a09-abf4-4f2a-9aac-0a4acb55bd3d',
  'boundary_wall_length', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 14.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum wall length for second storey walls set back in accordance with Table 3.4a (including any balconies)"}'::jsonb, 'The se cond storey of walls shall be set back in 
accordance with Table 3.4a for a maximum wall 
length of 14m (including any balconies)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '19e0af4c267e7ab017c674980118d037cb1394bb9e8096add96d24de48922de5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6fb59406-0edf-5c73-a11c-5132d9586e8a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '459d4232-eb75-5a21-b744-1b6c0f1e0b4c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '54051a09-abf4-4f2a-9aac-0a4acb55bd3d',
  'side_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "For portion of second storey wall exceeding 14m in length, remainder set back from lot boundary"}'::jsonb, 'the w
all is to be set back 3m from the lot 
boundary for the remainder of its length', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9afbd74ac8fd9520f5a042d82be7f50c396ebedfa8006f8e3a7040defed8cdda',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '6fb59406-0edf-5c73-a11c-5132d9586e8a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd998af98-1929-5af5-8ab8-91f73334a3a5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'f70f876a-42ec-4d48-b69a-b56f26bc77c5',
  'boundary_wall_length', 'deemed_to_comply', 'deemed_to_comply', 'lt', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Carports, patios, verandahs or equivalent structures built up to the lot boundary"}'::jsonb, 'str
uctures are less than 10m in length', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd2a863ee4aa94100b2559a3a25c3115f17f7ba6db6a96acfa9b51c925c99f353',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '16f6613e-b766-57d2-b4ee-5df8dad52518', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lt''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '39cb3915-5bbd-52fd-8edc-ffce0d4b11ca', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'f70f876a-42ec-4d48-b69a-b56f26bc77c5',
  'wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Carports, patios, verandahs or equivalent structures built up to the lot boundary; equivalent wall height measured to top of pillar and/or post"}'::jsonb, 'str
uctures do not exceed an equivalent wall
height of 3m (measured to the top of pillar and/
or post, refer Figure 3.4e)', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7570ad818dab6cc916c29c5172a84a1237b4f07c8c22851c83586c8f0fbbeabf',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '16f6613e-b766-57d2-b4ee-5df8dad52518', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'da54d21c-2def-5526-94a5-4e348734b9fb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'f70f876a-42ec-4d48-b69a-b56f26bc77c5',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 4.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Carports, patios, verandahs or equivalent structures built up to the lot boundary; ridge height limit"}'::jsonb, 'str
uctures do not exceed a ridge height of 4.2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ab70042c231950cff4a7cca26fcd4591164da7c8ca00199f9cb929ced6a905c5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '16f6613e-b766-57d2-b4ee-5df8dad52518', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.2 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '645a2852-e307-520a-862e-e7f70c541625', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '6e5092da-09b3-462e-a2fe-ef36c54e7673',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 13.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum boundary wall height; boundary walls permitted behind the street setback"}'::jsonb, 'to a ma
ximum boundary wall height  of 13m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '90d35d06246132f2032d19961f488f04a0fe25216c7d24f31539093c08da0fb0',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '90cd191f-9bd5-55fb-a413-53cd793358cc', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": false, "detail": "no normative word found in clause text; searched for: at least, maximum, minimum, must, no more than, not exceed, not less than, required, requirement, shall"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 13.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd5e3581f-087d-5aa1-b157-093fd3406e39', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'bab8510f-c0b1-4288-bd79-630b40bf3825',
  'retaining_wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Table 3.5a row: retaining walls and fill 1m or less requires 0m setback (measured from natural ground level)"}'::jsonb, '1m or less 0m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '534b048dd578253b6e3d59e8be0ab9142b38b90178f6871c2ad1f101350baf64',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '11555f7d-76cd-5656-9611-05debd91f3ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6edfcfad-aedb-5911-ad2a-6f17f342707a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'bab8510f-c0b1-4288-bd79-630b40bf3825',
  'retaining_wall_height', 'deemed_to_comply', 'deemed_to_comply', 'eq', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Table 3.5a row: retaining wall/fill height of 1.5m requires 1.5m setback"}'::jsonb, '1.5m 1.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dc2c49caa9a9b12a27b20b393ecaca5fcc23f42022bdcd862e45f2ebad78bede',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '11555f7d-76cd-5656-9611-05debd91f3ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''eq''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7f903ec9-4d8e-5346-be4f-e83cadfa1557', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'bab8510f-c0b1-4288-bd79-630b40bf3825',
  'retaining_wall_height', 'deemed_to_comply', 'deemed_to_comply', 'eq', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Table 3.5a row: retaining wall/fill height of 2m requires 2m setback"}'::jsonb, '2m 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0dcc5269b5c6328cd370ed3ce2d96414c26faf78d56aa0783e182229482034b7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '11555f7d-76cd-5656-9611-05debd91f3ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''eq''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '748a46f5-7173-578d-a372-24cb80849ac4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'bab8510f-c0b1-4288-bd79-630b40bf3825',
  'retaining_wall_height', 'deemed_to_comply', 'deemed_to_comply', 'eq', '{"value": 2.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Table 3.5a row: retaining wall/fill height of 2.5m requires 2.5m setback"}'::jsonb, '2.5m 2.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'da940722c4ce36a41c6ee7e37039fa8aa9dea681a84da6bcc9c46dcf7d5b8dc0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '11555f7d-76cd-5656-9611-05debd91f3ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''eq''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.5 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '44e29d6e-94ff-5eb6-bbe2-f7488c65f9a3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'bab8510f-c0b1-4288-bd79-630b40bf3825',
  'retaining_wall_height', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Table 3.5a row: retaining wall/fill height of 3m or more requires 3m setback"}'::jsonb, '3m + 3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '86ecf4bc65873dbba3ec855ea30be6a51f05932f1a331f4321f3583a5eb534b2',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '11555f7d-76cd-5656-9611-05debd91f3ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e461aaf4-db81-59d3-812d-76c16d4ddfe1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4217ba5f-705d-4e13-9bdb-21ee58429f47',
  'garage_dominance', 'deemed_to_comply', 'deemed_to_comply', 'pct_lte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Carports and supporting structures projected forward of the primary street setback line"}'::jsonb, 'Carports and supporting structure shall not exceed 
60 per cent of the frontage where projected forward 
of the primary street setback line', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '292d193d49de450b81c592f49cb5e1d7ced00882c1df140456a204523e3ae142',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '92b3248f-e939-5f67-8bc7-0b9833a1c697', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Carports and supporting structure shall not exceed 60 per cent of the frontage where projected forward of the primary street setback line''"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''garage_dominance'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e05ec10c-bccd-55ce-a5a5-3b18a9db5963', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'f8b1c999-c579-4c9d-874f-aec970fea1f0',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum driveway width within a communal street or battleaxe leg"}'::jsonb, '3m wid
e driveway in accordance with C3.7.3', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8b41368427b18eb41aeafa88b94f9d3992ad86abd23019e51167d70df21b860a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '7e840c37-b9d5-54d4-8bbc-39ee6fcd48e1', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '014d1358-ce11-589b-ab09-e9aed450f93f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c2345e6e-fcb0-4b73-ad19-08231ec0ea09',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum paved vehicular carriageway width within a 12m communal street serving potential 20+ lots"}'::jsonb, 'a pav
ed vehicular carriageway with a minimum 
width of 5.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '78b233c625a27c73c8f47af6d8388438f0aa4ed2f310c42ed90f75b454313f96',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'b61f2bc8-84c2-5b61-be10-e5e9ac0a8934', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5.5 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '49e06a69-e2b8-510e-b2af-93db3561227e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c2345e6e-fcb0-4b73-ad19-08231ec0ea09',
  'soft_landscaping', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum soft landscaping width within a communal street serving potential 20+ lots"}'::jsonb, 'soft
 landscaping of a minimum width 2.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6cb5118606e248df3f83fcf8a2ec6ddaa716a4e41847388904f3c641b58055c3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'b61f2bc8-84c2-5b61-be10-e5e9ac0a8934', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''soft_landscaping'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": false, "detail": "value 2.5 m vs prior [0.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c362956f-2ce7-57e1-b487-f1e80b768fdb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3db1037f-4fcf-478b-b839-51f0d0eb08bf',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum driveway width"}'::jsonb, 'a min
imum 3m wide', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '82e5fbc531d51433cdc1773c27945b50b258638db4c2bd8d03b9935067e271e4',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '7139f6d4-5e58-5e8e-b2c0-dd189cd7604d', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3ca4a824-7eb3-5ce7-83ae-087202fa0822', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3db1037f-4fcf-478b-b839-51f0d0eb08bf',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Maximum driveway width at the street boundary"}'::jsonb, 'a max
imum 6m wide at the street boundary', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4bd45e7b4136bbca92e6587351f1ead48da1498b82809fef5f6bf65fe2c704da',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '7139f6d4-5e58-5e8e-b2c0-dd189cd7604d', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4b2df382-576a-5bee-8de1-8000779b3c4d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'a3449762-bcfe-4903-893a-d12ca6575a61',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Minimum driveway width at passing points where driveway serves five or more dwellings"}'::jsonb, 'driveways to be minimum 5.5m wide', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9b7dc09500f370203c14aec0abadbcda5d98d81cca9711f9676964bae417312c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4947a63b-7338-58bc-8241-0d496a468118', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5.5 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a529a7ca-d347-5d81-9e6b-af8eb5ee77f7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4a77971d-4fd5-402d-aa84-bc102d4355bf',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Grouped and multiple dwellings located on a designated primary distributor or integrator arterial road; minimum width for a minimum 6.3m length excluding manoeuvring tapers from the street boundary"}'::jsonb, 'Driveways must be minimum 5.5m wide for a minimum 6.3m length (excluding manoeuvring tapers) from the street boundary', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'bfd7b845f17b6e48db97e7a3e3da6ff1a66aaeee65de016b68fbe4288f76fe62',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4d56e13d-c910-5ea3-815e-defb006de389', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''must''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5.5 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c7fcfebd-8392-522e-ad6a-072a9e0f9fad', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '3e41a63a-9128-4a86-85a3-0030511348ef',
  'fence_height_front', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 1.8}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Solid pillars forming part of front fences above natural ground level; pillar horizontal dimension not greater than 400mm by 400mm and separated by visually permeable fencing"}'::jsonb, 'Solid pillars that form part of front fences not more than 1.8m above natural ground level', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7ba8c12672b4829187c6ca63ca16e9925c13646541904c46a0fd9cf52722c16d',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9f45fb77-0717-5dd8-bf11-ecf056e4bc6f', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Solid pillars that form part of front fences not more than 1.8m above natural ground level''"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.8 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ac7bdb60-b9f7-55d9-b2dd-ebfd0ea9226b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '2fe04a9d-f7f1-4a08-83d5-233788e8b2ff',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "Driveways for multiple and grouped dwellings where the number of dwellings is five or more"}'::jsonb, 'Driveways for multiple and grouped dwellings 
where the number of dwellings is five or more, shall 
be:
• a mi
nimum width of 4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9020b8337bb82b5ad9473fb52b885c9c32680b5259ceb23285272df454cc8757',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'c092358c-2319-535e-bb42-5de80e63386b', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Driveways for multiple and grouped dwellings where the number of dwellings is five or more, shall be: \u2022 a mi nimum width of 4m''"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8376b294-7251-538e-8e98-1fc6445fe137', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '2fe04a9d-f7f1-4a08-83d5-233788e8b2ff',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Driveways for multiple and grouped dwellings where the number of dwellings is five or more"}'::jsonb, 'Driveways for multiple and grouped dwellings 
where the number of dwellings is five or more, shall 
be:
• a mi
nimum width of 4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5f127887adb8d6e899ce0bf6a6395ef6af6e4dd52c4d56ae497a3662b8db15b9',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'c092358c-2319-535e-bb42-5de80e63386b', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Driveways for multiple and grouped dwellings where the number of dwellings is five or more, shall be: \u2022 a mi nimum width of 4m''"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3dac9748-1ed5-5793-a387-409463bcb46d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '8c107804-884a-4637-bf3d-65681cbbe1d5',
  'driveway_width', 'exception', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "grouped_dwelling", "condition": "Driveways for multiple and grouped dwellings may be reduced where it is necessary to retain an existing dwelling and a passing bay or similar is provided"}'::jsonb, 'Driveways designed for multiple and grouped dwellings 
may be reduced to no less than 3m where 
it is necessary to retain an existing dwelling and a 
passing bay or similar is provided', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'be156a0f6619c9a92043ea2fcf3a14700ee951e57e123d186cac1a618fc0c2df',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9525c7a7-21f2-5e06-b5ba-544b61370a6b', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Driveways designed for multiple and grouped dwellings may be reduced to no less than 3m where it is necessary to retain an existing dwelling and a passing bay or similar is provided''"}, "normative_language": {"pass": false, "detail": "no normative word found in clause text; searched for: at least, maximum, minimum, must, no more than, not exceed, not less than, required, requirement, shall"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1651a161-d3b3-5ea8-a01e-2f125cadfd7a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '8c107804-884a-4637-bf3d-65681cbbe1d5',
  'driveway_width', 'exception', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "multiple_dwelling", "condition": "Driveways for multiple and grouped dwellings may be reduced where it is necessary to retain an existing dwelling and a passing bay or similar is provided"}'::jsonb, 'Driveways designed for multiple and grouped dwellings 
may be reduced to no less than 3m where 
it is necessary to retain an existing dwelling and a 
passing bay or similar is provided', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ce95f2c94f06850b26cff5fad0766c3e75252f87597fa2ce52b2cd23446a0461',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9525c7a7-21f2-5e06-b5ba-544b61370a6b', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Driveways designed for multiple and grouped dwellings may be reduced to no less than 3m where it is necessary to retain an existing dwelling and a passing bay or similar is provided''"}, "normative_language": {"pass": false, "detail": "no normative word found in clause text; searched for: at least, maximum, minimum, must, no more than, not exceed, not less than, required, requirement, shall"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '039ce4a3-2f35-513f-b43c-e627dedbde0b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '173ecad9-e80a-468a-a3b5-3cefb6d0a1e9',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5.5}'::jsonb, 'm',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Communal street serving development with potential to be subdivided to create 20 or more green title lots, strata lots or survey strata lots - paved vehicular carriageway minimum width"}'::jsonb, 'a paved vehicular carriageway with a minimum width 
 of 5.5 metres', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7d36cf81e8ac379797f02149eae4ba8b863f954e8e787729ab0efc28320c3631',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'b9e608f9-5776-57e5-b9bf-2a2e831beb40', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5.5 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  '674fe08f-c35f-5873-b85d-9cf6b3ab07a6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '5fca8bd9-ade4-4ae2-bd80-fa40451cb728',
  'retaining_wall_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 0.5}'::jsonb, 'm',
  '{"density_codes": ["any"], "dwelling_type": "any", "condition": "Retaining walls, fill and excavation between the street boundary and the street setback - maximum above or below natural ground level (exceptions for access, drainage, natural light)"}'::jsonb, 'Retaining wall s, fill and excavation between the 
 street boundary and the street setback , not more 
 than 0.5m above or below the natural ground level', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0c95506e2e84bf665736a7afcddd62020781c80f9442188d5820e142fb613cad',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '20b966a7-911b-5185-a1b4-1b9828889431', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''retaining_wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.5 m vs prior [0.1,6.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  '772968b5-ada3-5632-bf5d-40182459ebb9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5000.0}'::jsonb, 'm2',
  '{"density_codes": ["R2"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R2"}'::jsonb, 'R2 Single house or 
grouped dwelling Min 5000', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a5a76e7adaf3b6dc340c30c461b73482560b562c6092c8bd62b4be1900bba12f',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  '48867bbd-b5bd-5106-955f-d33242721215', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 50.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "single_house", "condition": "Minimum frontage at R2 (only applies to single houses)"}'::jsonb, 'R2 Single house or 
grouped dwelling Min 5000 - 50', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2b81b92fd0d1a6f32b1e31ed05c09e5a2dc6bd38739e3180e51bbe0f69e9c28a',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  'af380976-42fb-5e71-bfab-cf38c9c55dcb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4000.0}'::jsonb, 'm2',
  '{"density_codes": ["R2.5"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R2.5"}'::jsonb, 'R2.5 Single house or 
grouped dwelling Min 4000', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0d238d6c55d0fe1841bea53a5faf6ca17d6cea585ec0c0e826a10fa2750153fe',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '1abf53d1-5dcb-5f06-8f26-cc4d2a3dbb16', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 40.0}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "single_house", "condition": "Minimum frontage at R2.5"}'::jsonb, 'R2.5 Single house or 
grouped dwelling Min 4000 - 40', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5423a0ae3bc9e2454d5e36710e490cd8764f4e875530143c4cec515910f63647',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 40.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  'b7fb98b7-5474-5cd0-a4c1-b00da8ef8075', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2000.0}'::jsonb, 'm2',
  '{"density_codes": ["R5"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R5"}'::jsonb, 'R5 Single house or 
grouped dwelling Min 2000', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '599baa527435a5ca6569181c09e936e2e7279326f43ce87f4ee0f12dc49fce96',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '480aa5cf-53b3-5986-8fa8-0a67a0ae680f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "single_house", "condition": "Minimum frontage at R5"}'::jsonb, 'R5 Single house or 
grouped dwelling Min 2000 - 30', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7863620f4ce2956498db708bcd1d9983ebd165a9f2c996e686f8fca6013cdfad',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 30.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7484df46-9e74-52c3-a678-32aca6baae54', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 875.0}'::jsonb, 'm2',
  '{"density_codes": ["R10"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R10"}'::jsonb, 'Single house or 
grouped dwelling
Min 875 
Av 1000 925 20', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4469790e3e40458e0605e3a1613d36c63e13bf9530efe0cf10d39e504c9eeb73',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 875.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c09f4ee6-b251-5a40-9ad8-ec38ccfa0099', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 20.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "single_house", "condition": "Minimum frontage at R10"}'::jsonb, 'Min 875 
Av 1000 925 20', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'e1b15a876a4d14c933bb716315c3848b2bd14dc8d4b15b5c211fe97ebb2c2114',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '66f306d1-6d2f-5286-a401-42d573490b0a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 700.0}'::jsonb, 'm2',
  '{"density_codes": ["R12.5"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R12.5"}'::jsonb, 'R12.5
Single house or 
grouped dwelling
Min 700', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'e7295d5dda1550c578df3f55a51cb57e686248313114c61f97212d73a82ca384',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 700.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '904c048a-211f-5eb1-8d9d-16b453122bc1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 17.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "single_house", "condition": "Minimum frontage at R12.5"}'::jsonb, 'Min 700
Av 800 762.5 17', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8e432ea72d632168d45a0a1b4ffd819dafa0f93e10e4da7d1bc089f866a3d074',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 17.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f0d67fed-7c09-54fe-bd4d-c29d9e10d7c7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 580.0}'::jsonb, 'm2',
  '{"density_codes": ["R15"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R15"}'::jsonb, 'R15
Single house or 
grouped dwelling
Min 580', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '604f09e2e871202255d830214b0f10c2bbca6ed440ee8edf1cab296e98343a1b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 580.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'af459095-e1d5-5e53-8ac6-d7434ee5428c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 12.0}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "single_house", "condition": "Minimum frontage at R15"}'::jsonb, 'Min 580
Av 666 655 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ad3cb49f9f46e6b5a8919e523bab338b1c40992898c8536fc855379a0a8837a8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6916c8aa-ed45-51aa-8fa0-8937ed9c22b6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 500.0}'::jsonb, 'm2',
  '{"density_codes": ["R17.5"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R17.5"}'::jsonb, 'R17.5
Single house or 
grouped dwelling
Min 500', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'aefaffb47728100abf8634aa9c7e719ceabc9d8635341216e7f843ac84f600e9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 500.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '399eca36-ba6a-57f7-b330-71bb39a4b382', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 12.0}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "single_house", "condition": "Minimum frontage at R17.5"}'::jsonb, 'Min 500
Av 571 587.5 12', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3aa6236926e6a3ed8844f5bdf157f10d107275828a5e49a80a3a992ed62f3d2e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2295940f-d823-5763-8247-0caa51a84fd9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 350.0}'::jsonb, 'm2',
  '{"density_codes": ["R20"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R20"}'::jsonb, 'R20
Single house or 
grouped dwelling
Min 350 ', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '418cd3a9faa788e866aa17108672663ed58c70f9874029b7146896d08dc65c32',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 350.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9d60cc88-b663-5bcc-8573-d15644fed616', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "single_house", "condition": "Minimum frontage at R20"}'::jsonb, 'Min 350 
Av 450 450 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1f022555da2d35c3bae99bc6f8b5f4c9b7edbb801c5f9ab26874de7ea4685520',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0daf376c-4a9e-56d1-b6e8-e37f577ca934', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 300.0}'::jsonb, 'm2',
  '{"density_codes": ["R25"], "dwelling_type": "single_house", "condition": "Minimum site area for single house or grouped dwelling at R25"}'::jsonb, 'R25
Single house or 
grouped dwelling
Min 300 ', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '80304c5543b638de58e4c94d68474a6134a926d5aaf98f83001e554b10e401b7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 300.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e6a6aa83-7bc3-5144-a8ea-d8282e7cce47', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'minimum_frontage', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 8.0}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "single_house", "condition": "Minimum frontage at R25"}'::jsonb, 'Min 300 
Av 450 425 8', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '57237ae93678c894c59205fb862f931b740f5be2792c0c2ca185851664253a3b',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''Min 300 Av 450 425 8''"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 8.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '319d0166-b15d-5386-9dc7-e792be10b404', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 260.0}'::jsonb, 'm2',
  '{"density_codes": ["R30"], "dwelling_type": "single_house", "condition": "Minimum site area for single house at R30 (Part B)"}'::jsonb, 'R30 Single house Min 260 
Av 300 410 -', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2a68f98358322dfe140e87c8d3fec798e5449dfda3623d0bc7052da9d50240cb',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ed4ea9bc-d9bb-53d7-b0e0-a274b0df87ae', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 220.0}'::jsonb, 'm2',
  '{"density_codes": ["R35"], "dwelling_type": "single_house", "condition": "Minimum site area for single house at R35 (Part B)"}'::jsonb, 'R35 Single house Min 220
Av 260 395 -', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ceecea1740eaf15772b357e572310faa88ff4e0f7ad91e556815aff94f1f0d20',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 220.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '27c7527e-8170-5d20-aa83-4ec44f2821ce', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'fdd1ef1f-608f-4dce-b1b7-fa435fb0b6e0',
  'site_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 180.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Minimum site area for single house at R40 (Part B)"}'::jsonb, 'R40 Single house Min 180
Av 220 380 -', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '58b461cc09ee4f09d019f752151c4009b67eaf4b51d5bf8b20053355a2964a57',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '77cc1c9b-e492-5491-821c-14799cedf287', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 180.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 300.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 300.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 220.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 260.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 180.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 220.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 115.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 160.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 180.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 120.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 150.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 85.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 120.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 80.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ba0f9f97-e3a7-58e8-bef3-6d6edceff74f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'a14ffc14-da93-4b87-8ff9-846fdf796a42',
  'primary_street_setback', 'standard', 'none', 'lte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Buildings within Additional Use AU 8 area; maximum front setback to ''main street''"}'::jsonb, 'buildings shall have a 
 maximum front setback to 
 "main street" of 3.0 metres.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8af74d99691ed59b3d4f495cdaccb8b20f0fac2e47d1b45ea9c764fd64a5b776',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '61a8d000-7915-51fb-9185-3426cc8546a9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c5fa2e5d-2501-5341-a9a4-51c723d3bd56', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'a14ffc14-da93-4b87-8ff9-846fdf796a42',
  'side_setback', 'standard', 'none', 'eq', '{"value": 0.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Buildings within Additional Use AU 8 area; nil side setbacks permitted"}'::jsonb, 'Nil 
 side setbacks are permitted.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dfd7c00565255a28755e555b48c4fb6f99b365a543fc85c943bd5b444540527a',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '61a8d000-7915-51fb-9185-3426cc8546a9', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''eq''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 0.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fd0a8682-77e6-5359-8eeb-a8cb3fd94418', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '94fc2a72-016c-4fbf-80ec-23373d6e1bb1',
  'site_area', 'standard', 'none', 'gte', '{"value": 900.0}'::jsonb, 'm2',
  '{"density_codes": ["R20"], "dwelling_type": "grouped_dwelling", "condition": "Minimum lot area for permitting 2 grouped dwellings in R20 zones (variation from Table 1 Columns 3 and 4 of the Codes)."}'::jsonb, 'permitting 2 grouped dwellings on any lot with an area of 
900m2 or greater', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0d7e25b7b45b03b2f51fa66fa406338f574458aa359a23f34585eb66047571ad',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '869c8684-5dc7-5d5a-ab51-587381c60acb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 900.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c99c39d8-62a6-5fcd-8f98-edb89724fced', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '04af4474-d245-4267-a4ce-08e9a770d825',
  'plot_ratio', 'standard', 'none', 'lte', '{"value": 70.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Special Purpose - Small Dwelling (single house or grouped dwelling) with no more than two habitable rooms capable of use as a bedroom"}'::jsonb, 'Special Purpose – Small Dwelling is a single house or grouped dwelling with a maximum 
plot ratio of 70m 2 containing no more than two habitable rooms capable of use as a 
bedroom.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '131a127bc47c43af0c98d04b0dcc1152f343205fcd619e65ba4b1d9ab7a06144',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '1280b122-6aba-5c9c-adfb-a3ba3f840efa', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''no more than''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''plot_ratio'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 70.0 m2 vs prior [0.1,15.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f7d3886e-8cd1-51da-89f2-e0a29b712cd4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 80.0}'::jsonb, '%',
  '{"density_codes": ["R2"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ad8db7c443e22f7c8018274ceb0e2b8b89114c53736ef1768bc641e2a832d2cb',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 80.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  'ce1a6ee6-6bcb-5ccc-8ec5-2a36b7c12e5c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 80.0}'::jsonb, '%',
  '{"density_codes": ["R2"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fcf210fbffff663df7e954b79f5ab050c0a7c47dd19f6777a78e87d2d691e398',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 80.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  '0c23299c-f190-5bb8-8c83-9d021192c5a5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 20.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '270ca38d710aae33caeea3ff0c0a1372ebb385d41ecaa38b95d418876041b727',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  '72ff4889-61ea-5c4e-88d2-8d88a649db23', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 20.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '307d50ac6a2af40134d9dc6100263982bc14c4977ac3c857c8fe1460de17bca0',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  '23776bcd-4545-56e0-9211-1cfa05d92a2d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0b60b37f6eb0e50f802545a63781d7b48d543bdc25fcc29e2a5d46c6bffdded0',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  'c4470d44-eccd-579a-9118-03b401953041', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'e0a82d5d820c76c0cdb3b99e034327b1dd197a21b91e3e1931e34939d9bb9490',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  'a77f9ec4-3538-5968-af03-32085a7a9481', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2; other/rear setback"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5680cddf6555264f1f27ef0047420f19ddf05d7a24de30b8a31a491662142eb9',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  '3d43cc25-4c68-5132-bfeb-b97356a3a2ac', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": ["R2"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2; other/rear setback"}'::jsonb, 'R2 Single house or
grouped dwelling 80 - 20 10 10', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '04e799f2285e73cea8966f9722f8751c933eba07eb6b6ddd7d21961a61ccb1e3',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2'']"}}'::jsonb, now(), now()
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
  '6f950b25-e514-543d-98fc-9543d57f21aa', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 80.0}'::jsonb, '%',
  '{"density_codes": ["R2.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2.5"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd84eb8190b384bc86c72589124bedf8deec458a4a6a9cb3fa9ed8c07457fb952',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 80.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '4d5f7ec4-4de1-5411-86ef-6418edd699ee', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 80.0}'::jsonb, '%',
  '{"density_codes": ["R2.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2.5"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '30145d10476f442c29d69ac4c7566d068f742574b92680bfae1a0097e3fb5801',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 80.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '6cd4a0d4-e2a9-5792-8dfa-dd38e96b8d42', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2.5"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '98f395cf6d2a03a6aed88fe4e5ebd845f6b742f19055cf4a64ae389da7724e76',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '16a5b5d5-0fbf-56ed-9e71-9b9655aa8bb3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 15.0}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2.5"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd90e89c13a9198de6e703f88fadf04bca290e2581a15e3e744dd85541b150a82',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '49ae65f5-e12f-5492-9bf9-5df84449e874', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2.5"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '82837f2020871f494476dc36826f0a8a4245620394d16b97709f49425428cbfc',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '75706dff-475a-5e48-9059-d36629a270c6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2.5"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1bea1bbdb30e298e509ad1126637b97df3ea67a03bb9a3961e68a993c8e87902',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  'fe164422-b7b6-5b49-a769-dd97ec3cb230', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R2.5; other/rear setback"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '490f15891f31b8ac14ab5bc6904b4fff2bdef407a42da6924111f69dd7a96dd5',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '07cb8591-bb2c-5e42-97c5-ca9c3eb4a483', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R2.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R2.5; other/rear setback"}'::jsonb, 'R2.5 Single house or
grouped dwelling 80 - 15 7.5 7.5', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9aacfb88569d5f33c4b471e35933578d0ed1e24b8ab9edc0684a39747ca2b04f',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''R2.5'']"}}'::jsonb, now(), now()
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
  '861335f5-13ff-5017-930d-feac7aaba06d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 70.0}'::jsonb, '%',
  '{"density_codes": ["R5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R5"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0195841a88c105dbf8d4818a9388d4b677a084f98da32571ed422294712ddc1f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 70.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '715ad04b-5228-5d21-9f42-859dab6e9e12', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 70.0}'::jsonb, '%',
  '{"density_codes": ["R5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R5"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3ab79ea7aab92b4749023e9bc488b5e1ed0ccc2e3df9ced346b328384bcc2061',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 70.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'dcdeca57-2a42-5f05-91c8-1631234c838d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 12.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R5"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0b6e7b6db07c51333529d2a467de7b01b70d4b9cbc0ca2cc649e26883f31eee9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e6151673-94b2-5723-8e0a-26a793595f63', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 12.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R5"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '75f007e16a8e9ee07832330f899999d7606417a93cc5a5a001f8b32e76a59c5c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8bd3f2af-99ea-55ed-aefb-398745dfd46a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R5"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '538f06abf516e97383c7b44032c50dcae2e3a2b7cb2bb492fba011cd050c8e7a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '79d763b0-1dd0-5745-a716-b0b28e9d7379', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R5"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '15c571aa0165872c4b79c823e050664f5143d42b43bf2deb4e31578a65a8335f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cfb9a4f3-519f-5859-bc8e-8b2c063498bf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R5; other/rear setback"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '775ea576cd6774a4abf02daa81b86e9ee16982880d9fac0eb7e7033f055148ba',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '64d652c2-9523-593c-bd74-491482a7bac3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R5; other/rear setback"}'::jsonb, 'R5 Single house or
grouped dwelling 70 - 12 6 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'cc76e04324acef506c1fe24717257c76e89729854ea333662b91f520a04c2fe4',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '833dc0c4-c6a0-5b50-96d8-81215d8c0088', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["R10"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R10"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd2bd2451c90348e8a24140777b017bcf180335969a5277b427c5a8b81949e5c7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4ba6ce93-c77b-53c8-a366-85689b9a2848', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["R10"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R10"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dd42fd1501f91699f7a22189440116d093205a9f4a8b259899a415941c49a90f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd7625e22-f065-5e49-a15a-b4270061fc30', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R10"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '59c702b58d1d58945c14d556a113e92ca06f1cd2f65e428cd5538f10b5ae6ce9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e11a6da7-d4cf-5255-aeb6-03781a044794', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R10"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd8c7dec662a4f87fc18ad7dfad46da700a014e2567472d94c8a05770f6921dcf',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '345898b0-b505-5c20-9438-b5184882b776', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R10"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fa38d1df6b9095b004b67352fb68a78a27741b557ab5021f8c1c9f94956a19d7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c84960fc-ee1c-5916-a905-699ac1c5f209', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R10"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4276d50699fe944bb91e695b124041479acb38d3e8b752182267c9bf02965749',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a8eda92c-13e6-59a8-8e2e-9e5b01db5fbd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R10; other/rear setback"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2b76fbab30122255ad6c3111814ea44b381c520ca28f4c9a07f60b48c5de6ece',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '93ef935e-3425-5d5f-9fc1-cc25f271deb9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R10; other/rear setback"}'::jsonb, 'Single house or
grouped dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c666ef9d99d1705eff527267f6ebe0723c4a6f2b7f5f311752def73200e26dd2',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd3c3368d-e7b5-57f9-91d6-ebed7746d93a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 60.0}'::jsonb, '%',
  '{"density_codes": ["R10"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R10"}'::jsonb, 'Multiple dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '61f83fd715388fcf56f440d32667b5a485619e3203702afe413ef9e19883205e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 60.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9406e213-527d-574c-b8de-9e25f6186d4c', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R10"}'::jsonb, 'Multiple dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6e3555cece29f91ada367092193c4833992b21e069c4f99c46d946e116d26bdd',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '88911764-eb32-52b5-94ef-eb5b17411540', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 3.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R10"}'::jsonb, 'Multiple dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '12b16ccf068e012c5e4cddc5c1e1fe6e5831275db5c7c459df3e71396d610526',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b4a609b7-bd54-5b6d-863d-5ca4ce153f5d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R10"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R10; other/rear setback"}'::jsonb, 'Multiple dwelling 60 - 7.5 3 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1aa7174ce537f0065a0e1e765f8ebf794935dad6f358f27ac0b983a8baac77a5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6e131cd2-4553-550f-9a7e-6f3d46ce1949', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 55.0}'::jsonb, '%',
  '{"density_codes": ["R12.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R12.5"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8f394193bd7cc014aab3f2d80739af3e3390be70e0238e67fabf32b40a2a3ba9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 55.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c57f4623-ef31-572f-ad6b-e70449aba53d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 55.0}'::jsonb, '%',
  '{"density_codes": ["R12.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R12.5"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b07fbd0958a9b0d168dc691fdc4ebba31da206db6df83f7a3d60073d0175cd21',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 55.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b2e10602-d675-5904-8973-0df13200b583', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R12.5"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd3b1b9d395aeddda2d5c5ef65868c9924c79b8b27ff6a91fb501efab67c97f71',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '464d7c2c-2d5d-5bfc-acf9-88e6fc8bcf25', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R12.5"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f77923540dbc2164f72c8d7a31cbfd23645e1cf8d08b96a00aa7040d6008c23e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'cb4f1aef-61d2-55e7-b0b3-60a968ba39d4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R12.5"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '104ff3e0d283e8f37bfe49b7ecd529c6b62229df8afd63450faf01a7e1021871',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '461f47db-5e21-540e-b20e-be77123e9c30', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R12.5"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6cc4eb08167cb1858b5c6656aba36e3b099c649066db4cb354400040e6d2e544',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ce780e76-621b-5785-8f78-1282ae363f03', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R12.5; other/rear setback"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '10ece6ead4ad709081c45e97cbf0525756eac0699219db0aded1cd21f409566e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '443c6064-81b2-5872-a782-980dbf6bf2aa', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R12.5; other/rear setback"}'::jsonb, 'Single house or
grouped dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fdad32791b92a753603f86a1f68f7fe329edb3f9ac8845d8a34cc75c2a7672ae',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b11a6fd6-3d9c-57d0-892d-d3f1aed4a0e2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 55.0}'::jsonb, '%',
  '{"density_codes": ["R12.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R12.5"}'::jsonb, 'Multiple dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '48b149ed31932b62f6cab3a1f99eff0afa0d3c7c560636258418fbba07ae2b0a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 55.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5326a3a9-dee3-561b-aa67-745624d88d6a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 7.5}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R12.5"}'::jsonb, 'Multiple dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '97a77767533a26f04199e5a2a5fba9f03628669f291ef461f6d11a7d319983b6',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd198076c-ebb5-5411-a023-5d74f5b712ee', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 2.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R12.5"}'::jsonb, 'Multiple dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7419998c5db79ca170d6f9e993da0be1ea9ab0760aef58d4fc48405105d38692',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6e07cfcf-5e64-544d-a6ef-a4a585e257a7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R12.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R12.5; other/rear setback"}'::jsonb, 'Multiple dwelling 55 - 7.5 2 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '60a6efac80e55c61cae15ce2932cb7616a96b1e23ef8a18be5630751d97b17c3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '690eea1c-027b-56f8-952f-2423522a50ba', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R15"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R15"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '77c73ed8638a10211df5f41cbee80c1d34db8d5497d4447e83174fca7e30f896',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'dc340c3f-0d08-5d57-b889-32cae91433b0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R15"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R15"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6614a2cd30ca1131f1fdd7ba1782fb020f2490008eceb1e03e8b0ee810c70577',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '68b79a39-b415-53f1-9cc0-f5813193357d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R15"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '05890d1a6ce5d12e1b87ddc926702f365fc4998dd2bb2646290e88efb80b6499',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0be63f46-dc36-5b4d-902f-a43812c1c862', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R15"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f0944f218d2150ac8a839a341dd16f657e709e022eb3a114b7cfcd8e4594e4b0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '00ac8863-aebb-52c7-87b6-f8d9937d0951', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R15"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '60b1b54e6c44f9dc426d4be93711c4c096364be9bfc53991775ef07c0a8047bc',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '918641ae-c30e-590e-8d39-35baa8a50781', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R15"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7a4f44d6b157de587fbea321c4305b01842abc3c17cd83a28d1134afa22541f1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '524a2cb2-ee46-59bf-8e1b-6193540f8a81', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R15; other/rear setback"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '178fbd2e65cda8a63e78ee651a78393b0f7bc189f80845feee3c67113a98b9d9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '751bc9a0-0da9-52d2-86f1-fe7a5667b7cd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'rear_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R15; other/rear setback"}'::jsonb, 'Single house or
grouped dwelling 50 - 6 1.5 */6', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '348c307c47fa2a867fcb9b39311353d76612a9c1fe46db3ba57e810c92afee79',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4b0fb135-6b93-5aad-9fae-2bafa6301202', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R15"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R15"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'cf21a157364b6bb505410476223b78ddb2fda0fefe348f11dc25eb8620310dd0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b31a8b0c-3865-5a2e-b99a-b388f1013220', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R15"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6757c7e93a3b7b2b69a8a8f1fe653f3b307666bf522843c944d8a4b651019702',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f9225325-7853-555b-b879-50ce21fb0b1b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R15"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R15"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '336315e5e4a9632ed8f5bb6dc6160952c44ac0768410f57c3d6e892b4587ffa6',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f3c69db7-d03c-586e-9fb7-aa96ca39f868', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R17.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dac6891782b1dfa50333b1289bc5e4e870c976ee7fbbff3292742f642a88afdd',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e6c49e6e-fbe1-58d2-8863-16400d81ddea', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R17.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7f55cf4e90fdf66111b11efcd79987e098ffa5132e9b58b7b9d0f639481889bb',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '67733045-a92a-5fc8-9538-974faa0b33fe', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 36.0}'::jsonb, 'm2',
  '{"density_codes": ["R17.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a515a7ae07c84bed9baa261a2f696a17577ef78f2cadf3fc9b811d98b40f67b5',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 36.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5a18336a-7601-5df0-99fa-129fe881d591', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 36.0}'::jsonb, 'm2',
  '{"density_codes": ["R17.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f228b1662e4320ffb65f082d90255a7d34a2a5f4b5eea172e614e2a7e64a7ad1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 36.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '71ddafd7-11bc-5e00-a4f4-9642e2cbe3c0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '99d0869c479525b4502cf0db3c56bb0c495088cdabdaf5e72372ef3de16a2e41',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c7b2f4cf-1036-5d2b-a95e-9726d39bbab8', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3f49615a12858fe389c1f663014d0e6bcc9a868f34726e60f792f1bbb85df649',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3b49531b-50e0-575a-b92b-c4ef7c593b08', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '41a9c4884ba0806bb5010a9ef339633b0b13b9934f3599620791451245272b5d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '590499a8-5905-5185-9b32-e746c5be964b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R17.5"}'::jsonb, 'Single house or
grouped dwelling 50 36 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2911563172ccce28daef6bc66791f9349c2f79f0faa1ac0712a5dcf79475b6d7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5be4f7bd-32fd-5076-8b12-2563f973be8f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R17.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R17.5"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7918d1f737b7078483dce99b977e31b67e76e3ff580360c9986662a2f1978a96',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'af0b8809-f35b-5466-be38-7630a6bea54b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R17.5"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'db47baa7c7b577cc36d25f39258e3c2ba2ba7376a97cc0fa95ab105a4c528c03',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '843e4c02-713f-56d8-98d2-5b8fce0f50eb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R17.5"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R17.5"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ad8908168307f1ed99a26b92da733629827e3ef78a8e2fc844cce79df20ab114',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '93e6dbbb-1d3d-5308-b134-4ba9442a1e5d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R20"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '605185baa31e06a1f250604b2f2f9a69be6a2db777bd219d7596dfd8810f4b50',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0d3d9aff-ace7-5082-b2de-54fd80333e23', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R20"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd7a434fceb812e9ff76daef60316f865edc437e599e7d8def722a60e19d002cf',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '59a20244-771e-5c23-b6e7-1a864520de56', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm2',
  '{"density_codes": ["R20"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9764d5cc1887fedad55218273d32884c9bec5b76f6b55583880a240cb727c710',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
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
  'a5578d9d-42a2-5e44-ae1f-1d1c9aeb008e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm2',
  '{"density_codes": ["R20"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a75b752d02cd0d3847de7b10f0061cc49a4463cdf1766dc80ca7be60fd62cb24',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
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
  'f580aba1-9ada-5fae-900f-c3bb9639f080', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'cab19c4ea9060317991f45a0da9703ee71af201b85748f70b104f2aa9dba230b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd0306e10-5269-5c8e-9215-09a3233f573f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'd5feabf684b258ef96e4f20495ea2b721d1a10bff9086d7e5260a2500ca30817',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '22e70a96-1865-5406-888b-b8896fb861e4', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0c215ec5816440800dc02c133c505da57f7d32b746c1efdf6e36f087764cdd41',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '38192660-0a45-55d5-88dc-c110065d9a71', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R20"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '85774805f8f5e4097d3f736befe0b5c9c87061924589ba8ea7c7c045219e199e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '70c673bd-6acd-5aa4-b7d0-167a3a5c4a2d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R20"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R20"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b3e4e4beae10415b52cd9433d8743b2c04b106cea1f14f1b4c547aced69b381a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd3190c0e-a0a9-5dc6-b2b5-4555634d0c83', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R20"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a8c94dcef43440d6d21f2cd6991407a4fc9e07c7319857a9a755a7256c3a529d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9d5b2d7f-4f77-5aef-bfe5-b1ff46acec1b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R20"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R20"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '46507b1758f19da3207c76fa9bfd329fd64428d175fb462d679f821049500e0a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '04a57de7-b03a-5d7e-879f-990768a2edaf', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R25"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '137e337c4a11f3210f8e9b7d8629d0eea894042037d1aa585054056961ba55d3',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'bfaeff6b-56b4-5cf5-a612-89baebf0511e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R25"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c8fe3c84f5208aa1ced4d87d4af5ac5a19cbc9c87450e9500eb2d910537600e9',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '0d4d86d8-f48f-5396-8a35-9cfe230e7a40', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm2',
  '{"density_codes": ["R25"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b4bd6daeb698757dbb74bd0e14f4d8fc99c24d9a4e7619ed1f271b2feaa1ad6e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
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
  'a5669687-7f31-5947-b563-55d408053f39', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 30.0}'::jsonb, 'm2',
  '{"density_codes": ["R25"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a3bcb68a18c874ef2fdb1b44d3842df81ed042be5644f1f9df68606db7050cf0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
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
  'e51c32c6-1f5d-5626-a930-c0717d637f9a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4799ee807edfb2dbe82d6059fa5e0cf6a6a3a094617a4d7b62ea03444b71a4f0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3abf4769-6aab-52b2-83bb-782231c16094', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '872754826fe16d6cc83518d734b8a0436e505db4da6ff17487c9325228400793',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'aeaf7651-2087-5d34-a8e8-7e0bd1f73adb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "single_house", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '8c566607a9e859640b0ad8050629a9eb690b98a694d85a82cc77849a83a8535f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ba423521-ce29-5256-9539-fd7f31c479e7', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "grouped_dwelling", "condition": "Single house or grouped dwelling in R25"}'::jsonb, 'Single house or
grouped dwelling 50 30 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dff212b6c03dc1bb5afde00929450a2f170148891ec8f4c3139380450d16b22a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a521187f-3c5f-595c-9875-eaa369e7e226', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 50.0}'::jsonb, '%',
  '{"density_codes": ["R25"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R25"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3b9f632feee5caab9496f94f7959bded50172bcf6ed6405a43fd62e416221316',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '70d090b5-0d7f-57b1-bdf7-64a4fd26d0c3', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.0}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R25"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '69eac692234fc353ca24a1007b8ee914dfee2b04e4d98d022ac1488912875f8f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f2dee675-927b-58fa-98a6-39664dadef5a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R25"], "dwelling_type": "multiple_dwelling", "condition": "Multiple dwelling in R25"}'::jsonb, 'Multiple dwelling 50 - 6 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '519817017dd6dcd6935bd25ba8e9997740b0cb897879eb1ab5cd8f3bd64e9122',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd9e1381c-b1c9-53f1-9fad-bc99c53b6609', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 45.0}'::jsonb, '%',
  '{"density_codes": ["R30"], "dwelling_type": "single_house", "condition": "Single house in R30"}'::jsonb, 'R30 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '444567c6e601bb25a957646c6685dec2dd15ba5dd6d1aac8f62d645a3584e97b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 45.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5877bab3-2685-54af-ba43-748f772a8637', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 24.0}'::jsonb, 'm2',
  '{"density_codes": ["R30"], "dwelling_type": "single_house", "condition": "Single house in R30"}'::jsonb, 'R30 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c2d4d2d403861ef21d27dca8343e0e7deccc8aa7c6098b8076ed5a57ee7eb2ee',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 24.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'a7261614-6af8-5c11-9af5-c30e40159148', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": ["R30"], "dwelling_type": "single_house", "condition": "Single house in R30"}'::jsonb, 'R30 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'bd3e1c08e573b15f5cd8ccaa039c7b9839db394f8ce049aa92df0feff4be1068',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c32939e8-40f2-5c63-8b44-6bc0f83028e6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R30"], "dwelling_type": "single_house", "condition": "Single house in R30"}'::jsonb, 'R30 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '047ea069aad2935f61fa37c2d4870b243957bb23348cdd9367fb251da0167cd1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1df00ec8-813f-55c1-8cf9-c0f8d858677b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 45.0}'::jsonb, '%',
  '{"density_codes": ["R35"], "dwelling_type": "single_house", "condition": "Single house in R35"}'::jsonb, 'R35 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b1d4122b11f98275a503c40935f036f68b51db63f256cf2acaf6239eae06b4f0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 45.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4d5c94dd-430e-5efd-8f7a-5afc9ff3310f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 24.0}'::jsonb, 'm2',
  '{"density_codes": ["R35"], "dwelling_type": "single_house", "condition": "Single house in R35"}'::jsonb, 'R35 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '77e64f4bd06601cb8428fc71d4ac5370ba41449d2539ecafd507ec0c2951a18a',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 24.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'fb31736f-aba9-509a-85ad-bb35ac45b3ae', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": ["R35"], "dwelling_type": "single_house", "condition": "Single house in R35"}'::jsonb, 'R35 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5fa863bfab39b418475dcae23492381b08f34259f285f17e0824eff0102f5141',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6e24d2d6-9442-5d21-ba80-14c4e4e11e92', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.5}'::jsonb, 'm',
  '{"density_codes": ["R35"], "dwelling_type": "single_house", "condition": "Single house in R35"}'::jsonb, 'R35 Single house 45 24 4 1.5 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ddcedfa18a66bd54c1475e1dcef960edda2406fbaa51618bec2e21260d5c5740',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.5 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2aaf8c48-ac32-5eb3-a425-32926d43df5d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'open_space', 'deemed_to_comply', 'deemed_to_comply', 'pct_gte', '{"value": 45.0}'::jsonb, '%',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single house in R40"}'::jsonb, 'R40 Single house 45 20 4 1 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'da760cd17f98ddd6e6435f29940c29212191200efb7906b15e06d605b749b376',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 45.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '066386a0-9d43-5c44-bba7-b886d02a2286', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 20.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single house in R40"}'::jsonb, 'R40 Single house 45 20 4 1 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '46d1bf35116b2b1e4bbb4db30aaf7a62cf83c0e5097ee31cf2f15a2e27b103b8',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
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
  '33dd1c37-e1b3-5dbb-99da-7046a40829b1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'primary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single house in R40"}'::jsonb, 'R40 Single house 45 20 4 1 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '738e3e866a4b995d94e2f9e4ae40792d665aca57fc8baaef3b02ed1e48913239',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8db9bdc8-dc3b-534b-894e-2ee6a447ba0f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '99321dbd-ed6b-49ec-a7fb-347013905f3d',
  'secondary_street_setback', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, 'm',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single house in R40"}'::jsonb, 'R40 Single house 45 20 4 1 *', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '437992edcca011ee6aed0dfea018ca95c4604114332f4dddbe861987aa74ff74',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'dbba623e-6f3a-5157-af0e-70c0ba646c21', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '90a93989-cf75-5389-a05a-a030c09984d0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Ancillary dwelling in Location A - minimum parking spaces per dwelling"}'::jsonb, 'Ancillary dwelling 0 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6aad66b16c05d92d4825d47c31bbf1ea6647939cfd03d5ec7e89bfad988607f0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3dc339ac-fea8-566d-bd15-241bc2770a10', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Studio and 1 bedroom dwelling in Location A - minimum parking spaces per dwelling"}'::jsonb, 'Studio and 1 bedroom dwelling 0 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f50f500154ac8d0e25d58fb4f4f76d4f459c323f79b95849848195d997b277d2',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ba65c449-7a7a-5584-9e3d-67610ebe3392', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "2 bedroom dwelling in Location A - minimum parking spaces per dwelling"}'::jsonb, '2 bedroom dwelling 0 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '4de5b2a06a2f361e240e0e44ecb6aa42e0c1c9edd4c1aa283179b9fe27b5a038',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2a577f1f-0467-503e-8420-51ab983b4510', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "3+ bedroom dwelling in Location A - minimum parking spaces per dwelling"}'::jsonb, '3+ bedroom dwelling 1 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'be562bad506685216cf8d8a275aad862f999d5e166421b0f9caed24645861049',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '45e902ab-f1ce-57b0-a96a-7d7d6e097791', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 0.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Ancillary dwelling in Location B - minimum parking spaces per dwelling"}'::jsonb, 'Ancillary dwelling 0 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fe839f04f6ee6ddbac358422219e529c7625f335772cb4e4ad72134665529464',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 0.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '9f977498-123c-51c0-8d42-cc2cb32a488a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "Studio and 1 bedroom dwelling in Location B - minimum parking spaces per dwelling"}'::jsonb, 'Studio and 1 bedroom dwelling 1 1', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '943ff3119caabfcb11a170fb648a3a117d26e1429795ec0ab06fa9634695c87f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f4d8e964-39cc-5c9d-b917-756d73455fb5', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "2 bedroom dwelling in Location B - minimum parking spaces per dwelling"}'::jsonb, '2 bedroom dwelling 1 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '990a6223793b9ab54e649dbba8f69e4b34129df1f064361cf258a13385bb6582',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '75f2ff14-6f59-5d05-b680-bb341eb58a7d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '819c3db2-4f95-48cd-b533-604b512f2f54',
  'parking_bays_per_dwelling', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "3+ bedroom dwelling in Location B - minimum parking spaces per dwelling"}'::jsonb, '3+ bedroom dwelling 1 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '9e774a522f846e719e04c8d44c0953343a72d66c7709f38388e2d44b1ea92e51',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '9455ee47-9d9f-524d-84a3-8414f1f85956', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8ba590dd-b268-5486-a79b-dafe0d72292d', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'aab6b18b-9170-49d7-a277-8869ba501de1',
  'fence_height_front', 'design_principle', 'design_principle', 'lte', '{"value": 1.2}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimises use of visually impermeable or solid front fences above this height"}'::jsonb, 'minimises the use of visually impermeable or 
solid front fences above 1.2m in height.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2d250e81329eb02e7a2f447820695f5721ca85fe06ebdf7111a5ed225807d26a',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '8f46e71e-5700-55fd-acde-61e50d301939', 1,
  '{"quote_anchor": {"pass": false, "detail": "quote not found verbatim in clause text: ''minimises the use of visually impermeable or solid front fences above 1.2m in height.''"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6ccf9a7c-564e-5d2c-87d1-a27a55e6dbdb', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'b026a1ae-f401-4508-b2b8-771b2a937e22',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 5.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Vehicle passing point driveway width for development with potential to be subdivided to create 20 or more lots"}'::jsonb, 'Min. 5.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '150add4001de6aa667cfeb70b723c0b12e2d52597201749a5b1100d8a88b2f18',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'cecf57b9-c46f-59e5-9b80-e45e5be6f7c0', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 5.5 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '3c6b9be3-01a7-5937-a0d6-c5e809d93094', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'b026a1ae-f401-4508-b2b8-771b2a937e22',
  'driveway_width', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 6.3}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Widened driveway at vehicle passing point to allow vehicles to enter and exit simultaneously"}'::jsonb, 'Min. 6.3m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3bf1afb339e162a69024a1468a87bbd987e94a63ee183a54447221d23f5d2188',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'cecf57b9-c46f-59e5-9b80-e45e5be6f7c0', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''driveway_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 6.3 m vs prior [2.0,12.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": true, "detail": "value 3.9 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''design_principle''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": false, "detail": "invalid density codes: [''any'']"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 17.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''20000''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": false, "detail": "value 20000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''1000''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1000.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''minimum_frontage'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [4.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_cover'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 50.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c4d5056e-31f5-5f38-a326-e1b1a11445a9', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'c0e0d535-7ce6-4980-87f1-b1cd1aca3b56',
  'building_height', 'deemed_to_comply', 'deemed_to_comply', 'lte', '{"value": 3.5}'::jsonb, 'm',
  '{"density_codes": ["R30", "R35"], "dwelling_type": "any", "condition": "Maximum boundary wall height for R30-R35"}'::jsonb, 'R30 – R35 3.5m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6cfda468fd624ba36c2f313d0bde4cd1fd6722b6e2cec04317b0d7c892dc21ed',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '520b1852-39a1-5663-bdf0-6a668279f50c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.5 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 7.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''boundary_wall_length'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 14.0 m vs prior [1.0,50.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'f0d9eb8a-b7ed-5bad-9050-6c67234cc5dd', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '83a8a761-48ae-4f8b-9bb9-52c76d7313fe',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 4.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimum length and width dimension of outdoor living area"}'::jsonb, 'wit
h a minimum length and width dimension
of 4m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'ab7afc954445b9a73288785f2934fefd36821c0e59dbce400842a160c733dac0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '8f032384-d204-5157-a468-9163520d50ec', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 4.0 m vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '372112f0-4904-557f-80db-0175bcbdfd5e', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', '4c0537b4-b94d-4a8d-9900-2ea4861e8574',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 40.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Site area greater than 220 m2; primary garden area minimum (single houses and grouped dwellings)"}'::jsonb, 'Greater 
than 220 40', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '748a537804bb2d88d035cf8d4c7ddeb9e947f87cf9e01486cb7ff949e9e6a56c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '83faa086-2806-5d7c-8d36-c47131896de8', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 40.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 35.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 30.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 25.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 20.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'db96eb51-8ffa-594b-997a-8dc895fa161f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9a909193-662d-4c8d-a595-fa2b25d0dcc4', 'd8405e1d-9bd2-40aa-8dec-75fb9abbd499',
  'outdoor_living_area', 'deemed_to_comply', 'deemed_to_comply', 'gte', '{"value": 8.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Studio / 1 bedroom dwelling - minimum private open space area per dwelling"}'::jsonb, 'Studio / 1 
bedroom 8m2 2m', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '5dfdb0285a17b0a5cfaea1d62bc6979b6f5127e43b2d51b3118fae641e232d07',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'a0ef06b3-05ab-5c05-8acd-c4afddda80ce', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 8.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 12.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 15.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''at least''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''outdoor_living_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 10.0 m2 vs prior [4.0,200.0] [''m'', ''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
INSERT INTO rule_candidates (
  id, org_id, source_version_id, clause_id,
  rule_key, rule_type, pathway, operator, value_json, unit,
  condition_json, quote, extractor_model, skill_version_id, prompt_hash,
  confidence, review_status, metadata_json, extraction_group_id, extraction_pass,
  validator_results_json, created_at, updated_at
) VALUES (
  'f26e3a4d-2b85-5c3d-bb52-d129d79038d6', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', 'f7bef6f4-8e24-48ba-9d99-4c9d20f494fd',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single Detached houses in Residential zones coded R40 must achieve a minimum height of three storeys"}'::jsonb, '_Development achieves a minimum height of three storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '84b87c36720fe92ece1a3c8d9bfc3c6207ca19a4ea89ce9fcbab2f7fa75749f4',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'c091ef11-359c-5c0b-8a15-c19426eb7887', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '268b3b6e-2f62-5002-b376-4b0f7ad54d60', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', 'f7bef6f4-8e24-48ba-9d99-4c9d20f494fd',
  'site_area', 'standard', 'none', 'lte', '{"value": 230.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single Detached houses in Residential zones coded R40 must have lot size not greater than 230m2"}'::jsonb, '_ The lot size in not greater than 230m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7ba8be0fec00acb0ce1914be2793acab364dcabf99f3c881f2da503538ac2d16',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'c091ef11-359c-5c0b-8a15-c19426eb7887', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''requirement''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 230.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '578a1291-cb04-5d9c-be86-1c5231ce8f79', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', 'ec331acf-9aa0-4168-8722-d2393245cf6d',
  'parking_bays_per_dwelling', 'standard', 'none', 'lte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "within 400m of quality public transport; maximum rate including visitor bays"}'::jsonb, '1 per dwelling (regardless of size), including visitor bays, within 400m of 
quality public transport', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3fd767d9a7340d4c4b97f2b9c3c6d403e311ab39e1877da462721c98281a4c83',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '89495e2a-1e49-509b-bd0c-9509342c2754', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b0fb462f-9c4d-5491-8452-78f7ec821c04', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', 'ec331acf-9aa0-4168-8722-d2393245cf6d',
  'parking_bays_per_dwelling', 'standard', 'none', 'lte', '{"value": 1.0}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "greater than 400m from quality public transport; maximum rate"}'::jsonb, '1 per dwelling (regardless of size), plus 1 visitor bay per 4 units, greater than 
400m from quality public transport', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '948328577bbf670227f2971ac58db8b6eb5250b157c73b5f9525ec9fdb57d86c',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '89495e2a-1e49-509b-bd0c-9509342c2754', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''parking_bays_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 None vs prior [0.0,5.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '8f756621-3057-59c0-9e69-517e36d6fa83', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', 'ec331acf-9aa0-4168-8722-d2393245cf6d',
  'visitor_parking_per_dwelling', 'standard', 'none', 'lte', '{"value": 0.25}'::jsonb, NULL,
  '{"density_codes": [], "dwelling_type": "any", "condition": "greater than 400m from quality public transport; 1 visitor bay per 4 units"}'::jsonb, '1 per dwelling (regardless of size), plus 1 visitor bay per 4 units, greater than 
400m from quality public transport', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '52143342a09d62c5daed1d9291dbf50ab9bde483036e0791f003fec7dc6e2adb',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '89495e2a-1e49-509b-bd0c-9509342c2754', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''maximum''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''0.25''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit is None (dimensionless)"}, "rule_key": {"pass": true, "detail": "rule_key ''visitor_parking_per_dwelling'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 0.25 None vs prior [0.0,2.0] [''None'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '91277f0a-2c7e-5e92-ab25-1b105a59b785', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', '9c993c99-50c5-451b-89bc-71ef39f1be7d',
  'site_area', 'standard', 'none', 'gte', '{"value": 800.0}'::jsonb, 'm2',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Lot size within areas coded R80 and above"}'::jsonb, 'Lot size within areas coded R80 and above shall be of a minimum area of 800m 2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a885750136ef6e737e075da9035c5231eb791df3b92b0ebd1351f12df8afeba0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ba040da2-3b1f-51ee-afc6-55b1f04d45fe', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 800.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '6c5ac119-9bef-59c6-9836-e959c1d43ae0', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', '9c993c99-50c5-451b-89bc-71ef39f1be7d',
  'lot_depth', 'standard', 'none', 'gte', '{"value": 20.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Lot size within areas coded R80 and above"}'::jsonb, 'with a minimum depth of 20 metres', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '1fa014028192e3abb2fc44828b1efaec7542f51098a07e5137ad0e8ccc3e71c0',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ba040da2-3b1f-51ee-afc6-55b1f04d45fe', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''lot_depth'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [10.0,300.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ff083002-f697-5083-bc65-2c8730e03a01', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', '9c993c99-50c5-451b-89bc-71ef39f1be7d',
  'lot_width', 'standard', 'none', 'gte', '{"value": 40.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Lot size within areas coded R80 and above"}'::jsonb, 'a minimum width of 40 metres', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3bf54ded18416f8f14a450b99131f23464ef5f3181dc0fb06dc7f39e35f2bcf7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, 'ba040da2-3b1f-51ee-afc6-55b1f04d45fe', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''lot_width'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 40.0 m vs prior [4.0,100.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '7df5e808-5b4a-5ed8-9ea9-e2a6ff0ccbc1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', '245c6a0e-42eb-4c03-bc4f-080148ba0e0c',
  'building_storeys', 'standard', 'none', 'gte', '{"value": 3.0}'::jsonb, 'storeys',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single houses approved at discretion of Council only when development is located within R40 residential zones and achieves minimum height of three storeys"}'::jsonb, 'Where development achieves a minimum height of three storeys', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'da271dc214fb97c1bcc69f3c0f546cb01f2082b896eaa21474730c5bb34c36b5',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3b32e890-5fe5-5b90-b087-cf7715b4d68a', 1,
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
  'c338d5e9-01a1-5a20-8e25-0c4df32ea6ac', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '9edd5573-6201-4d82-b6fc-3f63bcfd0aa1', '245c6a0e-42eb-4c03-bc4f-080148ba0e0c',
  'site_area', 'standard', 'none', 'lte', '{"value": 230.0}'::jsonb, 'm2',
  '{"density_codes": ["R40"], "dwelling_type": "single_house", "condition": "Single houses approved at discretion of Council only when within R40 residential zones and lot size no greater than 230m2"}'::jsonb, 'Where the lot size is no greater than 230m2', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b5ccb2b53807e404ddca50b3b9ffbef854cd4a6e832644e97791ae4eedfcbed7',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '3b32e890-5fe5-5b90-b087-cf7715b4d68a', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''minimum''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 230.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''deemed_to_comply''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1b5e1045-a6f2-511a-9df2-5a7f438acd1f', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'f0577494-0c98-498a-b3f2-98850496e4cd',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 20.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Where a lot has frontage to Russell Road, Coogee Road, Rockingham Road or Frobisher Avenue"}'::jsonb, 'Where a lot has frontage to 
Russell Road, Coogee Road, 
Rockingham Road or Frobisher 
Avenue the minimum building 
setback shall be 20 metres.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '64089ce1a36d31310d6f4c3c66d62635d7a0bd2e817df1c03975f44b46f9cd8e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4880c7d9-25dd-5215-a13b-b4cd794fd63c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 20.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '13f7f402-0ec7-529a-a892-7734f8c660f1', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'f0577494-0c98-498a-b3f2-98850496e4cd',
  'primary_street_setback', 'standard', 'none', 'gte', '{"value": 10.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Buildings to other streets (not Russell, Coogee, Rockingham, or Frobisher)"}'::jsonb, 'Buildings to other streets shall 
be setback a minimum of 10 
metres from the street 
frontage', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c0c0ae2b63ea49c1533dc75cfb64a83bc4d95cd0f7cd0da7980ec3a8aca4ea05',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4880c7d9-25dd-5215-a13b-b4cd794fd63c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e703e000-3ca9-5b33-94e2-d4c1c628f826', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'f0577494-0c98-498a-b3f2-98850496e4cd',
  'side_setback', 'standard', 'none', 'gte', '{"value": 5.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Side and rear boundary setbacks"}'::jsonb, 'Side and rear boundary 
setbacks shall be a minimum 
of 5 metres.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '52adf8470c47911a6d319ca313e29329bfa3ba20bdb11e267646f46be43d2e1b',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4880c7d9-25dd-5215-a13b-b4cd794fd63c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '85f37a1b-f521-55b9-8d9f-7ad7f4706243', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'f0577494-0c98-498a-b3f2-98850496e4cd',
  'rear_setback', 'standard', 'none', 'gte', '{"value": 5.0}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "any", "condition": "Side and rear boundary setbacks"}'::jsonb, 'Side and rear boundary 
setbacks shall be a minimum 
of 5 metres.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c64c0604a04e2af82e38c3b081e457cdef7b3956c3d2af350c5d25259c3456fd',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4880c7d9-25dd-5215-a13b-b4cd794fd63c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '79491d3c-6d7f-51e8-87b1-cf73bad8eb05', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'f0577494-0c98-498a-b3f2-98850496e4cd',
  'open_space', 'standard', 'none', 'pct_gte', '{"value": 25.0}'::jsonb, '%',
  '{"density_codes": [], "dwelling_type": "any", "condition": "minimum landscaped open space per lot in Development Area"}'::jsonb, 'A minimum of 25% of each lot 
shall be set aside as 
landscaped open space', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'a5639113e64b8588c36306e2126f4355f7c04860438819418365cb154ce48e8d',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4880c7d9-25dd-5215-a13b-b4cd794fd63c', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''%'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''open_space'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''pct_gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 25.0 % vs prior [10.0,100.0] [''%'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '2050b7f8-f889-58df-ad9b-0619dc144507', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '912fe37f-95fd-42fa-af45-0189690a17c9',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R20"], "dwelling_type": "any", "condition": "Development within R20, R25, R30 and R40 coded residential areas; restricted to two storeys plus a loft"}'::jsonb, 'Development within the R20, R25, R30 and R40 
coded residential areas is restricted to two storeys in 
height plus a loft.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'fdf5def150182b23cfb1e3c73bdc9f2fc0676c38d0e1ec28d19bef945a4a8e95',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '53119011-9b5d-5ea3-9583-c5b2a11d86fb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not less than''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'c7133664-a76f-5996-8122-84f3da2c42ca', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '912fe37f-95fd-42fa-af45-0189690a17c9',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R25"], "dwelling_type": "any", "condition": "Development within R20, R25, R30 and R40 coded residential areas; restricted to two storeys plus a loft"}'::jsonb, 'Development within the R20, R25, R30 and R40 
coded residential areas is restricted to two storeys in 
height plus a loft.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '6b70ed4148870318b04d42686d261d4c99838a06de1a0284f4944f6db938e656',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '53119011-9b5d-5ea3-9583-c5b2a11d86fb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not less than''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '23cdcdbb-b8e5-5901-b2b0-094c7c48f760', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '912fe37f-95fd-42fa-af45-0189690a17c9',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R30"], "dwelling_type": "any", "condition": "Development within R20, R25, R30 and R40 coded residential areas; restricted to two storeys plus a loft"}'::jsonb, 'Development within the R20, R25, R30 and R40 
coded residential areas is restricted to two storeys in 
height plus a loft.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '885e3fc30c0f3002fe827bef93c781b67b33a9bd1418f1f9cdb30219cd199a1d',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '53119011-9b5d-5ea3-9583-c5b2a11d86fb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not less than''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '1b3c51ab-e630-5166-aa9e-ebdef792f927', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '912fe37f-95fd-42fa-af45-0189690a17c9',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 2.0}'::jsonb, 'storeys',
  '{"density_codes": ["R40"], "dwelling_type": "any", "condition": "Development within R20, R25, R30 and R40 coded residential areas; restricted to two storeys plus a loft"}'::jsonb, 'Development within the R20, R25, R30 and R40 
coded residential areas is restricted to two storeys in 
height plus a loft.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '7756b3acad4b125f41db85865c92dbaa75a90e5c5c88959238728b26d288018d',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '53119011-9b5d-5ea3-9583-c5b2a11d86fb', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not less than''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'ef17f276-ac8c-5e96-aed2-09a55f445d83', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 8.0}'::jsonb, 'storeys',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Within the Marina Village and local centre areas coded R80; maximum eight stories"}'::jsonb, 'Within the Marina Village, and local centre areas 
coded R80, development is restricted to a maximum of 
eight stories.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '56f2343b5603354f16c8b7e5326f6ebb8f15a3b193551d7ec43bcbb24d1be2e5',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
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
  '59c75123-a25a-5c70-a8cd-ea0ca56b83ca', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 5.0}'::jsonb, 'storeys',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Residential R60 and R80 areas; height should be limited to maximum five storeys"}'::jsonb, 'The height of buildings in residential 
R60 and R80 areas should be limited to a maximum of 
five storeys (and not exceeding 21 metres) in height.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '694d216c70bedc9f11a4a5c4347254d1cccde8e1d707a0336988814d1c390dac',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''5''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5cef60f7-ca71-54fb-8532-a7e6ddb4f65b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_storeys', 'standard', 'none', 'lte', '{"value": 5.0}'::jsonb, 'storeys',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Residential R60 and R80 areas; height should be limited to maximum five storeys"}'::jsonb, 'The height of buildings in residential 
R60 and R80 areas should be limited to a maximum of 
five storeys (and not exceeding 21 metres) in height.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'dfdc225c6ea55464204b4b2cb0eb4ba82be8adde37e937ebdb61e503cdcdd183',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''5''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '5d2c8561-9936-5a72-b050-825f3be81124', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_height', 'standard', 'none', 'lte', '{"value": 21.0}'::jsonb, 'm',
  '{"density_codes": ["R60"], "dwelling_type": "any", "condition": "Residential R60 and R80 areas; not exceeding 21 metres in height"}'::jsonb, 'The height of buildings in residential 
R60 and R80 areas should be limited to a maximum of 
five storeys (and not exceeding 21 metres) in height.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'b942642ae76d6072cce2a5d6f3932bb34470d16559053a30e79a8c520ed520b1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 21.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '4ca7af79-92b2-5f04-8ba2-06d4947b41da', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_height', 'standard', 'none', 'lte', '{"value": 21.0}'::jsonb, 'm',
  '{"density_codes": ["R80"], "dwelling_type": "any", "condition": "Residential R60 and R80 areas; not exceeding 21 metres in height"}'::jsonb, 'The height of buildings in residential 
R60 and R80 areas should be limited to a maximum of 
five storeys (and not exceeding 21 metres) in height.', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '35c72ef9de60a663844ba98af62c4ac7c5b08a1cc52724088dfd53b382de368f',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 21.0 m vs prior [2.0,30.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'b7ecd6e5-b45e-5a35-881d-c092bd785589', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_storeys', 'exception', 'none', 'lte', '{"value": 8.0}'::jsonb, 'storeys',
  '{"density_codes": ["R60", "R80"], "dwelling_type": "any", "condition": "Higher structures permitted where conditions (a)-(e) met: community support, suitable location, tourist/activity node, no overshadowing of foreshore, visual permeability"}'::jsonb, 'Higher structures up to a maximum of eight storeys 
(and not exceeding 32 metres) in height may be 
permitted where:', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '0576581178543da2d98189c47b1bfb3bd36a37ad394b9fd7a125261e2fa92cf8',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
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
  '5db3ea05-c703-5dd2-9c1b-20b041a98c59', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', '79799773-cf86-4e59-bbf8-54b3a83b2e93',
  'building_height', 'exception', 'none', 'lte', '{"value": 32.0}'::jsonb, 'm',
  '{"density_codes": ["R60", "R80"], "dwelling_type": "any", "condition": "Higher structures permitted where conditions (a)-(e) met: community support, suitable location, tourist/activity node, no overshadowing of foreshore, visual permeability"}'::jsonb, 'Higher structures up to a maximum of eight storeys 
(and not exceeding 32 metres) in height may be 
permitted where:', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '49c3416561d138d2763d8fd64176697f6df8b2c62ee42072e3bd8dedf249f7e5',
  NULL, 'validator_failed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '4a4243da-c086-5ecb-bf9c-f70257ca79d3', 1,
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 10.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''4''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''required''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''rear_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.1 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''fence_height_front'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.2 m vs prior [0.3,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''secondary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 1.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''primary_street_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 5.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''side_setback'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 m vs prior [0.0,20.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''ground_floor_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.1 m vs prior [0.0,4.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''3''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 3.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''shall''"}, "no_orphan_numbers": {"pass": false, "detail": "numeric value(s) [''2''] from extraction not found in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''storeys'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''building_storeys'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''gte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 2.0 storeys vs prior [1.0,10.0] [''None'', ''storeys'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'd9b161f1-659a-5a57-902e-7316052ccef2', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'c2f7d8e2-ec48-43b4-aa33-f49769306fb9',
  'site_area', 'exception', 'none', 'lt', '{"value": 100.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Exemption from development approval for single house including extensions and ancillary outbuilding in Rural Zone and Rural Living Zone"}'::jsonb, 'of less than 100 square metres and a wall height not exceeding 4.5 metres in 
the Rural Zone and Rural Living Zone', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '3e6b2e3c78607724606256c3cf26994b1301d7e92e23be7cc4d5cdc9f7fdf1d4',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '44952cd7-3d4d-5d2e-ba11-0465b98bc8c4', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lt''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 100.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  'e760883d-e78c-51f5-af09-64c834dd5e2b', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'c2f7d8e2-ec48-43b4-aa33-f49769306fb9',
  'wall_height', 'exception', 'none', 'lte', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Exemption from development approval for single house including extensions and ancillary outbuilding in Rural Zone and Rural Living Zone"}'::jsonb, 'of less than 100 square metres and a wall height not exceeding 4.5 metres in 
the Rural Zone and Rural Living Zone', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'c952b6d7d55d76bcdea265c4065c97ea45c964210c11fd2b8abc730e157cb2c1',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '44952cd7-3d4d-5d2e-ba11-0465b98bc8c4', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '797d2102-6d4d-5839-8514-db00297ab02a', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'c2f7d8e2-ec48-43b4-aa33-f49769306fb9',
  'site_area', 'exception', 'none', 'lte', '{"value": 200.0}'::jsonb, 'm2',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Exemption from development approval for single house including extensions and ancillary outbuilding in Resource Zone"}'::jsonb, 'of 200 square metres or less with a wall height of 4.5 metres in 
the Resource Zone', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', '2ea82f1931ab90a017762775c1d9e44e22c85840630f2fd1c8d92c76e43e0d3e',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '44952cd7-3d4d-5d2e-ba11-0465b98bc8c4', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m2'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''site_area'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 200.0 m2 vs prior [50.0,10000.0] [''m2'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
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
  '806ffa92-0fc4-59cf-95b8-2cbdb305f0ec', '1d31c315-5087-47df-a8d4-ebfd08efad5d', '53d1da5b-3393-4146-8f39-b3e90b5a8023', 'c2f7d8e2-ec48-43b4-aa33-f49769306fb9',
  'wall_height', 'exception', 'none', 'lte', '{"value": 4.5}'::jsonb, 'm',
  '{"density_codes": [], "dwelling_type": "single_house", "condition": "Exemption from development approval for single house including extensions and ancillary outbuilding in Resource Zone"}'::jsonb, 'of 200 square metres or less with a wall height of 4.5 metres in 
the Resource Zone', 'anthropic:claude-sonnet-4-6', 'wp6_sonnet_v1', 'f24c2ff806c86321c650d9fe6c405281aaf471646c65c18a18d9db0bb034bd70',
  NULL, 'validators_passed', '{"wp6": true, "sonnet_pilot": true, "skill_version_id": "wp6_sonnet_v1"}'::jsonb, '44952cd7-3d4d-5d2e-ba11-0465b98bc8c4', 1,
  '{"quote_anchor": {"pass": true, "detail": "quote found in clause text"}, "normative_language": {"pass": true, "detail": "normative language found: ''not exceed''"}, "no_orphan_numbers": {"pass": true, "detail": "all numeric values present in quote"}, "unit_normalization": {"pass": true, "detail": "unit ''m'' is canonical"}, "rule_key": {"pass": true, "detail": "rule_key ''wall_height'' is valid"}, "operator_vocab": {"pass": true, "detail": "operator ''lte''"}, "pathway_mandatory": {"pass": true, "detail": "pathway ''none''"}, "range_prior": {"pass": true, "detail": "value 4.5 m vs prior [2.0,25.0] [''m'']"}, "r_code_sanity": {"pass": true, "detail": "density codes ok"}}'::jsonb, now(), now()
)
ON CONFLICT (id) DO UPDATE SET
  review_status = EXCLUDED.review_status,
  validator_results_json = EXCLUDED.validator_results_json,
  metadata_json = rule_candidates.metadata_json || EXCLUDED.metadata_json,
  updated_at = now();

COMMIT;

-- Summary (this slice):
-- {"clauses_seen": 126, "clauses_no_atoms": 0, "atoms_emitted": 438, "atoms_validators_passed": 334, "atoms_validator_failed": 104, "atoms_missing_clause_context": 7}
