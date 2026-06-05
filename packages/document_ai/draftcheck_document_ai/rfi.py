from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import ProjectDocument, ResponseDraft, RfiItem, Task
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import RfiItemRead, ResponseDraftRead

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
        for index, request in enumerate(requests, start=1):
            issue_type = _classify_issue(request)
            citations = self.retrieval.citation_for_check(f"{issue_type} {request}")
            missing = _missing_evidence(issue_type, request)
            item = RfiItem(
                project_id=project_id,
                source_document_id=doc.id if doc else None,
                item_number=index,
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
            self.db.add(
                Task(
                    project_id=project_id,
                    rfi_item_id=item.id,
                    title=f"Address RFI item {index}: {issue_type}",
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
            response = (
                f"Item {item.item_number}: The request has been noted. The drawings should be reviewed and "
                f"annotated to address: {item.requested_action}. Any response should refer to the cited policy "
                "material where relevant and avoid claiming final compliance."
            )
            paragraphs.append(response)
            table.append(
                {
                    "item_number": item.item_number,
                    "request": item.requested_action,
                    "draft_response": response,
                    "drawing_annotation": f"Add annotation addressing RFI item {item.item_number}.",
                    "missing_evidence": item.missing_evidence,
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
            confidence=0.55 if items else 0.0,
            assumptions_json=to_json(["Response wording is generated from parsed RFI text and retrieved citations."]),
            missing_information_json=to_json(sorted(set(missing))),
            citations_json=to_json([citation.model_dump(mode="json") for citation in citations]),
            requires_human_review=True,
        )
        self.db.add(draft)
        self.db.flush()
        record_audit(
            self.db,
            action="response_draft.generated",
            target_type="response_draft",
            target_id=draft.id,
            project_id=project_id,
            metadata={"rfi_item_count": len(items), "citation_count": len(citations)},
        )
        return _draft_to_schema(draft)

    def list_responses(self, project_id: str) -> list[ResponseDraftRead]:
        rows = self.db.scalars(
            select(ResponseDraft)
            .where(ResponseDraft.project_id == project_id)
            .order_by(ResponseDraft.created_at.desc())
        ).all()
        return [_draft_to_schema(row) for row in rows]


def _split_requests(text: str) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
    candidates: list[str] = []
    buffer = ""
    for line in lines:
        if re.match(r"^(\d+[\).]|item\s+\d+|request\s+\d+)", line, re.IGNORECASE):
            if buffer:
                candidates.append(buffer.strip())
            buffer = re.sub(r"^(\d+[\).]|item\s+\d+|request\s+\d+)[:.)\s-]*", "", line, flags=re.I)
        else:
            buffer = f"{buffer} {line}".strip() if buffer else line
    if buffer:
        candidates.append(buffer.strip())
    if len(candidates) <= 1:
        candidates = [
            part.strip()
            for part in re.split(r"(?<=[.?])\s+(?=(?:Please|Could|Provide|Clarify|Confirm|Revise)\b)", text)
            if part.strip()
        ]
    return candidates or [text.strip()]


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
