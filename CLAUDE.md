# DraftCheck WA Core Claude Rules

- Active implementation source: `docs/MASTER_REBUILD_PLAN.md` (single authority for the V3
  rebuild) plus refreshed `REPO_AUDIT.md`, `DATA_INVENTORY.md`, and `VERCEL_AUDIT.md`.
  (`docs/MASTER_IMPLEMENTATION_PLAN.md`, `MASTER_PLAN_ADDENDUM.md`, and
  `docs/PLAN_LOCK_NOTICE.md` are superseded background context.)
- Older planning docs are background context only where they conflict with the active implementation
  source.

## Operator Standing Approval (2026-06-08)

- The operator (Steven) pre-approves all operational and implementation work that follows the
  active implementation source: git commits/pushes, PRs and merges once CI is green, CI changes,
  VPS provisioning and deploys, DNS changes, backups, and infra scripts.
- Do not pause to ask permission or wait for confirmation; decide, act, and log the decision in
  the commit/PR description. Missing credentials → documented fallback, continue, and list the
  one-command unblock in the final report (see `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`).
- Process autonomy only: the legal governance rules below (citations, human signoff in the
  product) are runtime product features and stay as designed.

- Never claim final legal, planning, building, or certification compliance.
- All regulatory outputs must cite approved source versions or explicitly state that the approved source library cannot support the answer.

- Prefer deterministic calculations for measurements. If measurements are absent or ambiguous, return missing information or human review status.

## External Agent Resources

- Agent and workflow references:
  - [affaan-m/ECC](https://github.com/affaan-m/ECC)
  - [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
- Use these supporting tools or patterns for applicable graph, workflow, QA, or agent-output review tasks, provided they do not conflict with the active implementation source:
  - [safishamsi/graphify](https://github.com/safishamsi/graphify)
  - [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
