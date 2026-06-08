from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.rule_audits import RuleAuditService
from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.models import SourceDocument, SourceVersion
from draftcheck_core.review_queue import ReviewQueueService
from draftcheck_core.source_governance import SourceGovernanceService


def main() -> None:
    args = _parse_args()
    init_database()
    with SessionLocal() as db:
        targets = _select_targets(
            db,
            source_version_id=args.source_version_id,
            source_title_contains=args.source_title_contains,
            limit=args.limit,
        )
        if not targets:
            raise SystemExit("No matching source versions found.")
        lines = _build_report(db, targets)

    rendered = "\n".join(lines) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(str(output))
    else:
        print(rendered, end="")


def _select_targets(
    db: Session,
    *,
    source_version_id: str | None,
    source_title_contains: str | None,
    limit: int | None,
) -> list[tuple[SourceDocument, SourceVersion]]:
    if not source_version_id and not source_title_contains:
        raise SystemExit("Select a source with --source-version-id or --source-title-contains.")
    stmt = (
        select(SourceDocument, SourceVersion)
        .join(SourceVersion, SourceVersion.source_document_id == SourceDocument.id)
        .where(SourceVersion.is_superseded.is_(False))
        .order_by(SourceDocument.title, SourceVersion.id)
    )
    if source_version_id:
        stmt = stmt.where(SourceVersion.id == source_version_id)
    if source_title_contains:
        stmt = stmt.where(SourceDocument.title.ilike(f"%{source_title_contains}%"))
    if limit:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).all())


def _build_report(
    db: Session,
    targets: list[tuple[SourceDocument, SourceVersion]],
) -> list[str]:
    lines = ["# Rule Review Worklist", ""]
    governance = SourceGovernanceService(db)
    rules = RuleGovernanceService(db)
    orphan_audits = RuleAuditService(db)
    queue = ReviewQueueService(db)

    for source, version in targets:
        gate = governance.acceptance_gate(source.id, version.id)
        coverage = rules.coverage_audit(source_version_id=version.id, summary_only=True)
        no_orphan = orphan_audits.no_orphan_audit(source_version_id=version.id, summary_only=True)
        rule_rows = rules.list_rule_rows(source_version_id=version.id)
        candidates = rules.list_rule_candidates(source_version_id=version.id)
        open_items = queue.list_items(source_version_id=version.id, status="open")

        label = f" ({version.version_label})" if version.version_label else ""
        lines.extend(
            [
                f"## {source.title}{label}",
                "",
                f"- Source document: `{source.id}`",
                f"- Source version: `{version.id}`",
                f"- Acceptance gate: `{gate.status}`",
                f"- Can support retrieval: `{str(gate.can_support_retrieval).lower()}`",
                f"- Coverage gaps: `{coverage.gap_count}` / `{coverage.total_clauses}` clauses",
                f"- No-orphan blockers: `{no_orphan.blocking_count}`",
                f"- Open source-version review items: `{len(open_items)}`",
                "",
                "### Gate Checks",
                "",
            ]
        )
        for check in gate.checks:
            blocking = " blocking" if check.blocking else ""
            lines.append(f"- `{check.name}`: {check.status}{blocking} - {check.reason}")

        lines.extend(["", "### Coverage Summary", ""])
        for status, count in sorted(coverage.summary.items()):
            lines.append(f"- `{status}`: {count}")
        if not coverage.summary:
            lines.append("- None")

        lines.extend(["", "### No-Orphan Summary", ""])
        for status, count in sorted(no_orphan.summary.items()):
            lines.append(f"- `{status}`: {count}")
        if not no_orphan.summary:
            lines.append("- None")

        lines.extend(["", "### Rule Rows", ""])
        if rule_rows:
            for rule_row in rule_rows:
                quote = rule_row.quote.replace("\n", " ")
                lines.append(
                    f"- `{rule_row.id}` `{rule_row.lifecycle_status}` `{rule_row.rule_key}` "
                    f"{rule_row.value} `{rule_row.unit or ''}` - {quote}"
                )
                if rule_row.condition_text:
                    lines.append(f"  - Condition: {rule_row.condition_text}")
                if rule_row.lifecycle_status == "pending_review":
                    lines.append(
                        "  - Review actions: approve only after source, quote, condition, and rule semantics "
                        "are verified; otherwise reject or revise."
                    )
        else:
            lines.append("- None")

        lines.extend(["", "### Rule Candidates", ""])
        if candidates:
            for candidate in candidates:
                quote = candidate.quote.replace("\n", " ")
                lines.append(
                    f"- `{candidate.id}` `{candidate.status}` `{candidate.rule_key}` "
                    f"{candidate.value} `{candidate.unit or ''}` - {quote}"
                )
                if candidate.condition_text:
                    lines.append(f"  - Condition: {candidate.condition_text}")
                if candidate.status == "candidate":
                    lines.append(
                        "  - Review actions: promote to pending RuleRow, reject, or revise during rule review."
                    )
        else:
            lines.append("- None")

        lines.extend(["", "### Open Review Items", ""])
        if open_items:
            for item in open_items:
                lines.append(
                    f"- `{item.id}` `{item.queue}` `{item.target_type}` `{item.target_id}` - "
                    f"{item.reason}"
                )
                lines.extend(_review_item_detail_lines(item))
        else:
            lines.append("- None")
        lines.append("")
    return lines


def _review_item_detail_lines(item) -> list[str]:
    details: list[str] = []
    if item.suggested_action:
        details.append(f"  - Suggested action: {item.suggested_action}")
    evidence = item.evidence
    audit = evidence.get("audit")
    status = evidence.get("status")
    if audit or status:
        details.append(f"  - Audit: `{audit or 'unknown'}` / `{status or 'unknown'}`")
    quote = evidence.get("quote")
    if isinstance(quote, str) and quote.strip():
        details.append(f"  - Evidence quote: {_compact_text(quote)}")
    nested_evidence = evidence.get("evidence")
    if isinstance(nested_evidence, dict):
        tokens = nested_evidence.get("tokens")
        if isinstance(tokens, list) and tokens:
            details.append(f"  - Tokens: {', '.join(str(token) for token in tokens)}")
        terms = nested_evidence.get("terms")
        if isinstance(terms, list) and terms:
            details.append(f"  - Terms: {', '.join(str(term) for term in terms)}")
        candidate_ids = nested_evidence.get("rule_candidate_ids")
        if isinstance(candidate_ids, list) and candidate_ids:
            details.append(f"  - Candidate IDs: {', '.join(str(candidate_id) for candidate_id in candidate_ids)}")
        rule_row_ids = nested_evidence.get("rule_row_ids")
        if isinstance(rule_row_ids, list) and rule_row_ids:
            details.append(f"  - Rule row IDs: {', '.join(str(rule_row_id) for rule_row_id in rule_row_ids)}")
    candidate_ids = evidence.get("rule_candidate_ids")
    if isinstance(candidate_ids, list) and candidate_ids:
        details.append(f"  - Candidate IDs: {', '.join(str(candidate_id) for candidate_id in candidate_ids)}")
    return details


def _compact_text(value: str, *, limit: int = 280) -> str:
    compacted = " ".join(value.split())
    if len(compacted) <= limit:
        return compacted
    return f"{compacted[: limit - 3].rstrip()}..."


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render source-version rule review worklists.")
    parser.add_argument("--source-version-id")
    parser.add_argument("--source-title-contains")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output")
    return parser.parse_args()


if __name__ == "__main__":
    main()
