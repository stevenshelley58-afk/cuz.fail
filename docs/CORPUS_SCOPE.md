# Corpus Scope — LotFile (CORPUS_COMPLETENESS_PLAN Phase 0)

Date declared: 2026-06-10. Pilot LGA: **City of Cockburn** (M1 council per
`docs/MASTER_REBUILD_PLAN.md`). Every later "is this doc needed?" question is answered by
this file, not by agent opinion. Changes to this file are append-only with a date.

## In scope (acquire full text; category in parentheses)

- **SPP 7.3 Residential Design Codes Volume 1 and Volume 2** (`state_planning_policy`) —
  the primary rule source.
- **All State Planning Policies in force** (SPP 1 … SPP 7.3) plus their published
  guidelines, incl. SPP 3.7 (bushfire) and the Guidelines for Planning in Bushfire Prone
  Areas (`state_planning_policy`).
- **Planning and Development Act 2005** — relevant parts (`act`).
- **Planning and Development (Local Planning Schemes) Regulations 2015** incl. Schedule 2
  deemed provisions, and related subsidiary legislation in force under the P&D Act
  (`regulations`).
- **Pilot-LGA local instruments** for City of Cockburn (`local_planning_scheme`,
  `scheme_map`, `local_planning_policy`, `structure_plan`, `local_development_plan`,
  `local_planning_strategy`): Town Planning Scheme No. 3 text + all scheme maps, every
  adopted Local Planning Policy, approved structure plans, design guidelines.
- **DPLH development control / operational policies** (DC policies, position statements,
  practice notes) (`dc_policy`).
- **National Construction Code** — free ABCB volumes (Vol 1, Vol 2 incl. Livable Housing
  Standard, Vol 3 PCA, referenced free handbooks) (`building_code`). Registration-gated
  content → `metadata_only`.
- **Region schemes** — Metropolitan Region Scheme (text; Cockburn is in the MRS), Peel and
  Greater Bunbury region scheme texts (`region_scheme`).

## Metadata-only / licence-blocked (manifest rows exist; full text never stored)

- **Australian Standards** (AS 3959 etc.) — paid/proprietary; public metadata + access
  note only. Unblock: purchase licence from Standards Australia.
- **Landgate paid cadastre** (LGATE-217/218 attributes) — subscription. Unblock: email
  customerexperience@landgate.wa.gov.au.
- **DPLH bulk planning vectors** (DPLH-070/071/068/023 WFS/bulk) — Government-Use-Only
  pending licence. Unblock: email spatialdata@dplh.wa.gov.au. Display WMS is open.
- **PlanWA / SLIP catalogue spatial layers** (`spatial_layer`) — tracked in the manifest
  as `metadata_only` for cross-check against `spatial_datasets`; actual loads are WP2's
  job, governed by per-dataset licence rows.

## Out of scope (explicit, one line each)

- **Strata Titles Act 1985 / strata schemes** — tenure, not a drafting-check input.
- **Building Act 2011 / building permit process law** — process, not design-rule content;
  NCC carries the technical rules we check.
- **Environmental Protection Act / EPA bulletins** — assessment process beyond
  residential drafting checks.
- **Aboriginal Cultural Heritage Act** — site clearance process, not lot-level design
  rules (heritage *mapping* is in scope as a spatial layer).
- **Non-pilot LGA local instruments** — out of scope until the pilot list expands per
  MASTER_REBUILD_PLAN phases.
- **Council administrative pages** (DAP agendas, project news, "advice" landing pages,
  5G/underground-power notices) — navigation/news, not instruments; kept as
  `source_document` index anchors where already acquired, manifested `out_of_scope` or as
  index anchors with a note.
- **Superseded instrument versions** — manifested `out_of_scope` with note "superseded".
- **Draft/advertised (not yet approved) schemes, amendments, policies** — only
  instruments in force are answer sources.
- **Other states' planning law, Commonwealth law (except NCC)** — WA product.

## Exit gate

This file exists and is committed; `target_manifest` categories map 1:1 to the category
tags above.
