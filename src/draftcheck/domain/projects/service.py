"""Projects domain services for Stage 2.

Design invariants (must all hold):
  1. dwelling_type is a PROPOSAL FACT — it belongs in Proposal.dwelling_type only.
     It MUST NOT appear in PropertyFact.fact_type.  override_fact() raises ValueError
     if fact_type == "dwelling_type".
  2. Every PropertyFact override must record provenance (entered_by + reason).
     Missing or empty reason raises ValueError (caller should translate to 422).
  3. advisory: resolution_status values are advisory — "resolved" does NOT mean
     legal proof of anything.
  4. No direct table creation.  Alembic is the sole schema authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.db.models import Project, Property, PropertyFact, Proposal


# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------


@dataclass
class PropertyProfileData:
    """Lightweight view of a project's property facts for API serialisation."""

    project_id: str
    org_id: str
    facts: list[PropertyFact] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ProjectService
# ---------------------------------------------------------------------------


class ProjectService:
    """CRUD for Project rows.

    The caller is responsible for opening, committing, and closing the session.
    This service never opens its own session.
    """

    def create_project(
        self,
        org_id: str,
        name: str,
        council_scope: str | None,
        session: Session,
    ) -> Project:
        """Create a new project in draft status and flush it so the id is available."""
        project = Project(
            org_id=UUID(org_id),
            name=name,
            status="draft",
            metadata_json={"council_scope": council_scope} if council_scope else {},
        )
        session.add(project)
        session.flush()
        return project

    def get_project(
        self,
        project_id: str,
        session: Session,
    ) -> Project | None:
        return session.get(Project, UUID(project_id))

    def list_projects(
        self,
        org_id: str,
        session: Session,
    ) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.org_id == UUID(org_id))
            .order_by(Project.created_at.desc())
        )
        return list(session.scalars(stmt))


# ---------------------------------------------------------------------------
# PropertyService
# ---------------------------------------------------------------------------


class PropertyService:
    """Manages PropertyFact overrides for a project's property."""

    # Fact types that live in the Proposal model, not in PropertyFact.
    # INVARIANT: dwelling_type must NEVER be stored in PropertyFact.
    _PROPOSAL_ONLY_FACT_TYPES: frozenset[str] = frozenset({"dwelling_type"})

    def get_property_profile(
        self,
        project_id: str,
        session: Session,
    ) -> PropertyProfileData:
        """Return all PropertyFacts for a project."""
        project = session.get(Project, UUID(project_id))
        org_id = str(project.org_id) if project else project_id

        stmt = select(PropertyFact).where(
            PropertyFact.project_id == UUID(project_id)
        )
        facts = list(session.scalars(stmt))
        return PropertyProfileData(
            project_id=project_id,
            org_id=org_id,
            facts=facts,
        )

    def override_fact(
        self,
        project_id: str,
        fact_type: str,
        value: Any,
        reason: str,
        entered_by: str | None,
        session: Session,
    ) -> PropertyFact:
        """Create or update a PropertyFact row with method="manual_override".

        INVARIANT 1: dwelling_type is a proposal fact — never a property fact.
        INVARIANT 2: reason must not be empty.
        """
        # Invariant 1 — dwelling_type belongs in Proposal, not PropertyFact.
        if fact_type in self._PROPOSAL_ONLY_FACT_TYPES:
            raise ValueError(
                f"fact_type '{fact_type}' is a proposal fact and cannot be "
                "stored in PropertyFact.  Set dwelling_type on the Proposal "
                "instead via POST /projects/{id}/proposal."
            )

        # Invariant 2 — provenance reason is mandatory.
        if not reason or not reason.strip():
            raise ValueError("reason must not be empty for a manual fact override")

        # Resolve org_id from the project row.
        project = session.get(Project, UUID(project_id))
        if project is None:
            raise ValueError(f"project {project_id!r} not found")
        org_id = project.org_id

        # Resolve property_id if a Property row exists for this project.
        prop_stmt = select(Property).where(Property.project_id == UUID(project_id))
        property_row: Property | None = session.scalars(prop_stmt).first()
        property_id: UUID | None = property_row.id if property_row else None

        provenance = {
            "entered_by": entered_by or "unknown",
            "reason": reason.strip(),
            "method": "manual_override",
        }

        # Try to find an existing manual-override fact of the same type for
        # this project so repeated calls stay idempotent at the fact level.
        existing_stmt = (
            select(PropertyFact)
            .where(
                PropertyFact.project_id == UUID(project_id),
                PropertyFact.fact_type == fact_type,
                PropertyFact.method == "manual_override",
            )
            .order_by(PropertyFact.created_at.desc())
        )
        existing: PropertyFact | None = session.scalars(existing_stmt).first()

        if existing is not None:
            existing.value_json = {"value": value}
            existing.provenance_json = provenance
            existing.review_status = "pending_review"
            session.flush()
            return existing

        fact = PropertyFact(
            id=uuid4(),
            org_id=org_id,
            project_id=UUID(project_id),
            property_id=property_id,
            fact_type=fact_type,
            value_json={"value": value},
            confidence=None,
            method="manual_override",
            provenance_json=provenance,
            review_status="pending_review",
        )
        session.add(fact)
        session.flush()
        return fact


# ---------------------------------------------------------------------------
# ProposalService
# ---------------------------------------------------------------------------


class ProposalService:
    """Idempotent upsert of Proposal rows (one per project)."""

    # Fields accepted from the caller dict; all others are ignored.
    _PROPOSAL_FIELDS: frozenset[str] = frozenset(
        {
            "proposal_type",
            "dwelling_type",
            "building_class",
            "work_type",
            "new_or_existing",
            "lot_type",
            "primary_street_confirmed",
            "secondary_street_confirmed",
            "source",
            "confidence",
        }
    )

    def upsert_proposal(
        self,
        project_id: str,
        data: dict[str, Any],
        session: Session,
    ) -> Proposal:
        """Insert-or-update the single Proposal row for a project.

        Idempotent: repeated calls with identical data return the same row.
        """
        project = session.get(Project, UUID(project_id))
        if project is None:
            raise ValueError(f"project {project_id!r} not found")
        org_id = project.org_id

        stmt = select(Proposal).where(Proposal.project_id == UUID(project_id))
        proposal: Proposal | None = session.scalars(stmt).first()

        if proposal is None:
            proposal = Proposal(
                id=uuid4(),
                org_id=org_id,
                project_id=UUID(project_id),
            )
            session.add(proposal)

        for key in self._PROPOSAL_FIELDS:
            if key in data:
                setattr(proposal, key, data[key])

        session.flush()
        return proposal

    def get_proposal(
        self,
        project_id: str,
        session: Session,
    ) -> Proposal | None:
        stmt = select(Proposal).where(Proposal.project_id == UUID(project_id))
        return session.scalars(stmt).first()
