"""LotFile operational CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from functools import partial
import os
from pathlib import Path
import sys
from typing import Any, Sequence, TextIO, cast
from urllib.parse import urlencode, urlparse
from uuid import UUID

import yaml

from draftcheck.config import Settings
from draftcheck.domain.identity import (
    IdentityRole,
    InMemoryIdentityStore,
    InvalidIdentityInputError,
    normalize_role,  # noqa: F401 - re-exported for callers
)
from draftcheck.domain.identity.sqlalchemy_store import SqlAlchemyIdentityStore
from draftcheck.domain.identity.store import DEFAULT_ORG_NAME
from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary


DEFAULT_OWNER_EMAIL = "stevenshelley58@gmail.com"


@dataclass(frozen=True)
class LoginLinkResult:
    url: str
    expires_at: datetime


class _ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, stderr: TextIO | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._stderr = stderr

    def _print_message(self, message: str, file: Any = None) -> None:
        if not message:
            return
        target = self._stderr or file or sys.stderr
        target.write(message)


def _normalize_frontend_url(frontend_url: str) -> str:
    normalized = frontend_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("frontend URL must be an absolute http(s) URL")
    return normalized


def _magic_link_url(frontend_url: str, token: str) -> str:
    query = urlencode({"token": token})
    return f"{_normalize_frontend_url(frontend_url)}/auth/magic-link/verify?{query}"


def issue_login_link(
    *,
    email: str,
    org_slug: str | None = None,
    org_name: str = DEFAULT_ORG_NAME,
    role: IdentityRole | str = IdentityRole.OWNER,
    frontend_url: str | None = None,
    store: InMemoryIdentityStore | None = None,
    settings: Settings | None = None,
) -> LoginLinkResult:
    """Provision a bootstrap identity and issue a single-use magic-link URL."""

    active_settings = settings or Settings.from_env()
    normalized_frontend_url = _normalize_frontend_url(frontend_url or active_settings.frontend_url)
    identity_store = store or _default_identity_store(active_settings)
    normalized_role = normalize_role(role)

    org = identity_store.get_or_create_org(slug=org_slug, name=org_name)
    identity_store.get_or_create_user(org=org, email=email, role=normalized_role)
    issue = identity_store.request_magic_link(
        email=email,
        org_slug=org.slug,
        org_name=org.name,
        user_agent="draftcheck-cli login-link",
    )
    return LoginLinkResult(
        url=_magic_link_url(normalized_frontend_url, issue.token),
        expires_at=issue.record.expires_at,
    )


def _default_identity_store(settings: Settings) -> InMemoryIdentityStore | SqlAlchemyIdentityStore:
    token_hash_pepper = settings.auth_token_hash_pepper or None
    database_url = os.getenv("DATABASE_URL")
    if database_url and os.getenv("DRAFTCHECK_AUTH_STORE", "auto") != "memory":
        return SqlAlchemyIdentityStore.from_database_url(
            database_url,
            token_hash_pepper=token_hash_pepper,
        )
    return InMemoryIdentityStore(token_hash_pepper=token_hash_pepper)


def build_parser(*, stderr: TextIO | None = None) -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="draftcheck",
        description="LotFile operational CLI.",
        stderr=stderr,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=cast(Any, partial(_ArgumentParser, stderr=stderr)),
    )

    login_link = subparsers.add_parser(
        "login-link",
        help="Issue a one-time bootstrap magic-link URL.",
    )
    login_link.add_argument(
        "email",
        nargs="?",
        default=None,
        help="Provisioned operator email address. Defaults to DRAFTCHECK_OWNER_EMAIL.",
    )
    login_link.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug to provision or reuse.",
    )
    login_link.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    login_link.add_argument(
        "--role",
        choices=[role.value for role in IdentityRole],
        default=IdentityRole.OWNER.value,
        help="Identity role to provision for the operator.",
    )
    login_link.add_argument(
        "--frontend-url",
        default=None,
        help="Frontend base URL. Defaults to FRONTEND_URL or local settings.",
    )
    seed_sources = subparsers.add_parser(
        "seed-source-manifest",
        help="Record source manifest anchors into the durable V3 source tables.",
    )
    seed_sources.add_argument(
        "manifest_path",
        nargs="?",
        default="data/seed/source_manifest.example.yaml",
        help="YAML source manifest to seed.",
    )
    seed_sources.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    seed_sources.add_argument(
        "--operator-email",
        default=None,
        help="Provision/reuse this actor to record source fetch log rows.",
    )
    seed_sources.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for fetch log ownership.",
    )
    seed_sources.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    fetch_sources = subparsers.add_parser(
        "fetch-pending-sources",
        help="Lawfully fetch pending public source anchors into pending-review source versions.",
    )
    fetch_sources.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    fetch_sources.add_argument(
        "--source-type",
        default=None,
        help="Optional source type filter, for example scheme_map or local_planning_scheme.",
    )
    fetch_sources.add_argument(
        "--title-contains",
        default=None,
        help="Only fetch pending sources whose title contains this text.",
    )
    fetch_sources.add_argument(
        "--readiness",
        default=None,
        help="Only fetch sources whose current quality readiness matches this value.",
    )
    fetch_sources.add_argument(
        "--max-declared-size-mb",
        type=float,
        default=None,
        help="Skip pending sources whose title declares a larger PDF size.",
    )
    fetch_sources.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of pending source anchors to fetch.",
    )
    fetch_sources.add_argument(
        "--operator-email",
        required=True,
        help="Provision/reuse this actor to own fetch log rows.",
    )
    fetch_sources.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for fetch log ownership.",
    )
    fetch_sources.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    fetch_sources.add_argument(
        "--force",
        action="store_true",
        help="Refetch even when the latest version already has fetched text.",
    )
    repair_sources = subparsers.add_parser(
        "repair-parse-quality-sources",
        help="Create pending-review repaired versions from stored raw source artifacts.",
    )
    repair_sources.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    repair_sources.add_argument(
        "--source-type",
        default=None,
        help="Optional source type filter, for example structure_plan.",
    )
    repair_sources.add_argument(
        "--title-contains",
        default=None,
        help="Only repair sources whose title contains this text.",
    )
    repair_sources.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of repair-ready source versions to process.",
    )
    repair_sources.add_argument(
        "--operator-email",
        required=True,
        help="Provision/reuse this actor to own repair log rows.",
    )
    repair_sources.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for repair log ownership.",
    )
    repair_sources.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    repair_sources.add_argument(
        "--force",
        action="store_true",
        help="Create a repaired version even when repaired text is not longer.",
    )
    repair_sources.add_argument(
        "--ocr",
        action="store_true",
        help="Run bounded OCR from the stored raw PDF instead of text-layer repair.",
    )
    repair_sources.add_argument(
        "--max-ocr-pages",
        type=int,
        default=30,
        help="Maximum pages to OCR per PDF when --ocr is set.",
    )
    repair_sources.add_argument(
        "--ocr-dpi",
        type=int,
        default=200,
        help="Render DPI for OCR repair when --ocr is set.",
    )
    import_corpus = subparsers.add_parser(
        "import-corpus",
        help="Walk a corpus directory and import source files into the durable source tables.",
    )
    import_corpus.add_argument(
        "corpus_dir",
        nargs="?",
        default="data/corpus",
        help="Root directory to walk for corpus files. Defaults to data/corpus.",
    )
    import_corpus.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be imported without writing to the database.",
    )
    label_harvest = subparsers.add_parser(
        "label-harvest",
        help="Seed approved rules, clause dispositions, and golden eval cases from JSONL seed files.",
    )
    label_harvest.add_argument(
        "seeds_dir",
        nargs="?",
        default="evals/seeds",
        help="Directory containing rule_rows.jsonl, clause_dispositions.jsonl, and golden_eval_cases.jsonl. Defaults to evals/seeds.",
    )
    discover_links = subparsers.add_parser(
        "discover-source-links",
        help="Register child source links from fetched public source pages as pending-review fetch targets.",
    )
    discover_links.add_argument(
        "--local-government",
        default=None,
        help="Optional local government filter, for example Cockburn.",
    )
    discover_links.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of discovered child source links to register.",
    )
    discover_links.add_argument(
        "--operator-email",
        required=True,
        help="Provision/reuse this actor to own discovery fetch log rows.",
    )
    discover_links.add_argument(
        "--org-slug",
        default=None,
        help="Organisation slug for discovery log ownership.",
    )
    discover_links.add_argument(
        "--org-name",
        default=DEFAULT_ORG_NAME,
        help="Organisation display name when provisioning a new org.",
    )
    re_embed_parser = subparsers.add_parser(
        "re-embed",
        help="Re-generate embeddings for source chunks using the current embedding model.",
    )
    re_embed_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        metavar="N",
        help="Chunks to process per batch (default: 100)",
    )
    re_embed_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    return parser


def _run_login_link(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
    store: InMemoryIdentityStore | None,
    settings: Settings | None,
) -> int:
    email = args.email or os.getenv("DRAFTCHECK_OWNER_EMAIL") or DEFAULT_OWNER_EMAIL
    try:
        result = issue_login_link(
            email=email,
            org_slug=args.org_slug,
            org_name=args.org_name,
            role=args.role,
            frontend_url=args.frontend_url,
            store=store,
            settings=settings,
        )
    except (InvalidIdentityInputError, PermissionError, ValueError) as exc:
        stderr.write(f"error: {exc}\n")
        return 2

    stdout.write(f"{result.url}\n")
    return 0


def _run_seed_source_manifest(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source seeding\n")
        return 2
    manifest_path = Path(args.manifest_path)
    if not manifest_path.is_file():
        stderr.write(f"error: manifest not found: {manifest_path}\n")
        return 2
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        stderr.write(f"error: invalid source manifest YAML: {exc}\n")
        return 2
    if not isinstance(manifest, dict):
        stderr.write("error: source manifest must be a YAML object\n")
        return 2

    org_id = None
    user_id = None
    if args.operator_email:
        identity_store = SqlAlchemyIdentityStore.from_database_url(database_url)
        org = identity_store.get_or_create_org(slug=args.org_slug, name=args.org_name)
        user = identity_store.get_or_create_user(
            org=org,
            email=args.operator_email,
            role=IdentityRole.OWNER,
        )
        org_id = org.id
        user_id = user.id

    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    try:
        result = source_library.seed_manifest(
            manifest,
            local_government=args.local_government,
            org_id=org_id,
            requested_by_user_id=user_id,
        )
    except ValueError as exc:
        stderr.write(f"error: {exc}\n")
        return 2

    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def _operator_ids(
    *,
    database_url: str,
    email: str,
    org_slug: str | None,
    org_name: str,
) -> tuple[UUID, UUID]:
    identity_store = SqlAlchemyIdentityStore.from_database_url(database_url)
    org = identity_store.get_or_create_org(slug=org_slug, name=org_name)
    user = identity_store.get_or_create_user(
        org=org,
        email=email,
        role=IdentityRole.OWNER,
    )
    return org.id, user.id


def _run_fetch_pending_sources(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source fetching\n")
        return 2
    if args.limit < 1:
        stderr.write("error: --limit must be at least 1\n")
        return 2
    org_id, user_id = _operator_ids(
        database_url=database_url,
        email=args.operator_email,
        org_slug=args.org_slug,
        org_name=args.org_name,
    )
    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    result = source_library.fetch_pending_sources(
        local_government=args.local_government,
        source_type=args.source_type,
        title_contains=args.title_contains,
        readiness=args.readiness,
        max_declared_size_mb=args.max_declared_size_mb,
        limit=args.limit,
        org_id=org_id,
        requested_by_user_id=user_id,
        force=args.force,
    )
    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def _run_repair_parse_quality_sources(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source repair\n")
        return 2
    if args.limit < 1:
        stderr.write("error: --limit must be at least 1\n")
        return 2
    if args.max_ocr_pages < 1:
        stderr.write("error: --max-ocr-pages must be at least 1\n")
        return 2
    if args.ocr_dpi < 100:
        stderr.write("error: --ocr-dpi must be at least 100\n")
        return 2
    org_id, user_id = _operator_ids(
        database_url=database_url,
        email=args.operator_email,
        org_slug=args.org_slug,
        org_name=args.org_name,
    )
    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    result = source_library.repair_parse_quality_sources(
        local_government=args.local_government,
        source_type=args.source_type,
        title_contains=args.title_contains,
        limit=args.limit,
        org_id=org_id,
        requested_by_user_id=user_id,
        force=args.force,
        ocr=args.ocr,
        max_ocr_pages=args.max_ocr_pages,
        ocr_dpi=args.ocr_dpi,
    )
    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def _run_import_corpus(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    import hashlib
    import mimetypes
    from pathlib import Path

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.exists():
        stderr.write(f"error: corpus directory not found: {corpus_dir}\n")
        return 2

    extensions = {".txt", ".pdf", ".docx", ".html", ".htm", ".md"}
    files = [p for p in corpus_dir.rglob("*") if p.suffix.lower() in extensions]
    total = len(files)
    stdout.write(f"Found {total} files in {corpus_dir}\n")

    if args.dry_run:
        for f in files[:10]:
            stdout.write(f"  {f.relative_to(corpus_dir)}\n")
        if total > 10:
            stdout.write(f"  ... and {total - 10} more\n")
        return 0

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for corpus import\n")
        return 2

    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)

    imported = 0
    skipped = 0
    errors = 0

    binary_extensions = {".pdf", ".docx"}

    for i, filepath in enumerate(files):
        try:
            rel = filepath.relative_to(corpus_dir)
            title = filepath.stem.replace("_", " ").replace("-", " ").title()
            publisher = rel.parts[0] if len(rel.parts) > 1 else "unknown"
            uri = f"corpus://{rel.as_posix()}"

            media_type, _ = mimetypes.guess_type(str(filepath))
            media_type = media_type or "application/octet-stream"

            if filepath.suffix.lower() in binary_extensions:
                # Binary files: import as metadata-only — content cannot be stored as text
                source_library.import_source(
                    title=title,
                    content="",
                    uri=uri,
                    publisher=publisher,
                    media_type=media_type,
                    metadata_only=True,
                    source_type="corpus_file",
                    version_metadata={"corpus_path": rel.as_posix()},
                )
            else:
                content = filepath.read_text(encoding="utf-8", errors="replace")
                sha = hashlib.sha256(content.encode()).hexdigest()
                source_library.import_source(
                    title=title,
                    content=content,
                    uri=uri,
                    publisher=publisher,
                    media_type=media_type,
                    source_type="corpus_file",
                    version_metadata={"corpus_path": rel.as_posix(), "sha256": sha},
                )

            imported += 1
        except Exception as exc:
            stderr.write(f"\nWARN [{filepath.name}]: {exc}\n")
            errors += 1

        stdout.write(
            f"\r[{i + 1}/{total}] Imported: {imported}, Skipped: {skipped}, Errors: {errors}   "
        )
        stdout.flush()

    stdout.write(f"\nDone. Imported: {imported}, Skipped: {skipped}, Errors: {errors}\n")
    return 0


def _run_label_harvest(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    import json as _json
    from pathlib import Path

    from sqlalchemy import create_engine
    from sqlalchemy import text as sa_text
    from sqlalchemy.orm import Session

    seeds_dir = Path(args.seeds_dir)
    if not seeds_dir.exists():
        stderr.write(f"error: seeds directory not found: {seeds_dir}\n")
        return 2

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for label harvest\n")
        return 2

    engine = create_engine(database_url)

    rules_imported = 0
    clauses_updated = 0
    evals_imported = 0

    with Session(engine) as session:
        # 1. Import rule_rows.jsonl → rules table with lifecycle_status='approved'
        rule_rows_file = seeds_dir / "rule_rows.jsonl"
        if rule_rows_file.exists():
            with rule_rows_file.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = _json.loads(line)
                    rule_id = row["id"]
                    # condition_text in seeds maps to condition_json in model
                    condition_text = row.get("condition_text", "")
                    condition_json = {"text": condition_text} if condition_text else {}
                    value_json_raw = row.get("value_json", "{}")
                    if isinstance(value_json_raw, str):
                        value_json = _json.loads(value_json_raw)
                    else:
                        value_json = value_json_raw
                    existing = session.execute(
                        sa_text("SELECT id FROM rules WHERE id = CAST(:id AS uuid)"),
                        {"id": rule_id},
                    ).fetchone()
                    if existing:
                        session.execute(
                            sa_text(
                                "UPDATE rules SET "
                                "rule_key = :rule_key, "
                                "operator = :operator, "
                                "value_json = CAST(:value_json AS jsonb), "
                                "unit = :unit, "
                                "condition_json = CAST(:condition_json AS jsonb), "
                                "quote = :quote, "
                                "lifecycle_status = :lifecycle_status, "
                                "updated_at = now() "
                                "WHERE id = CAST(:id AS uuid)"
                            ),
                            {
                                "id": rule_id,
                                "rule_key": row["rule_key"],
                                "operator": row.get("operator"),
                                "value_json": _json.dumps(value_json),
                                "unit": row.get("unit"),
                                "condition_json": _json.dumps(condition_json),
                                "quote": row.get("quote", ""),
                                "lifecycle_status": row.get("lifecycle_status", "approved"),
                            },
                        )
                    else:
                        session.execute(
                            sa_text(
                                "INSERT INTO rules "
                                "(id, source_version_id, clause_id, rule_key, rule_type, pathway, "
                                "lifecycle_status, operator, value_json, unit, condition_json, quote, "
                                "metadata_json, created_at, updated_at) "
                                "VALUES "
                                "(CAST(:id AS uuid), CAST(:source_version_id AS uuid), "
                                "CAST(:clause_id AS uuid), "
                                ":rule_key, :rule_type, :pathway, :lifecycle_status, :operator, "
                                "CAST(:value_json AS jsonb), :unit, CAST(:condition_json AS jsonb), :quote, "
                                "'{}', now(), now())"
                            ),
                            {
                                "id": rule_id,
                                "source_version_id": row["source_version_id"],
                                "clause_id": row["clause_id"],
                                "rule_key": row["rule_key"],
                                "rule_type": row.get("rule_type", "requirement"),
                                "pathway": row.get("pathway", "none"),
                                "lifecycle_status": row.get("lifecycle_status", "approved"),
                                "operator": row.get("operator"),
                                "value_json": _json.dumps(value_json),
                                "unit": row.get("unit"),
                                "condition_json": _json.dumps(condition_json),
                                "quote": row.get("quote", ""),
                            },
                        )
                    rules_imported += 1

        # 2. Update clause dispositions from clause_dispositions.jsonl → clauses table
        clause_file = seeds_dir / "clause_dispositions.jsonl"
        if clause_file.exists():
            with clause_file.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = _json.loads(line)
                    clause_id = row["clause_id"]
                    disposition = row.get("disposition", "manual_review")
                    session.execute(
                        sa_text(
                            "UPDATE clauses SET disposition = :disposition, updated_at = now() "
                            "WHERE id = CAST(:clause_id AS uuid)"
                        ),
                        {"clause_id": clause_id, "disposition": disposition},
                    )
                    clauses_updated += 1

        # 3. Import golden_eval_cases.jsonl → eval_cases table
        eval_file = seeds_dir / "golden_eval_cases.jsonl"
        if eval_file.exists():
            with eval_file.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = _json.loads(line)
                    case_id = row["id"]
                    input_json_raw = row.get("input_json", "{}")
                    if isinstance(input_json_raw, str):
                        input_json = _json.loads(input_json_raw)
                    else:
                        input_json = input_json_raw
                    expected_json_raw = row.get("expected_json", "{}")
                    if isinstance(expected_json_raw, str):
                        expected_json = _json.loads(expected_json_raw)
                    else:
                        expected_json = expected_json_raw
                    # Map JSONL fields to model columns:
                    #   track → suite_name, name → case_key, derive skill_name from track
                    suite_name = row.get("track", "retrieval")
                    case_key = row.get("name", case_id)
                    skill_name = f"check_{suite_name}"
                    status = "active" if row.get("is_active", 1) else "disabled"
                    notes = row.get("notes", "")
                    metadata_json = {
                        "created_by": row.get("created_by", ""),
                        "notes": notes,
                    }
                    existing = session.execute(
                        sa_text(
                            "SELECT id FROM eval_cases WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": case_id},
                    ).fetchone()
                    if existing:
                        session.execute(
                            sa_text(
                                "UPDATE eval_cases SET "
                                "suite_name = :suite_name, "
                                "case_key = :case_key, "
                                "skill_name = :skill_name, "
                                "input_json = CAST(:input_json AS jsonb), "
                                "expected_json = CAST(:expected_json AS jsonb), "
                                "status = :status, "
                                "metadata_json = CAST(:metadata_json AS jsonb), "
                                "updated_at = now() "
                                "WHERE id = CAST(:id AS uuid)"
                            ),
                            {
                                "id": case_id,
                                "suite_name": suite_name,
                                "case_key": case_key,
                                "skill_name": skill_name,
                                "input_json": _json.dumps(input_json),
                                "expected_json": _json.dumps(expected_json),
                                "status": status,
                                "metadata_json": _json.dumps(metadata_json),
                            },
                        )
                    else:
                        session.execute(
                            sa_text(
                                "INSERT INTO eval_cases "
                                "(id, suite_name, case_key, skill_name, "
                                "input_json, expected_json, status, metadata_json, "
                                "created_at, updated_at) "
                                "VALUES "
                                "(CAST(:id AS uuid), :suite_name, :case_key, :skill_name, "
                                "CAST(:input_json AS jsonb), CAST(:expected_json AS jsonb), "
                                ":status, CAST(:metadata_json AS jsonb), now(), now())"
                            ),
                            {
                                "id": case_id,
                                "suite_name": suite_name,
                                "case_key": case_key,
                                "skill_name": skill_name,
                                "input_json": _json.dumps(input_json),
                                "expected_json": _json.dumps(expected_json),
                                "status": status,
                                "metadata_json": _json.dumps(metadata_json),
                            },
                        )
                    evals_imported += 1

        session.commit()

    stdout.write(f"Rules imported: {rules_imported}\n")
    stdout.write(f"Clauses updated: {clauses_updated}\n")
    stdout.write(f"Eval cases imported: {evals_imported}\n")
    return 0


def _run_discover_source_links(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        stderr.write("error: DATABASE_URL is required for durable source discovery\n")
        return 2
    if args.limit < 1:
        stderr.write("error: --limit must be at least 1\n")
        return 2
    org_id, user_id = _operator_ids(
        database_url=database_url,
        email=args.operator_email,
        org_slug=args.org_slug,
        org_name=args.org_name,
    )
    source_library = SqlAlchemySourceLibrary.from_database_url(database_url)
    result = source_library.discover_child_sources(
        local_government=args.local_government,
        limit=args.limit,
        org_id=org_id,
        requested_by_user_id=user_id,
    )
    stdout.write(json.dumps(result, sort_keys=True))
    stdout.write("\n")
    return 0


def _run_re_embed(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Re-embed source chunks that don't match the current embedding model."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        stderr.write("error: DATABASE_URL not set\n")
        return 2

    provider = os.environ.get("DRAFTCHECK_EMBEDDING_PROVIDER", "api")
    model = os.environ.get("DRAFTCHECK_EMBEDDING_MODEL", "text-embedding-3-small")
    dimension = int(os.environ.get("DRAFTCHECK_EMBEDDING_DIMENSION", "1536"))

    engine = create_engine(database_url)
    with Session(engine) as session:
        count_q = text(
            "SELECT COUNT(*) FROM source_chunks "
            "WHERE embedding_provider != :p OR embedding_model != :m"
        )
        total = session.execute(count_q, {"p": provider, "m": model}).scalar() or 0
        stdout.write(f"Chunks needing re-embedding: {total}\n")
        if args.dry_run or total == 0:
            return 0

        from draftcheck.domain.sources.library import (
            _batch_embed,
            default_embedding_config,
        )

        config = default_embedding_config()
        processed = 0
        last_id = None
        while True:
            if last_id is None:
                rows_q = text(
                    "SELECT id, text FROM source_chunks "
                    "WHERE (embedding_provider != :p OR embedding_model != :m) "
                    "ORDER BY id LIMIT :batch"
                )
                rows = session.execute(
                    rows_q, {"p": provider, "m": model, "batch": args.batch_size}
                ).fetchall()
            else:
                rows_q = text(
                    "SELECT id, text FROM source_chunks "
                    "WHERE (embedding_provider != :p OR embedding_model != :m) AND id > :last_id "
                    "ORDER BY id LIMIT :batch"
                )
                rows = session.execute(
                    rows_q,
                    {"p": provider, "m": model, "last_id": last_id, "batch": args.batch_size},
                ).fetchall()
            if not rows:
                break

            texts = [r[1] for r in rows]
            ids = [r[0] for r in rows]
            embeddings = _batch_embed(texts, config)

            for chunk_id, embedding in zip(ids, embeddings):
                update_q = text(
                    "UPDATE source_chunks SET embedding = :emb, "
                    "embedding_provider = :p, embedding_model = :m, embedding_dimension = :d "
                    "WHERE id = :id"
                )
                session.execute(
                    update_q,
                    {
                        "emb": list(embedding),
                        "p": provider,
                        "m": model,
                        "d": dimension,
                        "id": str(chunk_id),
                    },
                )
            session.commit()

            processed += len(rows)
            last_id = str(ids[-1])
            stdout.write(f"\rProcessed {processed}/{total}")
            stdout.flush()

        stdout.write(f"\nDone. Re-embedded {processed} chunks.\n")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    store: InMemoryIdentityStore | None = None,
    settings: Settings | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser(stderr=err)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    if args.command == "login-link":
        return _run_login_link(args, stdout=out, stderr=err, store=store, settings=settings)
    if args.command == "seed-source-manifest":
        return _run_seed_source_manifest(args, stdout=out, stderr=err)
    if args.command == "fetch-pending-sources":
        return _run_fetch_pending_sources(args, stdout=out, stderr=err)
    if args.command == "repair-parse-quality-sources":
        return _run_repair_parse_quality_sources(args, stdout=out, stderr=err)
    if args.command == "discover-source-links":
        return _run_discover_source_links(args, stdout=out, stderr=err)
    if args.command == "import-corpus":
        return _run_import_corpus(args, stdout=out, stderr=err)
    if args.command == "label-harvest":
        return _run_label_harvest(args, stdout=out, stderr=err)
    if args.command == "re-embed":
        return _run_re_embed(args, stdout=out, stderr=err)

    err.write("error: unsupported command\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "LoginLinkResult",
    "build_parser",
    "issue_login_link",
    "main",
]
