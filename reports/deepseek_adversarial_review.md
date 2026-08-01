# LotFile Adversarial Review — DeepSeek V4
Generated: 2026-08-01 02:50:18 UTC
Flash model: deepseek-v4-flash | Pro model: deepseek-v4-pro

---

## Flash Pass: Rule Selection Logic


---

## Flash Pass: Address Resolution


---

## Flash Pass: Spatial Scope & Conditions


---

## Flash Pass: Check Registry Consistency


---

## PRO SYNTHESIS (deep thinking)
# Final Adversarial Review — Compliance Engine & Resolver

This review consolidates and cross‑references defects from four parallel audits, then adds deep‑reasoning discoveries.  Every finding is traced back to the guard‑rail: **only the correct rule must be applied to each address**.

---

## Findings (deduplicated, ranked by real‑world severity)

### Finding 1: `dwelling_type` condition ignored – rules leak across dwelling types
- **Severity**: **CRITICAL**
- **Category**: `wrong_rule_applied`
- **Location**: `engine.py`, `_condition_rank()` and `_select_rule_with_context()`
- **What happens**
  A rule with `condition_json = {"dwelling_type": "grouped_dwelling"}` is treated as matching a single‑house proposal.  The function `_condition_rank()` only evaluates numeric keys (`wall_height_m`, `wall_length_m`) and explicitly skips all keys in `_CONDITION_METADATA_KEYS` – which includes `dwelling_type`, `density_codes`, etc.  
  The ranking function `_dwelling_type()` is used solely as a tie‑breaker after the rule is already considered a **valid** candidate; it does **not** filter out mis‑matched dwelling types.
- **Why it’s wrong**
  A grouped‑dwelling rule for `boundary_wall_length` (e.g., *max 9 m*) can be selected for a single‑dwelling proposal, or a single‑dwelling rule (e.g., *max 6 m*) for grouped dwellings.  The engine will then produce a **false pass** or **false fail** because the numerical threshold is inappropriate for the proposal’s actual dwelling type.
- **Suggested fix**
  Extend `_condition_rank()` to match categorical conditions.  When a rule specifies `dwelling_type`, look up a corresponding fact (e.g., `fact_type = "dwelling_type"`) and require an exact match.  If the property fact is missing, block the rule with `needs_more_info` rather than silently ignoring the condition.

---

### Finding 2: Zone/precedence hierarchy not respected – global rules can override local schemes
- **Severity**: **HIGH**
- **Category**: `wrong_rule_applied`
- **Location**: `engine.py`, `_select_rule_with_context()` ranking tuple
- **What happens**
  The ranking only considers `r_codes` specificity, not `applicable_zones`.  A rule from the state R‑Codes (global, `applicable_zones = NULL`) may out‑rank a local planning scheme rule scoped to a specific zone (e.g., `applicable_zones = ["R20"]`).  
  The tuple places `is_standard` and `created_at` above zone–specificity, so a newer generic rule can beat an older local‑scheme rule.
- **Why it’s wrong**
  The Western Australian planning hierarchy requires local scheme provisions to prevail over the R‑Codes where conflict exists.  The engine can select the wrong threshold – e.g., a 3 m R‑Code setback instead of the 4 m local‑scheme setback for the same zone – yielding an incorrect compliance verdict.
- **Suggested fix**
  Add a weighting component for zone specificity: rules with `applicable_zones` that intersect the project’s zones should be ranked higher than global rules.  Incorporate a formal instrument hierarchy (local scheme > structure plan > state R‑Codes).  Also consider `council_scope` specificity when filtering finishes (though council filtering is done in SQL, the ranking should still favour locally‑tailored rules).

---

### Finding 3: Side‑setback rules used for both primary and secondary without distinction
- **Severity**: **HIGH**
- **Category**: `wrong_rule_applied`
- **Location**: `engine.py`, `_CHECK_TO_BASE_RULE_KEYS` and `_select_rule_with_context()`
- **What happens**
  The check definitions `setback_side_primary` and `setback_side_secondary` both include `"side_setback"` in their base key tuple.  A rule with `base_rule_key = "side_setback"` (or `rule_key = "side_setback"`) and **no** discriminator condition will match both checks.  The same numeric threshold is then applied to the primary side **and** the secondary street side, even though DCP 2.2 prescribes different minimums.
- **Why it’s wrong**
  The engine cannot distinguish which side the rule describes, so it silently assigns the same numeric value to both, violating the planning standard and potentially producing a false pass/fail.
- **Suggested fix**
  Ensure extractors produce distinct rule keys (e.g., `side_setback.primary`, `side_setback.secondary`) or embed a categorical condition (`side_type`) in `condition_json`.  Update `_condition_rank()` to match on `side_type` and refuse the rule if the fact doesn’t align.

---

### Finding 4: Battle‑axe lot frontage heuristic yields wildly incorrect `frontage_m`
- **Severity**: **HIGH**
- **Category**: `wrong_value` / `edge_case`
- **Location**: `resolver.py`, `_frontage_from_parcel()` – “longest exterior edge”
- **What happens**
  On a battle‑axe (rear) lot, the longest edge is often the narrow access handle, which can be 40 m long.  The heuristic picks that edge as `frontage_m`, and the value is later used by `garage_width` and `garage_dominance` checks.  The rule selection engine trusts this value as the street frontage.
- **Why it’s wrong**
  The true street frontage is the width of the access leg (often 4–5 m).  The inflated frontage leads to permissive garage‑width thresholds and may flag as a pass when the design actually violates the required frontage – a **false pass**.
- **Suggested fix**
  Use street centre‑line data or user‑provided frontage.  Flag battle‑axe geometry and require manual confirmation of the measured frontage before using it in compliance.

---

### Finding 5: Structure‑plan facts not created by resolver → spatial scope filter drops all structure‑plan rules
- **Severity**: **HIGH**
- **Category**: `correct_rule_missed`
- **Location**: `resolver.py`, `_overlays_from_parcel()` — excludes `layer_type = 'structure_plan'`; `engine.py`, `_filter_rules_by_spatial_scope()` relies on `fact_type = 'structure_plan'`
- **What happens**
  The resolver only creates overlay facts for `('overlay', 'bushfire', 'heritage', 'special_control')`.  It **never** writes `fact_type = 'structure_plan'`.  Later, when the compliance engine loads facts, there are no structure‑plan references.  Consequently, any rule whose source is a structure plan (`source_type = 'structure_plan'`) will fail the spatial‑scope check: `_source_applies_to_spatial_facts()` returns `False` because `required_refs` is non‑empty and cannot intersect an empty property scope set.
- **Why it’s wrong**
  All structure‑plan rules are silently excluded, even when a parcel is wholly inside an approved structure plan.  The compliance result for those checks becomes `needs_more_info` (or falls back to an inappropriate global rule), giving a completely wrong compliance picture.
- **Suggested fix**
  Extend `_overlays_from_parcel()` to include `layer_type = 'structure_plan'` and create matching property facts.  Alternatively, ensure a dedicated “spatial synth” step always runs before `run_check` and writes these facts.

---

### Finding 6: LGA boundary straddling – only one LGA used
- **Severity**: **HIGH**
- **Category**: `correct_rule_missed` / `silent_data_loss`
- **Location**: `resolver.py`, `_lga_from_point()` – `LIMIT 1` on `ST_Intersects`
- **What happens**
  If a parcel intersects two LGAs, the query returns only the first row.  The compliance engine receives a single `council_scope` and loads rules only for that LGA.  Rules from the other LGA are not loaded at all, even though they apply to part of the property.
- **Why it’s wrong**
  The property is effectively dual‑jurisdiction; rules from the second council are completely ignored, potentially allowing development that breaches one LGA’s scheme.
- **Suggested fix**
  Detect multiple intersecting LGAs, flag a warning, and require the user to select or review.  Until resolved, the engine should not produce a compliance verdict; it should return `needs_more_info` or `unsupported`.

---

### Finding 7: Ignored categorical conditions beyond `dwelling_type` – `density_codes`, `heritage`, etc.
- **Severity**: **HIGH** (compounds with Finder 1)
- **Category**: `wrong_rule_applied`
- **Location**: `engine.py`, `_condition_rank()` metadata skip
- **What happens**
  Any condition key not in `_NUMERIC_CONDITION_FACTS` and not in `_CONDITION_METADATA_KEYS` is considered “unsupported” and **blocks** the rule (treated as missing evidence).  However, keys like `density_codes` and `dwelling_type` are in `_CONDITION_METADATA_KEYS` and are completely ignored – they neither block nor filter the rule.  The same logic applies to hypothetical future categorical conditions (e.g., `heritage = "true"`), which would fall into the unsupported bucket and block the rule, but if added to metadata, they would be ignored.
- **Why it’s wrong**
  Rules that should only apply to certain density codes (e.g., R‑Code variants) are applied universally, just as with dwelling type.
- **Suggested fix**
  Treat `density_codes` and similar keys as matchable conditions.  Compare against property facts (e.g., `fact_type = "r_code"`) and require intersection.

---

### Finding 8: Ranking treats “exception” rules as lower priority, but may still pick one if no standard rule exists
- **Severity**: **MEDIUM**
- **Category**: `wrong_rule_applied`
- **Location**: `engine.py`, `_select_rule_with_context()` – `is_standard` flag
- **What happens**
  If only exception‑variant rules exist for a check (e.g., a rule for “boundary_wall_length” that is an exception to the standard), the engine will still select one.  Because the engine does not compare the exception condition against the proposal, it may apply an exception that wasn’t triggered (e.g., a wall‑height exception).
- **Why it’s wrong**
  An exception that requires a specific trigger (like a minimum wall height) might be applied when that trigger is absent, leading to an incorrect (usually more permissive) threshold.
- **Suggested fix**
  Exception rules should only be applied if their numeric or categorical conditions are fully satisfied.  The current `_condition_rank()` does evaluate numeric conditions, so if the exception condition is numeric, it should work.  The risk is for exception rules whose condition is not numeric (and not in metadata).  They should be treated as unsupported until their trigger is explicitly verified.

---

### Finding 9: Frontage heuristic not validated – may yield 0 for tiny parcels, causing divide‑by‑zero downstream
- **Severity**: **MEDIUM**
- **Category**: `edge_case` / `silent_data_loss`
- **Location**: `resolver.py`, `_frontage_from_parcel()` – when `MAX(ST_Distance(...))` is 0
- **What happens**
  For a parcel consisting of a single point (degenerate geometry) or one with all edges collinear, `MAX(ST_Distance(...))` could be 0.  The resolver stores `frontage_m: 0.0`.  Later, `garage_dominance` and `garage_width` checks that divide by frontage may encounter zero, leading to `needs_more_info` or unexpected `likely_fail` because the threshold may be `0` or a fraction of zero.
- **Why it’s wrong**
  A 0‑frontage is physically impossible; this is a data error that should prevent any compliance verdict.  Currently it may pass through and produce nonsense.
- **Suggested fix**
  If `frontage_m` is 0 or `None`, set the fact to missing and flag `needs_more_info`; never emit a compliance result with a bogus zero.

---

### Finding 10: Advisory 80‑item cutoff may drop the most relevant non‑numeric rule
- **Severity**: **MEDIUM**
- **Category**: `silent_data_loss` (advisory only)
- **Location**: `engine.py`, `run_check()` advisory loop – `if len(seen_adv) > 80: break`
- **What happens**
  The advisory rules are sorted by `_advisory_relevance_score`, but if the scoring function mis‑ranks, a highly relevant rule could be pushed beyond the 80th position and never shown.  The panel would not see a critical qualitative requirement.
- **Why it’s wrong**
  While advisory only, a missing rule can conceal a non‑compliance that should be flagged for assessment.
- **Suggested fix**
  Remove the hard cap, or raise it significantly (e.g., 200).  Rely on the relevance score to order, and let the UI paginate.

---

### Finding 11: Unsupported condition keys block rules that could otherwise be matched
- **Severity**: **MEDIUM**
- **Category**: `silent_data_loss` / `needs_more_info`
- **Location**: `engine.py`, `_condition_rank()` – unsupported keys cause `missing`
- **What happens**
  If a rule has a condition key that is not numeric and not in `_CONDITION_METADATA_KEYS`, the function adds it to `missing`.  When all candidate rules for a check contain such unsupported keys, `_select_rule_with_context` returns `None` and the check becomes `needs_more_info`.  This is intentional: the engine won’t guess.  However, some keys might be safe to ignore (e.g., `"dwelling_type": "any"`) but are currently not in metadata, causing an unnecessary block.
- **Why it’s wrong**
  A rule that is actually applicable and clear on its numeric threshold is suppressed because of an irrelevant categorical condition that was not whitelisted.
- **Suggested fix**
  Expand `_CONDITION_METADATA_KEYS` to include common flags that can be ignored for numeric matching, or provide an explicit “ignore” list configured per rule type.

---

### Finding 12: `canonical_rule_key` attribute missing may cause rules to be overlooked
- **Severity**: **MEDIUM**
- **Category**: `correct_rule_missed`
- **Location**: `engine.py`, `_select_rule_with_context()` – `canonical = getattr(rule, "canonical_rule_key", None)`
- **What happens**
  The open‑vocab pipeline clusters rules under `canonical_rule_key`.  If a rule row does **not** have this attribute populated (e.g., older seed rules), `canonical` is `None`.  The matching logic then relies solely on `rule_key` and `base_rule_key`.  If the check definition’s key expects a canonical label that is missing from the rule’s base keys, the rule won’t be considered.
- **Why it’s wrong**
  A perfectly valid rule could be skipped, resulting in `unsupported` for that check.
- **Suggested fix**
  Ensure a migration backfills all approved rules with `canonical_rule_key` derived from their cluster; add a default fallback that derives canonical from `rule_key` if the column is `NULL`.

---

### Finding 13: `planwa_live_disagreement` sets all checks to `needs_more_info` – no partial results
- **Severity**: **MEDIUM** (design choice, but loses information)
- **Location**: `engine.py`, `run_check()` – after operator evaluation, if `live_disagreements` is non‑empty
- **What happens**
  If there is any live spatial disagreement, **every** check is forced to `needs_more_info`, even checks that are perfectly matched against a rule and have valid measurements.  The engine does not produce a partial pass/fail picture.
- **Why it’s wrong**
  The user sees no actionable result; they must resolve every disagreement before any compliance feedback appears.  This is safe but may delay the project unnecessarily.  It also masks which checks would have passed, making it harder to prioritise.
- **Suggested fix**
  Allow a “disagreed” flag per check rather than a global halt; show likely results with a warning.

---

## Cross‑referenced compound bugs

1. **Dwelling‑type ignorance + zone‑specificity missing**  
   *Finding 1 ∩ Finding 2*  
   A grouped‑dwelling proposal in a specific zone (e.g., R‑Code 30, City of Stirling) might be evaluated against a **global, single‑dwelling R‑Code rule**.  The engine picks the rule because it has a numeric threshold, is “standard”, and date‑ranks higher.  The local scheme’s grouped‑dwelling rule with a different (correct) threshold is ignored because it has a non‑matching `dwelling_type` (which the engine ignores) and because its zone specificity is not ranked higher.  Result: completely wrong compliance verdict.

2. **Side‑setback confusion + dwelling‑type ignorance**  
   *Finding 3 ∩ Finding 1*  
   A rule labelled `side_setback` with `dwelling_type = "grouped_dwelling"` could be applied to a single house’s primary side setback, giving a too‑generous minimum.  Since the engine cannot tell primary from secondary, the error propagates to both checks.

3. **Battle‑axe frontage + garage dominance/width checks**  
   *Finding 4*  
   A battle‑axe lot with 40 m longest edge triggers a garage‑width threshold that is far too large, producing a false pass.  If the user’s actual garage exceeds the real frontage rule, the engine misses the violation entirely.

4. **Missing structure‑plan facts + zone‑specific ranking**  
   *Finding 5 ∩ Finding 2*  
   Even if structure‑plan facts were created, the ranking could still pick a state R‑Code rule over the structure‑plan rule because structure‑plan rules might not have `applicable_zones` scoped (or they have it, but zone specificity weighting is the same).  The structure‑plan rule would need explicit prioritisation.

---

## Additional edge cases discovered by deep reasoning

*(At least five beyond the above, as required.)*

1. **Split R‑Code parcel**  
   *resolver + engine*  
   The resolver writes multiple `r_code` facts for a parcel with mixed density.  The engine loads rules that match **any** R‑code present.  A rule tagged `applicable_r_codes = ["R80"]` will be applied even if the building is only on the R40 portion.  The engine cannot know which R‑code applies to the specific structure location.

2. **Structure‑plan partial overlap**  
   *Spatial scope filtering*  
   The resolver (if augmented) would create a structure‑plan fact when the parcel’s geometry intersects the plan’s polygon.  The engine then treats the **entire** parcel as covered by that plan.  If only a sliver falls inside the plan area, all structure‑plan rules become active – potentially over‑constraining the rest of the development.

3. **Heritage overlay blocking numeric checks**  
   *Reserved category*  
   The engine doesn’t have special handling for heritage constraints.  If a heritage overlay imposes a height limit of 7 m, that rule would have a numeric threshold and a condition like `heritage = "true"`.  Because `heritage` is not in `_NUMERIC_CONDITION_FACTS` or `_CONDITION_METADATA_KEYS`, the rule would be blocked (`needs_more_info`).  The engine would then fall back to a non‑heritage height rule, allowing a building that violates heritage limits.

4. **Nil threshold with `eq` operator**  
   *Operator evaluation*  
   A rule for minimum lot area may state `value: 0, operator: "eq"` meaning “no minimum”.  The engine correctly parses 0 as threshold, but using `eq` will produce `likely_fail` unless the measured area is exactly 0, which is impossible.  The engine doesn’t recognise that a zero‑threshold with `lte` or `gte` might invert the logic; it simply applies the operator blindly.  This is a `wrong_value` scenario when the rule’s semantics are misinterpreted.

5. **Advisory keyword scoring mis‑weights commercial vs. residential**  
   *Advisory relevance*  
   The scoring adds 6.0 for R‑code mention, but a rule with text “R‑Code density bonuses for commercial development” gets a high score because of `residential` and `dwelling` keywords, pushing it above legitimate residential design rules.  This could bury a critical rule like “street surveillance” below the 80‑item cap.

---

## Verdict: Per‑check confidence for correct rule application

*(Tier‑1 checks only – using the seed definitions plus coverage expansion.)*

| Check                      | Confidence | Reasoning |
|----------------------------|------------|-----------|
| `setback_front`            | **60%**    | Zone specificity missing; dwelling-type ignored. A global R-Code rule could override a local scheme. |
| `setback_rear`             | **60%**    | Same as front; rear setback rules often dwelling-type specific. |
| `setback_side_primary`     | **45%**    | Side-setback rules used for both primary and secondary without distinction; dwelling-type ignored. |
| `setback_side_secondary`   | **45%**    | Same as primary; no distinction between primary/secondary; dwelling-type ignored. |
| `site_cover`               | **55%**    | Zone/precedence hierarchy not respected; global rules override local schemes; dwelling-type ignored. |
| `open_space`               | **55%**    | Zone/precedence hierarchy not respected; categorical conditions ignored; global rules may override. |
| `garage_width_dominance`   | **40%**    | Battle-axe lot frontage heuristic yields wildly incorrect frontage_m; dwelling-type ignored. |
| `boundary_wall_length`     | **50%**    | Zone/precedence hierarchy not respected; side-setback rules conflated; categorical conditions ignored. |
