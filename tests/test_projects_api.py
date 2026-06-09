"""Stage 2 Projects API tests.

Tests the four project endpoints:
  POST /projects                                  → 201
  GET  /projects                                  → 200
  POST /projects/{id}/property/override           → 200 | 403 | 422
  POST /projects/{id}/proposal                    → 200 (idempotent)

Strategy:
  - Patch the SQLite compiler to recognise JSONB (renders it as JSON).
  - Patch the duplicate sha256 index on the Document table so SQLite
    does not blow up on 'index already exists'.
  - Use FastAPI TestClient with dependency overrides for auth.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Boot-time patches — must execute before any SQLAlchemy model import.
# ---------------------------------------------------------------------------

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402

if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

    def _visit_jsonb(self, type_, **kw):  # type: ignore[misc]
        return "JSON"

    SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]

# Now patch the models module to remove the duplicate sha256 index so
# SQLite doesn't complain about 'index ix_documents_sha256 already exists'.
# This must happen before create_all is called.
import draftcheck.db.models as _models_mod  # noqa: E402

for _idx in list(_models_mod.Base.metadata.sorted_tables):
    break  # warm the metadata

# Remove the explicit Table-level ix_documents_sha256 index from metadata
# (the column's index=True auto-generates one with the same name, so there'd
# be a duplicate).  The real PG migration is unaffected.
_to_drop = []
for _tbl in _models_mod.Base.metadata.tables.values():
    if _tbl.name == "documents":
        for _idx in list(_tbl.indexes):
            if _idx.name == "ix_documents_sha256" and len(_idx.columns) == 1:
                _to_drop.append(_idx)
for _idx in _to_drop:
    _idx.table.indexes.discard(_idx)

# ---------------------------------------------------------------------------
# Normal imports
# ---------------------------------------------------------------------------

from datetime import UTC, datetime  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from draftcheck.api.auth import get_current_session  # noqa: E402
from draftcheck.api.projects import get_db_session, router as projects_router  # noqa: E402
from draftcheck.db.models import Base, Project  # noqa: E402
from draftcheck.domain.identity import (  # noqa: E402
    ActiveSession,
    IdentityRole,
    InMemoryIdentityStore,
)

_UTC = UTC


def _utc_now() -> datetime:
    return datetime.now(_UTC)


# ---------------------------------------------------------------------------
# SQLite engine + schema creation (once per process)
# ---------------------------------------------------------------------------

_ENGINE = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
# Only create the four tables our service layer uses — avoids PostGIS spatial
# column types that SQLite cannot parse.
_NEEDED_TABLES = ["orgs", "projects", "properties", "property_facts", "proposals"]
Base.metadata.create_all(
    _ENGINE,
    tables=[Base.metadata.tables[t] for t in _NEEDED_TABLES],
)
_SESSION_FACTORY = sessionmaker(
    bind=_ENGINE,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_active_session(
    store: InMemoryIdentityStore,
    role: IdentityRole = IdentityRole.OWNER,
) -> ActiveSession:
    slug = f"org-{uuid4().hex[:8]}"
    org = store.get_or_create_org(slug=slug)
    user = store.get_or_create_user(org=org, email=f"{role.value}@{slug}.test", role=role)
    issue = store.create_session(user=user, org=org)
    return ActiveSession(session=issue.session, user=issue.user, org=issue.org)


def _make_test_app(
    active_session: ActiveSession,
) -> tuple[FastAPI, Session]:
    """Return (FastAPI test app, open DB Session) backed by the shared SQLite engine.

    Each test uses the SAME in-memory database to avoid re-running create_all.
    Tests are responsible for not conflicting on data (use per-test UUIDs / org slugs).
    """
    db: Session = _SESSION_FACTORY()

    def override_db():
        try:
            yield db
            db.flush()
        except Exception:
            db.rollback()
            raise

    app = FastAPI()
    app.include_router(projects_router, prefix="")
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_session] = lambda: active_session

    return app, db


def _add_project(db: Session, org_id: UUID, name: str = "Test Project") -> Project:
    project = Project(
        org_id=org_id,
        name=name,
        status="draft",
        metadata_json={},
    )
    db.add(project)
    db.flush()
    return project


# ---------------------------------------------------------------------------
# Test: POST /projects creates a project with expected fields
# ---------------------------------------------------------------------------


def test_create_project_returns_201_with_expected_fields() -> None:
    store = InMemoryIdentityStore()
    active = _make_active_session(store)
    app, _ = _make_test_app(active)
    client = TestClient(app)

    response = client.post("/projects", json={"name": "Test Project", "council_scope": "Cockburn"})

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Test Project"
    assert body["council_scope"] == "Cockburn"
    assert body["status"] == "draft"
    assert body["org_id"] == str(active.org.id)
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_create_project_without_council_scope() -> None:
    store = InMemoryIdentityStore()
    active = _make_active_session(store)
    app, _ = _make_test_app(active)
    client = TestClient(app)

    response = client.post("/projects", json={"name": "Minimal Project"})

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Minimal Project"
    assert body["council_scope"] is None


# ---------------------------------------------------------------------------
# Test: POST /projects/{id}/property/override returns 422 for dwelling_type
# ---------------------------------------------------------------------------


def test_override_property_fact_returns_422_for_dwelling_type() -> None:
    store = InMemoryIdentityStore()
    active = _make_active_session(store)
    app, db = _make_test_app(active)
    project = _add_project(db, active.org.id, "Dwelling Type Guard Test")

    client = TestClient(app)
    response = client.post(
        f"/projects/{project.id}/property/override",
        json={
            "fact_type": "dwelling_type",
            "value": "single_house",
            "reason": "This should be rejected",
        },
    )

    assert response.status_code == 422, response.text
    detail = response.json().get("detail", "")
    assert "dwelling_type" in detail.lower() or "proposal" in detail.lower()


# ---------------------------------------------------------------------------
# Test: POST /projects/{id}/proposal is idempotent (two POSTs → same id)
# ---------------------------------------------------------------------------


def test_upsert_proposal_is_idempotent() -> None:
    store = InMemoryIdentityStore()
    active = _make_active_session(store)
    app, db = _make_test_app(active)
    project = _add_project(db, active.org.id, "Idempotent Proposal Test")
    project_id = str(project.id)

    client = TestClient(app)
    payload = {
        "proposal_type": "development_application",
        "dwelling_type": "single_house",
        "work_type": "new_building",
    }

    resp1 = client.post(f"/projects/{project_id}/proposal", json=payload)
    resp2 = client.post(f"/projects/{project_id}/proposal", json=payload)

    assert resp1.status_code == 200, resp1.text
    assert resp2.status_code == 200, resp2.text

    body1 = resp1.json()
    body2 = resp2.json()

    assert body1["id"] == body2["id"], (
        f"Idempotency violation: got {body1['id']} vs {body2['id']}"
    )
    assert body1["project_id"] == project_id
    assert body1["dwelling_type"] == "single_house"
    assert body1["proposal_type"] == "development_application"


# ---------------------------------------------------------------------------
# Test: GET /projects returns the org's projects
# ---------------------------------------------------------------------------


def test_list_projects_returns_created_projects() -> None:
    store = InMemoryIdentityStore()
    active = _make_active_session(store)
    app, db = _make_test_app(active)

    for name in ("Alpha", "Beta"):
        _add_project(db, active.org.id, name)

    client = TestClient(app)
    response = client.get("/projects")

    assert response.status_code == 200, response.text
    names = {p["name"] for p in response.json()}
    assert {"Alpha", "Beta"} <= names


# ---------------------------------------------------------------------------
# Test: POST /projects/{id}/property/override returns 422 for empty reason
# ---------------------------------------------------------------------------


def test_override_property_fact_returns_422_for_empty_reason() -> None:
    store = InMemoryIdentityStore()
    active = _make_active_session(store)
    app, db = _make_test_app(active)
    project = _add_project(db, active.org.id, "Empty Reason Test")

    client = TestClient(app)
    response = client.post(
        f"/projects/{project.id}/property/override",
        json={"fact_type": "zone", "value": "R20", "reason": "   "},
    )

    assert response.status_code == 422, response.text
