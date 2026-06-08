from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import ProjectDocument, ResponseDraft, RfiItem, Task
from draftcheck_core.review_queue import ReviewQueueService
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import ReviewQueueItemCreate, RfiItemRead, ResponseDraftRead

LIABILITY_NOTICE = (
    "Draft only. Requires review and approval by the designer or another qualified human before submission."
)


class RfiService:
    def __init__(self, db: Session):
        self.db = db
        self.retrieval = RetrievalService(db)

    def parse_rfi(
        self, project_id: str, *, text: str | None = None, document_id: str | None = None
    ) -> list[RfiItemRead]:
        if document_id:
            doc = self.db.get(ProjectDocument, document_id)
            if not doc or doc.project_id != project_id:
                raise KeyError("RFI document not found")
            source_text = doc.text_content
        else:
            doc = None
            source_text = text or ""
        if not source_text.strip():
            raise ValueError("RFI text or document_id is required")

        requests = _split_requests(source_text)
        parsed: list[RfiItemRead] = []
        existing_by_request = {
            _request_key(item.requested_action): item
            for item in self.db.scalars(select(RfiItem).where(RfiItem.project_id == project_id))
        }
        returned_item_ids: set[str] = set()
        next_item_number = self._next_item_number(project_id)
        for request in requests:
            request_key = _request_key(request)
            existing_item = existing_by_request.get(request_key)
            if existing_item:
                if existing_item.id not in returned_item_ids:
                    parsed.append(_rfi_to_schema(existing_item))
                    returned_item_ids.add(existing_item.id)
                continue
            issue_type = _classify_issue(request)
            citations = self.retrieval.citations_for_supported_answer(f"{issue_type} {request}")
            missing = _missing_evidence(issue_type, request)
            item = RfiItem(
                project_id=project_id,
                source_document_id=doc.id if doc else None,
                item_number=next_item_number,
                issue_summary=request[:180],
                requested_action=request,
                relevant_drawing_sheet=_sheet_ref(request),
                source_requirement_candidates_json=to_json(
                    [citation.model_dump(mode="json") for citation in citations]
                ),
                priority="high" if issue_type in {"bushfire", "setback", "privacy"} else "medium",
                missing_evidence_json=to_json(missing),
            )
            self.db.add(item)
            self.db.flush()
            next_item_number += 1
            existing_by_request[request_key] = item
            returned_item_ids.add(item.id)
            self.db.add(
                Task(
                    project_id=project_id,
                    rfi_item_id=item.id,
                    title=f"Address RFI item {item.item_number}: {issue_type}",
                    description=f"Review drawings and prepare evidence for: {request}",
                    priority=item.priority,
                )
            )
            parsed.append(_rfi_to_schema(item))
        record_audit(
            self.db,
            action="rfi.parsed",
            target_type="rfi_items",
            target_id=project_id,
            project_id=project_id,
            metadata={"item_count": len(parsed), "document_id": document_id},
        )
        return parsed

    def _next_item_number(self, project_id: str) -> int:
        max_item_number = self.db.scalar(
            select(func.max(RfiItem.item_number)).where(RfiItem.project_id == project_id)
        )
        return int(max_item_number or 0) + 1

    def list_items(self, project_id: str) -> list[RfiItemRead]:
        rows = self.db.scalars(
            select(RfiItem).where(RfiItem.project_id == project_id).order_by(RfiItem.item_number)
        ).all()
        return [_rfi_to_schema(row) for row in rows]

    def generate_response(self, project_id: str) -> ResponseDraftRead:
        items = self.list_items(project_id)
        citations = []
        paragraphs = [
            "Dear Assessing Officer,",
            "",
            "Please find below a draft item-by-item response for review. This draft does not assert final compliance and should be checked against the revised drawings before submission.",
        ]
        table: list[dict] = []
        missing: list[str] = []
        for item in items:
            citations.extend(item.source_requirement_candidates)
            missing.extend(item.missing_evidence)
            source_citation_count = len(item.source_requirement_candidates)
            source_support_status = "cited" if source_citation_count else "unsupported"
            if source_support_status == "unsupported":
                missing.append(f"approved source citation for RFI item {item.item_number}")
                source_support_sentence = (
                    f"No approved source citation matched RFI item {item.item_number}; this draft response "
                    "is limited to a drawing/evidence checklist until source support is added."
                )
            else:
                source_support_sentence = (
                    f"RFI item {item.item_number} has {source_citation_count} approved source citation(s); "
                    "the response should be checked against those cited source versions."
                )
            response = (
                f"Item {item.item_number}: The request has been noted. The drawings should be reviewed and "
                f"annotated to address: {item.requested_action}. {source_support_sentence} "
                "Avoid claiming final compliance."
            )
            paragraphs.append(response)
            table.append(
                {
                    "rfi_item_id": item.id,
                    "item_number": item.item_number,
                    "request": item.requested_action,
                    "draft_response": response,
                    "drawing_annotation": f"Add annotation addressing RFI item {item.item_number}.",
                    "missing_evidence": item.missing_evidence,
                    "source_support_status": source_support_status,
                    "source_citation_count": source_citation_count,
                }
            )
        paragraphs.extend(["", "Regards,", "DraftCheck WA Core"])
        draft = ResponseDraft(
            project_id=project_id,
            title="Draft council RFI response",
            draft_text="\n".join(paragraphs),
            content_json=to_json(
                {
                    "response_letter": "\n".join(paragraphs),
                    "item_table": table,
                    "drawing_annotation_checklist": [
                        row["drawing_annotation"] for row in table
                    ],
                    "client_summary": [
                        "Council has requested clarification or changes. Review the listed drawing annotations before resubmission."
                    ],
                    "consultant_request_email": "Please review the attached RFI items and provide any required supporting evidence.",
                }
            ),
            confidence=_draft_confidence(items, citations),
            assumptions_json=to_json(
                [
                    "Response wording is generated from parsed RFI text and approved source candidates where available.",
                    "RFI items without approved source candidates are drafting checklists only, not source-backed responses.",
                ]
            ),
            missing_information_json=to_json(sorted(set(missing))),
            citations_json=to_json([citation.model_dump(mode="json") for citation in citations]),
            requires_human_review=True,
        )
        self.db.add(draft)
        self.db.flush()
        self._enqueue_source_review_items(
            project_id=project_id,
            draft=draft,
            item_table=table,
            missing_information=sorted(set(missing)),
        )
        record_audit(
            self.db,
            action="response_draft.generated",
            target_type="response_draft",
            target_id=draft.id,
            project_id=project_id,
            metadata={"rfi_item_count": len(items), "citation_count": len(citations)},
        )
        return _draft_to_schema(draft)

    def _enqueue_source_review_items(
        self,
        *,
        project_id: str,
        draft: ResponseDraft,
        item_table: list[dict],
        missing_information: list[str],
    ) -> None:
        review_queue = ReviewQueueService(self.db)
        for row in item_table:
            if row.get("source_support_status") != "unsupported":
                continue
            item_number = row["item_number"]
            rfi_item_id = row["rfi_item_id"]
            review_queue.enqueue(
                ReviewQueueItemCreate(
                    queue="source_review",
                    project_id=project_id,
                    target_type="rfi_item",
                    target_id=rfi_item_id,
                    reason=f"RFI item {item_number} lacks approved source support",
                    blocking_level="blocking",
                    evidence={
                        "response_draft_id": draft.id,
                        "rfi_item_id": rfi_item_id,
                        "item_number": item_number,
                        "requested_action": row["request"],
                        "source_support_status": row["source_support_status"],
                        "source_citation_count": row["source_citation_count"],
                        "missing_evidence": row["missing_evidence"],
                        "missing_information": [
                            value
                            for value in missing_information
                            if value in row["missing_evidence"]
                            or value == f"approved source citation for RFI item {item_number}"
                        ],
                    },
                    suggested_action=(
                        "Add or approve an official source citation for this RFI item, or keep the "
                        "response as an unsupported drafting checklist until source support is available."
                    ),
                    priority="high",
                )
            )

    def list_responses(self, project_id: str) -> list[ResponseDraftRead]:
        rows = self.db.scalars(
            select(ResponseDraft)
            .where(ResponseDraft.project_id == project_id)
            .order_by(ResponseDraft.created_at.desc(), ResponseDraft.id.desc())
        ).all()
        return [_draft_to_schema(row) for row in rows]

    def latest_response(self, project_id: str) -> ResponseDraftRead | None:
        row = self.db.scalars(
            select(ResponseDraft)
            .where(ResponseDraft.project_id == project_id)
            .order_by(ResponseDraft.created_at.desc(), ResponseDraft.id.desc())
            .limit(1)
        ).first()
        return _draft_to_schema(row) if row else None


def _split_requests(text: str) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
    candidates: list[str] = []
    buffer = ""
    saw_structured_marker = False
    for line in lines:
        if re.match(r"^(\d+[\).]|item\s+\d+|request\s+\d+)", line, re.IGNORECASE):
            saw_structured_marker = True
            if buffer:
                candidates.append(buffer.strip())
            buffer = re.sub(r"^(\d+[\).]|item\s+\d+|request\s+\d+)[:.)\s-]*", "", line, flags=re.I)
        else:
            buffer = f"{buffer} {line}".strip() if buffer else line
    if buffer:
        candidates.append(buffer.strip())
    if len(candidates) <= 1 and not saw_structured_marker:
        candidates = [
            part.strip()
            for part in re.split(r"(?<=[.?])\s+(?=(?:Please|Could|Provide|Clarify|Confirm|Revise)\b)", text)
            if part.strip()
        ]
    return candidates or [text.strip()]


def _request_key(text: str) -> str:
    return " ".join(text.casefold().split())


def _classify_issue(text: str) -> str:
    lowered = text.lower()
    mapping = {
        "garage": "garage_dominance",
        "surveillance": "street_surveillance",
        "setback": "setback",
        "privacy": "privacy",
        "overshadow": "overshadowing",
        "bushfire": "bushfire",
        "bal": "bushfire",
        "retaining": "retaining_fill",
        "fill": "retaining_fill",
        "open space": "open_space",
        "site cover": "site_cover",
    }
    for needle, issue in mapping.items():
        if needle in lowered:
            return issue
    return "general_planning"


def _missing_evidence(issue_type: str, text: str) -> list[str]:
    missing = ["revised drawing reference"]
    if issue_type in {"setback", "site_cover", "open_space", "garage_dominance"}:
        missing.append("confirmed measurement")
    if "photo" in text.lower():
        missing.append("site photo")
    return missing


def _draft_confidence(items: list[RfiItemRead], citations: list) -> float:
    if not items:
        return 0.0
    if not citations:
        return 0.3
    return 0.55


def _sheet_ref(text: str) -> str | None:
    match = re.search(r"\bA\d{2,3}\b", text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def _rfi_to_schema(row: RfiItem) -> RfiItemRead:
    return RfiItemRead(
        id=row.id,
        item_number=row.item_number,
        issue_summary=row.issue_summary,
        requested_action=row.requested_action,
        relevant_drawing_sheet=row.relevant_drawing_sheet,
        due_date=row.due_date,
        source_requirement_candidates=from_json(row.source_requirement_candidates_json, []),
        priority=row.priority,
        status=row.status,
        missing_evidence=from_json(row.missing_evidence_json, []),
    )


def _draft_to_schema(row: ResponseDraft) -> ResponseDraftRead:
    return ResponseDraftRead(
        id=row.id,
        project_id=row.project_id,
        title=row.title,
        draft_text=row.draft_text,
        content=from_json(row.content_json, {}),
        confidence=row.confidence,
        assumptions=from_json(row.assumptions_json, []),
        missing_information=from_json(row.missing_information_json, []),
        citations=from_json(row.citations_json, []),
        liability_notice=LIABILITY_NOTICE,
        requires_human_review=row.requires_human_review,
        created_at=row.created_at,
    )
