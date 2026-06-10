# LotFile Agent Rules

- Active implementation source: `docs/MASTER_REBUILD_PLAN.md` plus refreshed
  `REPO_AUDIT.md` and `DATA_INVENTORY.md`.
- `docs/MASTER_REBUILD_PLAN.md` is the single implementation authority for the V3
  greenfield rebuild. Older planning docs are background context only where they conflict.

## Operator Standing Approval (2026-06-08)

- The operator (Steven) pre-approves all operational and implementation work that follows
  the active implementation source: git staging/commits/pushes, PRs and merges once CI is
  green, CI changes, VPS provisioning and deploys, DNS changes, backups, and infra scripts.
- Agents do not pause to ask for permission and do not end a turn waiting for confirmation.
  Decide, act, and log the decision in the commit/PR description.
- Missing credentials or access are never a reason to stop: apply the documented fallback,
  finish everything else, and list the one-command unblock in the final report
  (see `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`).
- Production VPS operations use `ssh draftcheck` (`root@76.13.209.160`) from the local
  operator shell. For exact deploy commands and verification, use
  `docs/PRODUCTION_DEPLOYMENT.md`.
- This grants process autonomy only. It does not loosen the product's legal governance
  below (rule approval, automated validation gates, citation requirements), which are runtime product
  features — they gate what the app emits, not what agents may build.

- Build toward one repo, one VPS, one `/api/v1` mount, one PostgreSQL database, one
  Postgres-backed queue, one content-addressed storage tree, one governed Hermes runtime,
  one deterministic compliance engine, and one address-first frontend under `web/`.

- Never claim final legal, planning, building, or certification compliance.
- All regulatory outputs must cite approved source versions or explicitly state that the
  approved source library cannot support the answer.
- LLMs may extract, classify, embed, and draft; they must never decide compliance verdicts.
- No LLM call may run outside the traced, skill-versioned, spend-capped adapter.
- No `likely_pass` or `likely_fail` may be emitted without an approved rule, promoted
  measurement, official citation, and decision trace.
- Prefer deterministic calculations for measurements. If measurements are absent or
  ambiguous, return missing information or operator review status.
- No raster/PDF-derived measurement may be used without explicit calibration.
- Approved rules never silently change; changed sources create new source versions.
- No paid Standards Australia full text may be stored unless lawfully supplied and reviewed.
- No export is submission-ready without automated validation gate.
- Numeric/legal examples in docs are illustrative only; hardcoding them is a defect.
- Alembic is the only schema authority for the new app. `create_all` must not ship in V3.

## External Agent Resources

- Agent and workflow references:
  - [affaan-m/ECC](https://github.com/affaan-m/ECC)
  - [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
- Use these supporting tools or patterns for applicable graph, workflow, QA, or agent-output
  review tasks, provided they do not conflict with `docs/MASTER_REBUILD_PLAN.md`:
  - [safishamsi/graphify](https://github.com/safishamsi/graphify)
  - [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
