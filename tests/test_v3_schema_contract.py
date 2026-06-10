from __future__ import annotations

from pathlib import Path

from sqlalchemy import Enum as SqlAlchemyEnum

from draftcheck.db.models import Base, IdentityRole


def test_v3_identity_schema_contract() -> None:
    tables = Base.metadata.tables

    assert {"orgs", "users", "sessions", "magic_link_tokens"} <= set(tables)
    role_type = tables["users"].c.role.type
    assert isinstance(role_type, SqlAlchemyEnum)
    assert set(role_type.enums) == {
        IdentityRole.OWNER.value,
        IdentityRole.OPERATOR.value,
        IdentityRole.COMPLIANCE_OWNER.value,
        IdentityRole.GUEST.value,
    }

    for table_name in ("users", "sessions", "magic_link_tokens"):
        table = tables[table_name]
        assert "org_id" in table.c
        assert table.c.org_id.foreign_keys

    for table_name in ("sessions", "magic_link_tokens"):
        table = tables[table_name]
        assert "token_hash" in table.c
        assert "token" not in table.c
        assert table.c.token_hash.unique


def test_v3_source_code_does_not_call_create_all() -> None:
    """PR0 contract: V3 schema is owned by Alembic.

    The pre-2026-06-10 implementation scanned src/ for the bare string
    ``create_all`` and rejected any file that mentioned it, even in
    docstrings. That false-positive broke every PR that documented the
    rule. The check now matches a real call pattern instead.
    """
    import re

    src_root = Path(__file__).resolve().parents[1] / "src" / "draftcheck"
    pattern = re.compile(r"(?<![\w\.])create_all\s*\(")
    offenders = [
        path
        for path in src_root.rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []
