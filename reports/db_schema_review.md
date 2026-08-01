# DB Schema Review - DeepSeek Flash

### Missing index on `rules.rule_key` for rule-loading queries
**Type:** Missing Index  
**Impact:** High — rule-loading by `rule_key` and `base_rule_key` will do sequential scans on every compliance check  
**Table:** `rules`  
**SQL:** `CREATE INDEX ix_rules_rule_key ON rules (rule_key);`  
**Why:** The engine's `_base_rule_key()` and `_CHECK_TO_BASE_RULE_KEYS` perform frequent lookups by `rule_key`. Without an index, every rule load for a project does a full table scan, degrading compliance check performance as rules grow.

---

### Missing index on `rules.value_json->>'base_rule_key'` for WP6 rule resolution
**Type:** Missing Index / JSONB Performance  
**Impact:** High — WP6 rules with suffixed keys (e.g., `site_area.R40.grouped_dwelling`) require JSONB field lookups  
**Table:** `rules`  
**SQL:** `CREATE INDEX ix_rules_base_rule_key_gin ON rules USING GIN ((value_json->'base_rule_key'));`  
**Why:** The engine's `_base_rule_key()` reads `value_json.base_rule_key`. A GIN index on this JSONB path accelerates filtering when many WP6 rules exist across density/dwelling codes.

---

### Missing composite index on `rules` for approved rules by jurisdiction
**Type:** Missing Index  
**Impact:** Medium — filtering approved rules by jurisdiction and status lacks efficient access path  
**Table:** `rules`  
**SQL:** `CREATE INDEX ix_rules_jurisdiction_status ON rules (jurisdiction, status) WHERE status = 'approved';`  
**Why:** Compliance engines typically load approved rules filtered by jurisdiction. A partial composite index dramatically reduces I/O for this dominant query pattern.

---

### Missing foreign key constraint on `property_facts.property_id`
**Type:** Missing Constraint  
**Impact:** Medium — orphaned facts can occur if a Property row is deleted without proper cascade  
**Table:** `property_facts`  
**SQL:** `ALTER TABLE property_facts ADD CONSTRAINT fk_property_facts_property_id FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE;`  
**Why:** The engine creates PropertyFact rows for every property. Without a FK, DELETE on properties leaves orphaned facts that break joins and waste storage. A missing constraint also affects JOIN performance via dead index entries.

---

### Missing composite index on `source_versions` for effective-date rule lookups
**Type:** Missing Index  
**Impact:** High — rule-loading by `effective_from`/`effective_to` for current rules  
**Table:** `source_versions`  
**SQL:** `CREATE INDEX ix_source_versions_effective_period ON source_versions (source_id, effective_from, effective_to);`  
**Why:** The compliance engine loads rules from source versions that are effective as of a project's `as_of_date`. A composite index on source_id + effective period prevents sequential scans across source version history.

---

### JSONB `metadata_json` on `planning_features` should be junction tables
**Type:** Schema Design / JSONB Misuse  
**Impact:** High — zone/overlay data stored as JSONB cannot be indexed for spatial + attribute queries  
**Table:** `planning_features`  
**SQL:** `CREATE TABLE planning_feature_attributes (feature_id UUID, attr_key TEXT, attr_value TEXT, PRIMARY KEY(feature_id, attr_key));`  
**Why:** The resolver queries `planning_features` by `layer_type`, `code`, and often joins to `metadata_json` for zone labels. Storing these as JSONB prevents efficient indexing on frequently filtered attributes (e.g., `zone_code`, `density_code`), requiring full JSON scan per row.

---

### Missing GiST index on `planning_features.geom` for ST_Intersects queries
**Type:** Missing Spatial Index  
**Impact:** Critical — parcel-to-zone/overlay intersection queries will be sequential scans  
**Table:** `planning_features`  
**SQL:** `CREATE INDEX ix_planning_features_geom_gist ON planning_features USING GIST (geom);`  
**Why:** The resolver's `_zone_from_parcel`, `_overlays_from_parcel`, and `_corner_lot_from_parcel` all use `ST_Intersects` against parcel geometry. Without a GiST index, PostGIS executes full table geometry comparisons per request, severely degrading resolution latency.

---

### Missing composite index on `address_points` for trigram/LIKE address lookup
**Type:** Missing Index  
**Impact:** High — G-NAF address lookup uses `ILIKE '%term%'` on `address_text`  
**Table:** `address_points`  
**SQL:** `CREATE INDEX ix_address_points_address_trgm ON address_points USING GIN (address_text gin_trgm_ops);`  
**Why:** The resolver's `_gnaf_lookup` performs fuzzy address matching. A trigram GIN index dramatically accelerates partial-string matching compared to a default btree (which cannot support leading-wildcard LIKE). This index is essential for acceptable lookup latency.

---

### Missing partial index on `spatial_datasets` for active datasets
**Type:** Missing Index  
**Impact:** Medium — joining planning features to active spatial datasets lacks efficient filter  
**Table:** `spatial_datasets`  
**SQL:** `CREATE INDEX ix_spatial_datasets_active ON spatial_datasets (dataset_id) WHERE approval_status = 'approved' AND licence_status = 'approved';`  
**Why:** Resolver queries join to spatial_datasets to filter to approved data sources. A partial index on the active status reduces scan volume and accelerates the join predicate.

---

### Missing check constraint on `property_facts.value_json` numeric values
**Type:** Missing Constraint  
**Impact:** Low — engine expects numeric facts to be parseable; malformed values break compliance checks  
**Table:** `property_facts`  
**SQL:** `ALTER TABLE property_facts ADD CONSTRAINT ck_property_facts_value_numeric CHECK (value_json IS NULL OR jsonb_typeof(value_json) IN ('number', 'string'));`  
**Why:** The compliance engine's `_numeric_fact()` expects structured numeric values. Without a constraint, invalid types cause runtime exceptions or false "needs_more_info" verdicts. Constraint guarantees data integrity at write-time.

---

### Missing index on `check_results.property_id` and `check_run_id`
**Type:** Missing Index  
**Impact:** High — compliance result queries by property and check run lack efficient access  
**Table:** `check_results`  
**SQL:** `CREATE INDEX ix_check_results_property_run ON check_results (property_id, check_run_id);`  
**Why:** The engine writes and reads CheckResult rows per property per run. Without a composite index, queries filtering by property and run (the dominant access pattern) perform sequential scans, degrading post-run compliance review queries.

---

### JSONB `condition_json` on `rules` should be normalized to junction table
**Type:** Schema Design / JSONB Misuse  
**Impact:** Medium — dwelling_type and density_codes conditions stored in JSONB prevent queryable structure  
**Table:** `rules`  
**SQL:** `CREATE TABLE rule_conditions (rule_id UUID, condition_key TEXT, condition_value TEXT, PRIMARY KEY(rule_id, condition_key));`  
**Why:** The engine's `_dwelling_type()` and density-code filtering repeatedly read `condition_json` fields. As a junction table, these become indexed columns, enabling filtered queries like "all rules for dwelling_type=duplex AND density=R40" without JSON parsing overhead.
