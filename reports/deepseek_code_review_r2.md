# Code Review Round 2 — engine.py + resolver.py

### engine.py — `_condition_rank` returns `(False, 0.0, ())` for unmet dwelling_type, but `_select_rule_with_context` only checks `conditions_match` via the tuple's first element, while the code elsewhere checks truthiness of the returned tuple `(True, -distance, ())` — this is actually consistent, but there's a subtle bug below.

---

### HIGH — `density_codes` condition uses `conditions.get("density_codes")` but `_exception_trigger_gap` iterates `set(conditions) - set(_NUMERIC_CONDITION_FACTS) - _CONDITION_METADATA_KEYS` which includes `dwelling_type` and `density_codes` — this is correct.

---

### CRITICAL — `_filter_rules_by_spatial_scope` evaluates rules against **only non-blocked** scope types, but blocking is based on global `live_disagreements` keys, not per-rule. If the live verification disagrees on `structure_plan` but a rule's source is a `local_development_plan` (fact_type remapped to `structure_plan`), the rule gets incorrectly blocked.

- **Severity**: HIGH
- **Location**: engine.py:378–390 (`_filter_rules_by_spatial_scope`)
- **Bug**: `_source_spatial_scope` returns `fact_type = "structure_plan"` when the source metadata specifies `fact_type == "local_development_plan"` (line 329: `if fact_type == "local_development_plan": fact_type = "structure_plan"`). However, `blocked_scope_types` is built from `set(live_disagreements)` which uses the property fact's **original** `fact_type` (e.g., `"local_development_plan"` if the overlay layer_type was that). When `_filter_rules_by_spatial_scope` pops `"local_development_plan"` from `property_scopes`, the rule's source (remapped to `structure_plan`) still matches `property_scopes["structure_plan"]` — so it's not actually blocked. But if the live disagreement key is `"structure_plan"` and the property fact was written with `fact_type="structure_plan"` (which is the canonical remapped value from overlay.layer_type), popping `"structure_plan"` removes it, and the rule source (fact_type `structure_plan`) correctly becomes blocked. The actual bug is **inconsistent remapping**: resolver writes `fact_type` from `_SPATIAL_SCOPE_FACT_TYPES` which maps `"local_development_plan" → "local_development_plan"` (no remap), but `_source_spatial_scope` remaps `"local_development_plan" → "structure_plan"`. So a resolver-written `fact_type="local_development_plan"` fact will never be found by `_source_applies_to_spatial_facts` which looks up `property_scopes.get(fact_type)` where fact_type is `"structure_plan"` — meaning **LDP-sourced rules are always filtered out** even when the parcel is inside the LDP area.
- **Fix**: In `_source_spatial_scope`, don't remap `"local_development_plan"` to `"structure_plan"`; keep them distinct sets. In `_filter_rules_by_spatial_scope`, pop from `property_scopes` the fact_type as returned by `_source_spatial_scope` (i.e., match on the same key), and in resolver, use the canonical `fact_type` consistently (e.g., map `local_development_plan` → `structure_plan` in `_SPATIAL_SCOPE_FACT_TYPES`).

---

### HIGH — `_numeric_fact` reads `fact_by_type[fact_key]` but the fact's `value_json` may be non-dict (e.g., plain number), and it calls `_extract_numeric` which handles that — OK.

---

### CRITICAL — `_select_rule_with_context` rank ordering puts `has_material_conditions` (rank index 6) **after** `source_type_hierarchy_rank` (index 3). A global rule with conditions (e.g., `"dwelling_type == 'single_house'"`) can outrank a zone-specific rule without conditions, causing the conditional rule to be preferred even when it's less relevant.

- **Severity**: MEDIUM
- **Location**: engine.py:434–441
- **Bug**: The ranking tuple places `1 if has_material_conditions else 0` at index 6, after `conditions_rank` and before `base-key preference`. A rule with a dwelling_type condition (rank 1) beats a rule without (rank 0) at that index, but the zone-specificity at index 2 and source-hierarchy at index 3 come earlier. So a local-scheme zone-specific rule **without conditions** (rank: threshold=1, standard=1, zone_specific=1, source=2, ...) vs a global rule **with conditions** (rank: threshold=1, standard=1, zone_specific=0, source=0, ...) — the zone-specific one wins at index 2, so that's fine. But consider two rules with same zone_specific/source rank: a conditional one beats a non-conditional one, which is intentional (conditions make it more precise). This seems intentional, not a bug. However, `conditional_rules_seen`/`matched` logic at lines 445–448: if **any** conditional rule was seen but **none** matched, returns `needs_more_info`. But if a non-conditional rule was selected as `best`, and there were other conditional rules seen but not matched, it still returns `needs_more_info` — **this is a real bug**: a property with a valid global rule (no conditions) will be downgraded to `needs_more_info` solely because there exists an unrelated conditional rule (e.g., for a different dwelling type) that doesn't match.
- **Fix**: Only block when the **selected best rule** is conditional and unmet, or when the only available rules are conditional and all unmet. The current logic blocks even when a non-conditional fallback exists and is selected.

---

### HIGH — `_condition_rank` for numeric conditions uses boundary comparison but treats `label == "over"` as "measured > boundary", while labels like `"up to 3m"` get default `else` branch (`measured <= boundary`). However, the label check only looks for `"over"`; labels like `"3m and over"` or `"more than 3m"` won't match `"over"` and will be treated as upper-bound, producing wrong condition matching.

- **Severity**: MEDIUM
- **Location**: engine.py:168–172
- **Bug**: `label = str(...).lower()` then `if "over" in label:` — this misses common phrasing like `"3m or more"`, `"greater than 3m"`, `"exceeds 3m"`. A rule with condition `{"wall_height_m": 3, "wall_height_label": "more than 3m"}` would be treated as `measured <= 3` (upper bound), incorrectly rejecting a 3.5m wall.
- **Fix**: Expand detection to `any(marker in label for marker in ("over", "more than", "greater than", "exceeds", "minimum"))`.

---

### HIGH — `_advisory_relevance_score` downweights rules containing `"structure plan area"` or `"precinct"` in `_DOWNWEIGHT_KW`, but these keywords can appear in the **what_it_means** text of a residential rule that merely references a structure plan overlay. This silently relegates genuinely applicable advisory rules.

- **Severity**: LOW
- **Location**: engine.py:531–559
- **Bug**: Not really a correctness bug for pass/fail (advisory only), but can cause relevant rules to be ranked below irrelevant ones. Impact is low since results are advisory. Not reporting.

---

### CRITICAL — `_filter_rules_by_spatial_scope` queries `SourceVersion` and `Source` via `session.query(SourceVersion.id, Source)` which returns rows `(version_id, Source)` — but the query is `join(Source, SourceVersion.source_id == Source.id)` — this is correct. However, if a rule's `source_version_id` is missing from the query (e.g., the source was deleted), the rule is **kept** (line 388: `rule.source_version_id not in sources_by_version` → kept). This means a rule from a deleted/spatial-blocked source silently becomes LGA-wide — a fail-open that contradicts the "fail closed" intent documented at line 336.

- **Severity**: HIGH
- **Location**: engine.py:388–394
- **Bug**: When `source_version_id` is not in `sources_by_version` (source deleted or version missing), the rule is included unconditionally. A parcel-specific rule from a now-deleted spatial source could be applied LGA-wide, producing false compliance results.
- **Fix**: Fail closed: `return []` or filter out rules whose source_version_id can't be resolved. At minimum, log and exclude.

---

### HIGH — `_upsert_facts` deletes facts with `review_status NOT IN ('approved', 'promoted', 'confirmed')` — this includes `'pending_review'` facts (which are the ones just created) and **also deletes manual_override facts** created by the user, because manual overrides have `method='manual_override'` but their `review_status` may be `'pending_review'` or `'draft'`. This silently wipes user-entered proposed values whenever the resolver re-runs.

- **Severity**: CRITICAL
- **Location**: resolver.py:447–456
- **Bug**: The DELETE clause only preserves `approved/promoted/confirmed`, so any fact with `review_status='pending_review'` and `method='manual_override'` (the exact set the engine relies on per engine.py line ~590: `or_(PropertyFact.review_status == "confirmed", PropertyFact.method == "manual_override")`) will be **deleted** on every re-resolution. If a user enters a proposed setback and then the address is re-resolved, their input vanishes, causing silent `needs_more_info`.
- **Fix**: Change the DELETE to also preserve `method='manual_override'`:
  ```sql
  AND method != 'manual_override'
  ```

---

### MEDIUM — `_resolve_council_scope` prioritizes `council`/`local_government` facts over `project.council_scope`. The resolver writes `local_government` facts with `review_status='pending_review'`, but engine.py loads facts with `review_status == 'confirmed' OR method == 'manual_override'`. The resolver facts have `method='postgis_st_intersects_lga'` — **they will never be loaded**, so `council_scope` falls back to project.council_scope (which may be None). This means freshly-resolved properties get no council scoping until a human confirms the LGA fact — a silent gap.

- **Severity**: HIGH
- **Location**: engine.py:587–593, resolver.py:466–472
- **Bug**: Resolver writes `review_status='pending_review'` for all facts including `local_government`. Engine only reads `confirmed` or `manual_override`. So the `local_government` fact is invisible to `_resolve_council_scope`, making `council_scope=None` for all newly-resolved projects. Rules not scoped to any council still load (NULL council_scope), but rules scoped to the property's actual LGA won't, and rules from other LGAs might leak in.
- **Fix**: Either have resolver write `review_status='confirmed'` for authoritative spatial facts, or have engine also accept `method LIKE 'postgis_st_intersects%'` as a valid fact source.

---

### HIGH — `_select_rule_with_context` scores `specific` (r-code intersection) at rank index 5, but `rule.applicable_r_codes` could be `[]` (empty list) which Python treats as falsy — `2 if specific else (1 if not rule.applicable_r_codes else 0)` gives `1` for empty list, `0` for non-empty non-matching. This is correct: empty list means global. No bug.

---

### CRITICAL — In `run_check`, `_select_rule_with_context` returns `(None, unresolved)` when `unresolved` is non-empty, but the engine then records `status='needs_more_info'`. However, the **selected `best` rule may be non-None** while `missing_conditions` contains entries from **other** rules that were evaluated but not selected. The code at line 596–598 uses `missing_conditions` (which accumulates across ALL rules) to decide `needs_more_info vs unsupported`. If any unrelated rule has a missing condition fact, even a perfectly-resolved check gets downgraded.

- **Severity**: HIGH
- **Location**: engine.py:596–601
- **Bug**: `missing_conditions` is extended for every rule looped (line 438) but `unresolved` is checked before returning `best`. The final `return best` only happens when `unresolved` is empty. So the earlier concern about conditional fallback applies more broadly: any missing condition fact on any candidate rule blocks the entire check, even when a valid unconditional rule was selected.
- **Fix**: Only treat missing conditions as blocking when they belong to the **selected best rule** (or when no rule could be selected). Track per-rule missing and discard on replacement.

---

### MEDIUM — `_normalized_spatial_reference` uses `re.fullmatch(r"(SPN|LDP)\s*[/_-]?\s*(\d+)", raw)` but the searchable string in `_source_spatial_scope` is built from title/URL/file_number; `_SPATIAL_REFERENCE_RE` uses `\b(?:SPN|LDP)\s*[/_-]?\s*\d+\b` which will match `SPN 123` but also `SPN123` — fine. However, `_normalized_spatial_reference` is case-insensitive via `.upper()` — fine.

---

### CRITICAL — `_source_applies_to_spatial_facts` requires `required_refs & property_scopes` but `property_scopes` is built from facts with `fact_type.lower()` in `{"structure_plan", "special_area", "local_development_plan"}` (line 305). Resolver writes `fact_type` from `_SPATIAL_SCOPE_FACT_TYPES` mapping `local_development_plan → local_development_plan` (no remap), so the fact_type is `"local_development_plan"` — matches the engine's set. But `_source_spatial_scope` remaps `fact_type` from `"local_development_plan"` → `"structure_plan"` (line 329). So `_source_applies_to_spatial_facts` looks up `property_scopes["structure_plan"]` while the property fact lives under `property_scopes["local_development_plan"]` — **permanent mismatch, LDP rules never apply**.

- **Severity**: CRITICAL
- **Location**: engine.py:329, engine.py:308, resolver.py:505
- **Bug**: As identified above, the fact_type remap in `_source_spatial_scope` (`if fact_type == "local_development_plan": fact_type = "structure_plan"`) is inconsistent with how facts are stored. This means any rule sourced from a Local Development Plan will always be filtered out (fail-closed, but incorrectly).
- **Fix**: Remove the remap in `_source_spatial_scope` so `fact_type` stays `"local_development_plan"`, and ensure `_SPATIALLY_SCOPED_SOURCE_TYPES` includes `"local_development_plan"` (it does, at line 321).

---

### HIGH — `_build_citation` uses only `rule.rule_key` and `source_version_id`, but `CheckResult.citations_json` is expected to contain human-readable legal citations (e.g., "R-Codes 5.1.2"). This yields useless machine IDs as citations.

- **Severity**: LOW (advisory display issue, not a compliance logic bug) — skip.

---

### MEDIUM — `_exception_trigger_satisfied` for `dwelling_type`: if `required` is `None` or empty, returns `True` (line 242). But `_exception_trigger_gap` iterates trigger_keys which are condition keys **present** in `conditions`. If `conditions` has `{"dwelling_type": ""}` (empty string), `_exception_trigger_satisfied` returns True (via the `if not str(required).strip()` guard), so it won't be reported as a gap. That's correct.

---

### CRITICAL — `_council_scope` filtering in `_get_applicable_rules` uses `Rule.council_scope == None | == council_scope`. If `council_scope` is `None` (common for unresolved LGAs), the filter is skipped entirely, meaning **all council-scoped rules from every LGA load** and may be selected, producing false outcomes. A rule scoped to "City of Perth" could be applied to a "City of Fremantle" property when the LGA fact is unconfirmed.

- **Severity**: HIGH
- **Location**: engine.py:459–462
- **Bug**: When `council_scope is None`, no `council_scope` filter is applied — rules from all councils are candidates. The `_select_rule_with_context` ranking doesn't penalize council mismatch (no council component in rank), so a Perth rule may outrank a global rule.
- **Fix**: When `council_scope is None`, filter to `Rule.council_scope == None` only (global rules) — or add a rank penalty for rules whose council_scope doesn't match.

---

### MEDIUM — `_numeric_fact` tries fact_keys in order but doesn't check `fact.method == 'assumption'` before using; the later check at line 640 checks `matched_fact.method == "assumption"` — but only for the first matched fact. If the first matching fact in `fact_keys` is assumption-based, it's fine (blocked). But if the first is assumption and the second is real, the code breaks at first match and uses the assumption one — this is arguably correct (block).

---

### HIGH — `_corner_lot_from_parcel` uses `ST_GeometryN(geom, 1)` for MultiPolygons — takes only the **first** polygon, which may be wrong for multi-part parcels (e.g., two separate lots). Frontage may be the second part's edge; corner-lot heuristic misclassifies.

- **Severity**: MEDIUM
- **Location**: resolver.py:351–359
- **Bug**: `ST_GeometryN(geom, 1)` selects the first sub-polygon arbitrarily. For a legit multi-part parcel, the longest edge may be in a different part, producing wrong frontage/corner flags.
- **Fix**: Use `ST_Dump` and union, or select the part with the largest area: `(SELECT ST_GeometryN(geom, (SELECT (ST_Dump(geom)).path[1] FROM ... ORDER BY ST_Area(...) DESC LIMIT 1))`.

---

### CRITICAL — `_upsert_facts` deletes facts with `review_status NOT IN ('approved', 'promoted', 'confirmed')` — this wipes `manual_override` facts (method='manual_override', review_status probably 'draft' or 'pending_review') — **user-entered proposed values are lost whenever the resolver re-runs**. This directly contradicts the engine's reliance on `manual_override` for proposed values (engine.py line 590). Users who enter a proposed setback get it erased silently.

- **Severity**: CRITICAL (repeat)
- **Fix**: Add `AND method != 'manual_override'` to the DELETE.

---

### HIGH — `run_check` loads facts with `or_(review_status=='confirmed', method=='manual_override')` — but the resolver writes facts with `review_status='pending_review'` and `method='postgis_st_intersects_*'`. So all spatial facts (zone, r_code, LGA, lot_area, frontage, overlays) are **invisible** to the engine until a human confirms them. A freshly-resolved project will show `unsupported`/`needs_more_info` for all checks even though data exists.

- **Severity**: CRITICAL
- **Location**: engine.py:587–593
- **Bug**: This is the most severe integration failure. The resolver persists facts as `pending_review`; the engine only reads `confirmed` or `manual_override`. There is no promotion step visible in these files. The entire pipeline produces zero checks for new projects.
- **Fix**: Either engine reads `pending_review` facts from the resolver (e.g., method LIKE 'postgis%') or resolver writes `review_status='confirmed'` for authoritative spatial facts. The safest: engine includes `PropertyFact.method.like('postgis\\_st\\_intersects%')`.

---

### MEDIUM — `_get_advisory_rules` then `_filter_rules_by_spatial_scope` applies blocking, but advisory items with `key in emitted_keys` are skipped. If the same canonical key appears as both an advisory rule and a numeric check's rule, it's skipped — OK.

---

### Summary of most critical fixes needed (in priority order):

1. **resolver.py:447** — DELETE wipes manual_override facts (also engine never sees pending_review). Fix both.
2. **engine.py:329** — fact_type remap mismatch between `_source_spatial_scope` and resolver's `local_development_plan` fact_type.
3. **engine.py:388** — fail-open for missing source_version_id in spatial filtering.
4. **engine.py:444–448** — `needs_more_info` triggered by unrelated missing conditions even when a valid rule is selected.
5. **engine.py:459–462** — council_scope None loads all council rules.
6. **resolver.py:351** — multi-polygon parts ignored in frontage/corner heuristics.


